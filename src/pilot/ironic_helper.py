#!/usr/bin/python

# Copyright (c) 2016-2017 Dell Inc. or its subsidiaries.
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
from credential_helper import CredentialHelper

from ironicclient.common.apiclient.exceptions import NotFound


class IronicHelper:

    @staticmethod
    def get_ironic_client():
        os_auth_url, os_tenant_name, os_username, os_password = \
            CredentialHelper.get_undercloud_creds()

        kwargs = {'os_username': os_username,
                  'os_password': os_password,
                  'os_auth_url': os_auth_url,
                  'os_tenant_name': os_tenant_name,
                  'os_ironic_api_version': '1.15'}
        return ironicclient.client.get_client(1, **kwargs)

    @staticmethod
    def get_ironic_node(ironic_client, ip_mac_service_tag):
        node = None

        if ":" in ip_mac_service_tag:
            # Assume we're looking for the MAC address of the provisioning NIC
            try:
                port = ironic_client.port.get_by_address(ip_mac_service_tag)
            except NotFound:
                pass
            else:
                node = ironic_client.node.get(port.node_uuid)
        elif "." in ip_mac_service_tag:
            # Assume we're looking for the IP addres of the iDRAC
            for n in ironic_client.node.list(
                fields=[
                    "driver",
                    "driver_info",
                    "uuid"]):
                drac_ip, _ = CredentialHelper.get_drac_ip_and_user(n)

                if drac_ip == ip_mac_service_tag:
                    node = n
                    break
        else:
            # Assume we're looking for the chassis service tag
            for n in ironic_client.node.list(
                fields=[
                    "driver",
                    "driver_info",
                    "uuid",
                    "properties"]):
                if n.properties["service_tag"] == ip_mac_service_tag:
                    node = n
                    break

        return node
