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
from constants import Constants
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
from discover_nodes.dracclient.exceptions import NotFound  # noqa

# Suppress InsecureRequestWarning: Unverified HTTPS request is being made
requests.packages.urllib3.disable_warnings()

LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Performs initial configuration of an iDRAC.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ArgHelper.add_ip_service_tag(parser)

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
        ip_service_tag,
        pxe_nic_id,
        node):
    LOG.info("Configuring NIC {} on {} to PXE boot".format(
        pxe_nic_id, ip_service_tag))

    job_ids = []
    reboot_required = False
    provisioning_mac = None

    for nic in drac_client.list_nics(sort=True):
        result = None
        nic_id = nic.id

        # Compare the NIC IDs case insensitively. Assume ASCII strings.
        if nic_id.lower() == pxe_nic_id.lower():
            provisioning_mac = nic.mac_address.lower()

            # This is the NIC we want to PXE boot, so set it to PXE if it's
            # not set to PXE already
            if not drac_client.is_nic_legacy_boot_protocol_pxe(nic_id):
                result = drac_client.set_nic_legacy_boot_protocol_pxe(nic_id)
        else:
            try:
                if not drac_client.is_nic_legacy_boot_protocol_none(nic_id):
                    result = drac_client.set_nic_legacy_boot_protocol_none(
                        nic_id)
            except NotFound:
                LOG.warn("Unable to check the legacy boot protocol of NIC {} "
                         "on {}, and so cannot set it to None".format(
                             nic_id, ip_service_tag))

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

    return reboot_required, job_ids, provisioning_mac


def config_legacy_boot_setting(drac_client, ip_service_tag, node):
    LOG.info("Setting the iDRAC on {} to legacy boot".format(
        ip_service_tag))
    settings = {"BootMode": "Bios"}
    response = drac_client.set_bios_settings(settings)

    job_id = None
    if response['commit_required']:
        job_id = drac_client.commit_pending_bios_changes(reboot=False,
                                                         start_time=None)

    # Note that "commit_required" is actually "reboot_required" under the
    # covers
    return response['commit_required'], job_id


def config_idrac_settings(drac_client, ip_service_tag, password, node):
    LOG.info("Configuring initial iDRAC settings on {}".format(
        ip_service_tag))

    idrac_settings = {
        "IPMILan.1#Enable": "Enabled",
        "IPMILan.1#PrivLimit": "Administrator",
        "VirtualMedia.1#Attached": "AutoAttach",
        "WebServer.1#Enable": "Enabled",
        "IPv4.1#Enable": "Enabled",
        "Users.2#Enable": "Enabled",
        "Users.2#IpmiLanPrivilege": "Administrator",
        "Users.2#Privilege": 0x1ff
        }

    if password:
        LOG.warn("Updating the password on {}".format(ip_service_tag))
        idrac_settings["Users.2#Password"] = password

    # Set the iDRAC card attributes
    response = drac_client.set_idrac_settings(idrac_settings)

    job_id = None
    if response['commit_required']:
        job_id = drac_client.commit_pending_idrac_changes(reboot=False,
                                                          start_time=None)

    return response['reboot_required'], job_id


def clear_job_queue(drac_client, ip_service_tag):
    LOG.info("Clearing the job queue on {}".format(ip_service_tag))
    drac_client.delete_jobs()

    # It takes a second or two for the iDRAC to switch from the ready state to
    # the not-ready state, so wait for this transition to happen
    sleep(5)

    drac_client.wait_until_idrac_is_ready()


def reset_idrac(drac_client, ip_service_tag):
    LOG.info('Resetting the iDRAC on {}'.format(ip_service_tag))
    drac_client.wait_until_idrac_is_reset(False)


