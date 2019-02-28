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

import argparse
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

    return parser.parse_args()


def main():
    args = parse_arguments()

    LoggingHelper.configure_logging(args.logging_level)

    cmd = "source ~/stackrc;openstack baremetal node list -f value -c UUID"
    nodes = subprocess.check_output(cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)

    for node in nodes.splitlines():
        if len(node) < 1:
            continue
        # Power off the node
        logger.info("Powering off node " + node)
        cmd = "openstack baremetal node power off " + node
        logger.debug("    {}".format(cmd))
        os.system(cmd)

        # Set the first boot device to PXE
        logger.info("Setting the provisioning NIC to PXE boot on node " + node)

        cmd = "openstack baremetal node boot device set --persistent " + \
            node + " pxe"
        logger.debug("    {}".format(cmd))
        os.system(cmd)
        cmd = "openstack baremetal node set --driver-info " + \
              "force_persistent_boot_device=True " + node
        logger.debug("    {}".format(cmd))
        os.system(cmd)


if __name__ == "__main__":
    main()
