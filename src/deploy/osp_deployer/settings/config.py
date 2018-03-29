#!/usr/bin/env python

# Copyright (c) 2015-2018 Dell Inc. or its subsidiaries.
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

import logging
import os
import inspect
import json
import subprocess
import ConfigParser
from osp_deployer.node_conf import NodeConf

logger = logging.getLogger("osp_deployer")


class Settings():
    settings = ''

    def __init__(self, settings_file):

        assert os.path.isfile(
            settings_file), settings_file + " file does not exist"

        f_name = "/sample_xsp_profile.ini"
        sample_ini = os.path.dirname(inspect.getfile(Settings)) + f_name

        conf = ConfigParser.ConfigParser()
        # The following line makes the parser return case sensitive keys
        conf.optionxform = str
        conf.read(sample_ini)

        your_ini = settings_file
        yourConf = ConfigParser.ConfigParser()
        # The following line makes the parser return case sensitive keys
        yourConf.optionxform = str
        yourConf.read(your_ini)

        error_msg = ""
        warning_msg = ""
        for stanza in conf.sections():
            if yourConf.has_section(stanza):
                # Because the NIC settings are variable, we don't check them
                # here and instead check them during configuration validation
                if stanza != 'Nodes Nics and Bonding Settings':
                    for setting in conf.options(stanza):
                        if yourConf.has_option(stanza, setting):
                            pass
                        else:
                            error_msg = error_msg + "Missing \"" +\
                                setting + "\" setting in your ini file [" +\
                                stanza + "] section \n"
            else:
                error_msg = error_msg + "Missing [" + stanza + "] " +\
                    "section in your ini file \n"

        for stanza in yourConf.sections():
            if conf.has_section(stanza):
                # Because the NIC settings are variable, we don't check them
                # here and instead check them during configuration validation
                if stanza != 'Nodes Nics and Bonding Settings':
                    for setting in yourConf.options(stanza):
                        if conf.has_option(stanza, setting):
                            pass
                        else:
                            warning_msg = warning_msg + "\"" + setting + \
                                "\" setting in your ini file [" + \
                                stanza + "] section is deprecated and " +\
                                "should be removed\n"
            else:
                warning_msg = warning_msg + "Section [" + stanza + \
                    "] in your ini file is deprecated" +\
                    " and should be removed\n"

        if len(error_msg) > 0:
            raise AssertionError("\n" + error_msg)
        if len(warning_msg) > 0:
            logger.info("\n" + warning_msg)

        self.conf = yourConf
        self.settings_file = settings_file

        network_settings = self.get_settings_section(
            "Network Settings")
        self.storage_network = network_settings['storage_network']
        self.storage_cluster_network = network_settings[
            'storage_cluster_network']
        self.public_api_network = network_settings['public_api_network']
        self.provisioning_network = network_settings[
            'provisioning_network']
        self.private_api_network = network_settings[
            'private_api_network']
        self.private_api_allocation_pool_start = network_settings[
            'private_api_allocation_pool_start']
        self.private_api_allocation_pool_end = network_settings[
            'private_api_allocation_pool_end']
        self.storage_allocation_pool_start = network_settings[
            'storage_allocation_pool_start']
        self.storage_allocation_pool_end = network_settings[
            'storage_allocation_pool_end']
        self.storage_cluster_allocation_pool_start = network_settings[
            'storage_cluster_allocation_pool_start']
        self.storage_cluster_allocation_pool_end = network_settings[
            'storage_cluster_allocation_pool_end']
        self.public_api_allocation_pool_start = network_settings[
            'public_api_allocation_pool_start']
        self.public_api_allocation_pool_end = network_settings[
            'public_api_allocation_pool_end']
        self.public_api_gateway = network_settings['public_api_gateway']
        self.provisioning_vlanid = network_settings[
            'provisioning_vlanid']
        self.provisioning_netmask = network_settings[
            'provisioning_netmask']
        self.provisioning_gateway = network_settings[
            'provisioning_gateway']
        self.storage_vlanid = network_settings['storage_vlanid']
        self.storage_netmask = network_settings['storage_netmask']
        self.public_api_vlanid = network_settings['public_api_vlanid']
        self.public_api_netmask = network_settings[
            'public_api_netmask']
        self.private_api_vlanid = network_settings[
            'private_api_vlanid']
        self.private_api_netmask = network_settings[
            'private_api_netmask']
        self.management_network = network_settings[
            'management_network']
        self.management_vlanid = network_settings['management_vlanid']
        self.management_netmask = network_settings['management_netmask']
        self.management_gateway = network_settings['management_gateway']
        self.management_allocation_pool_start = network_settings[
            'management_allocation_pool_start']
        self.management_allocation_pool_end = network_settings[
            'management_allocation_pool_end']
        self.name_server = network_settings['name_server']
        self.storage_cluster_vlanid = network_settings[
            'storage_cluster_vlanid']
        self.provisioning_net_dhcp_start = network_settings[
            'provisioning_net_dhcp_start']
        self.provisioning_net_dhcp_end = network_settings[
            'provisioning_net_dhcp_end']
        self.discovery_ip_range = network_settings[
            'discovery_ip_range']
        self.tenant_tunnel_network = network_settings['tenant_tunnel_network']
        self.tenant_tunnel_network_allocation_pool_start = network_settings[
            'tenant_tunnel_network_allocation_pool_start']
        self.tenant_tunnel_network_allocation_pool_end = network_settings[
            'tenant_tunnel_network_allocation_pool_end']
        self.tenant_tunnel_vlanid = network_settings[
            'tenant_tunnel_network_vlanid']
        self.tenant_vlan_range = network_settings['tenant_vlan_range']
        mtu_settings = self.get_settings_section(
            "MTU Settings")
        self.mtu_selection = mtu_settings[
            'mtu_selection']
        self.mtu_size_global_default = mtu_settings[
            'mtu_size_global_default']
        if self.mtu_selection == 'global':
            self.tenant_tunnel_network_mtu = self.mtu_size_global_default
            self.tenant_network_mtu = self.mtu_size_global_default
            self.storage_cluster_network_mtu = self.mtu_size_global_default
            self.storage_network_mtu = self.mtu_size_global_default
            self.private_api_network_mtu = self.mtu_size_global_default
            self.public_api_network_mtu = self.mtu_size_global_default
            self.floating_ip_network_mtu = self.mtu_size_global_default
        elif self.mtu_selection == 'per_network':
            self.mtu_size_global_default = '1500'
            self.tenant_tunnel_network_mtu = mtu_settings[
                'tenant_tunnel_network_mtu']
            self.tenant_network_mtu = mtu_settings[
                'tenant_network_mtu']
            self.storage_cluster_network_mtu = mtu_settings[
                'storage_cluster_network_mtu']
            self.storage_network_mtu = mtu_settings[
                'storage_network_mtu']
            self.private_api_network_mtu = mtu_settings[
                'private_api_network_mtu']
            self.public_api_network_mtu = mtu_settings[
                'public_api_network_mtu']
            self.floating_ip_network_mtu = mtu_settings[
                'floating_ip_network_mtu']
        # fixed mtu values
        self.default_bond_mtu = '9216'
        self.management_network_mtu = '1500'
        self.provisioning_network_mtu = '1500'

        vips_settings = self.get_settings_section(
            "Vips Settings")
        if vips_settings['use_static_vips'].lower() == 'true':
            self.use_static_vips = True
            self.redis_vip = vips_settings['redis_vip']
            self.provisioning_vip = vips_settings['provisioning_vip']
            self.private_api_vip = vips_settings['private_api_vip']
            self.public_api_vip = vips_settings['public_api_vip']
            self.storage_vip = vips_settings['storage_vip']
            self.storage_cluster_vip = vips_settings['storage_cluster_vip']
        else:
            self.use_static_vips = False

        rhsm_settings = self.get_settings_section(
            "Subscription Manager Settings")
        self.subscription_manager_user = rhsm_settings[
            'subscription_manager_user']
        self.subscription_manager_password = rhsm_settings[
            'subscription_manager_password']
        self.subscription_manager_pool_sah = rhsm_settings[
            'subscription_manager_pool_sah']
        self.subscription_manager_pool_vm_rhel = rhsm_settings[
            'subscription_manager_pool_vm_rhel']
        self.subscription_manager_vm_ceph = rhsm_settings[
            'subscription_manager_vm_ceph']
        if 'subscription_check_retries' in rhsm_settings:
            self.subscription_check_retries = rhsm_settings[
                'subscription_check_retries']
        else:
            self.subscription_check_retries = 20

        ipmi_settings = self.get_settings_section(
            "IPMI credentials Settings")
        self.sah_ipmi_user = ipmi_settings['sah_ipmi_user']
        self.sah_ipmi_password = ipmi_settings['sah_ipmi_password']
        self.ipmi_user = ipmi_settings['ipmi_user']
        self.ipmi_password = ipmi_settings['ipmi_password']
        self.new_ipmi_password = ipmi_settings['new_ipmi_password']

        deploy_settings = self.get_settings_section(
            "Deployment Settings")
        self.director_install_account_user = deploy_settings[
            'director_install_user']
        self.director_install_account_pwd = deploy_settings[
            'director_install_user_password']
        self.overcloud_name = deploy_settings[
            'overcloud_name']
        self.network_conf = deploy_settings[
            'cluster_nodes_configuration_file']
        self.domain = deploy_settings['domain']
        self.ntp_server = deploy_settings['ntp_servers']
        self.time_zone = deploy_settings['time_zone']
        if deploy_settings['overcloud_static_ips'].lower() == 'true':
            self.overcloud_static_ips = True
        else:
            self.overcloud_static_ips = False

        self.profile = deploy_settings['profile'].lower()

        if deploy_settings['enable_rbd_backend'].lower() == 'true':
            self.enable_rbd_backend = True
        else:
            self.enable_rbd_backend = False

        if deploy_settings['enable_rbd_nova_backend'].lower() == 'true':
            self.enable_rbd_nova_backend = True
        else:
            self.enable_rbd_nova_backend = False

        if deploy_settings['enable_fencing'].lower() == 'true':
            self.enable_fencing = True
        else:
            self.enable_fencing = False

        if deploy_settings['enable_instance_ha'].lower() == 'true':
            self.enable_instance_ha = True
        else:
            self.enable_instance_ha = False
        self.overcloud_nodes_pwd = deploy_settings['overcloud_nodes_pwd']
        dellnfv_settings = self.get_settings_section(
            "Dell NFV Settings")
        if dellnfv_settings['hpg_enable'].lower() == 'true':
            self.hpg_enable = True
        else:
            self.hpg_enable = False
        self.hpg_size = dellnfv_settings['hpg_size']
        if dellnfv_settings['numa_enable'].lower() == 'true':
            self.numa_enable = True
        else:
            self.numa_enable = False

        backend_settings = self.get_settings_section(
            "Storage back-end Settings")
        if backend_settings['enable_dellsc_backend'].lower() == 'true':
            self.enable_dellsc_backend = True
            self.dellsc_san_ip = backend_settings['dellsc_san_ip']
            self.dellsc_san_login = backend_settings[
                'dellsc_san_login']
            self.dellsc_san_password = backend_settings[
                'dellsc_san_password']
            self.dellsc_iscsi_ip_address = backend_settings[
                'dellsc_iscsi_ip_address']
            self.dellsc_iscsi_port = backend_settings[
                'dellsc_iscsi_port']
            self.dellsc_api_port = backend_settings['dellsc_api_port']
            self.dellsc_ssn = backend_settings['dellsc_ssn']
            self.dellsc_server_folder = backend_settings[
                'dellsc_server_folder']
            self.dellsc_volume_folder = backend_settings[
                'dellsc_volume_folder']
        else:
            self.enable_dellsc_backend = False

        sanity_settings = self.get_settings_section(
            "Sanity Test Settings")
        self.floating_ip_network = sanity_settings['floating_ip_network']
        self.floating_ip_network_start_ip = \
            sanity_settings['floating_ip_network_start_ip']
        self.floating_ip_network_end_ip = \
            sanity_settings['floating_ip_network_end_ip']
        self.floating_ip_network_gateway = \
            sanity_settings['floating_ip_network_gateway']
        self.floating_ip_network_vlan = \
            sanity_settings['floating_ip_network_vlan']
        self.sanity_tenant_network = sanity_settings['sanity_tenant_network']
        self.sanity_user_password = sanity_settings['sanity_user_password']
        self.sanity_user_email = sanity_settings['sanity_user_email']
        self.sanity_key_name = sanity_settings['sanity_key_name']
        self.sanity_number_instances = \
            sanity_settings['sanity_number_instances']
        self.sanity_image_url = sanity_settings['sanity_image_url']
        if sanity_settings['run_sanity'].lower() == 'true':
            self.run_sanity = True
        else:
            self.run_sanity = False

        tempest_settings = self.get_settings_section(
            "Tempest Settings")
        if tempest_settings['run_tempest'].lower() == 'true':
            self.run_tempest = True
            if tempest_settings['tempest_smoke_only'].lower() \
                    == 'true':
                self.tempest_smoke_only = True
            else:
                self.tempest_smoke_only = False
        else:
            self.run_tempest = False
            self.tempest_smoke_only = False

        dev_settings = self.get_settings_section(
            "Advanced Settings")
        if dev_settings['deploy_overcloud_debug'].lower() == 'true':
            self.deploy_overcloud_debug = True
        else:
            self.deploy_overcloud_debug = False
        self.overcloud_deploy_timeout = dev_settings[
            'overcloud_deploy_timeout']
        jsonv = dev_settings['use_custom_instack_json'].lower()
        if jsonv == 'true':
            self.use_custom_instack_json = True
            self.custom_instack_json = dev_settings[
                'custom_instack_json']
        else:
            self.use_custom_instack_json = False
        if dev_settings['use_internal_repo'].lower() == 'true':
            self.internal_repos = True
            self.internal_repos_urls = []
            for each in dev_settings['internal_repos_locations'].split(';'):
                self.internal_repos_urls.append(each)
        else:
            self.internal_repos = False
        if dev_settings['enable_version_locking'].lower() == 'true':
            self.version_locking_enabled = True
        else:
            self.version_locking_enabled = False
        if dev_settings['use_ipmi_driver'].lower() == 'true':
            self.use_ipmi_driver = True
        else:
            self.use_ipmi_driver = False
        if dev_settings['use_in_band_introspection'].lower() == 'true':
            self.use_in_band_introspection = True
        else:
            self.use_in_band_introspection = False
        self.cloud_repo_dir = dev_settings['cloud_repo_dir']

        if dev_settings['pull_images_from_cdn'].lower() == 'true':
            self.pull_images_from_cdn = True
        else:
            self.pull_images_from_cdn = False
            self.discovery_ram_disk_image = dev_settings[
                'discovery_ram_disk_image']
            self.overcloud_image = dev_settings['overcloud_image']

        self.rhel_iso = dev_settings['rhel_iso']
        repos = len(dev_settings['rhsm_repos'])
        if 'rhsm_repos' in dev_settings and repos > 0:
            logger.info("Using ini repo settings")
            self.rhsm_repos = dev_settings['rhsm_repos'].split(',')
        else:
            logger.info("using default repo settings")
            self.rhsm_repos = [
                'rhel-7-server-openstack-10-rpms',
                'rhel-7-server-openstack-10-devtools-rpms']
        if dev_settings['verify_rhsm_status'].lower() \
                == 'true':
            self.verify_rhsm_status = True
        else:
            self.verify_rhsm_status = False

        self.cygwin_installdir = 'n/a'
        try:
            self.bastion_host_ip = dev_settings['bastion_host_ip']
            self.bastion_host_user = dev_settings[
                'bastion_host_user']
            self.bastion_host_password = dev_settings[
                'bastion_host_password']
            self.retreive_switches_config = True
        except KeyError:
            self.retreive_switches_config = False

        self.lock_files_dir = self.cloud_repo_dir + "/data/vlock_files"
        self.foreman_configuration_scripts = self.cloud_repo_dir + "/src"

        self.sah_kickstart = self.cloud_repo_dir + "/src/mgmt/osp-sah.ks"
        self.director_deploy_sh = self.foreman_configuration_scripts +\
            '/mgmt/deploy-director-vm.sh'
        self.dashboard_deploy_py = self.foreman_configuration_scripts +\
            '/mgmt/deploy-dashboard-vm.py'

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
        self.static_ips_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/static-ip-environment.yaml'
        self.static_vip_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/static-vip-environment.yaml'
        self.sanity_ini = self.foreman_configuration_scripts + \
            '/pilot/deployment-validation/sanity.ini'
        self.ipxe_rpm = self.foreman_configuration_scripts + \
            '/pilot/ipxe/ipxe-bootimgs-20151005-1.git6847232.el7.' \
            'test.noarch.rpm'

        # The NIC configurations settings are validated after the Settings
        # class has been instanciated.  Guard against the case where the two
        # fixed are missing here to prevent an exception before validation
        nics_settings = self.get_nics_settings()
        if 'nic_env_file' in nics_settings:
            self.nic_env_file = nics_settings['nic_env_file']
            self.nic_env_file_path = self.foreman_configuration_scripts + \
                '/pilot/templates/nic-configs/' + self.nic_env_file
        if 'sah_bond_opts' in nics_settings:
            self.sah_bond_opts = nics_settings['sah_bond_opts']

        self.controller_nodes = []
        self.compute_nodes = []
        self.ceph_nodes = []
        self.switches = []
        self.nodes = []

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
                    if node.is_dashboard == "true":
                        self.dashboard_node = node
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

    def get_curated_nics_settings(self):
        nics_settings = self.get_nics_settings()
        if 'sah_bond_opts' in nics_settings:
            del nics_settings['sah_bond_opts']
        if 'nic_env_file' in nics_settings:
            del nics_settings['nic_env_file']
        return nics_settings

    def get_nics_settings(self):
        return self.get_settings_section("Nodes Nics and Bonding Settings")

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
