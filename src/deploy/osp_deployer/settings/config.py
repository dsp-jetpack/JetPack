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

import ConfigParser
import sys
import logging
import os
import json
import subprocess
from osp_deployer.node_conf import NodeConf

logger = logging.getLogger("osp_deployer")


class Settings():
    settings = ''

    def __init__(self, settings_file):

        assert os.path.isfile(
            settings_file), settings_file + " file does not exist"
        self.conf = ConfigParser.ConfigParser()
        self.conf.read(settings_file)
        self.settings_file = settings_file
        cluster = self.get_settings_section(
            "Cluster Settings")
        if cluster['deploy_overcloud_debug'].lower() == 'true':
            self.deploy_overcloud_debug = True
        else:
            self.deploy_overcloud_debug = False
        self.storage_network = cluster['storage_network']
        self.storage_cluster_network = cluster[
            'storage_cluster_network']
        self.public_api_network = cluster['public_api_network']
        self.provisioning_network = cluster[
            'provisioning_network']
        self.private_api_network = cluster[
            'private_api_network']
        self.private_api_allocation_pool_start = cluster[
            'private_api_allocation_pool_start']
        self.private_api_allocation_pool_end = cluster[
            'private_api_allocation_pool_end']
        self.storage_allocation_pool_start = cluster[
            'storage_allocation_pool_start']
        self.storage_allocation_pool_end = cluster[
            'storage_allocation_pool_end']
        self.storage_cluster_allocation_pool_start = cluster[
            'storage_cluster_allocation_pool_start']
        self.storage_cluster_allocation_pool_end = cluster[
            'storage_cluster_allocation_pool_end']
        self.public_api_allocation_pool_start = cluster[
            'public_api_allocation_pool_start']
        self.public_api_allocation_pool_end = cluster[
            'public_api_allocation_pool_end']
        self.public_api_gateway = cluster['public_api_gateway']
        self.provisioning_vlanid = cluster[
            'provisioning_vlanid']
        self.provisioning_netmask = cluster[
            'provisioning_netmask']
        self.provisioning_gateway = cluster[
            'provisioning_gateway']
        self.storage_vlanid = cluster['storage_vlanid']
        self.storage_netmask = cluster['storage_netmask']
        self.public_api_vlanid = cluster['public_api_vlanid']
        self.public_api_netmask = cluster[
            'public_api_netmask']
        self.private_api_vlanid = cluster[
            'private_api_vlanid']
        self.private_api_netmask = cluster[
            'private_api_netmask']
        self.management_network = cluster[
            'management_network']
        self.management_vlanid = cluster['management_vlanid']
        self.management_netmask = cluster['management_netmask']
        self.management_gateway = cluster['management_gateway']
        self.management_allocation_pool_start = cluster[
            'management_allocation_pool_start']
        self.management_allocation_pool_end = cluster[
            'management_allocation_pool_end']
        self.name_server = cluster['name_server']
        self.storage_cluster_vlanid = cluster[
            'storage_cluster_vlanid']
        self.provisioning_net_dhcp_start = cluster[
            'provisioning_net_dhcp_start']
        self.provisioning_net_dhcp_end = cluster[
            'provisioning_net_dhcp_end']
        self.discovery_ip_range = cluster[
            'discovery_ip_range']
        self.tenant_tunnel_network = cluster['tenant_tunnel_network']
        self.tenant_tunnel_network_allocation_pool_start = cluster[
            'tenant_tunnel_network_allocation_pool_start']
        self.tenant_tunnel_network_allocation_pool_end = cluster[
            'tenant_tunnel_network_allocation_pool_end']
        self.tenant_tunnel_vlanid = cluster['tenant_tunnel_network_vlanid']
        self.tenant_vlan_range = cluster['tenant_vlan_range']
        self.director_install_account_user = cluster[
            'director_install_user']
        self.director_install_account_pwd = cluster[
            'director_install_user_password']
        self.overcloud_name = cluster[
            'overcloud_name']
        self.controller_bond0_interfaces = cluster[
            'controller_bond0_interfaces']
        self.controller_bond1_interfaces = cluster[
            'controller_bond1_interfaces']
        self.controller_provisioning_interface = cluster[
            'controller_provisioning_interface']
        self.compute_bond0_interfaces = cluster[
            'compute_bond0_interfaces']
        self.compute_bond1_interfaces = cluster[
            'compute_bond1_interfaces']
        self.compute_provisioning_interface = cluster[
            'compute_provisioning_interface']
        self.storage_bond0_interfaces = cluster[
            'storage_bond0_interfaces']
        self.storage_bond1_interfaces = cluster[
            'storage_bond1_interfaces']
        self.storage_provisioning_interface = cluster[
            'storage_provisioning_interface']
        self.network_conf = cluster[
            'cluster_nodes_configuration_file']
        self.domain = cluster['domain']
        self.sah_ipmi_user = cluster['sah_ipmi_user']
        self.sah_ipmi_password = cluster['sah_ipmi_password']
        self.ipmi_user = cluster['ipmi_user']
        self.ipmi_password = cluster['ipmi_password']
        self.new_ipmi_password = cluster['new_ipmi_password']
        self.subscription_manager_user = cluster[
            'subscription_manager_user']
        self.subscription_manager_password = cluster[
            'subscription_manager_password']
        self.subscription_manager_pool_sah = cluster[
            'subscription_manager_pool_sah']
        self.subscription_manager_pool_vm_rhel = cluster[
            'subscription_manager_pool_vm_rhel']
        self.subscription_manager_vm_ceph = cluster[
            'subscription_manager_vm_ceph']
        self.controller_bond_opts = cluster[
            'controller_bond_opts']
        self.compute_bond_opts = cluster['compute_bond_opts']
        self.storage_bond_opts = cluster['storage_bond_opts']
        self.overcloud_deploy_timeout = cluster[
            'overcloud_deploy_timeout']
        self.ntp_server = cluster['ntp_servers']
        self.time_zone = cluster['time_zone']

        if 'subscription_check_retries' in cluster:
            self.subscription_check_retries = cluster[
                'subscription_check_retries']
        else:
            self.subscription_check_retries = 20
        jsonv = cluster['use_custom_instack_json'].lower()
        if jsonv == 'true':
            self.use_custom_instack_json = True
            self.custom_instack_json = cluster[
                'custom_instack_json']
        else:
            self.use_custom_instack_json = False
        if cluster['use_internal_repo'].lower() == 'true':
            self.internal_repos = True
            self.internal_repos_urls = []
            for each in cluster['internal_repos_locations'].split(';'):
                self.internal_repos_urls.append(each)
        else:
            self.internal_repos = False
        if cluster['overcloud_static_ips'].lower() == 'true':
            self.overcloud_static_ips = True
        else:
            self.overcloud_static_ips = False
        if cluster['use_static_vips'].lower() == 'true':
            self.use_static_vips = True
            self.redis_vip = cluster['redis_vip']
            self.provisioning_vip = cluster['provisioning_vip']
            self.private_api_vip = cluster['private_api_vip']
            self.public_api_vip = cluster['public_api_vip']
            self.storage_vip = cluster['storage_vip']
            self.storage_cluster_vip = cluster['storage_cluster_vip']
        else:
            self.use_static_vips = False
        if cluster['enable_version_locking'].lower() == 'true':
            self.version_locking_enabled = True
        else:
            self.version_locking_enabled = False
        if cluster['hardware'].lower() == 'fx':
            self.is_fx = True
        else:
            self.is_fx = False
        if cluster['use_ipmi_driver'].lower() == 'true':
            self.use_ipmi_driver = True
        else:
            self.use_ipmi_driver = False

        if cluster['use_in_band_introspection'].lower() == 'true':
            self.use_in_band_introspection = True
        else:
            self.use_in_band_introspection = False

        if cluster['enable_eqlx_backend'].lower() == 'true':
            self.enable_eqlx_backend = True
            self.eqlx_san_ip = cluster['eqlx_san_ip']
            self.eqlx_san_login = cluster['eqlx_san_login']
            self.eqlx_san_password = cluster[
                'eqlx_san_password']
            self.eqlx_ch_login = cluster['eqlx_ch_login']
            self.eqlx_ch_pass = cluster['eqlx_ch_pass']
            self.eqlx_group_n = cluster['eqlx_group_n']
            self.eqlx_thin_provisioning = cluster[
                'eqlx_thin_provisioning']
            self.eqlx_pool = cluster['eqlx_pool']
            self.eqlx_use_chap = cluster['eqlx_use_chap']
        else:
            self.enable_eqlx_backend = False

        if cluster['enable_dellsc_backend'].lower() == 'true':
            self.enable_dellsc_backend = True
            self.dellsc_san_ip = cluster['dellsc_san_ip']
            self.dellsc_san_login = cluster[
                'dellsc_san_login']
            self.dellsc_san_password = cluster[
                'dellsc_san_password']
            self.dellsc_iscsi_ip_address = cluster[
                'dellsc_iscsi_ip_address']
            self.dellsc_iscsi_port = cluster[
                'dellsc_iscsi_port']
            self.dellsc_api_port = cluster['dellsc_api_port']
            self.dellsc_ssn = cluster['dellsc_ssn']
            self.dellsc_server_folder = cluster[
                'dellsc_server_folder']
            self.dellsc_volume_folder = cluster[
                'dellsc_volume_folder']
        else:
            self.enable_dellsc_backend = False

        if cluster['enable_rbd_backend'].lower() == 'true':
            self.enable_rbd_backend = True
        else:
            self.enable_rbd_backend = False

        if cluster['enable_rbd_nova_backend'].lower() == 'true':
            self.enable_rbd_nova_backend = True
        else:
            self.enable_rbd_nova_backend = False

        if cluster['enable_fencing'].lower() == 'true':
            self.enable_fencing = True
        else:
            self.enable_fencing = False

        if cluster['enable_instance_ha'].lower() == 'true':
            self.enable_instance_ha = True
        else:
            self.enable_instance_ha = False

        self.bastion_settings_map = self.get_settings_section(
            "Bastion Settings")
        self.cloud_repo_dir = self.bastion_settings_map['cloud_repo_dir']

        if self.bastion_settings_map['pull_images_from_cdn'].lower() == 'true':
            self.pull_images_from_cdn = True
        else:
            self.pull_images_from_cdn = False
            self.discovery_ram_disk_image = self.bastion_settings_map[
                'discovery_ram_disk_image']
            self.overcloud_image = self.bastion_settings_map['overcloud_image']

        self.rhel_iso = self.bastion_settings_map['rhel_iso']

        if sys.platform.startswith('linux'):
            self.cygwin_installdir = 'n/a'
        else:
            self.cygwin_installdir = self.bastion_settings_map[
                'cygwin_installdir']
        try:
            if self.bastion_settings_map['run_sanity'].lower() == 'true':
                self.run_sanity = True
            else:
                self.run_sanity = False
        except KeyError:
            self.run_sanity = False
        try:
            self.bastion_host_ip = self.bastion_settings_map['bastion_host_ip']
            self.bastion_host_user = self.bastion_settings_map[
                'bastion_host_user']
            self.bastion_host_password = self.bastion_settings_map[
                'bastion_host_password']
            self.retreive_switches_config = True
        except KeyError:
            self.retreive_switches_config = False
        try:
            if self.bastion_settings_map['run_tempest'].lower() == 'true':
                self.run_tempest = True
                if self.bastion_settings_map['tempest_smoke_only'].lower() \
                        == 'true':
                    self.tempest_smoke_only = True
                else:
                    self.tempest_smoke_only = False
            else:
                self.run_tempest = False
                self.tempest_smoke_only = False
        except KeyError:
            self.run_tempest = False
            self.tempest_smoke_only = False
        try:
            if self.bastion_settings_map['verify_rhsm_status'].lower() == 'true':
                self.verify_rhsm_status = True
            else:
                self.verify_rhsm_status = False
        except KeyError:
            self.verify_rhsm_status = True

        sanity_settings = self.get_settings_section(
            "Sanity Test Settings")
        self.floating_ip_network = sanity_settings['floating_ip_network']
        self.floating_ip_network_start_ip = sanity_settings['floating_ip_network_start_ip']
        self.floating_ip_network_end_ip = sanity_settings['floating_ip_network_end_ip']
        self.floating_ip_network_gateway = sanity_settings['floating_ip_network_gateway']
        self.floating_ip_network_vlan = sanity_settings['floating_ip_network_vlan']
        self.sanity_tenant_network = sanity_settings['sanity_tenant_network']
        self.sanity_user_password = sanity_settings['sanity_user_password']
        self.sanity_user_email = sanity_settings['sanity_user_email']
        self.sanity_key_name = sanity_settings['sanity_key_name']
        self.sanity_number_instances= sanity_settings['sanity_number_instances']
        self.sanity_image_url = sanity_settings['sanity_image_url']

        self.lock_files_dir = self.cloud_repo_dir + "/data/vlock_files"
        self.foreman_configuration_scripts = self.cloud_repo_dir + "/src"

        self.sah_kickstart = self.cloud_repo_dir + "/src/mgmt/osp-sah.ks"
        self.director_deploy_sh = self.foreman_configuration_scripts +\
            '/mgmt/deploy-director-vm.sh'
        self.rhscon_deploy_py = self.foreman_configuration_scripts +\
            '/mgmt/deploy-rhscon-vm.py'

        self.undercloud_conf = self.foreman_configuration_scripts +\
            '/pilot/undercloud.conf'
        self.install_director_sh = self.foreman_configuration_scripts +\
            '/pilot/install-director.sh'
        self.deploy_overcloud_sh = self.foreman_configuration_scripts + \
            '/pilot/deploy-overcloud.py'
        self.assign_role_py = self.foreman_configuration_scripts +\
            '/pilot/assign_role.py'
        self.network_env_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/network-environment.yaml'
        self.dell_storage_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/dell-cinder-backends.yaml'
        self.dell_env_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/dell-environment.yaml'
        if self.is_fx is True:
            self.controller_yaml = self.foreman_configuration_scripts + \
                '/pilot/templates/nic-configs-fx/controller.yaml'
            self.compute_yaml = self.foreman_configuration_scripts + \
                '/pilot/templates/nic-configs-fx/compute.yaml'
            self.ceph_storage_yaml = self.foreman_configuration_scripts + \
                '/pilot/templates/nic-configs-fx/ceph-storage.yaml'
        else:
            self.controller_yaml = self.foreman_configuration_scripts + \
                '/pilot/templates/nic-configs/controller.yaml'
            self.compute_yaml = self.foreman_configuration_scripts + \
                '/pilot/templates/nic-configs/compute.yaml'
            self.ceph_storage_yaml = self.foreman_configuration_scripts + \
                '/pilot/templates/nic-configs/ceph-storage.yaml'
        self.static_ips_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/static-ip-environment.yaml'
        self.static_vip_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/static-vip-environment.yaml'
        self.sanity_ini = self.foreman_configuration_scripts + \
            '/pilot/deployment-validation/sanity.ini'
        self.ipxe_rpm = self.foreman_configuration_scripts + \
            '/pilot/ipxe/ipxe-bootimgs-20151005-1.git6847232.el7.' \
            'test.noarch.rpm'

        self.controller_nodes = []
        self.compute_nodes = []
        self.ceph_nodes = []
        self.switches = []
        self.nodes = []

        self.overcloud_nodes_pwd = cluster['overcloud_nodes_pwd']
        if 'rhsm_repos' in cluster and len(cluster['rhsm_repos']) > 0:
            logger.info("Using ini repo settings")
            self.rhsm_repos = cluster['rhsm_repos'].split(',')
        else:
            logger.info("using default repo settings")
            self.rhsm_repos = [
                'rhel-7-server-openstack-10-rpms',
                'rhel-7-server-openstack-10-devtools-rpms']

        with open(self.network_conf) as config_file:
            json_data = json.load(config_file)
            for each in json_data:
                node = NodeConf(each)
                try:
                    if node.is_sah == "true":
                        self.sah_node = node
                except AttributeError:
                    pass
                try:
                    if node.is_director == "true":
                        self.director_node = node
                except AttributeError:
                    pass
                try:
                    if node.is_rhscon == "true":
                        self.rhscon_node = node
                except AttributeError:
                    pass
                try:
                    if node.is_controller == "true":
                        node.is_controller = True
                        self.controller_nodes.append(node)
                except AttributeError:
                    node.is_controller = False
                    pass
                try:
                    if node.is_compute == "true":
                        node.is_compute = True
                        self.compute_nodes.append(node)
                except AttributeError:
                    node.is_compute = False
                    pass
                try:
                    if node.is_ceph_storage == "true":
                        self.ceph_nodes.append(node)
                        node.is_storage = True
                except AttributeError:
                    node.is_storage = False
                    pass
                try:
                    if node.is_switch == "true":
                        self.switches.append(node)
                except AttributeError:
                    self.nodes.append(node)
                    pass
                try:
                    if node.skip_raid_config == "true":
                        node.skip_raid_config = True
                except AttributeError:
                    node.skip_raid_config = False
                    pass

        Settings.settings = self

    def get_settings_section(self, section):
        dictr = {}
        options = self.conf.options(section)
        for option in options:
            try:
                dictr[option] = self.conf.get(section, option)
                if dictr[option] == -1:
                    logger.debug("skip: %s" % option)
            except ConfigParser.NoSectionError:
                logger.debug("exception on %s!" % option)
                dictr[option] = None
        return dictr

    def get_version_info(self):
        # Grab the source version info from either built .tar or git
        try:
            repo_release_txt = self.cloud_repo_dir + "/release.txt"
            if os.path.isfile(repo_release_txt):
                re_ = open(repo_release_txt, 'r').read()
            else:
                cmd = "cd " + self.cloud_repo_dir + ";" + \
                      "git log | grep -m 1 'commit'"
                re_ = subprocess.check_output(cmd,
                                              stderr=subprocess.STDOUT,
                                              shell=True).rstrip()
            self.source_version = re_
        except:
            logger.debug("unconventional setup...can t" +
                         " pick source version info")
            self.source_version = "????"
