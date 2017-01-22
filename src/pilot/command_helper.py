#!/usr/bin/env python

# Copyright (c) 2016-2017 Dell Inc. or its subsidiaries.
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
import subprocess

logger = logging.getLogger(__name__)


class Scp():

    @staticmethod
    def get_file(address, localfile, remotefile,
                 user=None, password=None, pkey=None):
        logger.debug("Copying {}@{}:{} to {}".format(user, address, remotefile,
                     localfile))
        client = Ssh.get_client(address, user, password, pkey)
        sftp = client.open_sftp()
        sftp.get(remotefile, localfile)
        sftp.close()
        client.close()

    @staticmethod
    def put_file(address, localfile, remotefile,
                 user=None, password=None, pkey=None):
        logger.debug("Copying {} to {}@{}:{}".format(localfile, user, address,
                     remotefile))
        client = Ssh.get_client(address, user, password, pkey)
        sftp = client.open_sftp()
        sftp.put(localfile, remotefile)
        sftp.close()
        client.close()


class Ssh():

    @staticmethod
    def get_client(address, user=None, password=None, pkey=None):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(address, username=user, password=password, pkey=pkey)
        return client

    @staticmethod
    def execute_command(address, command, user=None, password=None, pkey=None):
        try:
            logger.debug("ssh {}@{}, running: {}".format(user, address,
                         command))
            client = Ssh.get_client(address, user, password, pkey)
            _, stdout_stream, stderr_stream = client.exec_command(command)
            stdout, stderr = stdout_stream.read(), stderr_stream.read()
            exit_code = stdout_stream.channel.recv_exit_status()
            logger.debug("exit_code: " + str(exit_code))
            logger.debug("stdout: " + stdout)
            logger.debug("stderr: " + stderr)
            client.close()
        except IOError:
            logger.warning(".. host " + address + " is not up")
            return "host not up"

        return exit_code, stdout, stderr


class Exec():

    @staticmethod
    def execute_command(cmd):
        logger.debug("Executing command: " + str(cmd))
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        exit_code = process.returncode
        logger.debug("Got back:\n"
                     "    returncode={}\n"
                     "    stdout={}\n"
                     "    stderr={}".format(str(process.returncode),
                                            stdout, stderr))

        return exit_code, stdout, stderr
