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

import collections
import os
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


def directory_check(_path):
    def inner(func):
        if not os.path.exists(_path):
            os.makedirs(_path)
        return func
    return inner
