#!/usr/bin/python

# Copyright (c) 2017-2019 Dell Inc. or its subsidiaries.
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
logger.setLevel(logging.INFO)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Introspects a specified overcloud node.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ArgHelper.add_ip_service_tag(parser)
    ArgHelper.add_inband_arg(parser)
    LoggingHelper.add_argument(parser)

    return parser.parse_args()


def main():
    args = parse_arguments()

    LoggingHelper.configure_logging(args.logging_level)

    ironic_client = IronicHelper.get_ironic_client()
    node = IronicHelper.get_ironic_node(ironic_client, args.ip_service_tag)

    introspect_nodes.introspect_nodes(args.in_band,
                                      ironic_client,
                                      [node])


if __name__ == "__main__":
    main()
