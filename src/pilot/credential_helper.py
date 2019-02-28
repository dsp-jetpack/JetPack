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

import logging
import json
import os
import sys
import subprocess
from constants import Constants
from subprocess import check_output
from keystoneclient.v3 import client
from heatclient.v1.client import Client as HeatClient


class CredentialHelper:
    LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])
    instackenv = None

    @staticmethod
    def get_creds(filename):
        command = ['bash', '-c', 'source %s && env' % filename]
        ret = check_output(command)
        env_keys = {}
        for line in ret.split('\n'):
            if line:
                (key, value) = line.split("=")[0:2]
                env_keys[key] = value

        if 'hiera' in env_keys['OS_PASSWORD']:
            env_keys['OS_PASSWORD'] = check_output(['sudo', 'hiera',
                                                    'admin_password']).strip()
        if 'OS_PROJECT_NAME' in env_keys:
            project_name = env_keys['OS_PROJECT_NAME']
        else:
            project_name = env_keys['OS_TENANT_NAME']
        return \
            env_keys['OS_AUTH_URL'], \
            project_name, \
            env_keys['OS_USERNAME'], \
            env_keys['OS_PASSWORD'], \
            env_keys['OS_USER_DOMAIN_NAME'], \
            env_keys['OS_PROJECT_DOMAIN_NAME']

    @staticmethod
    def get_undercloud_creds():
        return CredentialHelper.get_creds(
            CredentialHelper.get_undercloudrc_name())

    @staticmethod
    def get_overcloud_creds():
        return CredentialHelper.get_creds(
            CredentialHelper.get_overcloudrc_name())

    @staticmethod
    def get_drac_creds(ironic_client, node_uuid):
        # Get the DRAC IP, username, and password
        node = ironic_client.node.get(node_uuid, ["driver_info"])

        return CredentialHelper.get_drac_creds_from_node(node)

    @staticmethod
    def get_drac_creds_from_node(
            node, instackenv_file=Constants.INSTACKENV_FILENAME):
        drac_ip, drac_user = CredentialHelper.get_drac_ip_and_user(node)

        # Can't get the password out of ironic, so dig it out of the
        # instackenv.json file
        drac_password = CredentialHelper.get_drac_password(
            drac_ip, instackenv_file)

        return drac_ip, drac_user, drac_password

    @staticmethod
    def clear_instack_cache():
        CredentialHelper.instackenv = None

    @staticmethod
    def _load_instack(instackenv_file):
        if not CredentialHelper.instackenv:
            json_file = os.path.expanduser(instackenv_file)
            with open(json_file, 'r') as instackenv_json:
                CredentialHelper.instackenv = json.load(instackenv_json)

    @staticmethod
    def get_node_from_instack(
            ip_service_tag,
            instackenv_file=Constants.INSTACKENV_FILENAME):
        CredentialHelper._load_instack(instackenv_file)

        nodes = CredentialHelper.instackenv["nodes"]

        for node in nodes:
            if node["pm_addr"] == ip_service_tag or \
                    node["service_tag"] == ip_service_tag:
                return node

        return None

    @staticmethod
    def get_drac_ip_and_user(node):
        driver_info = node.driver_info
        if "drac_host" in driver_info:
            drac_ip = driver_info["drac_host"]
            drac_user = driver_info["drac_username"]
        elif "drac_address" in driver_info:
            drac_ip = driver_info["drac_address"]
            drac_user = driver_info["drac_username"]
        else:
            drac_ip = driver_info["ipmi_address"]
            drac_user = driver_info["ipmi_username"]

        return drac_ip, drac_user

    @staticmethod
    def get_drac_ip(node):
        drac_ip, _ = CredentialHelper.get_drac_ip_and_user(node)

        return drac_ip

    @staticmethod
    def get_drac_password(ip, instackenv_file):
        CredentialHelper._load_instack(instackenv_file)

        nodes = CredentialHelper.instackenv["nodes"]

        for node in nodes:
            if node["pm_addr"] == ip:
                return node["pm_password"]

        return None

    @staticmethod
    def save_instack(instackenv_file):
        if not CredentialHelper.instackenv:
            raise RuntimeError("No instackenv.json was loaded")

        try:
            json_file = os.path.expanduser(instackenv_file)
            with open(json_file, 'w') as instackenv_json:
                json.dump(CredentialHelper.instackenv, instackenv_json,
                          sort_keys=True, indent=2, separators=(',', ': '))
        except Exception as instack_ex:
            instack_ex.message = "Unable to save {}: {}".format(
                instackenv_file,
                instack_ex.message)
            raise

    @staticmethod
    def get_undercloudrc_name():
        return os.path.join(os.path.expanduser('~'), 'stackrc')

    @staticmethod
    def get_overcloudrc_name():
        home_dir = os.path.expanduser('~')
        overcloudrc_name = "{}rc".format(CredentialHelper.get_overcloud_name())

        return os.path.join(home_dir, overcloudrc_name)

    @staticmethod
    def get_overcloud_name():
        stack = CredentialHelper.get_overcloud_stack()
        if stack:
            return stack

        return None

    @staticmethod
    def get_overcloud_stack():
        cmd = "source  " + CredentialHelper.get_undercloudrc_name() + \
              ";openstack stack list | grep CREATE | awk '{print $4}'"
        return subprocess.check_output(cmd,
                                       stderr=subprocess.STDOUT,
                                       shell=True).strip()

    @staticmethod
    def get_overcloud_stack_status():
        cmd = "source  " + CredentialHelper.get_undercloudrc_name() + \
              ";openstack stack list | grep CREATE | awk '{print $8}'"
        return subprocess.check_output(cmd,
                                       stderr=subprocess.STDOUT,
                                       shell=True).strip()