def config_idrac(instack_lock,
                 ip_service_tag,
                 node_definition=Constants.INSTACKENV_FILENAME,
                 model_properties=Constants.MODEL_PROPERTIES_FILENAME,
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
    ironic_driver = node["pm_type"]

    if ironic_driver != "pxe_drac":
        LOG.info("{} is using the {} driver.  No iDRAC configuration is "
                 "possible.".format(ip_service_tag, ironic_driver))

        if pxe_nic:
            LOG.warn("Ignoring specified PXE NIC ({})".format(pxe_nic))

        if password:
            LOG.warn("Ignoring specified password")

        return

    drac_client = DRACClient(drac_ip, drac_user, drac_password)

    reset_idrac(drac_client, ip_service_tag)

    # Clear out any pending jobs in the job queue and fix the condition where
    # there are no pending jobs, but the iDRAC thinks there are
    clear_job_queue(drac_client, ip_service_tag)

    pxe_nic_fqdd = get_pxe_nic_fqdd(
        pxe_nic,
        model_properties,
        drac_client)

    reboot_required = False

    # Configure the NIC port to PXE boot or not
    reboot_required_nic, job_ids, provisioning_mac = \
        configure_nics_boot_settings(drac_client,
                                     ip_service_tag,
                                     pxe_nic_fqdd,
                                     node)

    reboot_required = reboot_required or reboot_required_nic

    # Configure the system to legacy boot
    reboot_required_legacy, legacy_job_id = config_legacy_boot_setting(
        drac_client, ip_service_tag, node)
    reboot_required = reboot_required or reboot_required_legacy
    if legacy_job_id:
        job_ids.append(legacy_job_id)

    # Do initial idrac configuration
    reboot_required_idrac, idrac_job_id = config_idrac_settings(drac_client,
                                                                ip_service_tag,
                                                                password,
                                                                node)
    reboot_required = reboot_required or reboot_required_idrac
    if idrac_job_id:
        job_ids.append(idrac_job_id)

    # If we need to reboot, then add a job for it
    if reboot_required:
        LOG.info("Rebooting {} to apply configuration".format(ip_service_tag))

        job_id = drac_client.create_reboot_job()
        job_ids.append(job_id)

    success = True
    if job_ids:
        drac_client.schedule_job_execution(job_ids, start_time='TIME_NOW')

        LOG.info("Waiting for iDRAC configuration to complete on {}".format(
            ip_service_tag))
        LOG.info("Do not unplug {}".format(ip_service_tag))

        # If the user set the password, then we need to change creds
        unfinished_jobs = None
        if password:
            new_drac_client = DRACClient(drac_ip, drac_user, password)

            # Try every 10 seconds over 2 minutes to connect with the new creds
            password_changed = False
            retries = 12
            while not password_changed and retries > 0:
                try:
                    LOG.debug("Attempting to access the iDRAC on {} with the "
                              "new password".format(ip_service_tag))
                    unfinished_jobs = new_drac_client.list_jobs(
                        only_unfinished=True)
                    password_changed = True
                except exceptions.WSManInvalidResponse as ex:
                    if "unauthorized" in ex.message.lower():
                        LOG.debug("Got an unauthorized exception on {}, so "
                                  "sleeping and trying again".format(
                                      ip_service_tag))
                        retries -= 1
                        if retries > 0:
                            sleep(10)
                    else:
                        raise

            # If the new creds were successful then use them.  If they were not
            # successful then assume the attempt to change the password failed
            # and stick with the original creds
            if password_changed:
                LOG.debug("Successfully changed the password on {}.  "
                          "Switching to the new password".format(
                              ip_service_tag))
                drac_client = new_drac_client
            else:
                success = False
                # Grab the unfinished_jobs list using the original creds
                LOG.warn("Failed to change the password on {}".format(
                    ip_service_tag))
                unfinished_jobs = drac_client.list_jobs(only_unfinished=True)
        else:
            unfinished_jobs = drac_client.list_jobs(only_unfinished=True)

        # Wait up to 10 minutes for the unfinished jobs to run
        retries = 60
        while unfinished_jobs and retries > 0:
            LOG.debug("{} jobs remain to complete on {}".format(
                len(unfinished_jobs), ip_service_tag))
            retries -= 1
            if retries > 0:
                sleep(10)
                unfinished_jobs = drac_client.list_jobs(only_unfinished=True)

        if retries > 0:
            LOG.debug("All jobs have completed on {}".format(ip_service_tag))
            success = JobHelper.determine_job_outcomes(drac_client, job_ids)
        else:
            LOG.error("Timed out while waiting for jobs to complete on "
                      "{}".format(ip_service_tag))
            success = False

    # We always want to update the password for the node in the instack file
    # if the user requested a password change and the iDRAC config job was
    # successful regardless of if the other jobs succeeded or not.
    new_password = None
    if password:
        job_status = drac_client.get_job(idrac_job_id).status

        if JobHelper.job_succeeded(job_status):
            new_password = password

    if new_password is not None or \
        "provisioning_mac" not in node or \
        ("provisioning_mac" in node and
         node["provisioning_mac"] != provisioning_mac):

        # Synchronize to prevent thread collisions while saving the instack
        # file
        if instack_lock is not None:
            LOG.debug("Acquiring the lock")
            instack_lock.acquire()
        try:
            if instack_lock is not None:
                LOG.debug("Clearing and reloading instack")
                # Force a reload of the instack file
                CredentialHelper.clear_instack_cache()
                node = CredentialHelper.get_node_from_instack(ip_service_tag,
                                                              node_definition)
            if new_password is not None:
                node["pm_password"] = new_password

            node["provisioning_mac"] = provisioning_mac

            LOG.debug("Saving instack")
            CredentialHelper.save_instack(node_definition)
        finally:
            if instack_lock is not None:
                LOG.debug("Releasing the lock")
                instack_lock.release()

    if success:
        LOG.info("Completed configuration of the iDRAC on {}".format(
            ip_service_tag))
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

        config_idrac(None,
                     args.ip_service_tag,
                     args.node_definition,
                     model_properties,
                     args.pxe_nic,
                     args.change_password)
    except ValueError as ex:
        LOG.error("An error occurred while configuring iDRAC {}: {}".format(
            args.ip_service_tag, ex.message))
        sys.exit(1)
    except Exception as ex:
        LOG.exception("An error occurred while configuring iDRAC {}: "
                      "{}".format(args.ip_service_tag, ex.message))
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig()
    main()
