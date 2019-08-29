#!/usr/bin/python

# Copyright (c) 2016-2019 Dell Inc. or its subsidiaries.
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
from constants import Constants
from shutil import copyfile
import json
import logging
import math
import os
import sys
import yaml
import errno
import fcntl
import time

from dracclient import utils
from dracclient.constants import POWER_OFF
from dracclient.constants import RebootRequired
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

NOT_SUPPORTED_MSG = " operation is not supported on th"

ROLES = {
    'controller': 'control',
    'compute': 'compute',
    'storage': 'ceph-storage',
    'computehci': 'computehci'
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
    parser.add_argument('-b',
                        '--skip-bios-config',
                        action='store_true',
                        help="skip configuring BIOS")
    parser.add_argument('-o',
                        '--os-volume-size-gb',
                        help="the size of the volume to install the OS on "
                             "in GB",
                        metavar="OSVOLUMESIZEGB")

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
    elif role == 'computehci':
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
    disk_ctrls = drac_client.list_raid_controllers()

    raid_controller_ids = [
        c.id for c in disk_ctrls if drac_client.is_raid_controller(c.id)]

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

    # None indicates an error occurred.
    if raid_10_logical_disk is None:
        return None

    logical_disks = list()

    # Add the disk to the list only if it is not empty.
    if raid_10_logical_disk:
        logical_disks.append(raid_10_logical_disk)

    return logical_disks


def define_compute_logical_disks(drac_client, raid_controller_name):
    raid_10_logical_disk = define_single_raid_10_logical_disk(
        drac_client, raid_controller_name)

    # None indicates an error occurred.
    if raid_10_logical_disk is None:
        return None

    logical_disks = list()

    # Add the disk to the list only if it is not empty.
    if raid_10_logical_disk:
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
        LOG.warning(
            "Did not find enough disks for RAID 10; defining RAID 1 on the "
            "following physical disks, and marking it the root volume:"
            "\n  {}".format(
                "\n  ".join(physical_disk_names)))
        logical_disk = define_logical_disk(
            'MAX',
            '1',
            raid_controller_name,
            physical_disk_names,
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
    all_physical_disks = drac_client.list_physical_disks()

    # Get the drives controlled by the RAID controller
    raid_cntlr_physical_disks = []
    for disk in all_physical_disks:
        if disk.controller == raid_controller_name:
            raid_cntlr_physical_disks.append(disk)

    # Make sure we have enough drives attached to the RAID controller to create
    # a RAID1
    num_raid_cntlr_physical_disks = len(raid_cntlr_physical_disks)
    if num_raid_cntlr_physical_disks < 2:
        LOG.critical(
            "Cannot configure RAID 1 with only {} drives; need at least two "
            "drives".format(num_raid_cntlr_physical_disks))
        return None

    # Make sure we have at least one drive for Ceph OSD/journals
    if len(all_physical_disks) < 3:
        LOG.critical(
            "Storage nodes must have at least one drive for Ceph OSD/journal "
            "configuration")
        return None

    os_logical_disk = define_storage_operating_system_logical_disk(
        raid_cntlr_physical_disks, drac_client, raid_controller_name)

    if os_logical_disk is None:
        return None

    # Determine the physical disks that remain for JBOD.
    #
    # The ironic RAID 'physical_disks' property is optional. While it is
    # presently used by this script, it is envisioned that it will not
    # be in the future.
    if 'physical_disks' in os_logical_disk:
        os_physical_disk_names = os_logical_disk['physical_disks']
        remaining_physical_disks = [d for d in raid_cntlr_physical_disks
                                    if d.id not in os_physical_disk_names]
    else:
        remaining_physical_disks = raid_cntlr_physical_disks

    # Define JBOD logical disks with the remaining physical disks.
    #
    # A successful call returns a list, which may be empty; otherwise,
    # None is returned.
    jbod_capable = drac_client.is_jbod_capable(raid_controller_name)
    jbod_logical_disks = define_jbod_logical_disks(
        drac_client, remaining_physical_disks, raid_controller_name,
        jbod_capable)

    if jbod_logical_disks is None:
        return None

    logical_disks = [os_logical_disk]
    logical_disks.extend(jbod_logical_disks)

    return logical_disks


def define_storage_operating_system_logical_disk(physical_disks, drac_client,
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
    if drac_client.is_boss_controller(raid_controller_name):
        os_logical_disk_size_gb = 0
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

    # Handle the case where we have no spinning disks
    if not ordered_disks_by_size:
        return (0, None)

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

        if jbod_logical_disk:
            logical_disks.append(jbod_logical_disk)

    return logical_disks


def define_jbod_or_raid_0_logical_disk(drac_client,
                                       raid_controller_name,
                                       physical_disk_name,
                                       is_root_volume=False,
                                       jbod_capable=None):
    if jbod_capable is None:
        jbod_capable = drac_client.is_jbod_capable(raid_controller_name)

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
        return dict()
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
    if len(components) > 3:
        enclosure_subcomponents = components[1].split('.')
        controller_subcomponents = components[2].split('.')
    else:
        enclosure_subcomponents = 'Enclosure.None.0-0'.split('.')
        controller_subcomponents = components[1].split('.')

    disk_connection_type = disk_subcomponents[1]
    try:
        disk_number = int(disk_subcomponents[2])
    except:  # noqa: E722
        disk_number = int(disk_subcomponents[2].split('-')[0])

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


def configure_raid(ironic_client, node_uuid, role, os_volume_size_gb,
                   drac_client):
    '''TODO: Add some selective exception handling so we can determine
    when RAID configuration failed and return False. Further testing
    should uncover interesting error conditions.'''

    if get_raid_controller_id(drac_client) is None:
        LOG.warning("No RAID controller is present.  Skipping RAID "
                    "configuration")
        return True

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

    # Work around the bugs in the ironic DRAC driver's RAID clean steps.

    '''TODO: After the upstream bugs have been resolved, remove the
    workarounds.'''

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

    target_raid_config = define_target_raid_config(
        role, drac_client)

    if target_raid_config is None:
        return False

    if not target_raid_config['logical_disks']:
        place_node_in_available_state(ironic_client, node_uuid)
        return True

    # Set the target RAID configuration on the ironic node.
    ironic_client.node.set_target_raid_config(node_uuid, target_raid_config)

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
    place_node_in_available_state(ironic_client, node_uuid)

    LOG.info("Completed RAID configuration")

    return True


def place_node_in_manageable_state(ironic_client, node_uuid):
    node = ironic_client.node.get(node_uuid, fields=['provision_state'])

    if node.provision_state != 'manageable':
        ironic_client.node.set_provision_state(node_uuid, 'manage')
        ironic_client.node.wait_for_provision_state(node_uuid, 'manageable')

    return True


def place_node_in_available_state(ironic_client, node_uuid):
    # Return the ironic node to the available state.
    ironic_client.node.set_provision_state(node_uuid, 'provide')
    ironic_client.node.wait_for_provision_state(node_uuid, 'available')


def assign_role(ip_mac_service_tag, node_uuid, role_index, os_volume_size_gb,
                ironic_client, drac_client):
    flavor = ROLES[role_index.role]
    LOG.info(
        "Setting role for {} to {}, flavor {}".format(
            ip_mac_service_tag,
            role_index.role,
            flavor))

    node = ironic_client.node.get(node_uuid, fields=['properties'])

    role = "profile:{}".format(flavor)

    if role_index.index:
        role = "node:{}-{}".format(flavor, role_index.index)

    if 'capabilities' in node.properties:
        value = "{},{}".format(role, node.properties['capabilities'])
    else:
        value = "{},boot_option:local".format(role)

    patch = [{'op': 'add',
              'value': value,
              'path': '/properties/capabilities'}]
    ironic_client.node.update(node_uuid, patch)

    # Select the volume for the OS to be installed on
    select_os_volume(os_volume_size_gb, ironic_client, drac_client,
                     node_uuid)

    # Generate Ceph OSD/journal configuration for storage nodes
    if flavor == "ceph-storage" or flavor =="computehci":
        generate_osd_config(ip_mac_service_tag, drac_client)


def generate_osd_config(ip_mac_service_tag, drac_client):
    controllers = drac_client.list_raid_controllers()

    found_hba = False
    for controller in controllers:
        if "hba330" in controller.model.lower():
            found_hba = True
            break

    if not found_hba:
        LOG.info("Not generating OSD config for {ip} because no HBA330 is "
                 "present.".format(ip=ip_mac_service_tag))
        return

    LOG.info("Generating OSD config for {ip}".format(ip=ip_mac_service_tag))
    system_id = drac_client.get_system().uuid

    spinners, ssds = get_drives(drac_client)

    new_osd_config = None
    if len(ssds) > 0 and len(spinners) == 0:
        # If we have an all flash config, then let Ceph colocate the journals
        new_osd_config, mklvm = generate_osd_config_without_journals(controllers,
                                                              ssds, system_id)
    elif len(ssds) > 0 and len(spinners) > 0:
        # If we have a mix of flash and spinners, then use the ssds as journals
        new_osd_config, mklvm = generate_osd_config_with_journals(controllers,
                                                           spinners, ssds, system_id)
    else:
        # We have all spinners, so let Ceph colocate the journals
        new_osd_config, mklvm  = generate_osd_config_without_journals(controllers,
                                                              spinners, system_id)

    # load the osd environment file
    osd_config_file = os.path.join(Constants.TEMPLATES, "ceph-osd-config.yaml")
    stream = open(osd_config_file, 'r+')
    while True:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except IOError as e:
            if e.errno != errno.EAGAIN:
                raise
            else:
                time.sleep(1)
    try:
        try:
            current_osd_configs = yaml.load(stream)
        except:
            raise
        node_data_lookup_str = \
        current_osd_configs["parameter_defaults"]["NodeDataLookup"]
        if not node_data_lookup_str:
            node_data_lookup = {}
        else:
            node_data_lookup = json.loads(node_data_lookup_str)
        LOG.info("Checking for existing config ")
        if system_id in node_data_lookup:
            current_osd_config = node_data_lookup[system_id]
            if new_osd_config == current_osd_config:
                LOG.info("The generated OSD configuration for "
                         "{ip_mac_service_tag} ({system_id}) is the same as the "
                         "one in {osd_config_file}.  Skipping OSD "
                         "configuration.".format(
                             ip_mac_service_tag=ip_mac_service_tag,
                             system_id=system_id,
                             osd_config_file=osd_config_file))
                return
            else:
                generated_config = json.dumps(new_osd_config, sort_keys=True,
                                              indent=2, separators=(',', ': '))
                current_config = json.dumps(current_osd_config, sort_keys=True,
                                            indent=2, separators=(',', ': '))
                raise RuntimeError("The generated OSD configuration for "
                                   "{ip_mac_service_tag} ({system_id}) is "
                                   "different from the one in {osd_config_file}.\n"
                                   "Generated:\n{generated_config}\n\n"
                                   "Current:\n{current_config}\n\n"
                                   "If this is unexpected, then check for failed"
                                   " drives. If this is expected, then delete the"
                                   " configuration for this node from "
                                   "{osd_config_file} and rerun "
                                   "assign_role.".format(
                                       ip_mac_service_tag=ip_mac_service_tag,
                                       system_id=system_id,
                                       osd_config_file=osd_config_file,
                                       generated_config=generated_config,
                                       current_config=current_config))

        node_data_lookup[system_id] = new_osd_config

        # make a backup copy of the file
        osd_config_file_backup = osd_config_file + ".bak"
        LOG.info("Backing up original OSD config file to "
                 "{osd_config_file_backup}".format(
                     osd_config_file_backup=osd_config_file_backup))
        copyfile(osd_config_file, osd_config_file_backup)

        # save the new config
        LOG.info("Saving new OSD config to {osd_config_file}".format(
            osd_config_file=osd_config_file))

        # Using the simple yaml.dump results in a completely
        # unreadable file, so we do it the hard way to create
        # something more user friendly
        stream.seek(0)
        with open(osd_config_file + ".orig", 'r') as instream:
            for line in instream:
                if '{}' not in line:
                    stream.write(line)

            osd_config_str = json.dumps(node_data_lookup,
                                        sort_keys=True,
                                        indent=2,
                                        separators=(',', ': '))
            for line in osd_config_str.split('\n'):
                line = "    " + line + "\n"
                stream.write(line)
        stream.truncate()
        instream.close()
    finally:
        fcntl.flock(stream, fcntl.LOCK_UN)
        stream.close()

    # Generate the mklvm script that ll create LVM's on firstboot

    mklvm_file = os.path.join(Constants.TEMPLATES, "mklvm.sh")
    streammklvm = open(mklvm_file, 'a+')

    while True:
        try:
            fcntl.flock(streammklvm, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except IOError as e:
            if e.errno != errno.EAGAIN:
                raise
            else:
                time.sleep(1)
    try:
        try:
            current_mklvm = streammklvm.readlines()
        except:
            raise
        streammklvm.seek(0)
        streammklvm.writelines("%s\n" % line for line in mklvm)
        streammklvm.truncate()

    finally:
        fcntl.flock(streammklvm, fcntl.LOCK_UN)
        streammklvm.close()
        


def get_drives(drac_client):
    spinners = []
    ssds = []
    physical_disks = drac_client.list_physical_disks()
    for physical_disk in physical_disks:
        # Eliminate physical disks that in a state other than non-RAID
        if physical_disk.raid_status != "non-RAID":
            LOG.info("Skipping disk {id}, because it has a RAID status of "
                     "{raid_status}".format(
                         id=physical_disk.id,
                         raid_status=physical_disk.raid_status))
            continue

        # Eliminate physical disks that have an error status
        if physical_disk.status == 'error':
            LOG.warning("Not using disk {id}, because it has a status of "
                        "{status}".format(id=physical_disk.id,
                                          status=physical_disk.status))
            continue

        # Go ahead and use any physical drive that's not in an error state, but
        # issue a warning if it's not in the ok or unknown state
        if physical_disk.status != 'ok' and physical_disk.status != 'unknown':
            LOG.warning("Using disk {id}, but it has a status of \""
                        "{status}\"".format(id=physical_disk.id,
                                            status=physical_disk.status))

        if physical_disk.media_type == "hdd":
            spinners.append(physical_disk)
        else:
            ssds.append(physical_disk)

    return spinners, ssds

def generate_osd_config_without_journals(controllers, drives, system_id):
    mklvm = []
    mklvm.append('if [[ $(dmidecode -s system-uuid) == "' + system_id + '" ]]; then')
    osd_config = {
        'osd_scenario': 'lvm',
        'osd_objectstore': 'bluestore',
        'lvm_volumes': []}
    drive_count = 0
    for osd_drive in drives:
        osd_drive_pci_bus_number = get_pci_bus_number(osd_drive, controllers)
        osd_drive_device_name = get_by_path_device_name(
            osd_drive_pci_bus_number, osd_drive)
        mklvm.append('  device=$(ls -la ' + osd_drive_device_name + " |  awk -F \"../../\" '{ print $2 }')")
        mklvm.append('  eval "wipefs -a /dev/${device}"')
        mklvm.append('  sleep 2')
        mklvm.append('  pvcreate ' + osd_drive_device_name)
        mklvm.append('  vgcreate ceph_vg' + str(drive_count) + ' ' + osd_drive_device_name)
        mklvm.append("  size=$(sudo fdisk -l /dev/${device} 2>/dev/null | grep -m1 \"Disk\" | awk '{print $5}')")
        mklvm.append("  sizeb=`expr $((${size} * 99 / 100))`")
        mklvm.append("  sizeb=`expr $((${sizeb} / 512 * 512))`")
        mklvm.append('  lvcreate -n ceph_lv' + str(drive_count) + '_data -L ${sizeb}B ceph_vg' + str(drive_count))
        mklvm.append('  sleep 2')
        osd_config['lvm_volumes'].append({"data": "ceph_lv" + str(drive_count) + "_data",
                                      "data_vg": "ceph_vg" + str(drive_count)})
        drive_count += 1
    mklvm.append("fi")
    return osd_config, mklvm

def generate_osd_config_with_journals(controllers, osd_drives, ssds, system_id):
    if len(osd_drives) % len(ssds) != 0:
        LOG.warning("There is not an even mapping of OSD drives to SSD "
                    "journals.  This will cause inconsistent performance "
                    "characteristics.")
    mklvm = []
    mklvm.append('if [[ $(dmidecode -s system-uuid) == "' + system_id + '" ]]; then')
    osd_config = {
        'osd_scenario': 'lvm',
        'osd_objectstore': 'bluestore',
        'lvm_volumes': []}
    osd_index = 0
    vg_index = 0
    remaining_ssds = len(ssds)
    for ssd in ssds:      
        ssd_pci_bus_number = get_pci_bus_number(ssd, controllers)
        ssd_device_name = get_by_path_device_name(ssd_pci_bus_number, ssd)
        num_osds_for_ssd = int(math.ceil((len(osd_drives)-osd_index) /
                                         (remaining_ssds * 1.0)))
        # x2 volumes for each data osd (DB & WAL)
        allocation_journals = 50 / num_osds_for_ssd - 1
        mklvm.append('  device=$(ls -la ' + ssd_device_name + " |  awk -F \"../../\" '{ print $2 }')")
        mklvm.append('  eval "wipefs -a /dev/${device}"')
        mklvm.append('  sleep 2')
        mklvm.append('  pvcreate ' + ssd_device_name)
        mklvm.append('  vgcreate ceph_vg' + str(vg_index) + ' ' + ssd_device_name)
        mklvm.append("  size=$(sudo fdisk -l /dev/${device} 2>/dev/null | grep -m1 \"Disk\" | awk '{print $5}')")
        mklvm.append("  siz=`expr $((${size} * " + str(allocation_journals) + " / 100))`")
        mklvm.append("  siz=`expr $((${siz} / 512 * 512))`")
        for i in range(0, num_osds_for_ssd):
            mklvm.append('  lvcreate -n ceph_lv' + str(vg_index) + "-" + str(i) + '_wal -L ${siz}B ceph_vg' + str(vg_index))
            mklvm.append('  lvcreate -n ceph_lv' + str(vg_index) + "-" + str(i) + '_db -L ${siz}B ceph_vg' + str(vg_index))
            mklvm.append('  sleep 2')

        osds_for_ssd = osd_drives[osd_index:
                                  osd_index + num_osds_for_ssd]
        ind = 0
        journal_index = vg_index
        for osd_drive in osds_for_ssd:
            vg_index += 1
            osd_drive_pci_bus_number = get_pci_bus_number(osd_drive,
                                                          controllers)
            osd_drive_device_name = get_by_path_device_name(
                osd_drive_pci_bus_number, osd_drive)
            mklvm.append('  device=$(ls -la ' + osd_drive_device_name + " |  awk -F \"../../\" '{ print $2 }')")
            mklvm.append('  eval "wipefs -a /dev/${device}"')
            mklvm.append('  sleep 2')
            mklvm.append('  pvcreate ' + osd_drive_device_name)
            mklvm.append('  vgcreate ceph_vg' + str(vg_index) + ' ' + osd_drive_device_name)
            mklvm.append("  size=$(sudo fdisk -l /dev/${device} 2>/dev/null | grep -m1 \"Disk\" | awk '{print $5}')")
            mklvm.append("  sizeb=`expr $((${size} * 99 / 100))`")
            mklvm.append("  sizeb=`expr $((${sizeb} / 512 * 512))`")
            mklvm.append('  lvcreate -n ceph_lv' + str(vg_index) + '_data -L ${sizeb}B ceph_vg' + str(vg_index))
            mklvm.append('  sleep 2')
            osd_config['lvm_volumes'].append({"data": "ceph_lv" + str(vg_index) + "_data",
                                      "data_vg": "ceph_vg" + str(vg_index),
                                      "db": "ceph_lv" + str(journal_index) + "-" + str(ind) + "_db",
                                      "db_vg": "ceph_vg" + str(journal_index),
                                      "wal": "ceph_lv" + str(journal_index) +  "-" + str(ind) + "_wal",
                                      "wal_vg": "ceph_vg" + str(journal_index)})
            ind += 1
        osd_index += num_osds_for_ssd
        remaining_ssds -= 1
        vg_index += 1
    mklvm.append("fi")

    return osd_config, mklvm


def get_pci_bus_number(spinner, controllers):
    bus = None
    for controller in controllers:
        if controller.id in spinner.id:
            bus = controller.bus.lower()
            break
    return bus


def get_by_path_device_name(pci_bus_number, physical_disk):
    return ('/dev/disk/by-path/pci-0000:'
            '{pci_bus_number}:00.0-sas-0x{sas_address}-lun-0').format(
                pci_bus_number=pci_bus_number,
                sas_address=physical_disk.sas_address.lower())


def get_fqdd(doc, namespace):
    return utils.find_xml(doc, 'FQDD', namespace).text


def get_size_in_bytes(doc, namespace):
    return utils.find_xml(doc, 'SizeInBytes', namespace).text


def select_os_volume(os_volume_size_gb, ironic_client, drac_client, node_uuid):
    if os_volume_size_gb is None:
        # Detect BOSS Card and find the volume size
        lst_ctrls = drac_client.list_raid_controllers()
        boss_disk = \
            [ctrl.id for ctrl in lst_ctrls if ctrl.model.startswith("BOSS")]
        if boss_disk:
            lst_physical_disks = drac_client.list_physical_disks()
            for disks in lst_physical_disks:
                if disks.controller in boss_disk:
                    os_volume_size_gb = disks.size_mb / 1024
                    LOG.info("Detect BOSS Card {} and volume size {}".format(
                        disks.controller,
                        os_volume_size_gb))
        else:
            drac_client = drac_client.client
            # Get the virtual disks
            virtual_disk_view_doc = drac_client.enumerate(DCIM_VirtualDiskView)
            virtual_disk_docs = utils.find_xml(virtual_disk_view_doc,
                                               'DCIM_VirtualDiskView',
                                               DCIM_VirtualDiskView,
                                               True)

            raid_physical_disk_ids = []

            # Look for a RAID of any type other than RAID0 and assume we want
            # to install the OS on that volume.  The first non-RAID0 found
            # will be used.
            raid_size_gb = 0
            for virtual_disk_doc in virtual_disk_docs:
                fqdd = get_fqdd(virtual_disk_doc, DCIM_VirtualDiskView)
                raid_type = utils.find_xml(virtual_disk_doc, 'RAIDTypes',
                                           DCIM_VirtualDiskView).text

                if raid_type != NORAID and raid_type != RAID0:
                    # Get the size
                    raid_size = get_size_in_bytes(virtual_disk_doc,
                                                  DCIM_VirtualDiskView)
                    raid_size_gb = int(raid_size) / units.Gi

                    # Get the physical disks that back this RAID
                    raid_physical_disk_docs = utils.find_xml(
                        virtual_disk_doc,
                        'PhysicalDiskIDs',
                        DCIM_VirtualDiskView,
                        True)
                    for raid_physical_disk_doc in raid_physical_disk_docs:
                        raid_physical_disk_id = raid_physical_disk_doc.text
                        raid_physical_disk_ids.append(raid_physical_disk_id)

                    LOG.debug(
                        "Found RAID {} virtual disk {} with a size of {} "
                        "bytes comprised of physical disks:\n  {}".format(
                            RAID_TYPE_TO_DESCRIPTION[raid_type],
                            fqdd,
                            raid_size,
                            "\n  ".join(raid_physical_disk_ids)))

                    break

            # Note: This code block represents single disk scenario.
            if raid_size_gb == 0:
                if virtual_disk_docs:
                    raid0_disk_sizes = []
                    for virtual_disk_doc in virtual_disk_docs:
                        fqdd = get_fqdd(virtual_disk_doc, DCIM_VirtualDiskView)
                        raid_type = utils.find_xml(
                            virtual_disk_doc,
                            'RAIDTypes',
                            DCIM_VirtualDiskView).text

                        if raid_type == RAID0:
                            raid_size = get_size_in_bytes(virtual_disk_doc,
                                                          DCIM_VirtualDiskView)
                            raid_size_gb = int(raid_size) / units.Gi
                            raid0_disk_sizes.append(raid_size_gb)

                            # Get the physical disks that back this RAID
                            raid_physical_disk_docs = utils.find_xml(
                                virtual_disk_doc,
                                'PhysicalDiskIDs',
                                DCIM_VirtualDiskView,
                                True)

                            for raid_physical_disk_doc in \
                                    raid_physical_disk_docs:
                                raid_physical_disk_id = \
                                    raid_physical_disk_doc.text
                                raid_physical_disk_ids.append(
                                    raid_physical_disk_id)

                            LOG.debug(
                                "Found RAID {} virtual disk {} with a size of"
                                " {} "
                                "bytes comprised of physical disks:\n"
                                " {}".format(
                                    RAID_TYPE_TO_DESCRIPTION[raid_type],
                                    fqdd,
                                    raid_size,
                                    "\n  ".join(raid_physical_disk_ids)))

                            break

                    if len(raid0_disk_sizes) != 1:
                        raise RuntimeError(
                            "There must be a non-RAID0 virtual disk,"
                            "a single disk RAID0, or a single JBOD disk"
                            "to install the OS on,"
                            "or os-volume-size-gb must be specified.")
                else:
                    physical_disk_view_doc = drac_client.enumerate(
                        DCIM_PhysicalDiskView)
                    physical_disk_docs = utils.find_xml(
                        physical_disk_view_doc,
                        'DCIM_PhysicalDiskView',
                        DCIM_PhysicalDiskView,
                        True)
                    physical_disk_sizes = [
                        get_size_in_bytes(physical_disk_doc,
                                          DCIM_PhysicalDiskView)
                        for physical_disk_doc in physical_disk_docs]
                    if len(physical_disk_sizes) != 1:
                        raise RuntimeError(
                            "There must be a non-RAID0 virtual disk,"
                            "a single disk RAID0, or a single JBOD disk"
                            "to install the OS on,"
                            "or os-volume-size-gb must be specified.")

                    os_volume_size_gb = int(physical_disk_sizes[0]) / units.Gi

            # Now check to see if we have any physical disks that don't back
            # the RAID that are the same size as the RAID

            # Get the physical disks
            physical_disk_view_doc = drac_client.enumerate(
                DCIM_PhysicalDiskView)
            physical_disk_docs = utils.find_xml(physical_disk_view_doc,
                                                'DCIM_PhysicalDiskView',
                                                DCIM_PhysicalDiskView,
                                                True)

            for physical_disk_doc in physical_disk_docs:
                fqdd = get_fqdd(physical_disk_doc, DCIM_PhysicalDiskView)
                if fqdd not in raid_physical_disk_ids:
                    physical_disk_size = get_size_in_bytes(
                        physical_disk_doc, DCIM_PhysicalDiskView)
                    physical_disk_size_gb = int(physical_disk_size) / units.Gi

                    if physical_disk_size_gb == raid_size_gb:
                        # If we did find a disk that's the same size as the
                        # located RAID (in GB), then we can't tell Ironic what
                        # volume to install the OS on.
                        # Abort the install at this point instead of having
                        # the OS installed on a random volume.
                        raise RuntimeError(
                            "Physical disk {} has the same size in GB ({}) "
                            "as the RAID.  Unable to specify the OS disk to "
                            "Ironic.".format(fqdd, physical_disk_size_gb))

    if os_volume_size_gb is not None:
        # If os_volume_size_gb was specified then just blindly use that
        raid_size_gb = os_volume_size_gb
        volume_type = "volume"
    else:
        # If we didn't find a disk the same size as the located RAID, then use
        # the size of the RAID set above
        volume_type = RAID_TYPE_TO_DESCRIPTION[raid_type]

    # Set the root_device property in ironic to the volume size in gigs
    LOG.info(
        "Setting the OS volume for this node to the {} with size "
        "{} GB".format(volume_type, raid_size_gb))
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

    if not response.is_commit_required:
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

    change_state_result = drac_client.change_physical_disk_state(
        mode, controllers_to_physical_disk_ids)

    job_ids = []
    is_reboot_required = False
    # Remove the line below to turn back on realtime conversion
    is_reboot_required = True
    conversion_results = change_state_result['conversion_results']
    for controller_id in conversion_results.keys():
        controller_result = conversion_results[controller_id]

        if controller_result['is_reboot_required'] == RebootRequired.true:
            is_reboot_required = True

        if controller_result['is_commit_required']:
            realtime = controller_result['is_reboot_required'] == \
                RebootRequired.optional
            # Remove the line below to turn back on realtime conversion
            realtime = False
            job_id = drac_client.commit_pending_raid_changes(
                controller_id,
                reboot=False,
                start_time=None,
                realtime=realtime)
            job_ids.append(job_id)

    result = True
    if job_ids:
        if is_reboot_required:
            LOG.debug("Rebooting the node to apply configuration")
            job_id = drac_client.create_reboot_job()
            job_ids.append(job_id)

        drac_client.schedule_job_execution(job_ids, start_time='TIME_NOW')

        LOG.info("Waiting for physical disk conversion to complete")
        JobHelper.wait_for_job_completions(ironic_client, node_uuid)
        result = JobHelper.determine_job_outcomes(drac_client, job_ids)

    return result


def main():

    try:
        drac_client = None

        args = parse_arguments()

        LoggingHelper.configure_logging(args.logging_level)

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
                    args.os_volume_size_gb,
                    drac_client)

                if not succeeded:
                    sys.exit(1)
            else:
                LOG.info("Skipping RAID configuration")

            if not args.skip_bios_config:
                succeeded = configure_bios(
                    node,
                    ironic_client,
                    bios_settings,
                    drac_client)

                if not succeeded:
                    sys.exit(1)
            else:
                LOG.info("Skipping BIOS configuration")
        assign_role(
            args.ip_mac_service_tag,
            node.uuid,
            args.role_index,
            args.os_volume_size_gb,
            ironic_client,
            drac_client)

    except (DRACOperationFailed, DRACUnexpectedReturnValue,
            InternalServerError, KeyError, TypeError, ValueError,
            WSManInvalidResponse, WSManRequestFailure):
        LOG.exception("")
        sys.exit(1)
    except SystemExit:
        raise
    except:  # noqa: E722
        LOG.exception("Unexpected error")
        sys.exit(1)
    finally:	
        # Leave the node powered off.	
        if drac_client is not None:	
            ensure_node_is_powered_off(drac_client)

if __name__ == "__main__":
    main()
