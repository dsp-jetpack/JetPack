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

import logging
import os
import inspect
import json
import subprocess
import configparser
from osp_deployer.node_conf import NodeConf

logger = logging.getLogger("osp_deployer")


class Settings:
    CEPH_OSD_CONFIG_FILE = 'pilot/templates/ceph-osd-config.yaml'
    TEMPEST_DEFAULT_WORKSPACE_NAME = 'mytempest'
    UNDERCLOUD_CONFIG_FILE = 'undercloud.conf'
    NIC_CONFIGS_PATH = '/pilot/templates/nic-configs/'

    settings = ''

    def __str__(self):
        settings = {}
        settings["edge_sites"] = str(self.edge_sites)
        settings["node_type_data_map"] = str(self.node_type_data_map)
        if self.node_types_map:
            settings["node_types_map"] = {}
            _node_types_map = settings["node_types_map"]
            for node_type, nodes in self.node_types_map.items():
                _node_types_map[node_type] = [str(node) for node in nodes]
        settings["undercloud_conf"] = str(self.undercloud_conf)
        return str(settings)

    def __init__(self, settings_file):
        assert os.path.isfile(
            settings_file), settings_file + " file does not exist"

        f_name = "/sample_xsp_profile.ini"
        sample_ini = os.path.dirname(inspect.getfile(Settings)) + f_name

        conf = configparser.ConfigParser()
        # The following line makes the parser return case sensitive keys
        conf.optionxform = str
        conf.read(sample_ini)

        your_ini = settings_file
        yourConf = configparser.ConfigParser()
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
            elif self.is_valid_subnet(yourConf, stanza):
                logger.debug("Found a valid node_type_tuples "
                             "stanza in configuration: %s",
                             stanza)
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
        self.private_api_gateway = network_settings[
            'private_api_gateway']
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
        self.storage_gateway = network_settings['storage_gateway']
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
        self.tenant_tunnel_gateway = network_settings['tenant_tunnel_gateway']
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
            self.default_bond_mtu = self.mtu_size_global_default
        elif self.mtu_selection == 'per_network':
            self.mtu_size_global_default = '1500'
            max_mtu = []
            self.tenant_tunnel_network_mtu = mtu_settings[
                'tenant_tunnel_network_mtu']
            max_mtu.append(self.tenant_tunnel_network_mtu)
            self.tenant_network_mtu = mtu_settings[
                'tenant_network_mtu']
            max_mtu.append(self.tenant_network_mtu)
            self.storage_cluster_network_mtu = mtu_settings[
                'storage_cluster_network_mtu']
            max_mtu.append(self.storage_cluster_network_mtu)
            self.storage_network_mtu = mtu_settings[
                'storage_network_mtu']
            max_mtu.append(self.storage_network_mtu)
            self.private_api_network_mtu = mtu_settings[
                'private_api_network_mtu']
            max_mtu.append(self.private_api_network_mtu)
            self.public_api_network_mtu = mtu_settings[
                'public_api_network_mtu']
            max_mtu.append(self.private_api_network_mtu)
            self.floating_ip_network_mtu = mtu_settings[
                'floating_ip_network_mtu']
            max_mtu.append(self.floating_ip_network_mtu)
            self.default_bond_mtu = max(max_mtu)
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
        if 'subscription_check_retries' in rhsm_settings:
            self.subscription_check_retries = rhsm_settings[
                'subscription_check_retries']
        else:
            self.subscription_check_retries = 20
        if rhsm_settings['use_satellite'].lower() == 'true':
            self.use_satellite = True
            self.satellite_ip = rhsm_settings['satellite_ip']
            self.satellite_hostname = rhsm_settings['satellite_hostname']
            self.satellite_org = rhsm_settings['satellite_org']
            self.satellite_activation_key = rhsm_settings['satellite_activation_key']
            if rhsm_settings['pull_containers_from_satellite'].lower() == 'true':
                self.pull_containers_from_satellite = True
                self.containers_prefix = rhsm_settings['containers_prefix']
            else:
                self.pull_containers_from_satellite = False
        else:
            self.use_satellite = False

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
        self.undercloud_admin_host = deploy_settings[
            'undercloud_admin_host']
        self.undercloud_public_host = deploy_settings[
            'undercloud_public_host']
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
        logger.info("Profile has been set to {}".format(self.profile))

        if deploy_settings['enable_rbd_backend'].lower() == 'true':
            self.enable_rbd_backend = True
        else:
            self.enable_rbd_backend = False

        if deploy_settings['enable_rbd_nova_backend'].lower() == 'true':
            self.enable_rbd_nova_backend = True
        else:
            self.enable_rbd_nova_backend = False

        # glance backend, possible values file, cinder, swift or rbd
        self.glance_backend = deploy_settings['glance_backend'].lower()

        if deploy_settings['enable_fencing'].lower() == 'true':
            self.enable_fencing = True
        else:
            self.enable_fencing = False

        if deploy_settings['enable_dashboard'].lower() == 'true':
            self.enable_dashboard = True
        else:
            self.enable_dashboard = False

        self.overcloud_nodes_pwd = deploy_settings['overcloud_nodes_pwd']
        dellnfv_settings = self.get_settings_section(
            "Dell NFV Settings")
        if dellnfv_settings['hpg_enable'].lower() == 'true':
            self.hpg_enable = True
            self.hpg_size = dellnfv_settings['hpg_size']
        else:
            self.hpg_enable = False
        if dellnfv_settings['numa_enable'].lower() == 'true':
            self.numa_enable = True
            self.hostos_cpu_count = \
                dellnfv_settings['numa_hostos_cpu_count']
        else:
            self.numa_enable = False
        if dellnfv_settings['dvr_enable'].lower() == 'true':
            self.dvr_enable = True
            logger.info("DVR is enabled.")
        else:
            self.dvr_enable = False
            logger.info("DVR is disabled.")
        if dellnfv_settings['barbican_enable'].lower() == 'true':
            self.barbican_enable = True
            logger.info("Barbican is enabled.")
        else:
            self.barbican_enable = False
            logger.info("Barbican is disabled.")
        if dellnfv_settings['octavia_enable'].lower() == 'true':
            self.octavia_enable = True
            logger.info("Octavia is enabled.")
        else:
            self.octavia_enable = False
            logger.info("Octavia is disabled.")
        if dellnfv_settings['octavia_generate_certs'].lower() == 'true':
            self.octavia_user_certs_keys = False
        else:
            self.octavia_user_certs_keys = True
            self.certificate_keys_path = \
                dellnfv_settings['certificate_keys_path']

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
            self.dellsc_second_san_ip = backend_settings['dellsc_second_san_ip']
            self.dellsc_second_san_login = backend_settings['dellsc_second_san_login']
            self.dellsc_second_san_password = backend_settings['dellsc_second_san_password']
            self.dellsc_second_api_port = backend_settings['dellsc_second_api_port']
            self.dellsc_excluded_domain_ip = backend_settings['dellsc_excluded_domain_ip']
            self.dellsc_multipath_xref = backend_settings['dellsc_multipath_xref']
        else:
            self.enable_dellsc_backend = False

        # unity
        if backend_settings['enable_unity_backend'].lower() == 'true':

            if (backend_settings['unity_storage_protocol'] != 'iSCSI' and
               backend_settings['unity_storage_protocol'] != 'FC'):
                  error_msg = "Invalid Unity Storage Protocol " + \
                      "in your ini file '" + backend_settings['unity_storage_protocol'] + \
                      "'. Valid protocols are iSCSI or FC"
                  raise AssertionError(error_msg)
            self.enable_unity_backend = True
            self.cinder_unity_container_version = backend_settings[
                'cinder_unity_container_version']
            self.unity_san_ip = backend_settings['unity_san_ip']
            self.unity_san_login = backend_settings[
                'unity_san_login']
            self.unity_san_password = backend_settings[
                'unity_san_password']
            self.unity_storage_protocol = backend_settings[
                'unity_storage_protocol']
            self.unity_io_ports = backend_settings[
                'unity_io_ports']
            self.unity_storage_pool_names = backend_settings[
                'unity_storage_pool_names']
        else:
            self.enable_unity_backend = False

       # Unity Manila
        if backend_settings['enable_unity_manila_backend'].lower() == 'true':
            self.enable_unity_manila_backend = True
            self.manila_unity_container_version = backend_settings[
                'manila_unity_container_version']
            self.manila_unity_driver_handles_share_servers = \
                backend_settings['manila_unity_driver_handles_share_servers']
            self.manila_unity_nas_login = \
                backend_settings['manila_unity_nas_login']
            self.manila_unity_nas_password = \
                backend_settings['manila_unity_nas_password']
            self.manila_unity_nas_server = \
                backend_settings['manila_unity_nas_server']
            self.manila_unity_server_meta_pool = \
                backend_settings['manila_unity_server_meta_pool']
            self.manila_unity_share_data_pools = \
                backend_settings['manila_unity_share_data_pools']
            self.manila_unity_ethernet_ports = \
                backend_settings['manila_unity_ethernet_ports']
            self.manila_unity_ssl_cert_verify = \
                backend_settings['manila_unity_ssl_cert_verify']
            self.manila_unity_ssl_cert_path = \
                backend_settings['manila_unity_ssl_cert_path']
        else:
            self.enable_unity_manila_backend = False

        # powermax
        if backend_settings['enable_powermax_backend'].lower() == 'true':
            if (backend_settings['powermax_protocol'] != 'iSCSI' and
               backend_settings['powermax_protocol'] != 'FC'):
                error_msg = "Invalid Powermax Protocol " +\
                    "in your ini file '" + backend_settings['powermax_protocol'] +\
                    "'. Valid protocols are iSCSI or FC"
                raise AssertionError(error_msg)

            self.enable_powermax_backend = True
            self.powermax_backend_name = backend_settings['powermax_backend_name']
            self.powermax_san_ip = backend_settings['powermax_san_ip']
            self.powermax_san_login = backend_settings[
                'powermax_san_login']
            self.powermax_san_password = backend_settings[
                'powermax_san_password']
            self.powermax_protocol = backend_settings[
                'powermax_protocol']
            self.powermax_array = backend_settings[
                'powermax_array']
            self.powermax_port_groups = backend_settings[
                'powermax_port_groups']
            self.powermax_srp = backend_settings[
                'powermax_srp']
        else:
            self.powermax_protocol = 'iSCSI'
            self.enable_powermax_backend = False

        # PowerMax Manila
        if backend_settings['enable_powermax_manila_backend'].lower() == 'true':
            self.enable_powermax_manila_backend = True
            self.manila_powermax_driver_handles_share_servers = \
                backend_settings['manila_powermax_driver_handles_share_servers']
            self.manila_powermax_nas_login = \
                backend_settings['manila_powermax_nas_login']
            self.manila_powermax_nas_password = \
                backend_settings['manila_powermax_nas_password']
            self.manila_powermax_nas_server = \
                backend_settings['manila_powermax_nas_server']
            self.manila_powermax_server_container = \
                backend_settings['manila_powermax_server_container']
            self.manila_powermax_share_data_pools = \
                backend_settings['manila_powermax_share_data_pools']
            self.manila_powermax_ethernet_ports = \
                backend_settings['manila_powermax_ethernet_ports']
        else:
            self.enable_powermax_manila_backend = False


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
        self.vlan_aware_sanity = \
            sanity_settings['vlan_aware_sanity']
        self.sanity_image_url = sanity_settings['sanity_image_url']
        self.sanity_vlantest_network = \
            sanity_settings['sanity_vlantest_network']
        self.share_storage_network = sanity_settings['share_storage_network']
        self.share_storage_network_start_ip = \
            sanity_settings['share_storage_network_start_ip']
        self.share_storage_network_end_ip = \
            sanity_settings['share_storage_network_end_ip']
        self.share_storage_network_gateway = \
            sanity_settings['share_storage_network_gateway']
        self.share_storage_network_vlan = \
            sanity_settings['share_storage_network_vlan']
        self.share_storage_network_name = \
            sanity_settings['share_storage_network_name']
        self.share_storage_subnet_name = \
            sanity_settings['share_storage_subnet_name']
        if sanity_settings['run_sanity'].lower() == 'true':
            self.run_sanity = True
        else:
            self.run_sanity = False

        tempest_settings = self.get_settings_section(
            "Tempest Settings")

        self.run_tempest = bool(tempest_settings['run_tempest']
                                .lower() == 'true')
        self.tempest_smoke_only = bool(tempest_settings['tempest_smoke_only']
                                       .lower() == 'true')

        self.tempest_workspace = Settings.TEMPEST_DEFAULT_WORKSPACE_NAME
        if 'tempest_workspace' in tempest_settings:
            self.tempest_workspace = tempest_settings['tempest_workspace']

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
                'rhel-8-for-x86_64-baseos-rpms',
                'rhel-8-for-x86_64-appstream-rpms',
                'rhel-8-for-x86_64-highavailability-rpms',
                'ansible-2.8-for-rhel-8-x86_64-rpms',
                'advanced-virt-for-rhel-8-x86_64-rpms',
                'satellite-tools-6.5-for-rhel-8-x86_64-rpms',
                'openstack-16-for-rhel-8-x86_64-rpms',
                'fast-datapath-for-rhel-8-x86_64-rpms',
                'rhceph-4-tools-for-rhel-8-x86_64-rpms']
        if dev_settings['verify_rhsm_status'].lower() \
                == 'true':
            self.verify_rhsm_status = True
        else:
            self.verify_rhsm_status = False

        self.cygwin_installdir = 'n/a'

        self.lock_files_dir = self.cloud_repo_dir + "/data/vlock_files"
        self.foreman_configuration_scripts = self.cloud_repo_dir + "/src"
        self.jinja2_templates = (self.foreman_configuration_scripts
                                 + "/deploy/jinja2_templates")

        self.sah_kickstart = self.cloud_repo_dir + "/src/mgmt/osp-sah.ks"
        self.director_deploy_sh = self.foreman_configuration_scripts +\
            '/mgmt/deploy-director-vm.sh'
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
        self.dellsc_cinder_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/dellsc-cinder-config.yaml'
        self.dell_unity_cinder_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/dellemc-unity-cinder-backend.yaml'
        self.dell_unity_cinder_container_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/dellemc-unity-cinder-container.yaml'
        self.unity_manila_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/unity-manila-config.yaml'
        self.unity_manila_container_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/unity-manila-container.yaml'
        self.dell_powermax_iscsi_cinder_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/dellemc-powermax-iscsi-cinder-backend.yaml'
        self.dell_powermax_fc_cinder_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/dellemc-powermax-fc-cinder-backend.yaml'
        self.powermax_manila_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/powermax-manila-config.yaml'
        self.dell_env_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/dell-environment.yaml'
        self.ceph_osd_config_yaml = self.foreman_configuration_scripts + \
            '/' + Settings.CEPH_OSD_CONFIG_FILE
        self.neutron_ovs_dpdk_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/neutron-ovs-dpdk.yaml'
        self.static_ips_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/static-ip-environment.yaml'
        self.static_vip_yaml = self.foreman_configuration_scripts + \
            '/pilot/templates/static-vip-environment.yaml'
        self.sanity_ini = self.foreman_configuration_scripts + \
            '/pilot/deployment-validation/sanity.ini'
        self.ipxe_rpm = self.foreman_configuration_scripts + \
            '/pilot/ipxe/ipxe-bootimgs-20151005-1.git6847232.el7.' \
            'test.noarch.rpm'
        self.nic_configs_abs_path = self.foreman_configuration_scripts + \
            Settings.NIC_CONFIGS_PATH
        self.undercloud_conf_path = self.foreman_configuration_scripts + \
            '/pilot/' + Settings.UNDERCLOUD_CONFIG_FILE
        self.templates_dir = self.foreman_configuration_scripts + \
            '/pilot/templates'
        self.neutron_sriov_yaml = self.templates_dir + '/neutron-sriov.yaml'

        # New custom node type and edge related fields
        # Advanced Settings[edge_sites] in ini
        self.edge_sites = []
        # node_type_data_map maps the various node types to the networking
        # attribute definitions in the .ini stanza that matches each node_type
        self.node_type_data_map = {}
        # node_types_map is a key/list map of all nodes in .properties
        # that have a matching node_type attribute. Key is each node_type.
        self.node_types_map = {}
        self.undercloud_conf = self.parse_undercloud_conf()
        # Process node types for edge sites etc
        if dev_settings['deploy_edge_sites'].lower() == 'true':
            self.deploy_edge_sites = True
        else:
            self.deploy_edge_sites = False
        if ('edge_sites' in dev_settings
                and len(dev_settings['edge_sites']) > 0):
            self.process_node_type_settings(dev_settings['edge_sites'])
        # The NIC configurations settings are validated after the Settings
        # class has been instanciated.  Guard against the case where the two
        # fixed are missing here to prevent an exception before validation
        nics_settings = self.get_nics_settings()
        if 'nic_env_file' in nics_settings:
            self.nic_env_file = nics_settings['nic_env_file']
            self.nic_dir = self.nic_env_file.split('/')[0]
            self.num_nics = self._find_number_of_nics(self.nic_dir)
            self.nic_env_file_path = (self.nic_configs_abs_path
                                      + self.nic_env_file)
        if 'sah_bond_opts' in nics_settings:
            self.sah_bond_opts = nics_settings['sah_bond_opts']

        # This particular section has been moved right after the nics_settings
        # section in order to catch the mode used by the nic-environment file
        dellnfv_settings = self.get_settings_section(
            "Dell NFV Settings")
        self.ovs_dpdk_enable = dellnfv_settings[
            'ovs_dpdk_enable']
        self.enable_ovs_dpdk = False
        if self.ovs_dpdk_enable.lower() == 'false':
            logger.info("OVS_DPDK is disabled.")
        elif self.ovs_dpdk_enable.lower() == 'true':
            self.enable_ovs_dpdk = True
            logger.info("OVS-DPDK is enabled.")
            if 'HostNicDriver' in nics_settings:
                self.HostNicDriver = nics_settings['HostNicDriver']

        # TO enable SRIOV
        self.sriov_enable = dellnfv_settings['sriov_enable']
        self.smart_nic = dellnfv_settings['smart_nic']
        self.enable_sriov = False
        self.enable_smart_nic = False
        if self.sriov_enable.lower() == 'false':
            pass
        else:
            self.enable_sriov = True
            self.sriov_vf_count = dellnfv_settings['sriov_vf_count']

        if self.enable_sriov:
            logger.info("SR-IOV is enabled.")
        else:
            logger.info("SR-IOV is disabled.")

        if self.smart_nic.lower() == 'true':
            self.enable_smart_nic = True
            logger.info("Smart NIC for SR-IOV Hardware Offload is enabled.")
        else:
            logger.info("Smart NIC for SR-IOV Hardware Offload is disabled.")

        self.controller_nodes = []
        self.compute_nodes = []
        self.computehci_nodes = []
        self.ceph_nodes = []
        self.all_overcloud_nodes = []
        self.switches = []
        self.nodes = []
        with open(self.network_conf) as config_file:
            json_data = json.load(config_file)
            for each in json_data:
                node = NodeConf(each)
                try:
                    node.is_sah = (True if node.is_sah
                                   == "true" else False)
                    if node.is_sah:
                        self.sah_node = node
                except AttributeError:
                    pass
                try:
                    node.is_director = (True if node.is_director
                                        == "true" else False)
                    if node.is_director:
                        self.director_node = node
                except AttributeError:
                    pass
                try:
                    node.is_controller = (True if node.is_controller
                                          == "true" else False)
                    if node.is_controller:
                        self.controller_nodes.append(node)
                except AttributeError:
                    node.is_controller = False
                    pass
                try:
                    node.is_computehci = (True if node.is_computehci
                                          == "true" else False)
                    if node.is_computehci:
                        self.computehci_nodes.append(node)
                except AttributeError:
                    node.is_computehci = False
                    pass
                try:
                    node.is_compute = (True if node.is_compute
                                       == "true" else False)
                    if node.is_compute:
                        self.compute_nodes.append(node)
                except AttributeError:
                    node.is_compute = False
                    pass
                try:
                    node.is_storage = (True if node.is_ceph_storage
                                       == "true" else False)
                    if node.is_storage:
                        self.ceph_nodes.append(node)
                except AttributeError:
                    node.is_storage = False
                    pass
                try:
                    node.is_switch = (True if node.is_switch
                                      == "true" else False)
                    if node.is_switch:
                        self.switches.append(node)
                except AttributeError:
                    self.nodes.append(node)
                    pass
                try:
                    node.skip_raid_config = (True if node.skip_raid_config
                                             == "true" else False)
                except AttributeError:
                    node.skip_raid_config = False
                    pass
                try:
                    node.skip_bios_config = (True if node.skip_bios_config
                                             == "true" else False)
                except AttributeError:
                    node.skip_bios_config = False
                    pass
                try:
                    node.skip_nic_config = (True if node.skip_nic_config
                                            == "true" else False)
                except AttributeError:
                    node.skip_nic_config = False
                    pass
                if "node_type" in node.__dict__:
                    logger.debug("node_type not in self.node_types_map: %s",
                                 str(node.node_type
                                     not in self.node_types_map))
                    if node.node_type not in self.node_types_map:
                        self.node_types_map[node.node_type] = []
                    self.node_types_map[node.node_type].append(node)
        self.all_overcloud_nodes = [*self.controller_nodes,
                                    *self.compute_nodes,
                                    *self.ceph_nodes,
                                    *self.computehci_nodes]

        Settings.settings = self
        logger.debug("Settings.settings is: %s",
                     str(Settings.settings))

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
            except configparser.NoSectionError:
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
        except:  # noqa: E722
            logger.debug("unconventional setup...can't"
                         " pick source version info")
            self.source_version = "????"

    def process_node_type_settings(self, edge_sites):
        self.edge_sites = (list(map(str.strip, edge_sites.split(','))))
        logger.debug("Edge sites: %s", str(self.edge_sites))
        for node_type in self.edge_sites:
            # if we have ini section name that mathes node type
            # this is edge an site subnet definition to be injected into
            # undercloud.com
            if self.conf.has_section(node_type):
                node_type_section = self.get_settings_section(node_type)
                self.node_type_data_map[node_type] = node_type_section

    def parse_undercloud_conf(self, path=None):
        undercloud_conf = configparser.ConfigParser()
        # The following line makes the parser return case sensitive keys
        undercloud_conf.optionxform = str
        path = path if path else self.undercloud_conf_path
        undercloud_conf.read(path)
        return undercloud_conf

    def is_valid_subnet(self, conf, stanza):
        if conf.has_option('Advanced Settings', 'edge_sites'):
            edge_sites = (
                list(map(str.strip, conf.get('Advanced Settings',
                                             'edge_sites').split(','))))
            if stanza in edge_sites and conf.has_section(stanza):
                return True
        return False

    def _find_number_of_nics(self, nic_dir):
        num_nics = int(list(filter(str.isdigit, nic_dir))[0])
        return num_nics
