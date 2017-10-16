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
import introspect_nodes
import logging
import os
import sys
from arg_helper import ArgHelper
from ironic_helper import IronicHelper
from logging_helper import LoggingHelper

logging.basicConfig()
logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])
logger.setLevel(logging.DEBUG)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Introspects a specified overcloud node.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ArgHelper.add_ip_service_tag(parser)

    LoggingHelper.add_argument(parser)

    parser.add_argument("-i", "--in-band",
                        help="Use in-band (PXE booting) introspection",
                        action="store_true")

    return parser.parse_args()


def main():
    args = parse_arguments()

    LoggingHelper.configure_logging(args.logging_level)

    ironic_client = IronicHelper.get_ironic_client()
    node = IronicHelper.get_ironic_node(ironic_client, args.ip_service_tag)

    if introspect_nodes.is_introspection_oob(args.in_band, node, logger):
        introspect_nodes.oob_introspect_nodes(ironic_client, [node])
    else:
        introspect_nodes.transition_to_state(ironic_client, [node],
                                             'manage', 'manageable')

        logger.info("Starting in-band introspection on node {} ({})".format(
            args.ip_service_tag, node.uuid))
        return_code = os.system("openstack overcloud node introspect "
                                "{}".format(node.uuid))

        if return_code != 0:
            logger.error("Failed to introspect node {} ({})".format(
                args.ip_service_tag, node.uuid))
            sys.exit(1)

        introspect_nodes.transition_to_state(
            ironic_client,
            [ironic_client.node.get(node.uuid)],
            'provide',
            'available')


if __name__ == "__main__":
    main()
