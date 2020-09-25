#!/usr/bin/python3

# Copyright (c) 2016-2020 Dell Inc. or its subsidiaries.
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
import sys
import utils
from arg_helper import ArgHelper
from command_helper import Exec
from ironic_helper import IronicHelper
from logging_helper import LoggingHelper

logging.basicConfig()
logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])

DOWNSTREAM_ATTRS = ["model", "provisioning_mac", "service_tag",
                    "subnet", "node_type"]


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Loads nodes into ironic.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ArgHelper.add_instack_arg(parser)

    LoggingHelper.add_argument(parser)

    return parser.parse_args()


def main():
    args = parse_arguments()

    LoggingHelper.configure_logging(args.logging_level)

    # Load the nodes into ironic
    import_json = os.path.expanduser('~/nodes.json')
    content = json.load(open(args.node_definition))
    for node in content['nodes']:
        for k in list(node.keys()):
            if k in DOWNSTREAM_ATTRS:
                node.pop(k)
    with open(import_json, 'w') as out:
        json.dump(content, out)
    logger.info("Importing {} into ironic".format(args.node_definition))
    cmd = ["openstack", "overcloud", "node", "import", import_json]

    exit_code, stdin, stderr = Exec.execute_command(cmd)
    if exit_code != 0:
        logger.error("Failed to import nodes into ironic: {}, {}".format(
            stdin, stderr))
        sys.exit(1)

    # Load the instack file
    try:
        json_file = os.path.expanduser(args.node_definition)
        with open(json_file, 'r') as instackenv_json:
            instackenv = json.load(instackenv_json)
    except (IOError, ValueError):
        logger.exception("Failed to load node definition file {}".format(
                         args.node_definition))
        sys.exit(1)

    nodes = instackenv["nodes"]

    # Loop thru the nodes
    for node in nodes:
        # Find the node in ironic
        ironic_client = IronicHelper.get_ironic_client()
        ironic_node = IronicHelper.get_ironic_node(ironic_client,
                                                   node["pm_addr"])

        # Set the model and service tag on the node
        logger.info("Setting model ({}), service tag ({}), and provisioning "
                    "MAC ({}) on {}".format(
                        node["model"] if "model" in node else "None",
                        node["service_tag"],
                        node["provisioning_mac"] if "provisioning_mac" in
                        node else "None",
                        node["pm_addr"]))
        patch = [{'op': 'add',
                  'value': node["service_tag"],
                  'path': '/properties/service_tag'}]

        if "model" in node:
            patch.append({'op': 'add',
                          'value': node["model"],
                          'path': '/properties/model'})
        if "node_type" in node:
            patch.append({'op': 'add',
                          'value': node["node_type"],
                          'path': '/properties/node_type'})

        if "provisioning_mac" in node:
            patch.append({'op': 'add',
                          'value': node["provisioning_mac"],
                          'path': '/properties/provisioning_mac'})

            logger.info("Adding port with physical address to node: %s",
                        str(ironic_node.uuid))
            subnet = "ctlplane"
            if "subnet" in node:
                subnet = node["subnet"]
            kwargs = {'address': node["provisioning_mac"],
                      'physical_network': subnet,
                      'node_uuid': ironic_node.uuid}
            ironic_client.port.create(**kwargs)

        ironic_client.node.update(ironic_node.uuid, patch)


if __name__ == "__main__":
    main()
