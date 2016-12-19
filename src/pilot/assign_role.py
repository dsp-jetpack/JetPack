#!/usr/bin/python

# Copyright (c) 2016 Dell Inc. or its subsidiaries.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import argparse
from collections import namedtuple
import json
import logging
import os
import sys

from dracclient import utils
from dracclient.constants import POWER_OFF
from dracclient.exceptions import DRACOperationFailed, \
    DRACUnexpectedReturnValue, WSManInvalidResponse, WSManRequestFailure
from oslo_utils import units
from credential_helper import CredentialHelper
from ironic_helper import IronicHelper
from job_helper import JobHelper
from logging_helper import LoggingHelper
import requests

discover_nodes_path = os.path.join(os.path.expanduser('~'),
                                   'pilot/discover_nodes')
sys.path.append(discover_nodes_path)

from discover_nodes.dracclient.client import DRACClient  # noqa

requests.packages.urllib3.disable_warnings()

# Perform basic configuration of the logging system, which configures the root
# logger. It creates a StreamHandler with a default Formatter and adds it to
# the root logger. Log messages are directed to stderr. This configuration
# applies to the log messages emitted by this script and the modules in the
# packages it uses, such as ironicclient and dracclient.
#
# Notably, the effective logging levels of this module and the packages it uses
# are configured to be different. The packages' is WARNING, because theirs is
# obtained from their ancestor, the root logger. This script's is INFO by
# default. That can be changed by an optional command-line argument.
logging.basicConfig()

# Create this script's logger. Give it a more friendly name than __main__.
LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])

# Create a factory function for creating tuple-like objects that contain the
# role that the node will play and an optional index that indicates placement
# order in the rack.
#
# The article
# http://stackoverflow.com/questions/35988/c-like-structures-in-python
# describes the use of collections.namedtuple to implement C-like structures in
# Python.
RoleIndex = namedtuple('RoleIndex', ['role', 'index', ])

DCIM_VirtualDiskView = ('http://schemas.dell.com/wbem/wscim/1/cim-schema/2/'
                        'DCIM_VirtualDiskView')
DCIM_PhysicalDiskView = ('http://schemas.dell.com/wbem/wscim/1/cim-schema/2/'
                         'DCIM_PhysicalDiskView')

RAID1 = "4"

ROLES = {
    'controller': 'control',
    'compute': 'compute',
    'storage': 'ceph-storage'
}

# TODO: Use the OpenStack Oslo logging library, instead of the Python standard
#       library logging facility.
#
#       This would have value if this code is contributed to ironic upstream
#       and ironic is using the Oslo logging library.


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Assigns role to Overcloud node.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("ip_mac_service_tag",
                        help="""IP address of the iDRAC, MAC address of the
                                interface on the provisioning network,
                                or service tag of the node""",
                        metavar="ADDRESS")
    parser.add_argument("role_index",
                        type=role_index,
                        help="""role that the node will play, with an optional
                                index that indicates placement order in the
                                rack; choices are controller[-<index>],
                                compute[-<index>], and storage[-<index>]""",
                        metavar="ROLE")
    parser.add_argument("-f",
                        "--flavor-settings",
                        default="~/pilot/flavors_settings.json",
                        help="file that contains flavor settings",
                        metavar="FILENAME")
    parser.add_argument("-n",
                        "--node-definition",
                        default="~/instackenv.json",
                        help="""node definition template file that defines the
                                node being assigned""",
                        metavar="FILENAME")
    LoggingHelper.add_argument(parser)

    return parser.parse_args()


def role_index(string):
    role = string
    index = None

    if string.find("-") != -1:
        role_tokens = role.split("-")
        role = role_tokens[0]
        index = role_tokens[1]

    if role not in ROLES.keys():
        raise argparse.ArgumentTypeError(
            "{} is not a valid role; choices are {}".format(
                role, str(
                    ROLES.keys())))

    if index and not index.isdigit():
        raise argparse.ArgumentTypeError(
            "{} is not a valid role index; it must be a number".format(index))

    return RoleIndex(role, index)


