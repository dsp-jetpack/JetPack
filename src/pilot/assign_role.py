#!/usr/bin/python

# Copyright (c) 2016-2017 Dell Inc. or its subsidiaries.
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
from collections import defaultdict
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
from arg_helper import ArgHelper
from credential_helper import CredentialHelper
from ironic_helper import IronicHelper
from job_helper import JobHelper
from logging_helper import LoggingHelper
import requests.packages
from ironicclient.common.apiclient.exceptions import InternalServerError

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

NORAID = "1"
RAID0 = "2"

RAID_TYPE_TO_DESCRIPTION = {
    NORAID:  "No RAID",
    RAID0:   "RAID0",
    "4":     "RAID1",
    "64":    "RAID5",
    "128":   "RAID6",
    "2048":  "RAID10",
    "8192":  "RAID50",
    "16384": "RAID60"
}

NOT_SUPPORTED_MSG = "This operation is not supported on this device"

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
    parser.add_argument('-s',
                        '--skip-raid-config',
                        action='store_true',
                        help="skip configuring RAID")

    ArgHelper.add_instack_arg(parser)

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


def define_target_raid_config(role, drac_client):
    raid_controller_name = get_raid_controller_id(drac_client)

    if not raid_controller_name:
        LOG.critical("Found no RAID controller")
        return None

    if role == 'controller':
        logical_disks = define_controller_logical_disks(drac_client,
                                                        raid_controller_name)
    elif role == 'compute':
        logical_disks = define_compute_logical_disks(drac_client,
                                                     raid_controller_name)
    elif role == 'storage':
        logical_disks = define_storage_logical_disks(drac_client,
                                                     raid_controller_name)
    else:
        LOG.critical(
            'Cannot define target RAID configuration for role "{}"').format(
                role)
        return None

    return {
        'logical_disks': logical_disks} if logical_disks is not None else None


def get_raid_controller_id(drac_client):
    disk_controllers = drac_client.list_raid_controllers()

    raid_controller_ids = [
        c.id for c in disk_controllers if c.id.startswith('RAID.Integrated.')]

    number_raid_controllers = len(raid_controller_ids)

    if number_raid_controllers == 1:
        return raid_controller_ids[0]
    elif number_raid_controllers == 0:
        LOG.critical("Found no RAID controllers")
        return None
    else:
        LOG.critical(
            "Found more than one RAID controller:\n  {}".format(
                "\n  ".join(raid_controller_ids)))
        return None


def define_controller_logical_disks(drac_client, raid_controller_name):
    raid_10_logical_disk = define_single_raid_10_logical_disk(
        drac_client, raid_controller_name)

    if raid_10_logical_disk is None:
        return None

    logical_disks = list()
    logical_disks.append(raid_10_logical_disk)

    return logical_disks


def define_compute_logical_disks(drac_client, raid_controller_name):
    raid_10_logical_disk = define_single_raid_10_logical_disk(
        drac_client, raid_controller_name)

    if raid_10_logical_disk is None:
        return None

    logical_disks = list()
    logical_disks.append(raid_10_logical_disk)

    return logical_disks


def define_single_raid_10_logical_disk(drac_client, raid_controller_name):
    physical_disk_names = get_raid_controller_physical_disk_ids(
        drac_client, raid_controller_name)

    number_physical_disks = len(physical_disk_names)

    if number_physical_disks >= 4:
        LOG.info(
            "Defining RAID 10 on the following physical disks, and marking it "
            "the root volume:\n  {}".format(
                "\n  ".join(physical_disk_names)))
        logical_disk = define_logical_disk(
            'MAX',
            '1+0',
            raid_controller_name,
            physical_disk_names,
            is_root_volume=True)
    elif number_physical_disks == 3 or number_physical_disks == 2:
        two_physical_disk_names = physical_disk_names[0:2]
        LOG.warning(
            "Did not find enough disks for RAID 10; defining RAID 1 on the "
            "following physical disks, and marking it the root volume:"
            "\n  {}".format(
                "\n  ".join(two_physical_disk_names)))
        logical_disk = define_logical_disk(
            'MAX',
            '1',
            raid_controller_name,
            two_physical_disk_names,
            is_root_volume=True)
    elif number_physical_disks == 1:
        LOG.warning(
            "Did not find enough disks for RAID; setting physical disk {} to "
            "JBOD mode".format(
                physical_disk_names[0]))
        logical_disk = define_jbod_or_raid_0_logical_disk(
            drac_client,
            raid_controller_name,
            physical_disk_names[0],
            is_root_volume=True)
    else:
        LOG.critical(
            "Found no physical disks connected to RAID controller {}".format(
                raid_controller_name))
        return None

    return logical_disk


