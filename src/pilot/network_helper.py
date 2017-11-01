#!/usr/bin/python

# Copyright (c) 2016 Dell Inc. or its subsidiaries.
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

import re
import os
import netaddr
import yaml
from netaddr import IPNetwork


class NetworkHelper:
    @staticmethod
    def get_provisioning_network():
        pattern = re.compile("^network_cidr\s*=\s*(.+)$")
        undercloud_conf = open(os.path.join(os.path.expanduser('~'), 'pilot',
                                            'undercloud.conf'), 'r')

        cidr = None
        for line in undercloud_conf:
            match = pattern.match(line)
            if match:
                cidr = netaddr.IPNetwork(match.group(1))
                break

        return cidr

    @staticmethod
    def _get_net_envt():
        net_envt_f = open(os.path.join(os.path.expanduser('~'),
                                       'pilot',
                                       'templates',
                                       'network-environment.yaml'), 'r')
        net_envt = yaml.load(net_envt_f)
        net_envt_f.close()
        return net_envt

    @staticmethod
    def get_public_api_network():
        net_envt = NetworkHelper._get_net_envt()
        return IPNetwork(net_envt['parameter_defaults']['ExternalNetCidr'])

    @staticmethod
    def get_private_api_network():
        net_envt = NetworkHelper._get_net_envt()
        return IPNetwork(net_envt['parameter_defaults']['InternalApiNetCidr'])

    @staticmethod
    def get_storage_network():
        net_envt = NetworkHelper._get_net_envt()
        return IPNetwork(net_envt['parameter_defaults']['StorageNetCidr'])

    @staticmethod
    def get_storage_clustering_network():
        net_envt = NetworkHelper._get_net_envt()
        return IPNetwork(net_envt['parameter_defaults']['StorageMgmtNetCidr'])

    @staticmethod
    def get_management_network():
        net_envt = NetworkHelper._get_net_envt()
        return IPNetwork(net_envt['parameter_defaults']['ManagementNetCidr'])

    @staticmethod
    def get_management_network_pools():
        net_envt = NetworkHelper._get_net_envt()
        return net_envt['parameter_defaults']['ManagementAllocationPools']

    @staticmethod
    def get_management_network_gateway():
        net_envt = NetworkHelper._get_net_envt()
        return net_envt['parameter_defaults']['ManagementNetworkGateway']

    @staticmethod
    def get_tenant_network():
        net_envt = NetworkHelper._get_net_envt()
        return IPNetwork(net_envt['parameter_defaults']['TenantNetCidr'])
