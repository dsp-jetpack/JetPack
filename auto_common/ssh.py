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

import subprocess, paramiko, sys
import logging
logger = logging.getLogger(__name__)

class Ssh():

    @staticmethod
    def execute_command(address, usr, pwd, command):
        try :
            logger.info ( "ssh @" + address + ", running : " + command )
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
            os = sys.platform
            
            client.connect(address, username=usr, password=pwd)
            stdin, ss_stdout, ss_stderr = client.exec_command(command)
            r_out, r_err = ss_stdout.read(), ss_stderr.read()
            logger.info(r_err)
            if len(r_err) > 5 :
                logger.error(r_err)
            else:
                logger.info(r_out)
            client.close()
        except IOError :
            logger.warning( ".. host "+ address + " is not up")
            return "host not up"
            
            
        return r_out, r_err

    @staticmethod
    def execute_command_readlines(address, usr, pwd, command):
        try :
            logger.info ( "ssh @" + address + ", running : " + command )
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            os = sys.platform

            client.connect(address, username=usr, password=pwd)
            stdin, ss_stdout, ss_stderr = client.exec_command(command)
            r_out, r_err = ss_stdout.readlines(), ss_stderr.read()
            logger.info( r_err)
            if len(r_err) > 5 :
                logger.error(r_err)
            else:
                logger.info(r_out)
            client.close()
        except IOError :
            logger.warning( ".. host "+ address + " is not up")
            return "host not up"


        return r_out, r_err

    @staticmethod
    def execute_command_tty(address, usr, pwd, command):
        try :
            logger.info ( "ssh @" + address + ", running : " + command )
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            os = sys.platform

            client.connect(address, username=usr, password=pwd)
            stdin, ss_stdout, ss_stderr = client.exec_command(command, get_pty=True)
            r_out, r_err = ss_stdout.read(), ss_stderr.read()
            logger.info(r_err)
            if len(r_err) > 5 :
                logger.error(r_err)
            else:
                logger.info(r_out)
            client.close()
        except IOError :
            logger.warning( ".. host "+ address + " is not up")
            return "host not up"


        return r_out, r_err
    
