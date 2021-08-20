#!/usr/bin/env python3

# Copyright (c) 2015-2021 Dell Inc. or its subsidiaries.
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

import subprocess
import time
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Ipmi:

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
        print("power state: [" + state + "]")
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
                print("executing :" + cmdline)
                out = subprocess.check_output(cmdline,
                                              stderr=subprocess.STDOUT,
                                              shell=True)
                out("cmd return :" + out)
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
