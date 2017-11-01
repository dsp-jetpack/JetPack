#!/usr/bin/env python

# Copyright (c) 2015-2017 Dell Inc. or its subsidiaries.
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


class NodeConf():

    def __init__(self, json):
        self.is_sah = False
        self.is_foreman = False
        self.is_rhscon = False
        self.is_director = False
        self.is_ceph_storage = False
        self.is_switch = False
        self.hostname = None
        self.idrac_ip = None
        self.service_tag = None
        self.root_password = None
        self.external_ip = None
        self.public_api_gateway = None
        self.public_bond = None
        self.public_api_ip = None
        self.external_ip = None
        self.external_netmask = None
        self.public_slaves = None
        self.provisioning_ip = None
        self.provisioning_gateway = None
        self.provisioning_bond = None
        self.provisioning_netmask = None
        self.provisioning_slaves = None
        self.name_server = None
        self.__dict__ = json
