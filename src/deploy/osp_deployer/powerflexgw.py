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

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import yaml
from osp_deployer.settings.config import Settings
from infra_host import InfraHost
from infra_host import directory_check
from auto_common import Scp

logger = logging.getLogger("osp_deployer")

class Powerflexgw(InfraHost):


    def __init__(self):

        self.settings = Settings.settings
        logger.info("Settings.settings: %s", str(Settings.settings))
        self.ip = self.settings.powerflexgw_vm.public_api_ip
        self.root_pwd = self.settings.powerflexgw_vm.root_password
        self.rpm_dir = "/root/rpms"
        

    def upload_rpm(self):

        cmd = "mkdir -p " + self.rpm_dir
        self.run_as_root(cmd)
        
        logger.debug("Uploading powerflex gateway rpm")
        source_file = "/root/JetPack/src/pilot/powerflex/rpms/" + \
                      self.settings.powerflex_gateway_rpm
        self.upload_file(source_file,
                         self.rpm_dir + "/" + \
                         self.settings.powerflex_gateway_rpm)


    def install_gateway(self):
  
        logger.debug("Installing the gateway")
        powerflexgw_ip = self.settings.powerflexgw_vm.public_api_ip
        cmd = "GATEWAY_ADMIN_PASSWORD=" + \
              self.settings.powerflex_password + \
              " rpm -ivh " + \
              self.rpm_dir + \
              "/" + \
              self.settings.powerflex_gateway_rpm
        self.run_as_root(cmd)



if __name__ == "__main__":
    settings = Settings("/root/r88;ini")
    powerflexgw = Powerflexgw()
      
      



