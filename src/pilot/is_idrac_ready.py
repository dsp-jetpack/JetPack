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
from logging_helper import LoggingHelper

discover_nodes_path = os.path.join(os.path.expanduser('~'),
                                   'pilot/discover_nodes')
sys.path.append(discover_nodes_path)

from discover_nodes.dracclient.client import DRACClient  # noqa

# Suppress InsecureRequestWarning: Unverified HTTPS request is being made
requests.packages.urllib3.disable_warnings()

logging.basicConfig()
LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


def main():
    parser = argparse.ArgumentParser(
        description="Queries an iDRAC to determine if it is ready to process "
                    "commands.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ArgHelper.add_ip_service_tag(parser)
    ArgHelper.add_instack_arg(parser)
    LoggingHelper.add_argument(parser)

    args = parser.parse_args()

    root_logger = logging.getLogger()
    root_logger.setLevel(args.logging_level)
    urllib3_logger = logging.getLogger("requests.packages.urllib3")
    urllib3_logger.setLevel(logging.WARN)

    ip_service_tag = args.ip_service_tag
    node_definition = args.node_definition

    return_code = 0

    try:
        node = CredentialHelper.get_node_from_instack(ip_service_tag,
                                                      node_definition)
        if not node:
            raise ValueError("Unable to find {} in {}".format(ip_service_tag,
                                                              node_definition))
        drac_ip = node["pm_addr"]
        drac_user = node["pm_user"]
        drac_password = node["pm_password"]

        drac_client = DRACClient(drac_ip, drac_user, drac_password)

        ready = drac_client.is_idrac_ready()

        if ready:
            LOG.info("iDRAC is ready")
        else:
            return_code = 1
            LOG.info("iDRAC is NOT ready")
    except:
        LOG.exception("An exception occurred:")
        return_code = 2

    sys.exit(return_code)

if __name__ == "__main__":
    main()
