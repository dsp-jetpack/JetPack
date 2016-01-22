#!/usr/bin/python

import argparse
import json
import os
import sys

import lxml
from lxml import etree as ElementTree
import ironicclient
from dracclient import wsman, utils
from subprocess import check_output
from oslo_utils import units
import requests


requests.packages.urllib3.disable_warnings()

DCIM_SystemView = ('http://schemas.dell.com/wbem/wscim/1/cim-schema/2/'
                   'DCIM_SystemView')
DCIM_VirtualDiskView = ('http://schemas.dell.com/wbem/wscim/1/cim-schema/2/'
                        'DCIM_VirtualDiskView')
DCIM_PhysicalDiskView = ('http://schemas.dell.com/wbem/wscim/1/cim-schema/2/'
                         'DCIM_PhysicalDiskView')

RAID1 = "4"


def get_openstack_creds():
    creds_file = open(os.environ['HOME'] + '/stackrc', 'r')

    for line in creds_file:
        prefix = "export"
        if line.startswith(prefix):
            line = line[len(prefix):]

        line = line.strip()
        key, val = line.split('=', 2)
        key = key.lower()

        if key == 'os_username':
            os_username = val
        elif key == 'os_auth_url':
            os_auth_url = val
        elif key == 'os_tenant_name':
            os_tenant_name = val

    os_password = check_output(['sudo', 'hiera', 'admin_password']).strip()

    return os_auth_url, os_tenant_name, os_username, os_password


def get_drac_creds(ironic_client, node_uuid):
    # Get the DRAC IP, username, and password
    node = ironic_client.node.get(node_uuid, ["driver_info"])
    driver_info = node.driver_info

    if "drac_host" in driver_info:
        drac_ip = driver_info["drac_host"]
        drac_user = driver_info["drac_username"]
    else:
        drac_ip = driver_info["ipmi_address"]
        drac_user = driver_info["ipmi_username"]

    # Can't get the password out of ironic, so dig it out of the
    # instackenv.json file
    drac_password = get_drac_password(drac_ip)

    return drac_ip, drac_user, drac_password


def get_drac_password(ip):
    instackenv_file = open(os.environ['HOME'] + '/instackenv.json', 'r')
    instackenv = json.load(instackenv_file)

    nodes = instackenv["nodes"]

    for node in nodes:
        if node["pm_addr"] == ip:
            return node["pm_password"]


def get_fqdd(doc, namespace):
    return utils.find_xml(doc, 'FQDD', namespace).text


def get_size_in_bytes(doc, namespace):
    return utils.find_xml(doc, 'SizeInBytes', namespace).text


def handle_r730xd_flex_bays(ironic_client, drac_client, node_uuid, debug):
    # Get the virtual disks
    virtual_disk_view_doc = drac_client.enumerate(DCIM_VirtualDiskView)
    virtual_disk_docs = utils.find_xml(virtual_disk_view_doc,
                                       'DCIM_VirtualDiskView',
                                       DCIM_VirtualDiskView,
                                       True)

    # Find the RAID 1 that the DTK created
    for virtual_disk_doc in virtual_disk_docs:
        fqdd = get_fqdd(virtual_disk_doc, DCIM_VirtualDiskView)
        raid_type = utils.find_xml(virtual_disk_doc, 'RAIDTypes',
                                   DCIM_VirtualDiskView).text

        if raid_type == RAID1:
            # Get the size
            raid1_size = get_size_in_bytes(virtual_disk_doc,
                                           DCIM_VirtualDiskView)

            # Get the physical disks that back this RAID 1
            raid1_physical_disk_docs = utils.find_xml(virtual_disk_doc,
                                                      'PhysicalDiskIDs',
                                                      DCIM_VirtualDiskView,
                                                      True)
            raid1_physical_disk_ids = []
            for raid1_physical_disk_doc in raid1_physical_disk_docs:
                raid1_physical_disk_id = raid1_physical_disk_doc.text
                raid1_physical_disk_ids.append(raid1_physical_disk_id)

            if debug:
                print ("Found RAID 1 virtual disk {} with a size of {} "
                       "bytes comprised of physical disks:".format(
                           fqdd, raid1_size))
                for p_d_id in raid1_physical_disk_ids:
                    print "  {}".format(p_d_id)

            break

    # Now check to see if we have any physical disks that don't back
    # the RAID that are the same size as the RAID

    # Get the physical disks
    physical_disk_view_doc = drac_client.enumerate(
        DCIM_PhysicalDiskView)
    physical_disk_docs = utils.find_xml(physical_disk_view_doc,
                                        'DCIM_PhysicalDiskView',
                                        DCIM_PhysicalDiskView,
                                        True)

    found_same_size_disk = False
    for physical_disk_doc in physical_disk_docs:
        fqdd = get_fqdd(physical_disk_doc, DCIM_PhysicalDiskView)
        if fqdd not in raid1_physical_disk_ids:
            physical_disk_size = get_size_in_bytes(
                physical_disk_doc, DCIM_PhysicalDiskView)

            if physical_disk_size == raid1_size:
                if debug:
                    print ("Physical disk {} has the same size ({}) "
                           "as the RAID 1".format(fqdd, physical_disk_size))
                found_same_size_disk = True
                break

    # If we did find a disk that's the same size, then passing a disk
    # size to ironic is pointless, so let whatever happens, happen
    if not found_same_size_disk:
        # Otherwise...
        raid1_size_gb = int(raid1_size) / units.Gi

        # Set the root_device property in ironic to the RAID 1 size in
        # gigs
        print ("Setting the OS disk for this node to the virtual disk "
               "with size {} GB".format(raid1_size_gb))
        patch = [{'op': 'add',
                  'value': {"size": raid1_size_gb},
                  'path': '/properties/root_device'}]
        node = ironic_client.node.update(node_uuid, patch)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("mac", help="The MAC address of the node")
    parser.add_argument("role",
                        choices=["controller", "compute", "storage"],
                        help="The role that the node will play")
    parser.add_argument("--debug", action='store_true', default=False)
    args = parser.parse_args()

    os_auth_url, os_tenant_name, os_username, os_password = \
        get_openstack_creds()

    # Get the UUID of the node
    kwargs = {'os_username': os_username,
              'os_password': os_password,
              'os_auth_url': os_auth_url,
              'os_tenant_name': os_tenant_name}
    ironic_client = ironicclient.client.get_client(1, **kwargs)

    port = ironic_client.port.get_by_address(args.mac)
    node_uuid = port.node_uuid

    # Assign the role to the node
    print "Setting role for {} to {}".format(args.mac, args.role)
    patch = [{'op': 'add',
              'value': "profile:{},boot_option:local".format(args.role),
              'path': '/properties/capabilities'}]
    node = ironic_client.node.update(node_uuid, patch)

    # Are we assigning the storage role to this node?
    if args.role == "storage":
        # Get the DRAC IP, username, and password
        drac_ip, drac_user, drac_password = get_drac_creds(ironic_client,
                                                           node_uuid)

        # Get the model of the server from the DRAC
        drac_client = wsman.Client(drac_ip, drac_user, drac_password)
        doc = drac_client.enumerate(DCIM_SystemView)
        model = utils.find_xml(doc, 'Model', DCIM_SystemView).text

        if model == "PowerEdge R730xd":
            handle_r730xd_flex_bays(ironic_client, drac_client, node_uuid,
                                    args.debug)


if __name__ == "__main__":
    main()