def get_raid_controller_physical_disk_ids(drac_client, raid_controller_fqdd):
    physical_disks = drac_client.list_physical_disks()

    return sorted(
        (d.id for d in physical_disks if d.controller == raid_controller_fqdd),
        key=physical_disk_id_to_key)


def define_storage_logical_disks(drac_client, raid_controller_name):
    all_physical_disks = get_raid_controller_physical_disks(
        drac_client, raid_controller_name)
    number_physical_disks = len(all_physical_disks)

    if number_physical_disks < 3:
        LOG.critical(
            "Cannot configure RAID 1 and JBOD with only {} disks; need three "
            "(3) or more".format(
                number_physical_disks))
        return None

    # Define a logical disk to host the operating system.
    os_logical_disk = define_storage_operating_system_logical_disk(
        all_physical_disks, raid_controller_name)

    if os_logical_disk is None:
        return None

    # Determine the physical disks that remain for JBOD.
    #
    # The ironic RAID 'physical_disks' property is optional. While it is
    # presently used by this script, it is envisioned that it will not
    # be in the future.
    if 'physical_disks' in os_logical_disk:
        os_physical_disk_names = os_logical_disk['physical_disks']
        remaining_physical_disks = [d for d in all_physical_disks
                                    if d.id not in os_physical_disk_names]
    else:
        remaining_physical_disks = all_physical_disks

    # Define JBOD logical disks with the remaining physical disks.
    #
    # A successful call returns a list, which may be empty; otherwise,
    # None is returned.
    jbod_capable = is_jbod_capable(drac_client, raid_controller_name)
    jbod_logical_disks = define_jbod_logical_disks(
        drac_client, remaining_physical_disks, raid_controller_name,
        jbod_capable)

    if jbod_logical_disks is None:
        return None

    logical_disks = [os_logical_disk]
    logical_disks.extend(jbod_logical_disks)

    return logical_disks


def get_raid_controller_physical_disks(drac_client, raid_controller_fqdd):
    physical_disks = drac_client.list_physical_disks()

    return [d for d in physical_disks if d.controller == raid_controller_fqdd]


def define_storage_operating_system_logical_disk(physical_disks,
                                                 raid_controller_name):
    (os_logical_disk_size_gb,
     os_physical_disk_names) = find_physical_disks_for_storage_os(
        physical_disks)

    if os_physical_disk_names is None:
        return None

    # Define a RAID 1 logical disk to host the operating system.
    LOG.info(
        "Defining RAID 1 logical disk of size {} GB on the following physical "
        "disks, and marking it the root volume:\n  {}".format(
            os_logical_disk_size_gb,
            '\n  '.join(os_physical_disk_names)))
    os_logical_disk = define_logical_disk(
        os_logical_disk_size_gb,
        '1',
        raid_controller_name,
        os_physical_disk_names,
        is_root_volume=True)

    return os_logical_disk


