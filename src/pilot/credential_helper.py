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

import os
import json
from subprocess import check_output
from os_cloud_config.utils import clients
from heatclient.client import Client as HeatClient


class CredentialHelper:
    @staticmethod
    def get_creds(filename):
        creds_file = open(filename, 'r')

        for line in creds_file:
            prefix = "export"
            if line.startswith(prefix):
                line = line[len(prefix):]

            line = line.strip()
            key, val = line.split('=', 2)
            key = key.lower()

            if key == 'os_username':
                os_username = val
            elif key == 'os_auth_url':
                os_auth_url = val
            elif key == 'os_tenant_name':
                os_tenant_name = val
            elif key == 'os_password':
                os_password = val

        if 'hiera' in os_password:
            os_password = check_output(['sudo', 'hiera',
                                       'admin_password']).strip()

        return os_auth_url, os_tenant_name, os_username, os_password

    @staticmethod
    def get_undercloud_creds():
        return CredentialHelper.get_creds(
            CredentialHelper.get_undercloudrc_name())

    @staticmethod
    def get_overcloud_creds():
        return CredentialHelper.get_creds(
            CredentialHelper.get_overcloudrc_name())

    @staticmethod
    def get_drac_creds(ironic_client, node_uuid,
                       instackenv_file="instackenv.json"):
        # Get the DRAC IP, username, and password
        node = ironic_client.node.get(node_uuid, ["driver_info"])

        return CredentialHelper.get_drac_creds_from_node(node)

    @staticmethod
    def get_drac_creds_from_node(node, instackenv_file="instackenv.json"):
        drac_ip, drac_user = CredentialHelper.get_drac_ip_and_user(node)

        # Can't get the password out of ironic, so dig it out of the
        # instackenv.json file
        drac_password = CredentialHelper.get_drac_password(
            drac_ip, instackenv_file)

        return drac_ip, drac_user, drac_password

    @staticmethod
    def get_drac_ip_and_user(node):
        driver_info = node.driver_info
        if "drac_host" in driver_info:
            drac_ip = driver_info["drac_host"]
            drac_user = driver_info["drac_username"]
        else:
            drac_ip = driver_info["ipmi_address"]
            drac_user = driver_info["ipmi_username"]

        return drac_ip, drac_user

    @staticmethod
    def get_drac_ip(node):
        drac_ip, drac_user = CredentialHelper.get_drac_ip_and_user(node)

        return drac_ip

    @staticmethod
    def get_drac_password(ip, instackenv_file):
        json_file = os.path.join(os.path.expanduser('~'), instackenv_file)
        instackenv_json = open(json_file, 'r')
        instackenv = json.load(instackenv_json)

        nodes = instackenv["nodes"]

        for node in nodes:
            if node["pm_addr"] == ip:
                return node["pm_password"]

        return None

    @staticmethod
    def get_undercloudrc_name():
        return os.path.join(os.path.expanduser('~'), 'stackrc')

    @staticmethod
    def get_overcloudrc_name():
        home_dir = os.path.expanduser('~')
        overcloudrc_name = "{}rc".format(CredentialHelper.get_stack_name())

        return os.path.join(home_dir, overcloudrc_name)

    @staticmethod
    def get_stack_name():
        os_auth_url, os_tenant_name, os_username, os_password = \
            CredentialHelper.get_undercloud_creds()

        keystone_client = clients.get_keystone_client(os_username,
                                                      os_password,
                                                      os_tenant_name,
                                                      os_auth_url)

        heat_url = keystone_client.service_catalog.url_for(
            service_type='orchestration',
            endpoint_type='publicURL')

        heat_client = HeatClient('1',
                                 endpoint=heat_url,
                                 token=keystone_client.auth_token)

        stacks = heat_client.stacks.list()

        # There can be only one overcloud stack, so get the name from the
        # first one if there is one
        stack_name = None
        stack = next(stacks, None)
        if stack:
            stack_name = stack.stack_name

        return stack_name
