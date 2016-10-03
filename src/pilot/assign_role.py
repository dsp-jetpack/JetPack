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
from time import sleep

import ironicclient
from dracclient import utils
from dracclient.constants import POWER_OFF
from dracclient.exceptions import DRACOperationFailed, \
    DRACUnexpectedReturnValue, WSManInvalidResponse, WSManRequestFailure
from oslo_utils import units
from credential_helper import CredentialHelper
from ironic_helper import IronicHelper
from logging_helper import LoggingHelper
import network_helper
import requests
try:  # OSP8
    from ironicclient.openstack.common.apiclient.exceptions import NotFound
except ImportError:  # OSP9
    from ironicclient.common.apiclient.exceptions import InternalServerError, \
        NotFound

discover_nodes_path = os.path.join(os.path.expanduser('~'),
                                   'pilot/discover_nodes')
sys.path.append(discover_nodes_path)

from discover_nodes.dracclient.client import DRACClient # noqa

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
                        help="""IP address of the iDRAC, or MAC address of the
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
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-p",
                       "--pxe-nic",
                       help="""fully qualified device descriptor (FQDD) of
                               network interface to PXE boot from""",
                       metavar="FQDD")
    group.add_argument("-m",
                       "--model-properties",
                       default="~/pilot/dell_systems.json",
                       help="""file that defines Dell system model properties,
                               including FQDD of network interface to PXE boot
                               from""",
                       metavar="FILENAME")
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


def get_model_properties(fqdd, json_filename):
    # Explicitly specifying the network interface controller (NIC) fully
    # qualified device descriptor (FQDD) takes precedence over determining the
    # PXE NIC by the node's system model.
    if fqdd is not None:
        return None

    model_properties = None
    expanded_filename = os.path.expanduser(json_filename)

    try:
        with open(expanded_filename, 'r') as f:
            try:
                model_properties = json.load(f)
            except ValueError:
                LOG.exception(
                    "Could not deserialize model properties file {}".format(
                        expanded_filename))
    except IOError:
        LOG.exception(
            "Could not open model properties file {}".format(
                expanded_filename))

    return model_properties


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


def get_pxe_nic_fqdd(fqdd, model_properties, drac_client):
    # Explicitly specifying the network interface controller (NIC) fully
    # qualified device descriptor (FQDD) takes precedence over determining the
    # PXE NIC by the node's system model.
    if fqdd is None:
        pxe_nic_fqdd = get_pxe_nic_fqdd_from_model_properties(
            model_properties,
            drac_client)
    else:
        pxe_nic_fqdd = fqdd

    # Ensure the identified PXE NIC FQDD exists in the system.

    nic_fqdds = [nic.id for nic in drac_client.list_nics(sort=True)]

    if pxe_nic_fqdd not in nic_fqdds:
        LOG.critical(
            "NIC to PXE boot from, {}, does not exist; available NICs are "
            "{}".format(
                pxe_nic_fqdd,
                ', '.join(nic_fqdds)))
        return None

    return pxe_nic_fqdd


def get_pxe_nic_fqdd_from_model_properties(model_properties, drac_client):
    if model_properties is None:
        return None

    model_name = drac_client.get_system_model_name()

    # If the model does not have an entry in the model properties JSON file,
    # return None, instead of raising a KeyError exception.
    if model_name in model_properties:
        return model_properties[model_name]['pxe_nic']
    else:
        return None


def assign_role(ip_mac_service_tag, node_uuid, role_index, ironic_client,
                drac_client):
    flavor = ROLES[role_index.role]

    LOG.info(
        "Setting role for {} to {}, flavor {}".format(
            ip_mac_service_tag,
            role_index.role,
            flavor))

    value = "profile:{},boot_option:local".format(flavor)

    if role_index.index:
        value = "node:{}-{},{}".format(flavor, role_index.index, value)

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


def configure_nics_boot_settings(drac_client, pxe_nic_id):
    LOG.info("Configuring NIC {} to PXE boot".format(pxe_nic_id))

    job_ids = []
    reboot_required = False

    for nic_id in [nic.id for nic in drac_client.list_nics(sort=True)]:
        result = None

        # Compare the NIC IDs case insensitively. Assume ASCII strings.
        if nic_id.lower() == pxe_nic_id.lower():
            if not drac_client.is_nic_legacy_boot_protocol_pxe(nic_id):
                result = drac_client.set_nic_legacy_boot_protocol_pxe(nic_id)
        else:
            if not drac_client.is_nic_legacy_boot_protocol_none(nic_id):
                result = drac_client.set_nic_legacy_boot_protocol_none(nic_id)

        if result is None:
            continue

        # TODO: Untangle the separate requirements for a configuration job and/
        #       or reboot after setting a NIC attribute via discover_nodes's
        #       dracclient.
        #
        #       Refer to the Dell Simple NIC Profile. Its discussions of the
        #       DCIM_NICService.SetAttribute() and
        #       DCIM_NICService.SetAttributes() methods describe their separate
        #       output parameters, SetResult[] and RebootRequeired[]. The value
        #       of SetResult[] is 'Set CurrentValue property' when the
        #       attribute's current value was set and 'Set PendingValue' when
        #       the attribute's pending value was set.
        #
        #       The documentation also states,
        #
        #       "The CreateTargetedConfigJob() method is used to apply the
        #       pending values created by the SetAttribute and SetAttributes
        #       methods. The successful execution of this method creates a job
        #       for application of pending attribute values."
        #
        #       Therefore, the value of SetResult[] should be used instead of
        #       RebootRequired[] to determine the need to invoke
        #       CreateTargetedConfigJob(). And the requirement to reboot should
        #       be communicated separately to the caller. Presently, the
        #       requirement for both is indicated by the boolean value of the
        #       'commit_needed' key in the returned dictionary. That key's
        #       value is determined from RebootRequired[] only.
        #
        #       This applies to the ironic upstream dracclient's BIOS and RAID
        #       resources, too. Those were used as models during the
        #       development of the NIC resource in discover_nodes's dracclient.
        #
        #       This can be accomplished without breaking existing code that
        #       uses dracclient by adding two (2) new key:value pairs to the
        #       returned dictionary.
        job_id = drac_client.create_nic_config_job(
            nic_id,
            reboot=False,
            start_time=None)
        job_ids.append(job_id)

        if result['commit_required']:
            reboot_required = True

    if reboot_required:
        LOG.info("Rebooting the node to apply NIC configuration")

        job_id = drac_client.create_reboot_job()
        job_ids.append(job_id)

    drac_client.schedule_job_execution(job_ids, start_time='TIME_NOW')

    LOG.info(
        "Waiting for NIC configuration to complete; this may take some time")
    LOG.info("Do not power off the node")
    wait_for_job_completions(drac_client, job_ids)
    LOG.info("Completed NIC configuration")

    return determine_job_outcomes(drac_client, job_ids)


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
    wait_for_job_completions(drac_client, job_ids)
    LOG.info("Completed BIOS configuration")

    return determine_job_outcomes(drac_client, job_ids)


def wait_for_job_completions(drac_client, job_ids):
    if not job_ids:
        return

    incomplete_job_ids = list(job_ids)

    while incomplete_job_ids:
        sleep(10)
        incomplete_job_ids[:] = [
            job_id for job_id in incomplete_job_ids if not
            determine_job_is_complete(drac_client, job_id)]

    # Wait for any other jobs to complete, such as the 'Exporting System
    # Configuration Profile XML file' job. This prevents an attempt to change
    # the configuration that may follow from failing because an unfinished
    # configuration job exists.
    #
    # Methods in the ironic DRAC driver that change the configuration first
    # validate the job queue is empty. The validation raises an exception if it
    # is not empty.
    while drac_client.list_jobs(only_unfinished=True):
        sleep(10)


def determine_job_is_complete(drac_client, job_id):
    job_state = drac_client.get_job(job_id).state

    return job_state in [
        'Completed',
        'Completed with Errors',
        'Failed',
        'Reboot Completed',
        'Reboot Failed']


def determine_job_outcomes(drac_client, job_ids):
    all_succeeded = True

    for job_id in job_ids:
        job_state = drac_client.get_job(job_id).state

        if job_state == 'Completed' or job_state == 'Reboot Completed':
            continue

        all_succeeded = False
        LOG.error(
            "Configuration job {} encountered issues; its final state is "
            "{}".format(job_id, job_state))

    return all_succeeded


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

        model_properties = get_model_properties(
            args.pxe_nic,
            args.model_properties)

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
            LOG.critical("Unable to find node {}".format(ip_mac_service_tag))
            sys.exit(1)

        drac_client = get_drac_client(args.node_definition, node)

        pxe_nic_fqdd = get_pxe_nic_fqdd(
            args.pxe_nic,
            model_properties,
            drac_client)

        if pxe_nic_fqdd is None:
            sys.exit(1)

        assign_role(
            args.ip_mac_service_tag,
            node.uuid,
            args.role_index,
            ironic_client,
            drac_client)

        succeeded = configure_nics_boot_settings(drac_client, pxe_nic_fqdd)

        if not succeeded:
            sys.exit(1)

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
