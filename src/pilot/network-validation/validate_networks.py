#!/usr/bin/env python

# (c) 2016 Dell
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

import sys
import argparse
import json
import logging
import os
import re
import socket
import subprocess

logging.basicConfig()
logger = logging.getLogger(__name__)


class Networks(object):

  def read_network_json(self):
    self.network_config=json.load(open(self.args.config))


  def parse_args(self):
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--latency", type=int, default=100, help="latency in miliseconds", action="store")
    parser.add_argument("-c", "--config", default="networks.json", help="path to network json config file", action="store")
    parser.add_argument("-m", "--message_level", default="info", help="output message verbosity - warn, info, debug", action="store")

    self.args=parser.parse_args()
    self.set_logging(self.args.message_level)

    logger.debug("latency={0}".format(self.args.latency))
    logger.debug("config=" + self.args.config)
    logger.debug("message_level=" + self.args.message_level)


  def set_logging(self, level):
    if (level == "info"):
      logger.setLevel(logging.INFO)
    elif (level == "warn"):
      logger.setLevel(logging.WARN)
    elif (level == "debug"):
      logger.setLevel(logging.DEBUG)


  def __init__(self):
    self.parse_args()


  def get_ip(self, node):
    if "provisioning" in self.network_config[node]["networks"]:
      node_ip = self.network_config[node]["networks"]["provisioning"]["ip"].encode('ascii','ignore')
    else:
      # This is for the Ceph VM where it does not have an IP on the
      # provisioning network
      node_ip = self.network_config[node]["networks"]["external"]["ip"].encode('ascii','ignore')

    return node_ip


  def collect_ssh_keys(self):
    node_ips = []

    logger.info("Collecting SSH keys...")
    for node in self.network_config:
      node_ips.append( self.get_ip(node) )

    pilot_dir = os.path.join(os.path.expanduser('~'), 'pilot')
    sys.path.append(pilot_dir)
    try:
      from update_ssh_config import update_known_hosts
    except:
      logger.error("Unable to locate 'update_ssh_config' utility in " + pilot_dir)
      sys.exit(1)

    logger.info("    update_known_hosts {}".format(' '.join(node_ips)))
    update_known_hosts(node_ips)


  def setup_ssh_access(self):
    logger.info("Setting up ssh access")

    for node_name in self.network_config.keys():
      if node_name == "director_vm":
        continue

      user = self.network_config[node_name]["user"]
      node_ip = self.get_ip(node_name)
      logger.debug("  Testing ssh access to " + node_name + " (" + node_ip + "):")

      cmd=[ "ssh",
            "-oNumberOfPasswordPrompts=0",
            user + "@" + node_ip,
            "pwd" ]
      process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
      process.communicate()[0]
      if process.returncode == 0:
        logger.debug("    ssh access to " + node_name + " (" + node_ip + ") works!)")
        continue

      logger.info("  ssh access to " + node_name + " (" + node_ip + ") needs to be configured.")
      logger.info("    Enter the password for the " + user + " user below:")
      cmd=[ "ssh-copy-id",
            user + "@" + node_ip]
      process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
      process.communicate()[0]


  def validate(self):
    logger.debug("Validating network communication")

    for node_name in self.network_config.keys():
      if node_name == "director_vm":
        continue

      user = self.network_config[node_name]["user"]
      node_ip = self.get_ip(node_name)
      logger.info("  From {} ({}):".format(node_name, node_ip))

      networks = self.network_config[node_name]["networks"]
      for network in networks.keys():
        logger.info("    Pinging {} network: ".format(network))
        for node in self.network_config:
          if network in self.network_config[node]["networks"]:
            node_network=self.network_config[node]["networks"][network]

            target_ip=node_network["ip"].encode('ascii','ignore')

            cmd=[ "ssh",
                  "{}@{}".format(user, node_ip),
                  "ping -c 1 -w 2 {}".format(target_ip)]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            stdout=process.stdout.read()
            match = re.search("64 bytes from {0}: icmp_.eq=\d+ ttl=\d+ time=(.*) ms".format(target_ip), stdout)

            if match:
              logger.info("      Pinged {0} - {1} ({2} ms)".format(node, target_ip, match.group(1)))
            else:
              logger.warn("      Ping failed for {0} {1} network {2}!".format(node, target_ip, network))
          else:
            logger.debug("      Node {0} is not on network {1}".format(node,network))


if __name__ == "__main__":
  logger.debug("Validating networks...")
  networks = Networks()
  networks.read_network_json()
  networks.collect_ssh_keys()
  networks.setup_ssh_access()
  networks.validate()
  logger.debug("validation complete...")
  sys.exit()