def get_flavor_settings(json_filename):
    flavor_settings = None

    try:
        with open(json_filename, 'r') as f:
            try:
                flavor_settings = json.load(f)
            except ValueError:
                LOG.exception(
                    "Could not deserialize flavor settings file {}".format(
                        json_filename))
    except IOError:
        LOG.exception(
            "Could not open flavor settings file {}".format(json_filename))

    return flavor_settings


def calculate_bios_settings(role, flavor_settings, json_filename):
    return calculate_category_settings_for_role(
        'bios',
        role,
        flavor_settings,
        json_filename)


def calculate_category_settings_for_role(
        category,
        role,
        flavor_settings,
        json_filename):
    default = {}

    if 'default' in flavor_settings and category in flavor_settings['default']:
        default = flavor_settings['default'][category]

    flavor = ROLES[role]
    flavor_specific = {}

    if flavor in flavor_settings and category in flavor_settings[flavor]:
        flavor_specific = flavor_settings[flavor][category]

    # Flavor-specific settings take precedence over default settings.
    category_settings = merge_two_dicts(default, flavor_specific)

    if not category_settings:
        LOG.critical(
            'File {} does not contain "{}" settings for flavor "{}"'.format(
                json_filename,
                category,
                flavor))
        return None

    return category_settings


def merge_two_dicts(x, y):
    z = x.copy()
    z.update(y)
    return z


def get_drac_client(node_definition_filename, node):
    drac_ip, drac_user, drac_password = \
        CredentialHelper.get_drac_creds_from_node(node,
                                                  node_definition_filename)
    drac_client = DRACClient(drac_ip, drac_user, drac_password)
    # TODO: Validate the IP address is an iDRAC.
    #
    #       This could detect an error by an off-roading user who provided an
    #       incorrect IP address for the iDRAC.
    #
    #       A to be developed dracclient API should be used to perform the
    #       validation.

    return drac_client


def assign_role(ip_mac_service_tag, node_uuid, role_index, ironic_client,
                drac_client):
    flavor = ROLES[role_index.role]

    LOG.info(
        "Setting role for {} to {}, flavor {}".format(
            ip_mac_service_tag,
            role_index.role,
            flavor))

    role = "profile:{}".format(flavor)

    if role_index.index:
        role = "node:{}-{}".format(flavor, role_index.index)

    value = "{},boot_option:local".format(role)

    patch = [{'op': 'add',
              'value': value,
              'path': '/properties/capabilities'}]
    ironic_client.node.update(node_uuid, patch)

    # Are we assigning the storage role to this node?
    if role_index.role == "storage":
        # Select the disk for the OS to be installed on.  Note that this is
        # only necessary for storage nodes because the other node types are
        # configured to have 1 huge volume created by the DTK.
        select_os_disk(ironic_client, drac_client.client, node_uuid)


def get_fqdd(doc, namespace):
    return utils.find_xml(doc, 'FQDD', namespace).text


def get_size_in_bytes(doc, namespace):
    return utils.find_xml(doc, 'SizeInBytes', namespace).text


def select_os_disk(ironic_client, drac_client, node_uuid):
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

            LOG.debug(
                "Found RAID 1 virtual disk {} with a size of {} bytes "
                "comprised of physical disks:\n  {}".format(
                    fqdd,
                    raid1_size,
                    "\n  ".join(raid1_physical_disk_ids)))

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
                LOG.debug(
                    "Physical disk {} has the same size ({}) as the RAID "
                    "1".format(
                        fqdd,
                        physical_disk_size))
                found_same_size_disk = True
                break

    # If we did find a disk that's the same size, then passing a disk
    # size to ironic is pointless, so let whatever happens, happen
    if not found_same_size_disk:
        # Otherwise...
        raid1_size_gb = int(raid1_size) / units.Gi

        # Set the root_device property in ironic to the RAID 1 size in
        # gigs
        LOG.info(
            "Setting the OS disk for this node to the virtual disk with size "
            "{} GB".format(raid1_size_gb))
        patch = [{'op': 'add',
                  'value': {"size": raid1_size_gb},
                  'path': '/properties/root_device'}]
        ironic_client.node.update(node_uuid, patch)


