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
import logging
import os
import sys
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

    return parser.parse_args()


def transition_to_state(ironic_client, transition, target_provision_state):
    logger.info("Transitioning nodes into the {} state".format(
        target_provision_state))
    for node in ironic_client.node.list(fields=["uuid", "provision_state"]):
        if node.provision_state == target_provision_state:
            logger.info("Node {} is already in the {} state".format(
                node.uuid, target_provision_state))
        else:
            logger.info("Transitioning node {} into the {} "
                        "state".format(node.uuid, target_provision_state))
            ironic_client.node.set_provision_state(node.uuid, transition)

    # Wait until all the nodes transition to the target provisioning state
    logger.info("Waiting for all nodes to transition to the {} state".format(
        target_provision_state))
    waiting_for_nodes = True
    while waiting_for_nodes:
        all_nodes_transitioned = True
        for node in ironic_client.node.list(fields=["uuid",
                                                    "provision_state"]):
            if node.provision_state != target_provision_state:
                logger.info("Node {} is still in the {} state".format(
                    node.uuid, node.provision_state))
                all_nodes_transitioned = False
                break

        if not all_nodes_transitioned:
            sleep(1)
        else:
            waiting_for_nodes = False


def main():
    args = parse_arguments()

    root_logger = logging.getLogger()
    root_logger.setLevel(args.logging_level)
    urllib3_logger = logging.getLogger("requests.packages.urllib3")
    urllib3_logger.setLevel(logging.WARN)

    ironic_client = IronicHelper.get_ironic_client()

    # Transition all nodes into manageable
    transition_to_state(ironic_client, 'manage', 'manageable')

    # Launch OOB introspection
    logger.info("Introspecting nodes")
    for node in ironic_client.node.list(fields=["uuid"]):
        logger.info("Introspecting node {}".format(node.uuid))
        return_code = os.system("openstack baremetal node inspect " +
                                node.uuid)
        if return_code != 0:
            logger.error("Failed to introspection node {}".format(node.uuid))
            sys.exit(1)

    # Transition all nodes into available
    transition_to_state(ironic_client, 'provide', 'available')


if __name__ == "__main__":
    main()
