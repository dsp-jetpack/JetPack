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

from .settings.config import Settings
import re
import os
import glob
import json
import inspect
import logging
from configparser import ConfigParser
from osp_deployer.settings.config import Settings

logger = logging.getLogger("osp_deployer")

class Profile:
    def __init__(self):

        self.settings = Settings.settings
        self.profile_name = self.settings.profile
        self.definition = self.settings.foreman_configuration_scripts + \
            '/deploy/osp_deployer/profiles/' + self.profile_name + ".json"
        if self.profile_name == "custom":
            logger.info("Using Custom profile")
            return
        if not os.path.isfile(self.definition):
            raise AssertionError(self.profile_name +
                                 " is not a valid " +
                                 " profile in your .ini settings")

    def validate_configuration(self):
        # Make sure the user ini matches the associated profile settings
        if self.profile_name == "custom":
            return
        with open(self.definition) as profile_config:
            profile_definition = json.load(profile_config)
        user_config = ConfigParser()
        user_config.read(self.settings.settings_file)
        profile_config = ConfigParser()
        profile_config.read(os.path.dirname(inspect.getfile(Settings)) +
                            "/" + profile_definition['sample_ini'])
        Err = ''

        for items in profile_definition['associated_settings']:
            for stanza, value in list(items.items()):
                for set, vals in list(value.items()):
                    allowed_settings = []
                    validated = False
                    try:
                        if vals['valid_values']:
                            allowed_settings = vals['valid_values']
                    except:  # noqa: E722
                        pass
                    try:
                        if vals['validate']:
                            for test in vals['validate']:
                                if 'should_be_valid_ip' in test:
                                    if self.is_valid_ip(user_config.get(str(
                                            stanza), set)) is False:
                                        Err = Err + "\nSetting for " + set + \
                                            " Should be a valid ip adress\n"
                                if 'should_be_valid_int' in test:
                                    if self.is_int(user_config.get(str(
                                            stanza), set)) is False:
                                        Err = Err + "\nSetting for " + set + \
                                            " Should be a valid integer\n"
                                if 'valid_buffer_pool_size' in test:
                                    if self.valid_buffer_pool_size(
                                            user_config.get(str(
                                            stanza), set)) is False:
                                        Err = Err + "\nSetting for " + set + \
                                            " Should be a valid value\n"
                                if 'should_be_version' in test:
                                    if (len(self.settings.powerflex_nodes)) > 0:
                                        rpm_type = {}
                                        rpm_type['core'] = vals['validate'][1]['core_version']
                                        if (self.settings.enable_powerflex_mgmt):
                                            rpm_type['mgmt'] = vals['validate'][1]['mgmt_version']
                                    for type, version in rpm_type.items():
                                       if self.valid_powerflex_version(
                                               type, version ) is False:
                                          Err = Err + "\nRPM version for PoweFlex " + type + \
                                              " is not supported!" 
                                    
                            validated = True
                        if vals['in_range']:
                            for test in vals['in_range']:
                                if self.is_in_range(user_config.get(str(
                                        stanza), set), test) is False:
                                    Err = Err + "\nSetting for " + set + \
                                        " Should be in valid" \
                                        " range "+test+"\n"
                    except:  # noqa: E722
                        pass
                    if len(allowed_settings) > 0:
                        if user_config.get(str(stanza), set) in \
                                allowed_settings:
                            pass
                        else:
                            Err = Err + "\nYour setting for " + stanza + \
                                "::" + set + \
                                " is not valid for the profile " + \
                                self.profile_name + \
                                ". It should be set to one of the " + \
                                "following options : " + \
                                json.dumps(allowed_settings)
                    elif validated is True:
                        pass
                    else:
                        usr_sett = user_config.get(str(stanza), set)
                        if profile_config.get(str(stanza), set) != usr_sett:
                            Err = Err + "\nYour setting for " + stanza + \
                                "::" + set + \
                                " is not valid for the profile " + \
                                self.profile_name + \
                                ". It should be set to " + \
                                profile_config.get(str(stanza), set)

        if len(Err) > 0:
            logger.info(Err)
            msg = "Your settings diverge from the " + \
                  self.profile_name + " profile" + \
                  "\nReview the settings and errors above" + \
                  " in your .ini file " + \
                  "or change to a custom profile."
            raise AssertionError(msg)

    def is_valid_ip(self, address):
        valid = True
        octets = address.split('.')
        if len(octets) != 4:
            valid = False
        try:
            for octet in octets:
                octet_num = int(octet)
                if octet_num < 0 or octet_num > 255:
                    valid = False
                    break
        except ValueError:
            valid = False
        return valid

    def is_int(self, value):
        valid = True
        try:
            int(value)
        except ValueError:
            valid = False
        return valid

    def is_in_range(self, value, input):
        valid = True
        list = input.split('-')
        min = int(list[0])
        max = int(list[1]) + 1
        if int(value) not in list(range(min, max)):
            valid = False
        return valid

    def valid_buffer_pool_size(self, value):
        if value != "dynamic":
            pattern = '^\d+G$'  # noqa: W605
            valid = re.match(pattern, value)
            if not valid:
                return False
            val = int(value.replace('G', ''))
            if val < 0:
                return False
        return True

    def valid_powerflex_version(self, type, version):
        valid = True
        if type == 'core': 
            rpms_glob = ['sdc', 'sds', 'mdm', 'lia']
        elif type == 'mgmt':
            rpms_glob = ['mgmt']
        dict = {}
        for rpm in rpms_glob:
            file = glob.glob(self.settings.foreman_configuration_scripts +
                             '/pilot/powerflex/rpms/*' +
                             rpm + 
                             '*.rpm')[0]
            if type == 'core':
                ver = file.split('/')[-1].split('-',3)[3].rsplit('.',3)[0]
            else:
                # Special case for mgmt rpm file format
                ver = file.split('/')[-1].split('-',4)[4].rsplit('.',2)[0]

            dict[rpm] = ver

        if len(set(dict.values())) == 1:
            found_version = ''.join(set(dict.values()))
            if found_version != version:
                valid = False
        else:
            valid = False
        
        return valid