def find_physical_disks_for_storage_os(physical_disks):
    physical_disk_selection_strategies = [
        (cardinality_of_smallest_spinning_disk_size_is_two,
         'two drives of smallest hard disk drive size'),
        (last_two_disks_by_location,
         'last two drives by location')]

    for index, (strategy, description) in enumerate(
            physical_disk_selection_strategies, start=1):
        os_logical_disk_size_gb, os_physical_disk_names = strategy(
            physical_disks)
        assert (os_logical_disk_size_gb and os_physical_disk_names) or not (
            os_logical_disk_size_gb or os_physical_disk_names)

        if os_physical_disk_names:
            LOG.info(
                "Strategy {} for selecting physical disks for the operating "
                "system logical disk -- {} -- found disks:\n  {}".format(
                    index,
                    description,
                    '\n  '.join(os_physical_disk_names)))
            assert len(os_physical_disk_names) >= 2
            break
        else:
            LOG.info(
                "Strategy {} for selecting physical disks for the operating "
                "system logical disk -- {} -- found no disks".format(
                    index,
                    description))

    if os_physical_disk_names is None:
        LOG.critical(
            "Could not find physical disks for operating system logical disk")

    return (os_logical_disk_size_gb, os_physical_disk_names)


def cardinality_of_smallest_spinning_disk_size_is_two(physical_disks):
    # Bin the spinning physical disks (hard disk drives (HDDs)) by size
    # in gigabytes (GB).
    disks_by_size = bin_physical_disks_by_size_gb(physical_disks,
                                                  media_type_filter='hdd')

    # Order the bins by size, from smallest to largest. Since Python
    # dictionaries are unordered, construct a sorted list of bins. Each
    # bin is a dictionary item, which is a tuple.
    ordered_disks_by_size = sorted(disks_by_size.items(), key=lambda t: t[0])

    # Obtain the bin for the smallest size.
    smallest_disks_bin = ordered_disks_by_size[0]

    smallest_disk_size = smallest_disks_bin[0]
    smallest_disks = smallest_disks_bin[1]
    cardinality_of_smallest_disks = len(smallest_disks)

    if cardinality_of_smallest_disks == 2:
        sorted_smallest_disk_ids = sorted((d.id for d in smallest_disks),
                                          key=physical_disk_id_to_key)
        return (smallest_disk_size, sorted_smallest_disk_ids)
    else:
        return (0, None)


def last_two_disks_by_location(physical_disks):
    assert len(physical_disks) >= 2
    disks_by_location = sorted((d for d in physical_disks),
                               key=physical_disk_to_key)

    last_two_disks = disks_by_location[-2:]

    # The two disks (2) must be of the same media type, hard disk drive
    # (HDD) spinner or solid state drive (SSD).
    if last_two_disks[0].media_type != last_two_disks[1].media_type:
        return (0, None)

    # Determine the smallest size of the two (2) disks, in gigabytes.

    logical_disk_size_mb = 0

    if last_two_disks[0].size_mb == last_two_disks[1].size_mb:
        # They are of equal size.
        logical_disk_size_mb = last_two_disks[0].size_mb
    elif last_two_disks[0].size_mb < last_two_disks[1].size_mb:
        # The first disk is smaller.
        logical_disk_size_mb = last_two_disks[0].size_mb
    else:
        # The second disk is smaller.
        logical_disk_size_mb = last_two_disks[1].size_mb

    logical_disk_size_gb = logical_disk_size_mb / 1024

    # Ensure that the logical disk size is unique from the perspective
    # of Linux logical volumes.

    # We only need to consider the other disks, those that are not the
    # last two (2).
    other_disks = disks_by_location[:-2]
    other_disks_by_size_gb = bin_physical_disks_by_size_gb(other_disks)

    while logical_disk_size_gb in other_disks_by_size_gb:
        # Subtract one (1) from the logical disk size and try again.
        logical_disk_size_gb -= 1
    else:
        assert logical_disk_size_gb > 0

    last_two_disk_ids = [d.id for d in last_two_disks]

    return (logical_disk_size_gb, last_two_disk_ids)


def bin_physical_disks_by_size_gb(physical_disks, media_type_filter=None):
    disks_by_size = defaultdict(list)

    for physical_disk in physical_disks:
        # Apply media type filter, if present.
        if (media_type_filter is None or
                physical_disk.media_type == media_type_filter):
            disks_by_size[physical_disk.size_mb / 1024].append(physical_disk)

    return disks_by_size


