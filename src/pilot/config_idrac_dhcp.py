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
import re
import sys
from command_helper import Scp
from command_helper import Ssh
from getpass import getpass
from logging_helper import LoggingHelper
from network_helper import NetworkHelper

logging.basicConfig()
LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


def parse_arguments(sah_user):
    parser = argparse.ArgumentParser(
        description="Configures DHCP server on SAH node for use by iDRACs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("sah_ip",
                        help="""The IP address of the SAH node on the
                                provisioning network""")
    parser.add_argument("-p",
                        "--password",
                        help="The {} password of the SAH node".format(
                             sah_user))
    LoggingHelper.add_argument(parser)

    return parser.parse_args()


def main():
    sah_user = "root"
    args = parse_arguments(sah_user)

    root_logger = logging.getLogger()
    root_logger.setLevel(args.logging_level)
    paramiko_logger = logging.getLogger("paramiko")
    paramiko_logger.setLevel(logging.WARN)

    sah_password = args.password
    if not sah_password:
        sah_password = getpass("Enter the password for the "
                               "{} user of the SAH node: ".format(sah_user))

    management_net = NetworkHelper.get_management_network()

    dhcp_conf = os.path.join(os.path.expanduser('~'), 'pilot', 'dhcpd.conf')
    LOG.info("Creating dhcp configuration file {}".format(dhcp_conf))
    dhcp_conf_template = os.path.join(os.path.expanduser('~'), 'pilot',
                                      'templates', 'dhcpd.conf')

    try:
        file = open(dhcp_conf_template, 'r')
        file_text = file.read()
    except IOError:
        LOG.exception("Could not open dhcp.conf template file {}".format(
                      dhcp_conf_template))
        sys.exit(1)

    token_map = {}
    token_map["SUBNET"] = str(management_net.network)
    token_map["NETMASK"] = str(management_net.netmask)
    token_map["BROADCAST"] = str(management_net.broadcast)
    token_map["GATEWAY"] = NetworkHelper.get_management_network_gateway()

    for token in token_map.keys():
        file_text = file_text.replace(token, token_map[token])

    # Get the management network pools
    management_net_pools = NetworkHelper.get_management_network_pools()

    # Plug in the management pool ranges
    range_lines = ""
    for pool in management_net_pools:
        range_lines += "		range {} {};\n".format(
            pool["start"], pool["end"])

    file_text = re.sub("[ \t]*range[ \t]+POOL_START[ \t]+POOL_END;\n",
                       range_lines, file_text)

    try:
        with open(dhcp_conf, 'w') as file:
            file.write(file_text)
    except IOError:
        LOG.exception("Could not open {} for writing.".format(dhcp_conf))
        sys.exit(1)

    # scp dhcp.conf to the SAH
    dest_dhcp_conf = "/etc/dhcp/dhcpd.conf"
    LOG.info("Copying {} to {}@{}:{}".format(dhcp_conf, sah_user, args.sah_ip,
             dest_dhcp_conf))
    Scp.put_file(args.sah_ip, dhcp_conf, dest_dhcp_conf,
                 user=sah_user, password=sah_password)

    # The dhcp service will not start without an existing leases file,
    # so touch it to make sure it exists before starting the service
    dhcp_leases = "/var/lib/dhcpd/dhcpd.leases"
    LOG.info("Touching {}:{} as {}".format(args.sah_ip, dhcp_leases, sah_user))
    exit_code, std_out, std_err = Ssh.execute_command(
        args.sah_ip,
        "touch " + dhcp_leases,
        user=sah_user,
        password=sah_password)
    if exit_code != 0:
        LOG.error("Unable to touch {}:{}: {}".format(args.sah_ip,
                                                     dhcp_leases,
                                                     std_err))
        sys.exit(1)

    # Enable and restart the dhcp server on the SAH
    LOG.info("Enabling dhcpd on {} as {}".format(args.sah_ip, sah_user))
    exit_code, std_out, std_err = Ssh.execute_command(
        args.sah_ip,
        "systemctl enable dhcpd",
        user=sah_user,
        password=sah_password)
    if exit_code != 0:
        LOG.error("Unable to enable dhcpd on {}: {}".format(args.sah_ip,
                                                            std_err))
        sys.exit(1)

    LOG.info("Restarting dhcpd on {} as {}".format(args.sah_ip, sah_user))
    exit_code, std_out, std_err = Ssh.execute_command(
        args.sah_ip,
        "systemctl restart dhcpd",
        user=sah_user,
        password=sah_password)
    if exit_code != 0:
        LOG.error("Unable to restart dhcpd on {}: {}".format(args.sah_ip,
                                                             std_err))
        sys.exit(1)


if __name__ == "__main__":
    main()
