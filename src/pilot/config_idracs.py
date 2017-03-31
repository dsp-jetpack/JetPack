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
import threading
from arg_helper import ArgHelper
from logging_helper import LoggingHelper
from utils import Utils

common_path = os.path.join(os.path.expanduser('~'), 'common')
sys.path.append(common_path)

from thread_helper import ThreadWithExHandling

# Suppress InsecureRequestWarning: Unverified HTTPS request is being made
requests.packages.urllib3.disable_warnings()

logging.basicConfig(format='(%(threadName)s)%(levelname)s:%(message)s')
LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Performs initial configuration of iDRACs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ArgHelper.add_instack_arg(parser)
    ArgHelper.add_model_properties_arg(parser)

    LoggingHelper.add_argument(parser)

    parser.add_argument("-j",
                        "--json_config",
                        default=None,
                        help="""JSON that specifies the PXE NIC FQDD and the "
                            "new password for each overcloud node""")

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

    json_config = None
    if args.json_config is not None:
        try:
            json_config = json.loads(args.json_config)
        except:
            LOG.exception("Failed to parse json_config data")
            sys.exit(1)

    try:
        model_properties = Utils.get_model_properties(args.model_properties)

        # Configure all the nodes
        if "nodes" not in instackenv:
            raise ValueError("{} must contain an array of "
                             "\"nodes\"".format(args.node_definition))

        instack_lock = threading.Lock()
        threads = []
        for node in instackenv["nodes"]:
            pxe_nic = None
            password = None
            if json_config is not None:
                node_config = None
                if node["pm_addr"] in json_config.keys():
                    node_config = json_config[node["pm_addr"]]
                elif node["service_tag"] in json_config.keys():
                    node_config = json_config[node["service_tag"]]

                if node_config is not None:
                    if "pxe_nic" in node_config.keys():
                        pxe_nic = node_config["pxe_nic"]

                    if "password" in node_config.keys():
                        password = node_config["password"]

            thread = ThreadWithExHandling(LOG,
                                          target=config_idrac.config_idrac,
                                          args=(instack_lock,
                                                node["pm_addr"],
                                                args.node_definition,
                                                model_properties,
                                                pxe_nic,
                                                password))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        failed_threads = 0
        for thread in threads:
            if thread.ex is not None:
                failed_threads += 1

        if failed_threads == 0:
            LOG.info("Successfully configured all iDRACs")
        else:
            LOG.info("Failed to configure {} out of {} iDRACs".format(
                failed_threads, len(threads)))
            sys.exit(1)
    except ValueError as ex:
        LOG.error(ex)
        sys.exit(1)
    except Exception as ex:
        LOG.exception(ex.message)
        sys.exit(1)

if __name__ == "__main__":
    main()