def define_jbod_logical_disks(
        drac_client, physical_disks, raid_controller_name, jbod_capable):
    sorted_physical_disk_names = sorted((d.id for d in physical_disks),
                                        key=physical_disk_id_to_key)

    logical_disks = list()

    for physical_disk_name in sorted_physical_disk_names:
        jbod_logical_disk = define_jbod_or_raid_0_logical_disk(
            drac_client, raid_controller_name, physical_disk_name,
            is_root_volume=False, jbod_capable=jbod_capable)

        if jbod_logical_disk is not None:
            logical_disks.append(jbod_logical_disk)

    return logical_disks


def define_jbod_or_raid_0_logical_disk(drac_client,
                                       raid_controller_name,
                                       physical_disk_name,
                                       is_root_volume=False,
                                       jbod_capable=None):
    if jbod_capable is None:
        jbod_capable = is_jbod_capable(drac_client, raid_controller_name)

    if jbod_capable:
        # Presently, when a RAID controller is JBOD capable, there is no
        # need to return a logical disk definition. That will hold as
        # long as this script executes the ironic DRAC driver RAID
        # delete_configuration clean step before the
        # create_configuration step, and it leaves all of the physical
        # disks in JBOD mode.
        '''TODO: Define a JBOD logical disk when the ironic DRAC driver
        supports the 'raid_level' property's 'JBOD' value in the RAID
        configuration JSON. That is a more robust approach and better
        documents the RAID configuration on the ironic node. It would
        also eliminate the dependency the RAID create_configuration
        clean step has on the delete_configuration step.'''
        return None
    else:
        return define_logical_disk('MAX', '0', raid_controller_name,
                                   [physical_disk_name], is_root_volume)


def define_logical_disk(
        size_gb,
        raid_level,
        controller_name,
        physical_disk_names,
        is_root_volume=False):
    logical_disk = dict(
        size_gb=size_gb,
        raid_level=raid_level,
        controller=controller_name,
        physical_disks=physical_disk_names)

    if is_root_volume:
        logical_disk['is_root_volume'] = is_root_volume

    return logical_disk


def physical_disk_id_to_key(disk_id):
    components = disk_id.split(':')

    disk_subcomponents = components[0].split('.')
    enclosure_subcomponents = components[1].split('.')
    controller_subcomponents = components[2].split('.')

    disk_connection_type = disk_subcomponents[1]
    disk_number = int(disk_subcomponents[2])

    enclosure_type = enclosure_subcomponents[1]
    enclosure_numbers = enclosure_subcomponents[2].split('-')

    enclosure_major_number = int(enclosure_numbers[0])
    enclosure_minor_number = int(enclosure_numbers[1])

    controller_type = controller_subcomponents[0]
    controller_location = controller_subcomponents[1]
    controller_numbers = controller_subcomponents[2].split('-')

    controller_major_number = int(controller_numbers[0])
    controller_minor_number = int(controller_numbers[1])

    return tuple([controller_type,
                  controller_location,
                  controller_major_number,
                  controller_minor_number,
                  enclosure_type,
                  enclosure_major_number,
                  enclosure_minor_number,
                  disk_connection_type,
                  disk_number])


def physical_disk_to_key(physical_disk):
    return physical_disk_id_to_key(physical_disk.id)


