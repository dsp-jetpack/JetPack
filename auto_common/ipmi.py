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

import subprocess
import time
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Ipmi():
    """
    this assumes CygWin is installed along with ipmi
    (if used on windows)
    ipmitools : download & extract from
        http://sourceforge.net/projects/ipmitool/files/
        ./configure --enable-intf-lanplus
        check the output contains :
        Interfaces
        lan : yes
        lanplus : yes
        if not, check the log output,
            and fix the missing dependencies etc.
        make
        make install
        Add c:\cygwin\bin and c:\cygwin\usr\local\bin to your path
        (or the relevant paths for your setup)
        make sure you can talk to one of your servers :
        in cygwin :
        ipmitool -I lanplus -H idracIp -U user -P password  power status
    """

    def __init__(self, cygwinlocation, ipmi_user, ipmi_password, idrac_ip):
        self.cygwin_loc = cygwinlocation
        self.ipmi_user = ipmi_user
        self.ipmi_password = ipmi_password
        self.idracIp = idrac_ip

    def power_on(self):
        logger.debug("powering on " + self.idracIp)
        self.__exec_ipmi_command("power on")
        while self.get_power_state() != PowerState.POWER_ON:
            logger.debug("give it time to wake up")
            time.sleep(5)

    def power_off(self):
        logger.debug("powering off" + self.idracIp)
        self.__exec_ipmi_command("power off")
        while self.get_power_state() != PowerState.POWER_OFF:
            logger.debug("give it time to turn off")
            time.sleep(5)

    def power_reset(self):
        return self.__exec_ipmi_command("power reset")

    def drac_reset(self):
        return self.__exec_ipmi_command("mc reset cold")

    def get_power_state(self):
        state = self.__exec_ipmi_command("power status").strip()
        logger.debug("power state: " + state)
        return state

    def set_boot_to_pxe(self):
        logger.debug("setting boot to pxe")
        self.__exec_ipmi_command("chassis bootdev pxe")

    def set_boot_to_disk(self):
        logger.debug("setting boot to disk")
        self.__exec_ipmi_command("chassis bootdev disk")

    def __exec_ipmi_command(self, command):
        cmd = "ipmitool.exe"
        if sys.platform.startswith('linux'):
            cmd = "ipmitool"

        cmdline = cmd + " -I lanplus -H " + self.idracIp + " -U " \
                      + self.ipmi_user + " -P " + self.ipmi_password \
                      + " " + command
        retries = 20
        for i in range(0, retries):
            try:
                logger.debug("executing :" + cmdline)
                out = subprocess.check_output(cmdline,
                                              stderr=subprocess.STDOUT,
                                              shell=True)
                logger.debug("cmd return :" + out)
                return out

            except subprocess.CalledProcessError as e:
                logger.debug(
                    "ipmi command failed, retrying (" + str(i) + "/" + str(
                        retries) + ")")
                time.sleep(10)
                if i == retries:
                    raise IOError("failed to execute ipmi command " + str(
                        cmdline) + e.output)


# noinspection PyClassHasNoInit
class PowerState:
    POWER_ON = 'Chassis Power is on'
    POWER_OFF = 'Chassis Power is off'
