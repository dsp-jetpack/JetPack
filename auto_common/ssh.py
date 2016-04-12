#!/usr/bin/env python

# OpenStack - A set of software tools for building and managing cloud computing
# platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.

import paramiko
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
    def ssh_edit_file(adress, user, passw, remotefile, regex,replace):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        trans = paramiko.Transport((adress, 22))
        trans.connect(username=user, password=passw)
        sftp = paramiko.SFTPClient.from_transport(trans)
        f_in = sftp.file(remotefile, "r")
        c_in = f_in.read()        
        pattern = re.compile(regex, re.MULTILINE|re.DOTALL)
        c_out = pattern.sub(replace,c_in)
        f_out = sftp.file(remotefile, "w")
        f_out.write(c_out)
        f_in.close()
        f_out.close()
        sftp.close()
        trans.close()


