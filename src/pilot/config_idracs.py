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
import config_idrac
import json
import logging
import os
import requests.packages
import sys
from arg_helper import ArgHelper
from logging_helper import LoggingHelper
from utils import Utils


# Suppress InsecureRequestWarning: Unverified HTTPS request is being made
requests.packages.urllib3.disable_warnings()

logging.basicConfig()
LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Performs initial configuration of iDRACs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ArgHelper.add_instack_arg(parser)
    ArgHelper.add_model_properties_arg(parser)

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

    try:
        model_properties = Utils.get_model_properties(args.model_properties)

        # Configure all the nodes
        if "nodes" not in instackenv:
            raise ValueError("{} must contain an array of "
                             "\"nodes\"".format(args.node_definition))

        for node in instackenv["nodes"]:
            if "pm_addr" not in node:
                raise ValueError("Each node in {} must have a \"pm_addr\" "
                                 "attribute".format(args.node_definition))

            ip_service_tag = node["pm_addr"]

            succeeded = config_idrac.config_idrac(ip_service_tag,
                                                  args.node_definition,
                                                  model_properties)
            if not succeeded:
                sys.exit(1)

    except ValueError as ex:
        LOG.error(ex)
        sys.exit(1)
    except Exception as ex:
        LOG.exception(ex.message)
        sys.exit(1)

if __name__ == "__main__":
    main()
