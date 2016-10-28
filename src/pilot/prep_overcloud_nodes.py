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

    root_logger = logging.getLogger()
    root_logger.setLevel(args.logging_level)
    urllib3_logger = logging.getLogger("requests.packages.urllib3")
    urllib3_logger.setLevel(logging.WARN)

    ironic_client = IronicHelper.get_ironic_client()

    for node in ironic_client.node.list(detail=True):
        ip, username, password = \
            CredentialHelper.get_drac_creds_from_node(node)

        # Power off the node
        cmd = "ipmitool -H {} -I lanplus -U {} -P '{}' chassis " \
            "power off".format(ip, username, password)
        logger.info("Powering off {}".format(ip))
        logger.info("    {}".format(cmd))
        os.system(cmd)

        # Set the first boot device to PXE
        cmd = "ipmitool -H {} -I lanplus -U {} -P '{}' chassis " \
            "bootdev pxe options=persistent".format(ip, username, password)
        logger.info("Setting the provisioning NIC to PXE boot on {}".format(
            ip))
        logger.info("    {}".format(cmd))
        os.system(cmd)

    cmd = "openstack baremetal configure boot"
    logger.info(cmd)
    os.system(cmd)


if __name__ == "__main__":
    main()
