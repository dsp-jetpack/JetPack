#!/usr/bin/python

# Copyright (c) 2016-2017 Dell Inc. or its subsidiaries.
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
import dracclient.wsman
import logging
import lxml
import requests.packages


# Suppress InsecureRequestWarning: Unverified HTTPS request is being made.
# See
# https://urllib3.readthedocs.org/en/latest/security.html#disabling-warnings.
# It emanates from the urllib3 instance inside of the requests package.
requests.packages.urllib3.disable_warnings()

logging.basicConfig()


def main():
    # Parse the command line arguments.
    parser = argparse.ArgumentParser(description='Probe iDRACs.')
    parser.add_argument("idrac", nargs='+', help='IP addresses of iDRACs')
    parser.add_argument("-u",
                        "--username",
                        default='',
                        help='username for accessing the iDRACs')
    parser.add_argument("-p",
                        "--password",
                        default='',
                        help='password for accessing the iDRACs')
    parser.add_argument("-m", "--mofs", default='',
                        help='A comma separated list of MOFs to retrieve')

    parser.add_argument("-l",
                        "--logging-level",
                        default="INFO",
                        choices=["CRITICAL", "ERROR", "WARNING",
                                 "INFO", "DEBUG"],
                        help="""logging level defined by the logging
                                module; choices include CRITICAL, ERROR,
                                WARNING, INFO, and DEBUG""",
                        metavar="LEVEL")

    args = parser.parse_args()

    root_logger = logging.getLogger()
    root_logger.setLevel(args.logging_level)
    urllib3_logger = logging.getLogger("requests.packages.urllib3")
    urllib3_logger.setLevel(logging.WARN)

    # List of Dell Common Information Models (DCIM) to enumerate.
    #
    # The Dell Common Information Model (DCIM) Extensions Library Managed
    # Object Format (MOF) Collection is available at
    # http://en.community.dell.com/techcenter/systems-management/w/wiki/1840.
    if args.mofs:
        dcims = args.mofs.split(",")
    else:
        dcims = [
            'DCIM_SystemView',
            'DCIM_PhysicalDiskView',
            'DCIM_VirtualDiskView',
            'DCIM_CPUView',
            'DCIM_NICView',
            'DCIM_NICStatistics',
        ]

    # Probe each iDRAC specified on the command line.
    for i in args.idrac:
        # Identify the iDRAC.
        print i + ':'

        # Create client for talking to the iDRAC over the WSMan protocol.
        client = dracclient.wsman.Client(i, args.username, args.password)

        # Enumerate and pretty print each DCIM in the list.
        for d in dcims:
            response = client.enumerate(
                'http://schemas.dell.com/wbem/wscim/1/cim-schema/2/' + d)
            print lxml.etree.tostring(response, pretty_print=True)

if __name__ == "__main__":
    main()
