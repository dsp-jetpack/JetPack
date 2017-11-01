#!/usr/bin/env python

# Copyright (c) 2014-2016 Dell Inc. or its subsidiaries.
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

import ConfigParser
import sys
import argparse
import json
import logging
import os
import re
import socket
import subprocess
import novaclient.client as nova_client
import ironicclient
from netaddr import IPNetwork

pilot_dir = os.path.join(os.path.expanduser('~'), 'pilot')  # noqa
sys.path.append(pilot_dir)  # noqa

from credential_helper import CredentialHelper
from network_helper import NetworkHelper

logging.basicConfig()
logger = logging.getLogger(__name__)


class NetworkValidation(object):

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-l", "--latency", type=int, default=100,
                            help="latency in miliseconds", action="store")
        parser.add_argument("-c", "--config", default="networks.json",
                            help="path to network json config file",
                            action="store")
        parser.add_argument("-m", "--message_level", default="info",
                            help="output message verbosity - "
                                 "warn, info, debug",
                            action="store")

        self.args = parser.parse_args()
        self.set_logging(self.args.message_level)

        logger.debug("latency={0}".format(self.args.latency))
        logger.debug("config=" + self.args.config)
        logger.debug("message_level=" + self.args.message_level)

    def read_network_json(self):
        self.network_config = json.load(open(self.args.config))

    def set_logging(self, level):
        if (level == "info"):
            logger.setLevel(logging.INFO)
        elif (level == "warn"):
            logger.setLevel(logging.WARN)
        elif (level == "debug"):
            logger.setLevel(logging.DEBUG)

    def __init__(self):
        self.parse_args()
        self.read_network_json()
        self.build_network_to_subnet_map()

    def build_network_to_subnet_map(self):
        # Build a map of network name to CIDR
        self.network_to_subnet = {}
        self.network_to_subnet["public_api"] = \
            NetworkHelper.get_public_api_network()
        self.network_to_subnet["private_api"] = \
            NetworkHelper.get_private_api_network()
        self.network_to_subnet["storage"] = \
            NetworkHelper.get_storage_network()
        self.network_to_subnet["storage_clustering"] = \
            NetworkHelper.get_storage_clustering_network()
        self.network_to_subnet["management"] = \
            NetworkHelper.get_management_network()
        self.network_to_subnet["provisioning"] = \
            NetworkHelper.get_provisioning_network()
        self.network_to_subnet["tenant"] = \
            NetworkHelper.get_tenant_network()

        # Pull in custom networks from the json
        for network in self.network_config["networks"].keys():
            self.network_to_subnet[network] = \
                IPNetwork(self.network_config["networks"][network])

        logger.debug("network_to_subnet map is:")
        for network in self.network_to_subnet.keys():
            logger.debug("    " + network + " => " +
                         str(self.network_to_subnet[network]))

    def build_node_list(self):
        self.nodes = []

        # Pull in the nodes that nova doesn't know about in our json file
        for server_name in self.network_config["nodes"].keys():
            server = self.network_config["nodes"][server_name]
            node = self.Node(server_name,
                             server["ip"],
                             server["user"],
                             server["networks"])

            self.nodes.append(node)

        # Sort just these by name so the SAH/Director/Rhscon nodes come first
        self.nodes.sort(key=lambda n: n.name)

        os_auth_url, os_tenant_name, os_username, os_password = \
            CredentialHelper.get_undercloud_creds()

        kwargs = {'os_username': os_username,
                  'os_password': os_password,
                  'os_auth_url': os_auth_url,
                  'os_tenant_name': os_tenant_name}

        nova = nova_client.Client('2',  # API version
                                  os_username,
                                  os_password,
                                  os_tenant_name,
                                  os_auth_url)

        ironic = ironicclient.client.get_client(1, **kwargs)

        # Build up a map that maps flavor ids to flavor names
        flavor_map = {}
        flavors = nova.flavors.list()
        for flavor in flavors:
            flavor_map[flavor.id] = flavor.name

        logger.debug("flavor_map is:")
        for flavor in flavor_map.keys():
            logger.debug("    " + flavor + " => " + flavor_map[flavor])

        # Get the nodes from nova
        tmp_nodes = []
        nova_servers = nova.servers.list()
        for nova_server in nova_servers:
            flavor_name = None
            if nova_server.flavor["id"]:
                flavor_name = flavor_map[nova_server.flavor["id"]]
                if flavor_name == "baremetal":
                    flavor_name = None

            if not flavor_name:
                ironic_server = ironic.node.get_by_instance_uuid(
                    nova_server.id)
                capabilities = ironic_server.properties["capabilities"]

                match = re.search("node:([a-zA-Z-]+)-\d+", capabilities)
                if match:
                    flavor_name = match.group(1)
                else:
                    logger.error("Unable to find flavor name for "
                                 "node {}".format(nova_server.name))
                    sys.exit(1)

            # From the flavor, get the networks
            networks = self.network_config["flavors_to_networks"][flavor_name]

            node = self.Node(nova_server.name,
                             nova_server.networks["ctlplane"][0],
                             "heat-admin",
                             networks)
            tmp_nodes.append(node)

        # Sort the overcloud nodes by name to group the role types together
        tmp_nodes.sort(key=lambda n: n.name)
        self.nodes.extend(tmp_nodes)

    def collect_ssh_keys(self):
        node_ips = []

        logger.info("Collecting SSH keys...")
        for node in self.nodes:
            node_ips.append(node.ip)

        try:
            from update_ssh_config import update_known_hosts
        except:
            logger.error("Unable to locate 'update_ssh_config' utility in " +
                         pilot_dir)
            sys.exit(1)

        logger.debug("    update_known_hosts {}".format(' '.join(node_ips)))
        update_known_hosts(node_ips)

    def setup_ssh_access(self):
        logger.info("Setting up ssh access")

        for node in self.nodes:
            logger.debug("  Testing ssh access to " + node.name + " (" +
                         node.ip + "):")

            cmd = ["ssh",
                   "-oNumberOfPasswordPrompts=0",
                   node.user + "@" + node.ip,
                   "pwd"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            process.communicate()[0]
            if process.returncode == 0:
                logger.debug("    ssh access to " + node.name + " (" +
                             node.ip + ") works!)")
                continue

            logger.info("  ssh access to " + node.name + " (" + node.ip +
                        ") needs to be configured.")
            logger.info("    Enter the password for the " + node.user +
                        " user below:")
            cmd = ["ssh-copy-id",
                   node.user + "@" + node.ip]
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            process.communicate()[0]

    def resolve_node_networks(self):
        logger.debug("Nodes after network resolution:")
        for node in self.nodes:
            node.resolve_networks(self.network_to_subnet)
            logger.debug("    " + str(node))

    class Node:
        def __init__(self, name, ip, user, networks):
            self.name = name
            self.ip = ip
            self.user = user
            self.networks = networks
            self.network_to_ip = {}

        def resolve_networks(self, network_to_subnet):
            # Get the IPs for the networks on the node
            cmd = ["ssh",
                   "{}@{}".format(self.user, self.ip),
                   "/usr/sbin/ip -4 a"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            stdout = process.stdout.read()

            for network in self.networks:
                subnet = str(network_to_subnet[network].network)
                subnet_prefix = subnet[:subnet.rfind('.')]
                subnet_prefix = subnet_prefix.replace('.', '\.')

                cidr = network_to_subnet[network].prefixlen

                match = re.search("inet ({}\.\d+)/{} brd".format(
                    subnet_prefix, cidr), stdout)

                if match:
                    self.network_to_ip[network] = match.group(1)
                else:
                    logger.error("Unable to find IP on subnet {} on "
                                 "node {}".format(subnet, self.name))
                    sys.exit(1)

        def __str__(self):
            return "name: " + self.name + ", ip: " + self.ip + ",user: " + \
                self.user + ", networks: " + str(self.networks) + \
                ", network_to_ip: " + str(self.network_to_ip)

    def validate(self):
        logger.debug("Validating network communication")

        for source_node in self.nodes:
            logger.info("  From {} ({}):".format(source_node.name,
                                                 source_node.ip))

            for network in source_node.networks:
                logger.info("    Pinging {} network: ".format(network))
                for destination_node in self.nodes:
                    if source_node == destination_node:
                        continue

                    if network in destination_node.networks:
                        destination_ip = \
                            destination_node.network_to_ip[network]

                        cmd = ["ssh",
                               "{}@{}".format(source_node.user,
                                              source_node.ip),
                               "ping -c 1 -w 2 {}".format(destination_ip)]
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                        stdout = process.stdout.read()
                        match = re.search("64 bytes from {0}: icmp_.eq=\d+ "
                                          "ttl=\d+ time=(.*) ms".format(
                                              destination_ip), stdout)

                        if match:
                            logger.info("      Pinged {0: <20} - {1: <15} "
                                        "({2} ms)".format(
                                            destination_node.name,
                                            destination_ip,
                                            match.group(1)))
                        else:
                            logger.warn("      FAILED {0: <20} - {1: <15} "
                                        "({2}) network {2}!".format(
                                            destination_node.name,
                                            destination_ip,
                                            network))
                    else:
                        logger.debug("      Node {0} is not on network {1}".
                                     format(destination_node, network))


if __name__ == "__main__":
    logger.debug("Validating networks...")
    network_validation = NetworkValidation()
    network_validation.build_node_list()
    network_validation.collect_ssh_keys()
    network_validation.setup_ssh_access()
    network_validation.resolve_node_networks()
    network_validation.validate()
    logger.debug("validation complete...")
    sys.exit()
