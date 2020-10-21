#!/usr/bin/env python3

# Copyright (c) 2015-2020 Dell Inc. or its subsidiaries.
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
import re
import time
from auto_common import Ssh, Scp


class InfraHost:

    def __init__(self):
        self.settings
        self.user
        self.ip
        self.pwd
        self.root_pwd

    def run(self, command):
        return Ssh.execute_command(self.ip,
                                   self.user,
                                   self.pwd,
                                   command)

    # WARNING: Do not use this method unless absolutely necessary.  Use the
    # run command above.  See the description of get_pty in
    # execute_command_tty.
    def run_tty(self, command):
        return Ssh.execute_command_tty(self.ip,
                                       self.user,
                                       self.pwd,
                                       command)

    # WARNING: Do not use this method unless absolutely necessary.  Use the
    # run command above.  See the description of get_pty in
    # execute_command_tty.
    def run_tty_as_root(self, command):
        return Ssh.execute_command_readlines(self.ip,
                                             "root",
                                             self.root_pwd,
                                             command)

    def run_as_root(self, command):
        return Ssh.execute_command(self.ip,
                                   "root",
                                   self.root_pwd,
                                   command)

    def run_ssh_edit(self, remotefile, find, replace):
        return Ssh.ssh_edit_file(self.ip,
                                 self.user,
                                 self.pwd,
                                 remotefile,
                                 find,
                                 replace)

    def upload_file(self, local_file, remote_file):
        Scp.put_file(self.ip,
                     "root",
                     self.root_pwd,
                     local_file,
                     remote_file)

    def download_file(self, local_file, remote_file):
        Scp.get_file(self.ip,
                     self.user,
                     self.pwd,
                     local_file,
                     remote_file)

    def create_directory(self, directory):
        Scp.mkdir(self.ip,
                  self.user,
                  self.pwd,
                  directory)

    def get_timestamped_path(self, path, filename, ext="conf"):
        timestamp = time.strftime('%Y%m%d%H%M%S')
        filename = filename + "_" + timestamp + "." + ext
        path = os.path.join(path, filename)
        return path

    def wait_for_vm_to_come_up(self, target_ip, user, password):
        while True:
            status = Ssh.execute_command(
                target_ip,
                user,
                password,
                "ps")[0]

            if status != "host not up":
                break

            time.sleep(10)

    def wait_for_vm_to_go_down(self, target_ip, user, password):
        while True:
            status = Ssh.execute_command(
                target_ip,
                user,
                password,
                "ps")[0]

            if status == "host not up":
                break
            time.sleep(5)

    def _generate_node_placement_exp(self, node_type):
        placement_exp = ((re.sub(
            r'[^a-z0-9]', " ", node_type.lower())).replace(" ", "-")
            + "-%index%")
        return placement_exp

    def _generate_node_type_az(self, node_type):
        az = self._generate_role_lower(node_type) + "_az"
        return az

    def _generate_cc_role(self, node_type):
        """Find non-alphanumerics in node type and replace with space then
        camel-case that and strip spaces
        :returns:  CamelCaseRoleName from my-node_type
        """
        role_cc = (re.sub(
            r'[^a-z0-9]', " ",
            node_type.lower()).title()).replace(" ", "")
        return role_cc

    def _generate_role_lower(self, node_type):
        _type_lwr = (re.sub(
            r'[^a-z0-9]', " ",
            node_type.lower()).replace(" ", "_"))
        return _type_lwr

    def _generate_subnet_name(self, node_type):
        return self._generate_role_lower(node_type) + '_subnet'

    def _generate_node_type_lower(self, node_type):
        # should look like denveredgecompute.yaml
        # if following existing pattern
        ntl = re.sub(r'[^a-z0-9]', "", node_type.lower())
        return ntl

    def _does_route_exist(self, route):
        cmd = "ip route show {}".format(route)
        _res = self.run_as_root(cmd)
        _does_route_exist = (len(_res[0].strip()) != 0)
        return _does_route_exist

    def _does_overcloud_node_route_exist(self, address,
                                         network, gateway, device):
        cmd = ("ssh -o StrictHostKeyChecking=no "
               "-o UserKnownHostsFile=/dev/null -o LogLevel=ERROR "
               "-o KbdInteractiveDevices=no heat-admin@{ip} "
               "ip route show {nw} dev {dev} via {gw}".format(ip=address,
                                                              nw=network,
                                                              gw=gateway,
                                                              dev=device))
        _res = self.run_tty(cmd)
        _does_route_exist = (len(_res[0].strip()) != 0)
        return _does_route_exist

    def _run_on_node(self, address, command):
        cmd = ("ssh -o StrictHostKeyChecking=no "
               "-o UserKnownHostsFile=/dev/null -o LogLevel=ERROR "
               "-o KbdInteractiveDevices=no heat-admin@{ip} "
               "\"{cmd}\"".format(ip=address, cmd=command))
        _res = self.run_tty(cmd)
        _does_route_exist = (len(_res[0].strip()) != 0)
        return _does_route_exist


def directory_check(_path):
    def wrap(f):
        def wrapped_f(*args):  # arg[0] is director object instance (self)
            path = _path
            if len(args) > 1 and isinstance(args[1], str):
                _type_lwr = (re.sub(r'[^a-z0-9]', " ",
                             args[1].lower()).replace(" ", "_"))
                path = os.path.join(_path, _type_lwr)
            if not os.path.exists(path):
                os.makedirs(path)
            return f(*args)
        return wrapped_f
    return wrap
