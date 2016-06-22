#!/usr/bin/python

# (c) 2016 Dell
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
