#!/usr/bin/env python

# Copyright (c) 2015-2017 Dell Inc. or its subsidiaries.
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

from auto_common import Ssh, Scp


class InfraHost():

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