def configure_raid(ironic_client, node_uuid, role, drac_client):
    '''TODO: Add some selective exception handling so we can determine
    when RAID configuration failed and return False. Further testing
    should uncover interesting error conditions.'''

    LOG.info("Configuring RAID")
    LOG.info("Do not power off the node; configuration will take some time")

    # To manually clean the ironic node, it must be in the manageable state.
    success = place_node_in_manageable_state(ironic_client, node_uuid)

    if not success:
        LOG.critical("Could not place node into the manageable state")
        return False

    # To facilitate workarounds to bugs in the ironic DRAC driver's RAID
    # clean steps, execute manual cleaning twice, first to delete the
    # configuration, and then to create it. The workarounds are inserted
    # in-between.

    '''TODO: After those upstream bugs have been resolved, perform both
    clean steps, delete_configurtion() and create_configuration(),
    during one (1) manual cleaning.'''

    LOG.info("Deleting the existing RAID configuration")
    clean_steps = [{'interface': 'raid', 'step': 'delete_configuration'}]
    ironic_client.node.set_provision_state(
        node_uuid,
        'clean',
        cleansteps=clean_steps)
    LOG.info("Waiting for deletion of the existing RAID configuration to "
             "complete")
    ironic_client.node.wait_for_provision_state(node_uuid, 'manageable')
    LOG.info("Completed deletion of the existing RAID configuration")

    target_raid_config = define_target_raid_config(
        role, drac_client)

    if target_raid_config is None:
        return False

    # Set the target RAID configuration on the ironic node.
    ironic_client.node.set_target_raid_config(node_uuid, target_raid_config)

    # Work around the bugs in the ironic DRAC driver's RAID clean steps.

    '''TODO: After the upstream bugs have been resolved, remove the
    workarounds.'''

    raid_controller_fqdd = get_raid_controller_id(drac_client)

    '''TODO: Workaround 1:
    Reset the RAID controller to delete all virtual disks and unassign
    all hot spare physical disks.'''

    '''TODO: Workaround 2:
    Prepare any foreign physical disks for inclusion in the local RAID
    configuration.'''

    # Workaround 3:
    # Attempt to convert all of the node's physical disks to JBOD mode.
    # This may succeed or fail. A controller's capability to do that, or
    # lack thereof, has no bearing on success or failure.
    LOG.info("Converting all physical disks to JBOD mode")
    succeeded = change_physical_disk_state_wait(
        node_uuid, ironic_client, drac_client, 'JBOD')

    if succeeded:
        LOG.info("Completed converting all physical disks to JBOD mode")
    else:
        LOG.critical("Attempt to convert all physical disks to JBOD mode "
                     "failed")
        return False

    # Workaround 4:
    # Attempt to convert all of the physical disks in the target RAID
    # configuration to RAID mode. This may succeed or fail. A
    # controller's capability to do that, or lack thereof, has no
    # bearing on success or failure.
    controllers_to_physical_disk_ids = defaultdict(list)

    for logical_disk in target_raid_config['logical_disks']:
        # Not applicable to JBOD logical disks.
        if logical_disk['raid_level'] == 'JBOD':
            continue

        for physical_disk_name in logical_disk['physical_disks']:
            controllers_to_physical_disk_ids[
                logical_disk['controller']].append(physical_disk_name)

    LOG.info("Converting physical disks configured to back RAID logical disks "
             "to RAID mode")
    succeeded = change_physical_disk_state_wait(
        node_uuid, ironic_client, drac_client, 'RAID',
        controllers_to_physical_disk_ids)

    if succeeded:
        LOG.info("Completed converting physical disks configured to back RAID "
                 "logical disks to RAID mode")
    else:
        LOG.critical("Attempt to convert physical disks configured to back "
                     "RAID logical disks to RAID mode failed")
        return False

    LOG.info("Applying the new RAID configuration")
    clean_steps = [{'interface': 'raid', 'step': 'create_configuration'}]
    ironic_client.node.set_provision_state(
        node_uuid,
        'clean',
        cleansteps=clean_steps)
    LOG.info(
        "Waiting for application of the new RAID configuration to complete")
    ironic_client.node.wait_for_provision_state(node_uuid, 'manageable')
    LOG.info("Completed application of the new RAID configuration")

    # Return the ironic node to the available state.
    ironic_client.node.set_provision_state(node_uuid, 'provide')
    ironic_client.node.wait_for_provision_state(node_uuid, 'available')
    LOG.info("Completed RAID configuration")

    return True