def configure_bios(node, ironic_client, settings, drac_client):
    LOG.info("Configuring BIOS")

    if 'drac' not in node.driver:
        LOG.critical("Node is not being managed by an iDRAC driver")
        return False

    # Filter out settings that are unknown.
    response = ironic_client.node.vendor_passthru(
        node.uuid,
        'get_bios_config',
        http_method='GET')

    unknown_attribs = set(settings).difference(response.__dict__)

    if unknown_attribs:
        LOG.warning(
            "Disregarding unknown BIOS settings {}".format(
                ', '.join(unknown_attribs)))

        for attr in unknown_attribs:
            del settings[attr]

    response = ironic_client.node.vendor_passthru(
        node.uuid,
        'set_bios_config',
        args=settings,
        http_method='POST')

    if not response.commit_required:
        LOG.info("Completed BIOS configuration")
        return True

    LOG.info("Rebooting the node to apply BIOS configuration")
    args = {'reboot': True}
    response = ironic_client.node.vendor_passthru(
        node.uuid,
        'commit_bios_config',
        args=args,
        http_method='POST')

    LOG.info(
        "Waiting for BIOS configuration to complete; this may take some time")
    LOG.info("Do not power off the node")
    job_ids = [response.job_id]
    JobHelper.wait_for_job_completions(ironic_client, node.uuid)
    LOG.info("Completed BIOS configuration")

    return JobHelper.determine_job_outcomes(drac_client, job_ids)


def ensure_node_is_powered_off(drac_client):
    # Power off the node only if it is not already powered off. The Dell Common
    # Information Model Extensions (DCIM) method used to power off a node is
    # not idempotent.
    #
    # Testing found that attempting to power off a node while it is powered off
    # raises an exception, DRACOperationFailed with the message 'The command
    # failed to set RequestedState'. That message is associated with a message
    # ID output parameter of the DCIM_ComputerSystem.RequestStateChange()
    # method. The message ID is SYS021. This is documented in the Base Server
    # and Physical Asset Profile, Version 1.2.0
    # (http://en.community.dell.com/techcenter/extras/m/white_papers/20440458/download).
    # See section 8.1 DCIM_ComputerSystem.RequestStateChange(), beginning on p.
    # 22 of 25.
    #
    # An alternative approach was considered, unconditionally powering off the
    # node, catching the DRACOperationFailed exception, and ignoring it.
    # However, because neither the documentation nor exception provides details
    # about the cause, that approach could mask an interesting error condition.
    if drac_client.get_power_state() is not POWER_OFF:
        LOG.info("Powering off the node")
        drac_client.set_power_state(POWER_OFF)


def main():

    try:
        drac_client = None

        args = parse_arguments()

        LOG.setLevel(args.logging_level)

        flavor_settings_filename = os.path.expanduser(args.flavor_settings)
        flavor_settings = get_flavor_settings(flavor_settings_filename)

        if flavor_settings is None:
            sys.exit(1)

        bios_settings = calculate_bios_settings(
            args.role_index.role,
            flavor_settings,
            flavor_settings_filename)

        if bios_settings is None:
            sys.exit(1)

        ironic_client = IronicHelper.get_ironic_client()

        node = IronicHelper.get_ironic_node(ironic_client,
                                            args.ip_mac_service_tag)
        if node is None:
            LOG.critical("Unable to find node {}".format(
                         args.ip_mac_service_tag))
            sys.exit(1)

        drac_client = get_drac_client(args.node_definition, node)

        assign_role(
            args.ip_mac_service_tag,
            node.uuid,
            args.role_index,
            ironic_client,
            drac_client)

        succeeded = configure_bios(
            node,
            ironic_client,
            bios_settings,
            drac_client)

        if not succeeded:
            sys.exit(1)
    except (DRACOperationFailed, DRACUnexpectedReturnValue,
            InternalServerError, KeyError, TypeError, ValueError,
            WSManInvalidResponse, WSManRequestFailure):
        LOG.exception("")
        sys.exit(1)
    except SystemExit:
        raise
    except:  # Catch all exceptions.
        LOG.exception("Unexpected error")
        raise
    finally:
        # Leave the node powered off.
        if drac_client is not None:
            ensure_node_is_powered_off(drac_client)


if __name__ == "__main__":
    main()
