#!/usr/bin/env python

# Copyright (c) 2015-2019 Dell Inc. or its subsidiaries.
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

from auto_common import Ipmi
from settings.config import Settings
from profile import Profile
import logging
import os.path
import collections
import yaml

logger = logging.getLogger("osp_deployer")


class DeployerSanity():
    def __init__(self):
        self.settings = Settings.settings

    @staticmethod
    def is_valid_ip(address):
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

    def check_files(self):

        logger.debug("Check settings ip's are valid.")
        shouldbbevalidips = [
            'public_api_gateway',
            'public_api_netmask',
            'public_api_allocation_pool_end',
            'private_api_netmask',
            'private_api_allocation_pool_start',
            'private_api_allocation_pool_end',
            'storage_netmask', 'storage_allocation_pool_start',
            'storage_allocation_pool_end',
            'provisioning_netmask', 'provisioning_net_dhcp_start',
            'provisioning_net_dhcp_end', 'provisioning_gateway',
            'storage_cluster_allocation_pool_start',
            'storage_cluster_allocation_pool_end',
            'management_netmask',
            'management_gateway',
            'management_allocation_pool_start',
            'management_allocation_pool_end',
            'name_server',
        ]

        for ip in getattr(self.settings, 'discovery_ip_range').split(","):
            self.is_valid_ip(ip),\
                "Setting for discovery_ip_range " + \
                ip + " is not a valid ip "
        for each in shouldbbevalidips:
            assert self.is_valid_ip(getattr(self.settings, each)),\
                "Setting for " + each + " is not a valid ip " +\
                getattr(self.settings, each)

        assert os.path.isfile(
            self.settings.rhel_iso), \
            self.settings.rhel_iso + \
            "ISO doesn't seem to exist"
        assert os.path.isfile(
            self.settings.director_deploy_sh), \
            self.settings.director_deploy_sh + \
            " script doesn't seem to exist"
        assert os.path.isfile(
            self.settings.undercloud_conf), \
            self.settings.undercloud_conf + \
            " file doesn't seem to exist"
        if self.settings.use_custom_instack_json is True:
            assert os.path.isfile(
                self.settings.custom_instack_json),\
                self.settings.custom_instack_json + \
                " file doesn't seem to exist"
        if self.settings.pull_images_from_cdn is False:
            assert os.path.isfile(
                self.settings.discovery_ram_disk_image),\
                self.settings.discovery_ram_disk_image +\
                " file doesn't seem to exist"
            assert os.path.isfile(
                self.settings.overcloud_image), \
                self.settings.overcloud_image + \
                " file doesn't seem to exist"
        if self.settings.octavia_user_certs_keys is True:
            assert os.path.isfile(
                self.settings.certificate_keys_path),\
                self.settings.certificate_keys_path +\
                " file doesn't seem to exist"
        assert os.path.isfile(
            self.settings.install_director_sh), \
            self.settings.install_director_sh +\
            " file doesn't seem to exist"
        assert os.path.isfile(
            self.settings.rhel_iso), \
            self.settings.rhel_iso +\
            " file doesn't seem to exist"

    def check_ipmi_to_nodes(self):
        self.check_ipmi_to_node(self.settings.sah_node.idrac_ip,
                                self.settings.sah_ipmi_user,
                                self.settings.sah_ipmi_password)

        hdw_nodes = (self.settings.controller_nodes +
                     self.settings.compute_nodes +
                     self.settings.ceph_nodes)

        for node in hdw_nodes:
            if hasattr(node, "idrac_ip"):
                self.check_ipmi_to_node(node.idrac_ip,
                                        self.settings.ipmi_user,
                                        self.settings.ipmi_password)

    def check_ipmi_to_node(self, idrac_ip, ipmi_user, ipmi_password):
        try:
            logger.debug(idrac_ip)
            ipmi_session = Ipmi(self.settings.cygwin_installdir,
                                ipmi_user,
                                ipmi_password,
                                idrac_ip)
            logger.debug(
                " :: " + ipmi_session.get_power_state())
        except:  # noqa: E722
            raise AssertionError("Could not ipmi to host " +
                                 idrac_ip)

    def check_network_overlaps(self):
        # Verify the dhcp ranges defined in the ini don't overlap with static
        # ips defined in the .properties or with the VIPs if used & that vips
        # are sitting on the right networks.

        # public_api network allocation pool
        start = self.settings.public_api_allocation_pool_start.split(".")[-1]
        end = self.settings.public_api_allocation_pool_end.split(".")[-1]
        for each in self.settings.nodes:
            if hasattr(each, 'public_api_ip'):
                ip = each.public_api_ip.split(".")[-1]
                if int(start) <= int(ip) <= int(end):
                    raise AssertionError(each.public_api_ip +
                                         " in .properties is in the public" +
                                         " api allocation pool range defined" +
                                         " in the .ini")
        if self.settings.use_static_vips is True:
            if int(start) <= int(
                    self.settings.public_api_vip.split(".")[-1]) <= int(end):
                raise AssertionError("public_api_vip should be outside the \
                                     public api allocation pool range")
            net = ".".join(self.settings.public_api_network.split(".")[:-1])
            if net not in self.settings.public_api_vip:
                raise AssertionError("public_api_vip setting appears to  "
                                     "be on the wrong network, should be "
                                     "on the public api network")

        # private_api network allocation pool
        start = self.settings.private_api_allocation_pool_start.split(".")[-1]
        end = self.settings.private_api_allocation_pool_end.split(".")[-1]
        for each in self.settings.nodes:
            if hasattr(each, 'private_api_ip'):
                ip = each.private_api_ip.split(".")[-1]
                if int(start) <= int(ip) <= int(end):
                    raise AssertionError(each.private_api_ip + " in " +
                                         ".properties is in the private " +
                                         "api allocation pool range defined" +
                                         " in the .ini")
        if self.settings.use_static_vips is True:
            net = ".".join(self.settings.private_api_network.split(".")[:-1])
            if int(start) <= int(
                    self.settings.redis_vip.split(".")[-1]) <= int(end):
                raise AssertionError("redis_vip should be outside the \
                                     private api allocation pool range")
            if int(start) <= int(
                    self.settings.private_api_vip.split(".")[-1]) <= int(end):
                raise AssertionError("private_api_vip should be outside the \
                                     private api allocation pool range")
            if net not in self.settings.redis_vip:
                raise AssertionError("redis_vip setting appears to  "
                                     "be on the wrong network, should be "
                                     "on the private api network")
            if net not in self.settings.private_api_vip:
                raise AssertionError("private_api_vip setting appears to  "
                                     "be on the wrong network, should be "
                                     "on the private api network")

        # storage_network allocation pool
        start = self.settings.storage_allocation_pool_start.split(".")[-1]
        end = self.settings.storage_allocation_pool_end.split(".")[-1]
        for each in self.settings.nodes:
            if hasattr(each, 'storage_ip'):
                ip = each.storage_ip.split(".")[-1]
                if int(start) <= int(ip) <= int(end):
                    raise AssertionError(each.storage_ip + " in " +
                                         ".properties is in the storage " +
                                         "allocation pool range defined " +
                                         "in the .ini")
        if self.settings.use_static_vips is True:
            if int(start) <= int(
                    self.settings.storage_vip.split(".")[-1]) <= int(end):
                raise AssertionError("storage_vip should be outside the \
                                     storage allocation pool range")
            net = ".".join(self.settings.storage_network.split(".")[:-1])
            if net not in self.settings.storage_vip:
                raise AssertionError("storage_vip setting appears to  "
                                     "be on the wrong network, should be "
                                     "on the storage network")

        # provisioning network allocation pool
        start = self.settings.provisioning_net_dhcp_start.split(".")[-1]
        end = self.settings.provisioning_net_dhcp_end.split(".")[-1]
        for each in self.settings.nodes:
            if hasattr(each, 'provisioning_ip'):
                ip = each.provisioning_ip.split(".")[-1]
                if int(start) <= int(ip) <= int(end):
                    raise AssertionError(each.provisioning_ip + " in " +
                                         ".properties is in the provisioning" +
                                         " dhcp allocation pool " +
                                         "range defined in the .ini")

        net = ".".join(self.settings.provisioning_network.split(".")[:-1])

        if self.settings.use_static_vips is True:
            if int(start) <= int(
               self.settings.storage_cluster_vip.split(".")[-1]) <= int(end):
                raise AssertionError("storage_cluster_vip should be outside \
                                     the provisioning allocation pool range")
            if net not in self.settings.storage_cluster_vip:
                raise AssertionError("storage_cluster_vip setting appears to  "
                                     "be on the wrong network, should be "
                                     "on the provisioning  network")

        if self.settings.use_static_vips is True:
            if int(start) <= int(
               self.settings.provisioning_vip.split(".")[-1]) <= int(end):
                raise AssertionError("provisioning_vip should be outside the \
                                     provisioning allocation pool range")

            if net not in self.settings.provisioning_vip:
                raise AssertionError("provisioning_vip setting appears to  "
                                     "be on the wrong network, should be "
                                     "on the provisioning  network")

        # discovery_ip_range (provisioning network)
        start = self.settings.discovery_ip_range.split(",")[0].split(".")[-1]
        end = self.settings.discovery_ip_range.split(",")[1].split(".")[-1]
        for each in self.settings.nodes:
            if hasattr(each, 'provisioning_ip'):
                ip = each.provisioning_ip.split(".")[-1]
                if int(start) <= int(ip) <= int(end):
                    raise AssertionError(each.provisioning_ip + " in " +
                                         ".properties is in the discovery ip" +
                                         " range defined in the .ini")

        # storage cluster allocation pool
        start = self.settings.storage_cluster_allocation_pool_start.split(
            ".")[-1]
        end = self.settings.storage_cluster_allocation_pool_end.split(".")[-1]
        for each in self.settings.nodes:
            if hasattr(each, 'storage_cluster_ip'):
                ip = each.storage_cluster_ip.split(".")[-1]
                if int(start) <= int(ip) <= int(end):
                    raise AssertionError(each.storage_cluster_ip + " in " +
                                         ".properties is in the storage " +
                                         "cluster allocation pool range " +
                                         "defined in the .ini")

        # management allocation pool
        start = self.settings.management_allocation_pool_start.split(
            ".")[-1]
        end = self.settings.management_allocation_pool_end.split(".")[-1]
        management_gateway = self.settings.management_gateway.split(".")[-1]
        if int(start) <= int(management_gateway) <= int(end):
            raise AssertionError("management_gateway in .ini is in the "
                                 "management_allocation_pool range "
                                 "defined in the .ini")
        sah_management_ip = self.settings.sah_node.management_ip.split(".")[-1]
        if int(start) <= int(sah_management_ip) <= int(end):
            raise AssertionError("SAH management_ip in .properties is in "
                                 "the management_allocation_pool range "
                                 "defined in the .ini")
        sah_drac_ip = self.settings.sah_node.idrac_ip.split(".")[-1]
        if int(start) <= int(sah_drac_ip) <= int(end):
            raise AssertionError("SAH idrac_ip in .properties is in "
                                 "the management_allocation_pool range "
                                 "defined in the .ini")

    def check_duplicate_ips(self):
        # Check for duplicate ip adresses in .properties and .ini
        ips = []
        for each in self.settings.__dict__:
            if ("ip" in each and
                    type(getattr(self.settings, each)) is str and
                    self.is_valid_ip(getattr(self.settings, each))):
                ips.append(getattr(self.settings, each))
        for each in self.settings.nodes:
            for att in each.__dict__:
                if self.is_valid_ip(str(getattr(each, att))):
                    ips.append(getattr(each, att))
        dups = [item for item,
                count in collections.Counter(ips).items() if count > 1]
        if len(dups) > 0:
            raise AssertionError("Duplicate ips found in your \
                                 .properties/.ini :" + ', '.join(dups))

    def verify_overcloud_name(self):
        # Do not allow a _ in the overcloud name
        # https://bugzilla.redhat.com/show_bug.cgi?id=1380099
        if "_" in self.settings.overcloud_name:
            raise AssertionError(" _ character is not allowed " +
                                 "in the .ini overcloud_name setting")

    def check_os_volume_size(self):
        hdw_nodes = (self.settings.controller_nodes +
                     self.settings.compute_nodes +
                     self.settings.ceph_nodes)

        for node in hdw_nodes:
            if hasattr(node, "os_volume_size_gb"):
                try:
                    os_volume_size_gb = int(node.os_volume_size_gb)
                except ValueError:
                    raise AssertionError("os_volume_size_gb of \"{}\" on node "
                                         "{} is not an integer".format(
                                             node.os_volume_size_gb,
                                             node.idrac_ip))

                if os_volume_size_gb <= 0:
                    raise AssertionError("os_volume_size_gb of \"{}\" on node "
                                         "\"{}\" on node {} is not a positive "
                                         "integer".format(
                                             node.os_volume_size_gb,
                                             node.idrac_ip))

    def check_net_attrs(self, node, should_have_attributes,
                        should_be_valid_ips):
        for each in should_have_attributes:
            assert hasattr(node, each), \
                " node has no " + each + " attribute"
        for each in should_be_valid_ips:
            if hasattr(node, "service_tag"):
                node_identifier = node.service_tag
            elif hasattr(node, "hostname"):
                node_identifier = node.hostname
            else:
                node_identifier = node.idrac_ip
            assert self.is_valid_ip(getattr(node, each)), \
                "Node " + node_identifier + " does not have a valid ip"

    def check_overcloud_node_net_attrs(self, node, should_have_attributes,
                                       should_be_valid_ips):
        if hasattr(node, "idrac_ip"):
            should_be_valid_ips.append("idrac_ip")
        else:
            assert hasattr(node, "service_tag"), \
                " node must have either the idrac_ip or service_tag attribute"

        self.check_net_attrs(node, should_have_attributes, should_be_valid_ips)

    def check_network_settings(self):
        # Verify SAH node network definition
        logger.debug("verifying sah network settings")
        shouldhaveattributes = ['hostname',
                                'idrac_ip',
                                'root_password',
                                'anaconda_ip',
                                'anaconda_iface',
                                'public_bond',
                                'public_slaves',
                                'private_bond',
                                'private_slaves',
                                'provisioning_ip',
                                'storage_ip',
                                'private_api_ip',
                                'management_ip',
                                'public_api_ip']

        shouldbbevalidips = ['idrac_ip',
                             'anaconda_ip',
                             'provisioning_ip',
                             'storage_ip',
                             'public_api_ip',
                             'private_api_ip',
                             'management_ip']

        self.check_net_attrs(self.settings.sah_node,
                             shouldhaveattributes,
                             shouldbbevalidips)

        # Verify director network definition
        logger.debug("verifying director vm network settings")
        shouldhaveattributes = ['hostname',
                                'root_password',
                                'provisioning_ip',
                                'management_ip',
                                'public_api_ip',
                                'private_api_ip']

        shouldbbevalidips = ['provisioning_ip',
                             'management_ip',
                             'public_api_ip',
                             'private_api_ip']

        self.check_net_attrs(self.settings.director_node,
                             shouldhaveattributes,
                             shouldbbevalidips)

        # Verify Dashboard VM node network definition
        logger.debug("verifying Dashboard VM network settings")
        shouldhaveattributes = ['hostname',
                                'root_password',
                                'storage_ip',
                                'public_api_ip']
        shouldbbevalidips = ['storage_ip', 'public_api_ip']

        self.check_net_attrs(self.settings.dashboard_node,
                             shouldhaveattributes,
                             shouldbbevalidips)

        # Verify Controller nodes network definitioncls
        logger.debug("verifying controller nodes network settings")
        for controller in self.settings.controller_nodes:
            shouldhaveattributes = []
            shouldbbevalidips = []

            if self.settings.overcloud_static_ips is True:
                shouldhaveattributes.extend(["public_api_ip",
                                             "private_api_ip",
                                             "storage_ip",
                                             "tenant_tunnel_ip"])
                shouldbbevalidips.extend(["public_api_ip",
                                          "private_api_ip",
                                          "storage_ip",
                                          "tenant_tunnel_ip"])
            self.check_overcloud_node_net_attrs(controller,
                                                shouldhaveattributes,
                                                shouldbbevalidips)

        # Verify Compute nodes network definition
        logger.debug("verifying compute nodes network settings")
        for compute in self.settings.compute_nodes:
            shouldhaveattributes = []
            shouldbbevalidips = []
            if self.settings.overcloud_static_ips is True:
                shouldhaveattributes.extend(["private_api_ip",
                                             "storage_ip",
                                             "tenant_tunnel_ip"])
                shouldbbevalidips.extend(["private_api_ip",
                                          "storage_ip",
                                          "tenant_tunnel_ip"])
            self.check_overcloud_node_net_attrs(compute,
                                                shouldhaveattributes,
                                                shouldbbevalidips)

        # Verify Storage nodes network definition
        logger.debug("verifying storage nodes network settings")
        for storage in self.settings.ceph_nodes:
            shouldhaveattributes = []
            shouldbbevalidips = []
            if self.settings.overcloud_static_ips is True:
                shouldhaveattributes.extend(["storage_ip",
                                             "storage_cluster_ip"])
                shouldbbevalidips.extend(["storage_ip",
                                          "storage_cluster_ip"])
            self.check_overcloud_node_net_attrs(storage,
                                                shouldhaveattributes,
                                                shouldbbevalidips)

    def validate_profile(self):
        self.profile = Profile()
        self.profile.validate_configuration()

    def validate_nic_configs(self):

        # Get the user supplied NIC settings from the .ini
        ini_nics_settings = self.settings.get_nics_settings()

        missing_settings = []
        nic_env_file_missing = False
        if 'nic_env_file' not in ini_nics_settings:
            nic_env_file_missing = True
            missing_settings.append('nic_env_file')

        if 'sah_bond_opts' not in ini_nics_settings:
            missing_settings.append('sah_bond_opts')

        extra_settings = set()
        missing_variable_settings = set()
        if not nic_env_file_missing:
            if not os.path.isfile(self.settings.nic_env_file_path):
                raise AssertionError("The nic_env_file {} does not exist"
                                     "!".format(
                                         self.settings.nic_env_file_path))

            # Get the NIC settings from the NIC environment file
            with open(self.settings.nic_env_file_path, 'r') as yaml_stream:
                nic_yaml = yaml.load(yaml_stream)
            nic_env_nics_settings = nic_yaml['parameter_defaults']

            # Error check for extra or missing NIC settings
            ini_settings_names = set(
                self.settings.get_curated_nics_settings().keys())

            nic_env_settings_names = set(nic_env_nics_settings.keys())

            extra_settings = ini_settings_names - nic_env_settings_names
            missing_variable_settings = nic_env_settings_names - \
                ini_settings_names

        missing_settings.extend(missing_variable_settings)

        error_msg = ""
        if len(extra_settings) > 0:
            error_msg += ("The following settings in the [Nodes Nics and "
                          "Bonding Settings] section in {} are "
                          "unused:\n{}\n".format(
                              self.settings.settings_file,
                              ',\n'.join(sorted(extra_settings))))

        if len(missing_settings) > 0:
            error_msg += ("The following settings are missing from the [Nodes "
                          "Nics and Bonding Settings] section in {}:\n"
                          "{}".format(
                              self.settings.settings_file,
                              ',\n'.join(sorted(missing_settings))))

        if error_msg:
            raise AssertionError(error_msg)

    def verify_dpdk_dependencies(self):
        # DPDK requires CPU Pinning and Hugepages
        logger.debug("verifying numa and hugepages enabled when dpdk enabled")
        if (self.settings.enable_ovs_dpdk is True and
                self.settings.numa_enable is True and
                self.settings.hpg_enable is False):
            raise AssertionError("Hugepages are not enabled, this is" +
                                 " required for OVS-DPDK. Please verify" +
                                 " this setting.")
        elif (self.settings.enable_ovs_dpdk is True and
              self.settings.numa_enable is False and
              self.settings.hpg_enable is True):
            raise AssertionError("NUMA is not enabled, this is required" +
                                 " for OVS-DPDK. Please verify this setting.")
        elif (self.settings.enable_ovs_dpdk is True and
              self.settings.numa_enable is False and
              self.settings.hpg_enable is False):
            raise AssertionError("Neither Hugepages nor NUMA is enabled," +
                                 " this is required for OVS-DPDK. Please" +
                                 " verify this setting.")
        if (self.settings.enable_ovs_dpdk is True and
                self.settings.hpg_size == "2MB"):
            raise AssertionError("Hugepages size should be 1GB, this is" +
                                 " required for OVS-DPDK. Please verify" +
                                 " this setting.")
        logger.debug("verifying DVR is disabled when OVS-DPDK is enabled")
        if (self.settings.enable_ovs_dpdk is True and
                self.settings.dvr_enable is True):
            raise AssertionError("OVS-DPDk and DVR can not be enabled" +
                                 " together.Please disable one " +
                                 "feature and verify the settings.")

    def verify_sriov_dependencies(self):
        logger.debug("verifying DVR is disabled when SR-IOV is enabled")
        if (self.settings.enable_sriov is True and
                self.settings.dvr_enable is True):
            raise AssertionError("SR-IOV and DVR can not be " +
                                 "enabled together.Please disable" +
                                 "one feature and verify the settings.")

    def verify_hw_offload_dependencies(self):
        logger.debug("verifying Smart NIC is enabled when SR-IOV is enabled")
        if (self.settings.enable_sriov is False and
                self.settings.enable_smart_nic is True):
            raise AssertionError("SR-IOV hardware offload cant be " +
                                 "enabled as SRIOV is not being enabled. " +
                                 "Please verify the settings.")
