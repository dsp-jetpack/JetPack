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
import config_idrac
import json
import logging
import os
import requests.packages
import sys
from logging_helper import LoggingHelper


# Suppress InsecureRequestWarning: Unverified HTTPS request is being made
requests.packages.urllib3.disable_warnings()

logging.basicConfig()
LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Performs initial configuration of iDRACs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-n",
                        "--node-definition",
                        default="~/instackenv.json",
                        help="""node definition template file that defines the
                                node being assigned""",
                        metavar="FILENAME")

    LoggingHelper.add_argument(parser)

    return parser.parse_args()


def main():
    args = parse_arguments()

    root_logger = logging.getLogger()
    root_logger.setLevel(args.logging_level)
    urllib3_logger = logging.getLogger("requests.packages.urllib3")
    urllib3_logger.setLevel(logging.WARN)

    try:
        json_file = os.path.expanduser(args.node_definition)
        with open(json_file, 'r') as instackenv_json:
            instackenv = json.load(instackenv_json)
    except (IOError, ValueError):
        LOG.exception("Failed to load node definition file {}".format(
                      args.node_definition))
        sys.exit(1)

    # Configure all the nodes
    for node in instackenv["nodes"]:
        ip_service_tag = node["pm_addr"]

        config_idrac.config_idrac(ip_service_tag, args.node_definition)


if __name__ == "__main__":
    main()
