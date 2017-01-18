#!/usr/bin/python

# Copyright (c) 2017 Dell Inc. or its subsidiaries.
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
import logging
import os
import requests.packages
import sys
from arg_helper import ArgHelper
from credential_helper import CredentialHelper
from dracclient import exceptions
from job_helper import JobHelper
from logging_helper import LoggingHelper
from time import sleep
from utils import Utils

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
        description="Performs initial configuration of an iDRAC.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("ip_service_tag",
                        help="""IP address of the iDRAC
                                or service tag of the node""",
                        metavar="ADDRESS")
    parser.add_argument("-p",
                        "--pxe-nic",
                        help="""fully qualified device descriptor (FQDD) of
                                network interface to PXE boot from""",
                        metavar="FQDD")
    parser.add_argument("-c",
                        "--change-password",
                        help="The new password for the root user")

    ArgHelper.add_instack_arg(parser)
    ArgHelper.add_model_properties_arg(parser)

    LoggingHelper.add_argument(parser)

    return parser.parse_args()


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
        raise ValueError("NIC to PXE boot from, {}, does not exist; "
                         "available NICs are {}".format(
                             pxe_nic_fqdd,
                             ', '.join(nic_fqdds)))

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
        node):
    LOG.info("Configuring NIC {} on {} to PXE boot".format(
        pxe_nic_id, node["pm_addr"]))

    job_ids = []
    reboot_required = False

    for nic in drac_client.list_nics(sort=True):
        result = None
        nic_id = nic.id

        # Compare the NIC IDs case insensitively. Assume ASCII strings.
        if nic_id.lower() == pxe_nic_id.lower():
            # Set the MAC for the provisioning/PXE interface on the node for
            # use by the OOB introspection workaround
            node["provisioning_mac"] = nic.mac_address.lower()

            # This is the NIC we want to PXE boot, so set it to PXE if it's
            # not set to PXE already
            if not drac_client.is_nic_legacy_boot_protocol_pxe(nic_id):
                result = drac_client.set_nic_legacy_boot_protocol_pxe(nic_id)
        else:
            if not drac_client.is_nic_legacy_boot_protocol_none(nic_id):
                result = drac_client.set_nic_legacy_boot_protocol_none(nic_id)

        if result is None:
            continue

        if result['commit_required']:
            job_id = drac_client.create_nic_config_job(
                nic_id,
                reboot=False,
                start_time=None)
            job_ids.append(job_id)

        if result['reboot_required']:
            reboot_required = True

    return reboot_required, job_ids


def config_idrac_settings(drac_client, password, node):
    LOG.info("Configuring initial iDRAC settings on {}".format(
        node["pm_addr"]))

    idrac_settings = {
        "IPMILan.1#Enable": "Enabled",
        "IPMILan.1#PrivLimit": "Administrator",
        "WebServer.1#Enable": "Enabled",
        "IPv4.1#Enable": "Enabled",
        "Users.2#Enable": "Enabled",
        "Users.2#IpmiLanPrivilege": "Administrator",
        "Users.2#Privilege": 0x1ff
        }

    if password:
        LOG.warn("Updating the password")
        idrac_settings["Users.2#Password"] = password

    # Set the iDRAC card attributes
    response = drac_client.set_idrac_settings(idrac_settings)

    job_id = None
    if response['commit_required']:
        job_id = drac_client.commit_pending_idrac_changes(reboot=False,
                                                          start_time=None)

    return response['reboot_required'], job_id


def config_idrac(ip_service_tag,
                 node_definition,
                 model_properties,
                 pxe_nic=None,
                 password=None):
    node = CredentialHelper.get_node_from_instack(ip_service_tag,
                                                  node_definition)
    if not node:
        raise ValueError("Unable to find {} in {}".format(ip_service_tag,
                                                          node_definition))
    drac_ip = node["pm_addr"]
    drac_user = node["pm_user"]
    drac_password = node["pm_password"]

    drac_client = DRACClient(drac_ip, drac_user, drac_password)

    pxe_nic_fqdd = get_pxe_nic_fqdd(
        pxe_nic,
        model_properties,
        drac_client)

    reboot_required_nic, job_ids = configure_nics_boot_settings(drac_client,
                                                                pxe_nic_fqdd,
                                                                node)

    reboot_required_idrac, idrac_job_id = config_idrac_settings(drac_client,
                                                                password,
                                                                node)
    if idrac_job_id:
        job_ids.append(idrac_job_id)

    if reboot_required_nic or reboot_required_idrac:
        LOG.info("Rebooting the node to apply configuration")

        job_id = drac_client.create_reboot_job()
        job_ids.append(job_id)

    success = True
    if job_ids:
        drac_client.schedule_job_execution(job_ids, start_time='TIME_NOW')

        LOG.info("Waiting for iDRAC configuration to complete")
        LOG.info("Do not unplug the node")

        # If the user set the password, then we need to change creds
        unfinished_jobs = None
        if password:
            new_drac_client = DRACClient(drac_ip, drac_user, password)

            # Try 3 times over 30 seconds to connect with the new creds
            success = False
            retries = 3
            while not success and retries > 0:
                try:
                    LOG.debug("Attempting to access the iDRAC with the new "
                              "password")
                    unfinished_jobs = new_drac_client.list_jobs(
                        only_unfinished=True)
                    success = True
                except exceptions.WSManInvalidResponse as ex:
                    if "unauthorized" in ex.message.lower():
                        LOG.debug("Got an unauthorized exception, so sleeping "
                                  "and trying again")
                        retries -= 1
                        if retries > 0:
                            sleep(10)
                    else:
                        raise

            # If the new creds were successful then use them.  If they were not
            # successful then assume the attempt to change the password failed
            # and stick with the original creds
            if success:
                LOG.debug("Success.  Switching to the new password")
                drac_client = new_drac_client
            else:
                LOG.warn("Failed to change the password")

        else:
            unfinished_jobs = drac_client.list_jobs(only_unfinished=True)

        # Wait for the unfinished jobs to run
        while unfinished_jobs:
            LOG.debug("{} jobs remain to complete".format(
                len(unfinished_jobs)))
            sleep(10)
            unfinished_jobs = drac_client.list_jobs(only_unfinished=True)

        LOG.debug("All jobs have completed")
        success = JobHelper.determine_job_outcomes(drac_client, job_ids)

    # We always want to update the password for the node in the instack file
    # if the user requested a password change and the iDRAC config job was
    # successful regardless of if the other jobs succeeded or not.
    if password:
        job_status = drac_client.get_job(idrac_job_id).status

        if JobHelper.job_succeeded(job_status):
            node["pm_password"] = password

    CredentialHelper.save_instack(node_definition)

    if success:
        LOG.info("Completed iDRAC configuration")
    else:
        raise RuntimeError("An error occurred while configuring the iDRAC "
                           "on {}".format(drac_ip))


def main():
    args = parse_arguments()

    root_logger = logging.getLogger()
    root_logger.setLevel(args.logging_level)
    urllib3_logger = logging.getLogger("requests.packages.urllib3")
    urllib3_logger.setLevel(logging.WARN)

    try:
        model_properties = Utils.get_model_properties(args.model_properties)

        config_idrac(args.ip_service_tag,
                     args.node_definition,
                     model_properties,
                     args.pxe_nic,
                     args.change_password)
    except ValueError as ex:
        LOG.error(ex)
        sys.exit(1)
    except Exception as ex:
        LOG.exception(ex.message)
        sys.exit(1)


if __name__ == "__main__":
    main()
