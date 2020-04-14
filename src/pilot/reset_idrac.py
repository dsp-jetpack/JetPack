#!/usr/bin/python

# Copyright (c) 2017-2020 Dell Inc. or its subsidiaries.
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
from dracclient import client
from dracclient import wsman
from dracclient import exceptions
from dracclient.resources import uris
from dracclient.resources import nic
import boot_mode_helper
from boot_mode_helper import BootModeHelper
from constants import Constants
from credential_helper import CredentialHelper
from job_helper import JobHelper
from logging_helper import LoggingHelper
from time import sleep
from utils import Utils

# Suppress InsecureRequestWarning: Unverified HTTPS request is being made
requests.packages.urllib3.disable_warnings()

LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Performs initial configuration of an iDRAC.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    ArgHelper.add_ip_service_tag(parser)

    parser.add_argument("-u",
                        "--user",
                        help="""username""",
                        metavar="user")
    parser.add_argument("-p",
                        "--password",
                        help="Password",
                        metavar="password")



    LoggingHelper.add_argument(parser)

    return parser.parse_args()



def main():
    args = parse_arguments()

    LoggingHelper.configure_logging(args.logging_level)
    LOG.info(args)
    try:
        drac_client = client.DRACClient(args.ip_service_tag,
                                        args.user, args.password)
         # def reset_idrac(self, force=False, wait=False,
        #                 ready_wait_time=30):
        LOG.info('Resetting the iDRAC on {}'.format(args.ip_service_tag))
        drac_client.reset_idrac(force=True, wait=True, ready_wait_time=60)
        # reset_idrac(drac_client, args.ip_service_tag)

    except Exception as ex:
        LOG.exception("An error occurred while configuring iDRAC {}: "
                      "{}".format(args.ip_service_tag, ex.message))
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig()
    main()
