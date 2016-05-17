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

import argparse
import json
import os
from ironicclient import client
from subprocess import check_output
from credential_helper import CredentialHelper


def main():
  os_auth_url, os_tenant_name, os_username, os_password = \
    CredentialHelper.get_undercloud_creds()

  kwargs = {'os_username': os_username,
            'os_password': os_password,
            'os_auth_url': os_auth_url,
            'os_tenant_name': os_tenant_name}
  ironic = client.get_client(1, **kwargs)

  for node in ironic.node.list(detail=True):
    ip, username, password = CredentialHelper.get_drac_creds_from_node(node)

    # Power off the node
    cmd="ipmitool -H {} -I lanplus -U {} -P '{}' chassis power off".format(
      ip, username, password)
    print cmd
    os.system(cmd)

    # Set the first boot device to PXE
    cmd="ipmitool -H {} -I lanplus -U {} -P '{}' chassis bootdev pxe options=persistent".format(
      ip, username, password)
    print cmd
    os.system(cmd)


if __name__ == "__main__":
  main()
