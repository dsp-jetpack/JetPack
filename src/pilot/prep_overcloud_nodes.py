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
import subprocess
from logging_helper import LoggingHelper
from credential_helper import CredentialHelper

logging.basicConfig()
logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Prepares the overcloud nodes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    LoggingHelper.add_argument(parser)

    parser.add_argument("-n",
                        "--node_type",
                        default=None,
                        help="""Prepare nodes for this specific
                         node type only""")

    return parser.parse_args()


def main():
    args = parse_arguments()

    LoggingHelper.configure_logging(args.logging_level)
    cmd = "openstack baremetal node list --fields uuid properties -f json"
    nodes = json.loads(subprocess.check_output(cmd,
                                               stderr=subprocess.STDOUT,
                                               shell=True))

    for node in nodes:
        props = node["Properties"]
        _node_type = props["node_type"] if "node_type" in props else None
        match = ((not args.node_type) or (bool(_node_type)
                                          and args.node_type == _node_type))
        if (not match):
            continue

        uuid = node["UUID"]
        # Power off the node
        logger.info("Powering off node " + uuid)
        cmd = "openstack baremetal node power off " + uuid
        logger.debug("    {}".format(cmd))
        os.system(cmd)

        # Set the first boot device to PXE
        logger.info("Setting the provisioning NIC to PXE boot on node %s ",
                    uuid)

        cmd = ("openstack baremetal node boot device set --persistent "
               + uuid + " pxe")
        logger.debug("    {}".format(cmd))
        os.system(cmd)
        cmd = ("openstack baremetal node set --driver-info "
               "force_persistent_boot_device=True " + uuid)
        logger.debug("    {}".format(cmd))
        os.system(cmd)


if __name__ == "__main__":
    main()