def place_node_in_manageable_state(ironic_client, node_uuid):
    node = ironic_client.node.get(node_uuid, fields=['provision_state'])

    if node.provision_state != 'manageable':
        ironic_client.node.set_provision_state(node_uuid, 'manage')
        ironic_client.node.wait_for_provision_state(node_uuid, 'manageable')

    return True


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

    # Select the disk for the OS to be installed on
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

    # Look for a RAID of any type other than RAID0 and assume we want to
    # install the OS on that volume.  The first non-RAID0 found will be used.
    for virtual_disk_doc in virtual_disk_docs:
        fqdd = get_fqdd(virtual_disk_doc, DCIM_VirtualDiskView)
        raid_type = utils.find_xml(virtual_disk_doc, 'RAIDTypes',
                                   DCIM_VirtualDiskView).text

        if raid_type != NORAID and raid_type != RAID0:
            # Get the size
            raid_size = get_size_in_bytes(virtual_disk_doc,
                                          DCIM_VirtualDiskView)

            # Get the physical disks that back this RAID
            raid_physical_disk_docs = utils.find_xml(virtual_disk_doc,
                                                     'PhysicalDiskIDs',
                                                     DCIM_VirtualDiskView,
                                                     True)
            raid_physical_disk_ids = []
            for raid_physical_disk_doc in raid_physical_disk_docs:
                raid_physical_disk_id = raid_physical_disk_doc.text
                raid_physical_disk_ids.append(raid_physical_disk_id)

            LOG.debug(
                "Found RAID {} virtual disk {} with a size of {} bytes "
                "comprised of physical disks:\n  {}".format(
                    RAID_TYPE_TO_DESCRIPTION[raid_type],
                    fqdd,
                    raid_size,
                    "\n  ".join(raid_physical_disk_ids)))

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
        if fqdd not in raid_physical_disk_ids:
            physical_disk_size = get_size_in_bytes(
                physical_disk_doc, DCIM_PhysicalDiskView)

            if physical_disk_size == raid_size:
                LOG.warning(
                    "Physical disk {} has the same size ({}) as the "
                    "RAID.  Unable to specify the OS disk to Ironic.".format(
                        fqdd,
                        physical_disk_size))
                found_same_size_disk = True
                break

    # If we did find a disk that's the same size, then passing a disk
    # size to ironic is pointless, so let whatever happens, happen
    if not found_same_size_disk:
        # Otherwise...
        raid_size_gb = int(raid_size) / units.Gi

        # Set the root_device property in ironic to the RAID size in gigs
        LOG.info(
            "Setting the OS disk for this node to the {} with size "
            "{} GB".format(RAID_TYPE_TO_DESCRIPTION[raid_type], raid_size_gb))
        patch = [{'op': 'add',
                  'value': {"size": raid_size_gb},
                  'path': '/properties/root_device'}]
        ironic_client.node.update(node_uuid, patch)


def configure_bios(node, ironic_client, settings, drac_client):
    LOG.info("Configuring BIOS")

    if 'drac' not in node.driver:
        LOG.critical("Node is not being managed by an iDRAC driver")
        return False

    # Make sure the iDRAC is ready before configuring BIOS
    drac_client.wait_until_idrac_is_ready()

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


def change_physical_disk_state_wait(
        node_uuid, ironic_client, drac_client, mode,
        controllers_to_physical_disk_ids=None):
    reboot_required, job_ids = change_physical_disk_state(
        drac_client, mode, controllers_to_physical_disk_ids)

    result = True
    if job_ids:
        if reboot_required:
            LOG.debug("Rebooting the node to apply configuration")

            job_id = drac_client.create_reboot_job()
            job_ids.append(job_id)

        drac_client.schedule_job_execution(job_ids, start_time='TIME_NOW')

        LOG.info("Waiting for physical disk conversion to complete")
        JobHelper.wait_for_job_completions(ironic_client, node_uuid)
        result = JobHelper.determine_job_outcomes(drac_client, job_ids)

    return result


