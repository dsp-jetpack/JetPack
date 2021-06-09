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

import logging
import os
import inspect
import json
import subprocess
import configparser
import yaml

logger = logging.getLogger("ocp_deployer")

class OCP_Settings:

        def __init__(self, settings_file):
            assert os.path.isfile(
                    settings_file), settings_file + " file does not exist"
            self.settings_file = settings_file
            self.conf = configparser.ConfigParser()
            self.conf.optionxform = str
            self.conf.read(self.settings_file)

            rhsm_settings = self.get_settings_section(
                "Subscription Manager Settings")
            self.subscription_manager_user = rhsm_settings[
                'subscription_manager_user']
            self.subscription_manager_password = rhsm_settings[
                'subscription_manager_password']
            self.subscription_manager_pool_csah = rhsm_settings[
                'subscription_manager_pool_csah']

            ipmi_settings = self.get_settings_section(
                "IPMI credentials Settings")
            self.ipmi_user = ipmi_settings['ipmi_user']
            self.ipmi_pwd = ipmi_settings['ipmi_password']
  
            deploy_settings = self.get_settings_section(
                "Deployment Settings")
            self.nodes_yaml = deploy_settings['nodes_yaml']
            self.csah_root_pwd = deploy_settings['csah_root_password']

            # Load the nodes definition 
            with open(self.nodes_yaml, 'r') as file:
                nodes = yaml.load(file)
            self.controller_nodes = []
            self.compute_nodes = []
            self.csah_node = OCP_node(nodes['csah'][0], None, None)
            self.bootstrap_node = OCP_node(nodes['bootstrap_kvm'][0], None, None)
            for control in nodes['control_nodes']:
                self.controller_nodes.append(OCP_node(control, self.ipmi_user, self.ipmi_pwd))
            for comp in nodes['compute_nodes']:
                self.compute_nodes.append(OCP_node(comp, self.ipmi_user, self.ipmi_pwd))


            OCP_Settings.settings = self
        
        def get_settings_section(self, section):
            dictr = {}
            options = self.conf.options(section)
            for option in options:
                try:
                    dictr[option] = self.conf.get(section, option)
                    if dictr[option] == -1:
                        logger.debug("skip: %s" % option)
                except configparser.NoSectionError:
                    logger.debug("exception on %s!" % option)
                    dictr[option] = None
            return dictr



class OCP_node:

        def __init__(self, yaml_def, ipmi_user, ipmi_pwd):
            logger.debug("loading " + str(yaml_def))
            self.os_ip = yaml_def['ip_os']
            try:
                self.os_flavor = yaml_def['os']
            except:
                pass
            self.name = yaml_def['name']
            try:
                self.idrac_ip = yaml_def['ip_idrac']
            except:
                pass
            self.ipmi_user = ipmi_user
            self.ipmi_pwd = ipmi_pwd




