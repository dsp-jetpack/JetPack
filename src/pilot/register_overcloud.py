#!/usr/bin/python

# Copyright (c) 2016-2019 Dell Inc. or its subsidiaries.
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
import novaclient.client as nova_client
import ironicclient.client as ironic_client
import logging
import os
import re
import json
import sys
import subprocess
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client
from credential_helper import CredentialHelper
from netaddr import IPAddress
from network_helper import NetworkHelper


class RegisterOvercloud:

    def _set_logging(self, level):
        if (level == "info"):
            self.logger.setLevel(logging.INFO)
        elif (level == "warn"):
            self.logger.setLevel(logging.WARN)
        elif (level == "debug"):
            self.logger.setLevel(logging.DEBUG)

    def _execute_cmd(self, cmd):
        self.logger.debug("Executing command: " + str(cmd))
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        stdout, stderr = process.communicate()
        self.logger.debug("Got back:\n" +
                          "    returncode=" + str(process.returncode) + "\n"
                          "    stdout=" + stdout)

        return process.returncode, stdout

    def __init__(self):
        logging.basicConfig()
        self.logger = logging.getLogger(__name__)

        self.pool_id_matcher = re.compile("^Pool ID:\s+(.+)$")  # noqa: W605

    def _get_credential(self, credential_type, credential_name,
                        credential_value=None, required=True):
        if credential_value is None:
            if credential_type in self.subscriptions and \
                    credential_name in self.subscriptions[credential_type]:
                credential_value = \
                    self.subscriptions[credential_type][credential_name]
            elif required:
                self.logger.error(credential_name +
                                  " must be specified on either the command "
                                  "line or in the subscription json file")
                sys.exit(1)

        return credential_value

    def _collect_inputs(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-u',
                            '--cdn_username',
                            help='The username for registering the overcloud '
                                 'nodes with CDN')
        parser.add_argument('-p',
                            '--cdn_password',
                            help='The password for registering the overcloud '
                                 'nodes with CDN')
        parser.add_argument("-c",
                            "--config",
                            default="subscription.json",
                            help="The path to the subscription json file",
                            action="store")
        parser.add_argument('-l',
                            '--proxy_url',
                            default=None,
                            help='The proxy URL in host:port format')
        parser.add_argument('-n',
                            '--proxy_username',
                            default=None,
                            help='The proxy username')
        parser.add_argument('-s',
                            '--proxy_password',
                            default=None,
                            help='The proxy password')
        parser.add_argument("-m",
                            "--message_level",
                            default="info",
                            help="Logging message verbosity - "
                                 "warn, info, debug",
                            action="store")
        args = parser.parse_args()
        self._set_logging(args.message_level)

        self.subscriptions = json.load(open(args.config))

        # Get the CDN creds
        self.cdn_username = self._get_credential("cdn_credentials",
                                                 "cdn_username",
                                                 args.cdn_username)
        self.cdn_password = self._get_credential("cdn_credentials",
                                                 "cdn_password",
                                                 args.cdn_password)
        self.logger.debug("cdn_username: " + self.cdn_username)
        self.logger.debug("cdn_password: " + self.cdn_password)

        self.satellite_org = self._get_credential("satellite_credentials",
                                                  "satellite_organization")
        self.satellite_key = self._get_credential("satellite_credentials",
                                                  "satellite_activation_key")

        # Get the proxy creds
        self.proxy_args = ""
        proxy_url = self._get_credential("proxy_credentials",
                                         "proxy_url",
                                         args.proxy_url,
                                         False)
        if proxy_url:
            self.proxy_args += "--proxy=" + proxy_url

            proxy_username = self._get_credential("proxy_credentials",
                                                  "proxy_username",
                                                  args.proxy_username,
                                                  False)
            if proxy_username:
                self.proxy_args += " --proxyuser=" + proxy_username

            proxy_password = self._get_credential("proxy_credentials",
                                                  "proxy_password",
                                                  args.proxy_password,
                                                  False)
            if proxy_password:
                self.proxy_args += " --proxypassword=" + proxy_password

        self.logger.debug("proxy_args: " + self.proxy_args)

    def _get_nodes(self):
        os_auth_url, os_tenant_name, os_username, os_password, \
            os_user_domain_name, os_project_domain_name = \
            CredentialHelper.get_undercloud_creds()
        auth_url = os_auth_url + "v3"

        provisioning_network = NetworkHelper.get_provisioning_network()

        kwargs = {'os_username': os_username,
                  'os_password': os_password,
                  'os_auth_url': os_auth_url,
                  'os_tenant_name': os_tenant_name,
                  'os_user_domain_name': os_user_domain_name,
                  'os_project_domain_name': os_project_domain_name}
        i_client = ironic_client.get_client(1, **kwargs)

        auth = v3.Password(
            auth_url=auth_url,
            username=os_username,
            password=os_password,
            project_name=os_tenant_name,
            user_domain_name=os_user_domain_name,
            project_domain_name=os_project_domain_name
        )

        sess = session.Session(auth=auth)
        n_client = nova_client.Client(2, session=sess)

        # Build up a dictionary that maps roles to a list of IPs for that role
        self.node_roles_to_nodes = {}

        self.logger.debug("Querying ironic and nova for nodes")
        nodes = i_client.node.list(fields=["uuid", "instance_uuid",
                                           "properties"])
        for node in nodes:
            uuid = node.uuid
            instance_uuid = node.instance_uuid

            # Handle the case where we have a node in ironic that's not in nova
            # (possibly due to the node being in maintenance mode in ironic or
            #  the user not assigning a role to a node, etc)
            if instance_uuid is None:
                self.logger.debug("Ironic node " + uuid + " has no "
                                  "corresponding instance in nova.  Skipping")
                continue

            capabilities = node.properties["capabilities"]
            capabilities = dict(c.split(':') for c in capabilities.split(','))

            # Role is the 'profile' capability when node placement is not
            # in use. Otherwise it's encoded in the 'node' capability.
            if 'profile' in capabilities:
                role = capabilities['profile']
            elif 'node' in capabilities:
                role = capabilities['node']
                # Trim the trailing "-N" where N is the node number
                role = role[:role.rindex('-')]
            else:
                self.logger.error("Failed to determine role of node {}".format(
                    node))
                sys.exit(1)

            server = n_client.servers.get(instance_uuid)
            for address in server.addresses["ctlplane"]:
                ip = address["addr"]
                if IPAddress(ip) in provisioning_network:
                    break

            self.logger.debug("Got node:\n"
                              "    uuid=" + uuid + "\n"
                              "    ip=" + ip + "\n"
                              "    role=" + role + "\n"
                              "    instance_uuid=" + instance_uuid)

            if role not in self.node_roles_to_nodes:
                self.node_roles_to_nodes[role] = []

            self.node_roles_to_nodes[role].append(ip)

        self.logger.debug("node_roles_to_nodes: " +
                          str(self.node_roles_to_nodes))

    def _using_activation_key(self, role):
        using_activation_key = False
        if "activation_key_info" in self.subscriptions["roles"][role]:
            using_activation_key = True

        return using_activation_key

    def _register_node(self, role, node_ip):
        # First check to see if the node is already registered
        cmd = ["ssh",
               "heat-admin@{}".format(node_ip),
               "sudo",
               "subscription-manager",
               "identity",
               self.proxy_args]
        return_code, stdout = self._execute_cmd(cmd)
        if return_code == 0:
            self.logger.warn(role + " " + node_ip +
                             " is already registered.  "
                             "Using existing registration")
        else:
            if "This system is not yet registered" not in stdout:
                self.logger.error("Failed to determine if " + role + " " +
                                  node_ip + " is already registered: " +
                                  stdout)
                sys.exit(1)

            # The node isn't registered, so register it
            self.logger.info("Registering {} {}".format(role,
                                                        node_ip))

            # If we're using satellite, then construct the args for that
            cred_args = ""
            if len(self.satellite_org) > 1:
                cred_args = "--org=" + self.satellite_org + " " + \
                    "--activationkey=" + self.satellite_key
            else:
                cred_args = "--username=" + self.cdn_username + \
                    " --password=" + "'{}'".format(self.cdn_password)

            cmd = ["ssh",
                   "heat-admin@{}".format(node_ip),
                   "sudo",
                   "subscription-manager",
                   "register",
                   cred_args,
                   self.proxy_args]
            return_code, stdout = self._execute_cmd(cmd)
            if return_code == 0:
                self.logger.debug("Registered {} {} successfully".format(
                    role, node_ip))
            else:
                self.logger.error("Failed to register " + role + " " +
                                  node_ip + ": " + stdout)
                sys.exit(1)

    def _unregister_node(self, role, node_ip):
        self.logger.info("Unregistering {} {}".format(role, node_ip))

        cmd = ["ssh",
               "heat-admin@{}".format(node_ip),
               "sudo",
               "subscription-manager",
               "remove --all",
               self.proxy_args]
        return_code, stdout = self._execute_cmd(cmd)
        if return_code == 0:
            self.logger.debug("Removed subscriptions from {} "
                              "{} successfully".format(role, node_ip))
        else:
            self.logger.warn("Unable to remove subscriptions from " + role +
                             " " + node_ip + ": " + stdout)

        cmd = ["ssh",
               "heat-admin@{}".format(node_ip),
               "sudo",
               "subscription-manager",
               "unregister",
               self.proxy_args]
        return_code, stdout = self._execute_cmd(cmd)
        if return_code == 0:
            self.logger.debug("Unregistered {} {} successfully".format(
                role, node_ip))
        else:
            self.logger.warn("Failed to unregister " + role + " " + node_ip +
                             ": " + stdout)

    def _get_consumed_pool_ids(self, node_ip):
        # Build up a list of consumed pool IDs for this node
        consumed_pool_ids = []
        cmd = ["ssh",
               "heat-admin@{}".format(node_ip),
               "sudo",
               "subscription-manager",
               "list",
               "--consumed",
               self.proxy_args]
        return_code, stdout = self._execute_cmd(cmd)
        if return_code == 0:
            for line in stdout.splitlines():
                match = self.pool_id_matcher.match(line)
                if match:
                    consumed_pool_ids.append(match.group(1))
        else:
            self.logger.error("Failed to get the list of consumed pool IDs "
                              "for node " + node_ip + ": " + stdout)
            sys.exit(1)

        return consumed_pool_ids

    def _attach_node(self, role, node_ip):

        # Build up a list of consumed pool IDs for this node
        consumed_pool_ids = self._get_consumed_pool_ids(node_ip)

        if "pool_ids" not in self.subscriptions["roles"][role]:
            self.logger.error("pool_ids is missing in the json file under "
                              "the " + role + " role")
            sys.exit(1)

        pool_ids = set(self.subscriptions["roles"][role]["pool_ids"])
        for pool_id in pool_ids:
            # Check to see if this node is already attached to this pool ID
            if pool_id in consumed_pool_ids:
                self.logger.warn(role + " " + node_ip +
                                 " is already attached to pool " + pool_id +
                                 ".  Skipping attach")
            else:
                # Not already attached, so attach
                self.logger.info("Attaching " + role + " " + node_ip +
                                 " to pool " + pool_id)
                cmd = ["ssh",
                       "heat-admin@{}".format(node_ip),
                       "sudo",
                       "subscription-manager",
                       "attach",
                       "--pool",
                       pool_id,
                       self.proxy_args]
                return_code, stdout = self._execute_cmd(cmd)
                if return_code == 0:
                    self.logger.debug("Attached " + role + " " + node_ip +
                                      " to pool " + pool_id)
                else:
                    self.logger.error("Failed to attach " + role + " " +
                                      node_ip + " to pool " + pool_id + ": " +
                                      stdout)
                    sys.exit(1)

    def _subscribe_node(self, role, node_ip):
        # First disable all repos on the node
        self.logger.info("Disabling all repos on " + role + " " + node_ip)
        cmd = ["ssh",
               "heat-admin@{}".format(node_ip),
               "sudo",
               "subscription-manager",
               "repos",
               "--disable=*",
               self.proxy_args]
        return_code, stdout = self._execute_cmd(cmd)
        if return_code == 0:
            self.logger.debug("Successfully disabled all repos on " + role +
                              " " + node_ip)
        else:
            self.logger.error("Failed to disabled all repos on " + role + " " +
                              node_ip + ": " + stdout)
            sys.exit(1)

        # Enable all requested repos on the node
        repos = self.subscriptions["roles"][role]["repos"]

        repo_list = ""
        for repo in repos:
            repo_list += "--enable={} ".format(repo)

        self.logger.info("Enabling the following repos on " + role + " " +
                         node_ip + ": " + str(repos))
        cmd = ["ssh",
               "heat-admin@{}".format(node_ip),
               "sudo",
               "subscription-manager",
               "repos",
               repo_list,
               self.proxy_args]
        return_code, stdout = self._execute_cmd(cmd)
        if return_code == 0:
            self.logger.debug("Successfully enabled the repos on " + role +
                              " " + node_ip)
        else:
            self.logger.error("Failed to enable the repos on " + role + " " +
                              node_ip + ": " + stdout)
            sys.exit(1)

    def register_nodes(self):
        self._collect_inputs()
        self._get_nodes()

        # Iterate thru the node types
        for role in self.node_roles_to_nodes:
            # Iterate thru the IPs
            for node_ip in self.node_roles_to_nodes[role]:

                # Register the node
                self._register_node(role, node_ip)

                # Attach the node to the pool IDs
                self._attach_node(role, node_ip)

                # Subscribe the node to the requested repos
                self._subscribe_node(role, node_ip)

    def unregister_nodes(self):
        self._collect_inputs()
        self._get_nodes()

        # Iterate thru the node types
        for role in self.node_roles_to_nodes:
            # Iterate thru the IPs
            for node_ip in self.node_roles_to_nodes[role]:

                # Unregister the node
                self._unregister_node(role, node_ip)


if __name__ == "__main__":
    ro = RegisterOvercloud()
    ro.register_nodes()
