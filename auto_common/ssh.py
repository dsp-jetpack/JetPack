#!/usr/bin/env python

# (c) 2015-2016 Dell
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


try:
    import paramiko
except ImportError:
    pass
import logging
import re

logger = logging.getLogger(__name__)


# noinspection PyClassHasNoInit
class Ssh():
    @staticmethod
    def execute_command(address, usr, pwd, command):
        try:
            logger.debug("ssh @" + address + ", running : " + command)
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(address, username=usr, password=pwd)
            stdin, ss_stdout, ss_stderr = client.exec_command(command)
            r_out, r_err = ss_stdout.read(), ss_stderr.read()
            logger.debug(r_err)
            if len(r_err) > 5:
                logger.error(r_err)
            else:
                logger.debug(r_out)
            client.close()
        except IOError:
            logger.warning(".. host " + address + " is not up")
            return "host not up"

        return r_out, r_err

    @staticmethod
    def execute_command_readlines(address, usr, pwd, command):
        try:
            logger.debug("ssh @" + address + ", running : " + command)
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(address, username=usr, password=pwd)
            stdin, ss_stdout, ss_stderr = client.exec_command(command)
            r_out, r_err = ss_stdout.readlines(), ss_stderr.read()
            logger.debug(r_err)
            if len(r_err) > 5:
                logger.error(r_err)
            else:
                logger.debug(r_out)
            client.close()
        except IOError:
            logger.warning(".. host " + address + " is not up")
            return "host not up"

        return r_out, r_err

    @staticmethod
    def execute_command_tty(address, usr, pwd, command):
        try:
            logger.debug("ssh @" + address + ", running : " + command)
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(address, username=usr, password=pwd)
            stdin, ss_stdout, ss_stderr = client.exec_command(
                command, get_pty=True)
            r_out, r_err = ss_stdout.read(), ss_stderr.read()
            logger.debug(r_err)
            if len(r_err) > 5:
                logger.error(r_err)
            else:
                logger.debug(r_out)
            client.close()
        except IOError:
            logger.warning(".. host " + address + " is not up")
            return "host not up"

        return r_out, r_err

    @staticmethod
    def ssh_edit_file(adress, user, passw, remotefile, regex, replace):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        trans = paramiko.Transport((adress, 22))
        trans.connect(username=user, password=passw)
        sftp = paramiko.SFTPClient.from_transport(trans)
        f_in = sftp.file(remotefile, "r")
        c_in = f_in.read()
        pattern = re.compile(regex, re.MULTILINE | re.DOTALL)
        c_out = pattern.sub(replace, c_in)
        f_out = sftp.file(remotefile, "w")
        f_out.write(c_out)
        f_in.close()
        f_out.close()
        sftp.close()
        trans.close()
