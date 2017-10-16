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

import argparse
import logging
import os
import sys
from credential_helper import CredentialHelper
from ironic_helper import IronicHelper
from logging_helper import LoggingHelper
from time import sleep

logging.basicConfig()
logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Introspects the overcloud nodes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    LoggingHelper.add_argument(parser)

    parser.add_argument("-i", "--in-band",
                        help="Use in-band (PXE booting) introspection",
                        action="store_true")

    return parser.parse_args()


def is_introspection_oob(in_band, node, logger):
    out_of_band = True

    if in_band:
        # All drivers support in-band introspection
        out_of_band = False
    elif node.driver == "pxe_ipmitool":
        # Can't do in-band introspection with the IPMI driver
        logger.warn("The Ironic IPMI driver does not support out-of-band "
                    "introspection.  Using in-band introspection")
        out_of_band = False

    if out_of_band and "provisioning_mac" not in node.properties:
        raise RuntimeError("{} ({})must have config_idrac.py run against it "
                           "before running out-of-band introspection.".format(
                               CredentialHelper.get_drac_ip(node), node.uuid))

    return out_of_band


def transition_to_state(ironic_client, nodes, transition,
                        target_provision_state):
    for node in nodes:
        if node.provision_state == target_provision_state:
            logger.debug("Node {} ({}) is already in the {} state".format(
                CredentialHelper.get_drac_ip(node),
                node.uuid,
                target_provision_state))
        else:
            logger.debug("Transitioning node {} ({}) into the {} "
                         "state".format(CredentialHelper.get_drac_ip(node),
                                        node.uuid, target_provision_state))
            ironic_client.node.set_provision_state(node.uuid, transition)

    # Wait until all the nodes transition to the target provisioning state
    logger.debug("Waiting for transition to the {} state".format(
        target_provision_state))
    node_uuids = [node.uuid for node in nodes]
    while node_uuids:
        for node in ironic_client.node.list(fields=["driver_info",
                                                    "provision_state",
                                                    "uuid"]):
            if node.uuid in node_uuids:
                if node.provision_state != target_provision_state:
                    logger.debug("Node {} ({}) is still in the {} "
                                 "state".format(
                                     CredentialHelper.get_drac_ip(node),
                                     node.uuid,
                                     node.provision_state))
                    break
                else:
                    node_uuids.remove(node.uuid)

        if node_uuids:
            sleep(1)
        else:
            break


def oob_introspect_nodes(ironic_client, nodes):
    transition_to_state(ironic_client, nodes, 'manage', 'manageable')

    bad_nodes = []
    for node in nodes:
        logger.info("Starting out-of-band introspection on node "
                    "{} ({})".format(CredentialHelper.get_drac_ip(node),
                                     node.uuid))
        return_code = os.system("openstack baremetal node inspect " +
                                node.uuid)
        if return_code != 0:
            bad_nodes.append(node)

    if bad_nodes:
        ips = [CredentialHelper.get_drac_ip(node) for node in bad_nodes]
        raise RuntimeError("Failed to introspect {}".format(", ".join(ips)))

    # Rebuild the list of nodes to get the updated provisioning state
    node_uuids = [node.uuid for node in nodes]
    tmp_nodes = ironic_client.node.list(fields=["driver_info",
                                                "properties",
                                                "provision_state",
                                                "uuid"])

    refreshed_nodes = []
    for tmp_node in tmp_nodes:
        if tmp_node.uuid in node_uuids:
            refreshed_nodes.append(tmp_node)

    transition_to_state(ironic_client, refreshed_nodes,
                        'provide', 'available')

    # FIXME: Remove this hack when OOB introspection is fixed
    for node in nodes:
        delete_non_pxe_ports(ironic_client, node)


def delete_non_pxe_ports(ironic_client, node):
    ip = CredentialHelper.get_drac_ip(node)

    logger.info("Deleting all non-PXE ports from node {} ({})...".format(
        ip, node.uuid))

    for port in ironic_client.node.list_ports(node.uuid):
        if port.address.lower() != \
                node.properties["provisioning_mac"].lower():
            logger.info("Deleting port {} ({}) {}".format(
                ip, node.uuid, port.address.lower()))
            ironic_client.port.delete(port.uuid)


def main():
    args = parse_arguments()

    LoggingHelper.configure_logging(args.logging_level)

    ironic_client = IronicHelper.get_ironic_client()
    out_of_band = is_introspection_oob(
        args.in_band, ironic_client.node.list(
            fields=["driver", "properties"])[0], logger)

    if out_of_band:
        # Check to see if provisioning_mac has been set on all the nodes
        bad_nodes = []
        for node in ironic_client.node.list(fields=["uuid", "driver_info",
                                                    "properties"]):
            if "provisioning_mac" not in node.properties:
                bad_nodes.append(node)

        if bad_nodes:
            ips = [CredentialHelper.get_drac_ip(node) for node in bad_nodes]
            fail_msg = "\n".join(ips)

            logger.error("The following nodes must have config_idrac.py run "
                         "on them before running out-of-band introspection:"
                         "\n{}".format(fail_msg))
            sys.exit(1)

        nodes = ironic_client.node.list(fields=[
                    "driver",
                    "driver_info",
                    "properties",
                    "provision_state",
                    "uuid"])
        oob_introspect_nodes(ironic_client, nodes)
    else:
        logger.info("Starting in-band introspection")
        return_code = os.system("openstack baremetal introspection bulk start")
        if return_code != 0:
            logger.error("Introspection failed")
            sys.exit(1)

        # The PERC H740P RAID controller only makes virtual disks visible.
        # Physical disks are invisible with this controller because it does
        # not support pass-through mode.  This results in local_gb not being
        # set during IB introspection, which causes problems further along in
        # the flow.

        # Check to see if all nodes have local_gb defined, and if not run OOB
        # introspection to discover local_gb.
        bad_nodes = []
        nodes = ironic_client.nodes.node.list(fields=[
                    "driver",
                    "driver_info",
                    "properties",
                    "provision_state",
                    "uuid"])
        for node in nodes:
            if 'local_gb' not in node.properties:
                bad_nodes.append(node)

        ips = [CredentialHelper.get_drac_ip(node) for node in bad_nodes]
        fail_msg = "\n".join(ips)

        logger.info("local_gb was not discovered on the following nodes:"
                    "\n{}".format(fail_msg))

        logger.info("These nodes may have a RAID controller that does not "
                    "support pass-through mode such as the PERC H740P.  "
                    "Running OOB introspection against these nodes to "
                    "populate local_gb.")
        oob_introspect_nodes(ironic_client, bad_nodes)

if __name__ == "__main__":
    main()
