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

import argparse
import json
import logging
import os
import sys

logging.basicConfig()
logger = logging.getLogger(__name__)

class NetValidatorDeployer(object):

  def read_network_json(self):
    self.network_config=json.load(open(self.args.config))

  def parse_args(self):
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="networks.json", help="path to network json config file", action="store")
    parser.add_argument("-m", "--message_level", default="info", help="output message verbosity - warn, info, debug", action="store")

    self.args = parser.parse_args()
    self.set_logging(self.args.message_level)

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

  def collect_ssh_keys(self):
    node_ips = []

    logger.info("Collecting SSH keys...") 
    for node in self.network_config:
      if "provisioning" in self.network_config[node]["networks"]:
        node_ip = self.network_config[node]["networks"]["provisioning"]["ip"].encode('ascii','ignore')
      else:
        # This is for the Ceph VM where it does not have an IP on the
        # provisioning network
        node_ip = self.network_config[node]["networks"]["external"]["ip"].encode('ascii','ignore')

      node_ips.append(node_ip)

    pilot_dir = os.path.join(os.path.expanduser('~'), 'pilot')
    sys.path.append(pilot_dir)
    try:
      from update_ssh_config import update_known_hosts
    except:
      logger.error("Unable to locate 'update_ssh_config' utility in {}".format(pilot_dir))
      sys.exit(1)

    logger.info("    update_known_hosts {}".format(' '.join(node_ips)))
    update_known_hosts(node_ips)


  def deploy_network_validator(self):

    for node in self.network_config:
      logger.info("Copying network validation files to {}...".format(node)) 

      if "provisioning" in self.network_config[node]["networks"]:
        node_ip = self.network_config[node]["networks"]["provisioning"]["ip"].encode('ascii','ignore')
      else:
        # This is for the Ceph VM where it does not have an IP on the
        # provisioning network
        node_ip = self.network_config[node]["networks"]["external"]["ip"].encode('ascii','ignore')

      if "user" in self.network_config[node]:
        user_id = self.network_config[node]["user"].encode('ascii','ignore')
      else:
        user_id = os.environ['USER']

      cmd = "scp -r ~/pilot/network-validation {}@{}:~".format(user_id, node_ip)
      logger.info("    {}".format(cmd)) 
      os.system(cmd)

  def deploy(self):
    self.read_network_json()
    self.collect_ssh_keys()
    self.deploy_network_validator()

if __name__ == "__main__":
  logger.debug("Deploying network validator...")
  netValidatorDeployer = NetValidatorDeployer()
  netValidatorDeployer.deploy()
  logger.debug("Deployment complete...")
  sys.exit()
