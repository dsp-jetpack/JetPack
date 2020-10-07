#!/usr/bin/env python3

# Copyright (c) 2015-2020 Dell Inc. or its subsidiaries.
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

CTLPLANE_BRIDGE = "br-ctlplane"
PUBLIC_API_IF = "enp1s0"
PROVISIONING_IF = "enp2s0"
MANAGEMENT_IF = "enp3s0"
PRIVATE_API_IF = "enp4s0"
FIRST_BOOT = "first-boot"
SITE_NAME = "site-name"
OVERRIDES = "overrides"
CONTROL_PLANE_EXPORT = "control-plane-export"
TEMPEST_CONF = 'tempest.conf'
OVERCLOUD_PATH = 'overcloud'
OVERCLOUD_ENVS_PATH = OVERCLOUD_PATH + '/environments'
EDGE_COMMON_PATH = "edge_common"

STAGING_PATH = '/deployment_staging'
STAGING_TEMPLATES_PATH = STAGING_PATH + '/templates'
NIC_CONFIGS = 'nic-configs'
IMAGES_ENV = 'images-env'
CONTAINERS_PREPARE_PARAM = 'containers-prepare-parameter'
STAGING_NIC_CONFIGS = STAGING_TEMPLATES_PATH + '/' + NIC_CONFIGS
NIC_ENV = 'nic_environment'
NODE_PLACEMENT = 'node-placement'
NEUTRON_OVS = 'neutron-ovs'
DELL_ENV = 'dell-environment'
NET_ENV = 'network-environment'
INSTACKENV = 'instackenv'
STATIC_IP_ENV = 'static-ip-environment'
STATIC_VIP_ENV = 'static-vip-environment'
ROLES_DATA = 'roles_data'
NETWORK_DATA = 'network_data'
NET_ISO = 'network-isolation'
CONTROLLER = 'controller'
DEF_COMPUTE_ROLE_FILE = 'DistributedCompute.yaml'
DEF_COMPUTE_REMOTE_PATH = ('roles/{}'.format(DEF_COMPUTE_ROLE_FILE))
CONTROL_PLANE_NET = ('ControlPlane', "ctlplane")
INTERNAL_API_NET = ('InternalApi', 'internal_api')
STORAGE_NET = ('Storage', 'storage')
TENANT_NET = ('Tenant', 'tenant')
EXTERNAL_NET = ('External', 'external')

EDGE_NETWORKS = (INTERNAL_API_NET, STORAGE_NET,
                 TENANT_NET, EXTERNAL_NET)
EDGE_VLANS = ["TenantNetworkVlanID", "InternalApiNetworkVlanID",
              "StorageNetworkVlanID"]

# Jinja2 template constants
J2_EXT = '.j2.yaml'
NIC_ENV_EDGE_J2 = NIC_ENV + "_edge" + J2_EXT
EDGE_COMPUTE_J2 = 'compute_edge' + J2_EXT
CONTROLLER_J2 = CONTROLLER + J2_EXT
NETWORK_DATA_J2 = NETWORK_DATA + J2_EXT
NETWORK_ENV_EDGE_J2 = NET_ENV + "-edge" + J2_EXT
DELL_ENV_EDGE_J2 = DELL_ENV + "-edge" + J2_EXT
STATIC_IP_ENV_EDGE_J2 = STATIC_IP_ENV + "-edge" + J2_EXT
NODE_PLACEMENT_EDGE_J2 = NODE_PLACEMENT + "-edge" + J2_EXT
ROLES_DATA_EDGE_J2 = ROLES_DATA + "_edge" + J2_EXT
NET_ISO_EDGE_J2 = NET_ISO + "-edge" + J2_EXT
SITE_NAME_EDGE_J2 = SITE_NAME + "-edge" + J2_EXT
SITE_NAME_J2 = SITE_NAME + J2_EXT
OVERRIDES_EDGE_J2 = OVERRIDES + "-edge" + J2_EXT

EC2_IPCIDR = '169.254.169.254/32'
EC2_PUBLIC_IPCIDR_PARAM = 'EC2MetadataPublicIpCidr'

NWM_ROUTE_CMD = ("nmcli connection modify {dev} {add_rem}ipv4.routes "
                 "\"{cidr} {gw}\"")
NWM_UP_CMD = "nmcli connection load {dev} && exec nmcli device reapply {dev}"
LEGACY_DEL_ROUTE_CMD = ("sudo sed -i -e '/{cidr_esc} via {gw} dev {dev}/d' "
                        "/etc/sysconfig/network-scripts/route-{dev}; "
                        "sudo ip route del {cidr} via {gw} dev {dev}")
LEGACY_ROUTE_CMD = ("sudo echo \"{cidr} via {gw} dev {dev}\" >> "
                    "/etc/sysconfig/network-scripts/route-{dev}")
LEGACY_SSH_ROUTE_CMD = ("echo \"{cidr} via {gw} dev {dev}\" | sudo tee -a "
                        "/etc/sysconfig/network-scripts/route-{dev}")
ROUTE_UP_CMD = "sudo /etc/sysconfig/network-scripts/ifup-routes {dev}"
BR_DOWN_CMD = "sudo /etc/sysconfig/network-scripts/ifdown-ovs ifcfg-{dev}"
BR_UP_CMD = "sudo /etc/sysconfig/network-scripts/ifup-ovs ifcfg-{dev}"
IF_DOWN_CMD = "sudo /etc/sysconfig/network-scripts/ifdown {dev}"
IF_UP_CMD = "sudo /etc/sysconfig/network-scripts/ifup {dev}"
UNDERCLOUD_INSTALL_CMD = "openstack undercloud install"
MGMT_BRIDGE = "br-mgmt"
PROV_BRIDGE = "br-prov"

CONTAINER_IMAGE_PREPARE_CMD = "sudo openstack tripleo container image prepare"
STACK_SHOW_CMD = ("openstack stack show -c stack_name -c stack_status "
                  "-c creation_time -f json {stack}")
