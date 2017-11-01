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

import argparse
import json
import os
from ironicclient import client
from subprocess import check_output
from credential_helper import CredentialHelper


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--power", required=True, default=None,
                        choices=["on", "off", "reset", "cycle"],
                        help="Control power state of all overcloud nodes")
    args = parser.parse_args()

    os_auth_url, os_tenant_name, os_username, os_password = \
        CredentialHelper.get_undercloud_creds()

    kwargs = {'os_username': os_username,
              'os_password': os_password,
              'os_auth_url': os_auth_url,
              'os_tenant_name': os_tenant_name}
    ironic = client.get_client(1, **kwargs)

    for node in ironic.node.list(detail=True):
        ip, username, password = \
            CredentialHelper.get_drac_creds_from_node(node)

        cmd = "ipmitool -H {} -I lanplus -U {} -P '{}' chassis power {}". \
            format(ip, username, password, args.power)
        print cmd
        os.system(cmd)


if __name__ == "__main__":
    main()