def is_jbod_capable(drac_client, raid_controller_fqdd):
    is_jbod_capable = False

    # Grab all the disks associated with the RAID controller
    all_physical_disks = drac_client.list_physical_disks()
    physical_disks = [physical_disk for physical_disk in all_physical_disks
                      if physical_disk.controller == raid_controller_fqdd]

    # If there is a disk in the Non-RAID state, then the controller is JBOD
    # capable
    ready_disk = None
    for physical_disk in physical_disks:
        if physical_disk.raid_status == 'non-RAID':
            is_jbod_capable = True
            break
        elif not ready_disk and physical_disk.raid_status == 'ready':
            ready_disk = physical_disk

    if not is_jbod_capable:
        if not ready_disk:
            raise RuntimeError("Unable to find a disk in the Ready state")

        # Try moving a disk in the Ready state to JBOD mode
        try:
            drac_client.convert_physical_disks(
                ready_disk.controller,
                [ready_disk.id],
                False)

            is_jbod_capable = True

            # Flip the disk back to the Ready state.  This results in the
            # pending value being reset to nothing, so it effectively
            # undoes the last command and makes the check non-destructive
            drac_client.convert_physical_disks(
                ready_disk.controller,
                [ready_disk.id],
                True)
        except DRACOperationFailed as ex:
            if NOT_SUPPORTED_MSG in ex.message:
                pass
            else:
                raise

    return is_jbod_capable


# mode is either "RAID" or "JBOD"
# controllers_to_physical_disk_ids is a dictionary with the keys being the
# FQDD of RAID controllers, and the value being a list of physical disk FQDDs
def change_physical_disk_state(drac_client, mode,
                               controllers_to_physical_disk_ids=None):
    # The node is rebooting from the last RAID config step, and when it reboots
    # the "export to xml" job runs.  Wait until this completes so we don't blow
    # up when trying to create a config job below
    # TODO: Move this check into list_physical_disks along with all other iDRAC
    #       commands
    drac_client.wait_until_idrac_is_ready()

    physical_disks = drac_client.list_physical_disks()
    p_disk_id_to_state = {}
    for physical_disk in physical_disks:
        p_disk_id_to_state[physical_disk.id] = physical_disk.raid_status

    if not controllers_to_physical_disk_ids:
        controllers_to_physical_disk_ids = defaultdict(list)

        for physical_disk in physical_disks:
            physical_disk_ids = controllers_to_physical_disk_ids[
                physical_disk.controller]

            physical_disk_ids.append(physical_disk.id)

    # Weed out disks that are already in the mode we want
    failed_disks = []
    bad_disks = []
    for controller in controllers_to_physical_disk_ids.keys():
        final_physical_disk_ids = []
        physical_disk_ids = controllers_to_physical_disk_ids[controller]
        for physical_disk_id in physical_disk_ids:
            raid_status = p_disk_id_to_state[physical_disk_id]
            if (mode == "JBOD" and raid_status == "non-RAID") or \
                    (mode == "RAID" and raid_status == "ready"):
                # This means the disk is already in the desired state,
                # so skip it
                continue
            elif (mode == "JBOD" and raid_status == "ready") or \
                    (mode == "RAID" and raid_status == "non-RAID"):
                # This disk is moving from a state we expect to RAID or JBOD,
                # so keep it
                final_physical_disk_ids.append(physical_disk_id)
            elif raid_status == "failed":
                failed_disks.append(physical_disk_id)
            else:
                # This disk is in one of many states that we don't know what
                # to do with, so pitch it
                bad_disks.append("{} ({})".format(physical_disk_id,
                                                  raid_status))

        controllers_to_physical_disk_ids[controller] = final_physical_disk_ids

    if failed_disks or bad_disks:
        error_msg = ""

        if failed_disks:
            error_msg += "The following drives have failed: " \
                "{failed_disks}.  Manually check the status of all drives " \
                "and replace as necessary, then run the installation " \
                "again.".format(failed_disks=" ".join(failed_disks))

        if bad_disks:
            if failed_disks:
                error_msg += "\n"
            error_msg += "Unable to change the state of the following " \
                "drives because their status is not ready or non-RAID: {}.  " \
                "Bring up the RAID controller GUI on this node and change " \
                "the drives' state to ready or non-RAID.".format(
                    ", ".join(bad_disks))

        raise ValueError(error_msg)

    job_ids = []
    reboot_required = False
    try:
        for controller in controllers_to_physical_disk_ids.keys():
            physical_disk_ids = controllers_to_physical_disk_ids[controller]
            if physical_disk_ids:
                LOG.debug("Converting the following disks to {} on RAID "
                          "controller {}: {}".format(
                              mode, controller, str(physical_disk_ids)))
                try:
                    _ = drac_client.convert_physical_disks(
                        controller,
                        physical_disk_ids,
                        mode == "RAID")
                except DRACOperationFailed as ex:
                    if NOT_SUPPORTED_MSG in ex.message:
                        LOG.debug("Controller {} does not support "
                                  "JBOD mode".format(controller))
                        pass
                    else:
                        raise
                else:
                    # The iDRAC response can contain YES, NO, or OPTIONAL.
                    # Testing has shown that when OPTIONAL is returned,
                    # and a config job is created scheduled for TIME_NOW,
                    # the config job fails to run unless the node is rebooted.
                    # As a result, we always must reboot the node since if
                    # we made it this far then at least 1 disk was converted
                    # and either YES or OPTIONAL was returned.
                    reboot_required = True

                    job_id = drac_client.commit_pending_raid_changes(
                        controller, reboot=False, start_time=None)
                    job_ids.append(job_id)
    except:
        # If any exception (except Not Supported) occurred during the
        # conversion, then roll back all the changes for this node so we don't
        # leave pending config jobs in the job queue
        drac_client.delete_jobs(job_ids)
        raise

    return reboot_required, job_ids


