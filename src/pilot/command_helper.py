#!/usr/bin/env python

# Copyright (c) 2016 Dell Inc. or its subsidiaries.
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
import paramiko

logger = logging.getLogger(__name__)


class Scp():

    @staticmethod
    def get_file(address, localfile, remotefile,
                 user=None, password=None, pkey=None):
        logger.debug("Copying {}@{}:{} to {}".format(user, address, remotefile,
                     localfile))
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        trans = paramiko.Transport((address, 22))
        trans.connect(username=user, password=password, pkey=pkey)
        sftp = paramiko.SFTPClient.from_transport(trans)
        sftp.get(remotefile, localfile)
        sftp.close()
        trans.close()

    @staticmethod
    def put_file(address, localfile, remotefile,
                 user=None, password=None, pkey=None):
        logger.debug("Copying {} to {}@{}:{}".format(localfile, user, address,
                     remotefile))
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        trans = paramiko.Transport((address, 22))
        trans.connect(username=user, password=password, pkey=pkey)
        sftp = paramiko.SFTPClient.from_transport(trans)
        sftp.put(localfile, remotefile)
        sftp.close()
        trans.close()


class Ssh():

    @staticmethod
    def execute_command(address, command, user=None, password=None, pkey=None):
        try:
            logger.debug("ssh {}@{}, running: {}".format(user, address,
                         command))
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(address, username=user, password=password,
                           pkey=pkey)
            stdin, ss_stdout, ss_stderr = client.exec_command(command)
            r_out, r_err = ss_stdout.read(), ss_stderr.read()
            exit_code = ss_stdout.channel.recv_exit_status()
            logger.debug("exit_code: " + str(exit_code))
            logger.debug("stdout: " + r_out)
            logger.debug("stderr: " + r_err)
            client.close()
        except IOError:
            logger.warning(".. host " + address + " is not up")
            return "host not up"

        return exit_code, r_out, r_err
