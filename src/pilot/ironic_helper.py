#!/usr/bin/python

# Copyright (c) 2016-2019 Dell Inc. or its subsidiaries.
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
import os
from credential_helper import CredentialHelper

from ironicclient.common.apiclient.exceptions import NotFound


class IronicHelper:

    @staticmethod
    def get_ironic_client():
        kwargs = {'os_user_domain_name': os.environ['OS_USER_DOMAIN_NAME'],
                  'os_cacert': None,
                  'os_tenant_name': '',
                  'os_user_domain_id': '',
                  'os_cert': None,
                  'os_ironic_api_version': '1.34',
                  'os_project_id': '',
                  'retry_interval': 2,
                  'os_tenant_id': '',
                  'os_service_type': '',
                  'os_key': None,
                  'os_project_domain_id': '',
                  'insecure': False,
                  'max_retries': 5,
                  'os_endpoint_type': '',
                  'os_region_name': '',
                  'os_auth_token': '',
                  'ironic_url': '',
                  'timeout': 600,
                  'os_project_domain_name': os.environ[
                      'OS_PROJECT_DOMAIN_NAME'],
                  'os_username': os.environ['OS_USERNAME'],
                  'os_password': os.environ['OS_PASSWORD'],
                  'os_auth_url': os.environ['OS_AUTH_URL'],
                  'os_project_name': os.environ['OS_PROJECT_NAME']}
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
            # Assume we're looking for the IP address of the iDRAC
            for n in ironic_client.node.list(detail=True):
                drac_ip, _ = CredentialHelper.get_drac_ip_and_user(n)

                if drac_ip == ip_mac_service_tag:
                    node = n
                    break
        else:
            # Assume we're looking for the service tag
            for n in ironic_client.node.list(detail=True):
                if n.properties["service_tag"] == ip_mac_service_tag:
                    node = n
                    break

        return node
