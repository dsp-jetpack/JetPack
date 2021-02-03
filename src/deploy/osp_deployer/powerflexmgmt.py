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

class Powerflexmgmt(InfraHost):


    def __init__(self):

        self.settings = Settings.settings
        logger.info("Settings.settings: %s", str(Settings.settings))
        self.ip = self.settings.powerflexmgmt_vm.public_api_ip
        self.root_pwd = self.settings.powerflexmgmt_vm.root_password
        self.rpm_dir = "/root/rpms"
        self.pilot_dir = self.settings.foreman_configuration_scripts + "/pilot"
        self.powerflex_dir = self.pilot_dir + "/powerflex"


    def upload_rpm(self):

        cmd = "mkdir -p " + self.rpm_dir
        self.run_as_root(cmd)
        
        logger.debug("Uploading powerflex presentation server rpm")
        source_file = self.powerflex_dir + "/rpms/" + \
                      self.settings.powerflex_presentation_server_rpm
        self.upload_file(source_file,
                         self.rpm_dir + "/" + \
                         self.settings.powerflex_presentation_server_rpm)


    def install_presentation_server(self):
  
        logger.debug("Installing the presentation server")
        powerflexgw_ip = self.settings.powerflexmgmt_vm.public_api_ip
        cmd = "rpm -ivh " + \
              self.rpm_dir + \
              "/" + \
              self.settings.powerflex_presentation_server_rpm
        self.run_as_root(cmd)
