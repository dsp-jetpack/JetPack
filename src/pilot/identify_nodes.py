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

import ironicclient
from novaclient import client as novaclient
from os import path
from subprocess import check_output
from credential_helper import CredentialHelper


def main():
    os_auth_url, os_tenant_name, os_username, os_password = \
        CredentialHelper.get_undercloud_creds()

    kwargs = {'os_username': os_username,
              'os_password': os_password,
              'os_auth_url': os_auth_url,
              'os_tenant_name': os_tenant_name}
    ironic = ironicclient.client.get_client(1, **kwargs)
    nodes = ironic.node.list(detail=True)

    nova = novaclient.Client('2',  # API version
                             os_username,
                             os_password,
                             os_tenant_name,
                             os_auth_url)

    # Slightly odd syntax for declaring 'banner' reduces the line length
    banner = (
        "+-----------------+---------------------------+-----------------+"
    )
    nodeinfo = "| {:<15} | {:<25} | {:<15} |"
    print banner
    print nodeinfo.format('iDRAC Addr', 'Node Name', 'Provision Addr')
    print banner
    # Display the list ordered by the iDRAC address
    for n in sorted(nodes, key=lambda x: CredentialHelper.get_drac_ip(x)):
        idrac_addr = CredentialHelper.get_drac_ip(n)

        if 'display_name' in n.instance_info:
            node_name = n.instance_info['display_name']
        else:
            node_name = 'None'

        prov_addr = 'None'
        if n.instance_uuid:
            nova_ips = nova.servers.ips(n.instance_uuid)
            if nova_ips and 'ctlplane' in nova_ips:
                prov_addr = nova_ips['ctlplane'][0]['addr']

        print nodeinfo.format(idrac_addr, node_name, prov_addr)
    print banner


if __name__ == "__main__":
    main()
