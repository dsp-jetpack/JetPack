#!/usr/bin/python

# OpenStack - A set of software tools for building and managing cloud computing
# platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.

import sys
import argparse
import json
import logging
import re
import subprocess

logging.basicConfig()
logger = logging.getLogger(__name__)

class Networks(object):

    def read_network_json(self):
       self.network_config=json.load(open(self.args.config))

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("node_name", help="name of this node in the network json config file", action="store")
        parser.add_argument("-l", "--latency", type=int, default=100, help="latency in miliseconds", action="store")
        parser.add_argument("-c", "--config", default="networks.json", help="path to network json config file", action="store")
        parser.add_argument("-m", "--message_level", default="info", help="output message verbosity - warn, info, debug", action="store")
        parser.add_argument("-s", "--skip_connectivity_test", help="skip network connectivity test", action="store_true")

        self.args=parser.parse_args()
        self.set_logging(self.args.message_level)

        logger.debug("node_name=" + self.args.node_name)
        logger.debug("latency={0}".format(self.args.latency))
        logger.debug("config=" + self.args.config)
        logger.debug("message_level=" + self.args.message_level)
        logger.debug("skip_connectivity_test={0}".format(self.args.skip_connectivity_test))

    def set_logging(self, level):
        if (level == "info"):
            logger.setLevel(logging.INFO)
        elif (level == "warn"):
            logger.setLevel(logging.WARN)
        elif (level == "debug"):
            logger.setLevel(logging.DEBUG)

    def __init__(self):
        self.parse_args()

    def validate_active_configuration(self):
        logger.debug("Validating active network configuration")

    def validate_static_configuration(self):
        logger.debug("Validating static network configuration")

    def validate_network_configuration(self):
        logger.debug("Validating network configuration")
        self.validate_active_configuration()
        self.validate_static_configuration()

    def validate_network_communication(self):
        logger.debug("Validating network communication")
        networks = self.network_config[self.args.node_name]["networks"]
        for network in networks.keys():
            logger.info(" {0} pinging network {1}: ".format(self.args.node_name, network))
            for node in self.network_config:
                if network in self.network_config[node]["networks"]:
                    node_network=self.network_config[node]["networks"][network]
                    ip=node_network["ip"].encode('ascii','ignore')
                    args=[ "-c 1", "-w 2", ip ]
                    process = subprocess.Popen(args, executable="ping", stdout=subprocess.PIPE)
                    stdout=process.stdout.read()
                    match = re.search("64 bytes from {0}: icmp_.eq=\d+ ttl=\d+ time=(.*) ms".format(ip), stdout)
                    if match:
                        logger.info("   Pinged {0} - {1} ({2} ms)".format(node, ip, match.group(1)))
                    else:
                        logger.warn("   Ping failed for {0} {1} network {2}!".format(node, ip, network))
                else:
                    logger.debug("   Node {0} is not on network {1}".format(node,network))

    def validate(self):
        self.read_network_json()
        self.validate_network_configuration()
        if not self.args.skip_connectivity_test:
            self.validate_network_communication()

if __name__ == "__main__":
    logger.debug("Validating networks...")
    networks = Networks()
    networks.validate()
    logger.debug("validation complete...")
    sys.exit()