def main():

    try:
        drac_client = None

        args = parse_arguments()

        root_logger = logging.getLogger()
        root_logger.setLevel(args.logging_level)
        urllib3_logger = logging.getLogger("requests.packages.urllib3")
        urllib3_logger.setLevel(logging.WARN)

        flavor_settings_filename = os.path.expanduser(args.flavor_settings)
        flavor_settings = get_flavor_settings(flavor_settings_filename)

        if flavor_settings is None:
            sys.exit(1)

        ironic_client = IronicHelper.get_ironic_client()

        node = IronicHelper.get_ironic_node(ironic_client,
                                            args.ip_mac_service_tag)
        if node is None:
            LOG.critical("Unable to find node {}".format(
                         args.ip_mac_service_tag))
            sys.exit(1)

        drac_client = get_drac_client(args.node_definition, node)

        if node.driver == "pxe_drac":
            bios_settings = calculate_bios_settings(
                args.role_index.role,
                flavor_settings,
                flavor_settings_filename)

            if bios_settings is None:
                sys.exit(1)

            if not args.skip_raid_config:
                succeeded = configure_raid(
                    ironic_client,
                    node.uuid,
                    args.role_index.role,
                    drac_client)

                if not succeeded:
                    sys.exit(1)

            succeeded = configure_bios(
                node,
                ironic_client,
                bios_settings,
                drac_client)

            if not succeeded:
                sys.exit(1)

        assign_role(
            args.ip_mac_service_tag,
            node.uuid,
            args.role_index,
            ironic_client,
            drac_client)

    except (DRACOperationFailed, DRACUnexpectedReturnValue,
            InternalServerError, KeyError, TypeError, ValueError,
            WSManInvalidResponse, WSManRequestFailure):
        LOG.exception("")
        sys.exit(1)
    except SystemExit:
        raise
    except:  # Catch all exceptions.
        LOG.exception("Unexpected error")
        sys.exit(1)
    finally:
        # Leave the node powered off.
        if drac_client is not None:
            ensure_node_is_powered_off(drac_client)


if __name__ == "__main__":
    main()
