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

import argparse
import json
import logging
import os
import requests.packages
import sys
from credential_helper import CredentialHelper
from ironic_helper import IronicHelper
from job_helper import JobHelper
from logging_helper import LoggingHelper

discover_nodes_path = os.path.join(os.path.expanduser('~'),
                                   'pilot/discover_nodes')
sys.path.append(discover_nodes_path)

from discover_nodes.dracclient.client import DRACClient  # noqa

# Suppress InsecureRequestWarning: Unverified HTTPS request is being made
requests.packages.urllib3.disable_warnings()

logging.basicConfig()
LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Performs initial configuration of iDRACs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("ip_service_tag",
                        help="""IP address of the iDRAC,
                                or service tag of the node""",
                        metavar="ADDRESS")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-p",
                       "--pxe-nic",
                       help="""fully qualified device descriptor (FQDD) of
                               network interface to PXE boot from""",
                       metavar="FQDD")
    group.add_argument("-m",
                       "--model-properties",
                       help="""file that defines Dell system model properties,
                               including FQDD of network interface to PXE boot
                               from""",
                       metavar="FILENAME")
    parser.add_argument("-n",
                        "--node-definition",
                        default="~/instackenv.json",
                        help="""node definition template file that defines the
                                node being assigned""",
                        metavar="FILENAME")

    LoggingHelper.add_argument(parser)

    return parser.parse_args()


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


def get_drac_client(node_definition_filename, node):
    drac_ip, drac_user, drac_password = \
        CredentialHelper.get_drac_creds_from_node(node,
                                                  node_definition_filename)
    return DRACClient(drac_ip, drac_user, drac_password)


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


def configure_nics_boot_settings(
        drac_client,
        pxe_nic_id,
        ironic_client,
        node):
    LOG.info("Configuring NIC {} on {} to PXE boot".format(
        pxe_nic_id,
        CredentialHelper.get_drac_ip(node)))

    job_ids = []
    reboot_required = False

    for nic in drac_client.list_nics(sort=True):
        result = None
        nic_id = nic.id

        # Compare the NIC IDs case insensitively. Assume ASCII strings.
        if nic_id.lower() == pxe_nic_id.lower():

            # Set the MAC for the provisioning/PXE interface on the node for
            # use by the OOB introspection workaround
            patch = [{'op': 'add',
                      'value': nic.mac_address.lower(),
                      'path': '/properties/provisioning_mac'}]
            ironic_client.node.update(node.uuid, patch)

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
    JobHelper.wait_for_job_completions(ironic_client, node.uuid)
    LOG.info("Completed NIC configuration")

    return JobHelper.determine_job_outcomes(drac_client, job_ids)


def config_idrac(ip_service_tag, node_definition,
                 model_properties_filename="~/pilot/dell_systems.json",
                 pxe_nic=None):
    model_properties = get_model_properties(
        pxe_nic,
        model_properties_filename)

    ironic_client = IronicHelper.get_ironic_client()

    node = IronicHelper.get_ironic_node(ironic_client,
                                        ip_service_tag)
    if node is None:
        LOG.critical("Unable to find node {}".format(
                     ip_service_tag))
        sys.exit(1)

    drac_client = get_drac_client(node_definition, node)

    pxe_nic_fqdd = get_pxe_nic_fqdd(
        pxe_nic,
        model_properties,
        drac_client)

    if pxe_nic_fqdd is None:
        sys.exit(1)

    return configure_nics_boot_settings(
        drac_client,
        pxe_nic_fqdd,
        ironic_client,
        node)


def main():
    args = parse_arguments()

    root_logger = logging.getLogger()
    root_logger.setLevel(args.logging_level)
    urllib3_logger = logging.getLogger("requests.packages.urllib3")
    urllib3_logger.setLevel(logging.WARN)

    qwargs = {"ip_service_tag": args.ip_service_tag,
              "node_definition": args.node_definition,
              "pxe_nic": args.pxe_nic}

    if args.model_properties:
        qwargs["model_properties_filename"] = args.model_properties

    succeeded = config_idrac(**qwargs)

    if not succeeded:
        sys.exit(1)


if __name__ == "__main__":
    main()
