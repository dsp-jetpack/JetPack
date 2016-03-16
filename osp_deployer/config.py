#!/usr/bin/env python

# OpenStack - A set of software tools for building and managing cloud computing
# platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.

import ConfigParser, json, sys
from osp_deployer import Node_Conf
import logging
logger = logging.getLogger("osp_deployer")

class Settings():
    '''
    settings.ini & cluster.properties etc..
    '''
    settings = '' # so it can be read by UI lib's etc..

    def __init__(self, settingsFile):
        self.foreman_password = ''
        self.conf = ConfigParser.ConfigParser()
        self.conf.read(settingsFile)
        self.settingsFile = settingsFile
        self.cluster_settings_map = self.getSettingsSection("Cluster Settings")


        self.storage_network = self.cluster_settings_map['storage_network']
        self.storage_cluster_network = self.cluster_settings_map['storage_cluster_network']
        self.external_network = self.cluster_settings_map['external_network']
        self.provisioning_network = self.cluster_settings_map['provisioning_network']
        self.nova_public_network = self.cluster_settings_map['nova_public_network']
        self.nova_private_network = self.cluster_settings_map['nova_private_network']
        self.private_api_network = self.cluster_settings_map['private_api_network']

        self.private_api_allocation_pool_start = self.cluster_settings_map['private_api_allocation_pool_start']
        self.private_api_allocation_pool_end = self.cluster_settings_map['private_api_allocation_pool_end']
        self.storage_allocation_pool_start = self.cluster_settings_map['storage_allocation_pool_start']
        self.storage_allocation_pool_end = self.cluster_settings_map['storage_allocation_pool_end']
        self.storage_cluster_allocation_pool_start = self.cluster_settings_map['storage_cluster_allocation_pool_start']
        self.storage_cluster_allocation_pool_end = self.cluster_settings_map['storage_cluster_allocation_pool_end']
        self.external_allocation_pool_start = self.cluster_settings_map['external_allocation_pool_start']
        self.external_allocation_pool_end = self.cluster_settings_map['external_allocation_pool_end']

        self.public_gateway = self.cluster_settings_map['public_gateway']
        self.external_netmask = self.cluster_settings_map['external_netmask']
        self.external_gateway = self.cluster_settings_map['external_gateway']
        self.provisioning_vlanid = self.cluster_settings_map['provisioning_vlanid']
        self.provisioning_netmask = self.cluster_settings_map['provisioning_netmask']
        self.provisioning_gateway = self.cluster_settings_map['provisioning_gateway']
        self.storage_vlanid = self.cluster_settings_map['storage_vlanid']
        self.storage_netmask = self.cluster_settings_map['storage_netmask']
        self.public_api_vlanid = self.cluster_settings_map['public_api_vlanid']
        self.public_api_netmask = self.cluster_settings_map['public_api_netmask']
        self.private_api_vlanid = self.cluster_settings_map['private_api_vlanid']
        self.private_api_netmask = self.cluster_settings_map['private_api_netmask']
        self.management_network = self.cluster_settings_map['management_network']
        self.managment_vlanid = self.cluster_settings_map['managment_vlanid']
        self.managment_netmask = self.cluster_settings_map['managment_netmask']
        self.name_server = self.cluster_settings_map['name_server']
        self.storage_cluster_vlanid = self.cluster_settings_map['storage_cluster_vlanid']

        self.provisioning_net_dhcp_start = self.cluster_settings_map['provisioning_net_dhcp_start']
        self.provisioning_net_dhcp_end = self.cluster_settings_map['provisioning_net_dhcp_end']
        self.discovery_ip_range = self.cluster_settings_map['discovery_ip_range']
        self.tenant_vlan_range = self.cluster_settings_map['tenant_vlan_range']

        self.director_install_account_user = self.cluster_settings_map['director_install_user']
        self.director_install_account_pwd = self.cluster_settings_map['director_install_user_password']

        self.controller_bond0_interfaces = self.cluster_settings_map['controller_bond0_interfaces']
        self.controller_bond1_interfaces = self.cluster_settings_map['controller_bond1_interfaces']
        self.controller_provisioning_interface = self.cluster_settings_map['controller_provisioning_interface']

        self.compute_bond0_interfaces = self.cluster_settings_map['compute_bond0_interfaces']
        self.compute_bond1_interfaces = self.cluster_settings_map['compute_bond1_interfaces']
        self.compute_provisioning_interface = self.cluster_settings_map['compute_provisioning_interface']

        self.storage_bond0_interfaces = self.cluster_settings_map['storage_bond0_interfaces']
        self.storage_bond1_interfaces = self.cluster_settings_map['storage_bond1_interfaces']
        self.storage_provisioning_interface = self.cluster_settings_map['storage_provisioning_interface']

        self.ipmi_discovery_range_start = self.cluster_settings_map['ipmi_discovery_range_start']
        self.ipmi_discovery_range_end = self.cluster_settings_map['ipmi_discovery_range_end']

        if self.cluster_settings_map['use_custom_instack_json'].lower() == 'true':
            self.use_custom_instack_json = True
            self.custom_instack_json = self.cluster_settings_map['custom_instack_json']
        else:
            self.use_custom_instack_json = False


        self.network_conf = self.cluster_settings_map['cluster_nodes_configuration_file']
        self.domain = self.cluster_settings_map['domain']
        self.ipmi_user = self.cluster_settings_map['ipmi_user']
        self.ipmi_password = self.cluster_settings_map['ipmi_password']

        self.subscription_manager_user = self.cluster_settings_map['subscription_manager_user']
        self.subscription_manager_password = self.cluster_settings_map['subscription_manager_password']

        self.subscription_manager_pool_sah = self.cluster_settings_map['subscription_manager_pool_sah']
        self.subscription_manager_pool_vm_rhel = self.cluster_settings_map['subscription_manager_pool_vm_rhel']
        self.subscription_manager_vm_ceph = self.cluster_settings_map['subscription_manager_vm_ceph']

        if 'subscription_check_retries' in self.cluster_settings_map:
            self.subscription_check_retries = self.cluster_settings_map['subscription_check_retries']
        else:
            self.subscription_check_retries = 20
        self.controller_bond_opts=self.cluster_settings_map['controller_bond_opts']
        self.compute_bond_opts=self.cluster_settings_map['compute_bond_opts']
        self.storage_bond_opts=self.cluster_settings_map['storage_bond_opts']

        self.overcloud_deploy_timeout=self.cluster_settings_map['overcloud_deploy_timeout']



        self.ntp_server = self.cluster_settings_map['ntp_servers']
        self.time_zone = self.cluster_settings_map['time_zone']


        if self.cluster_settings_map['use_internal_repo'].lower() == 'true':
            self.internal_repos= True
            self.internal_repos_urls= []
            for each in self.cluster_settings_map['internal_repos_locations'].split(';'):
                self.internal_repos_urls.append(each)
        else:
            self.internal_repos= False





        if self.cluster_settings_map['enable_version_locking'].lower() == 'true':
            self.version_locking_enabled = True
        else:
            self.version_locking_enabled = False

        if self.cluster_settings_map['use_ipmi_driver'].lower() == 'true':
            self.use_ipmi_driver = True
        else:
            self.use_ipmi_driver = False

	if self.cluster_settings_map['enable_eqlx_backend'].lower() == 'true':
	    self.enable_eqlx_backend = True
	    self.eqlx_backend_name =  self.cluster_settings_map['eqlx_backend_name']
	    self.eqlx_san_ip =  self.cluster_settings_map['eqlx_san_ip']
            self.eqlx_san_login =  self.cluster_settings_map['eqlx_san_login']
            self.eqlx_san_password =  self.cluster_settings_map['eqlx_san_password']
            self.eqlx_ch_login =  self.cluster_settings_map['eqlx_ch_login']
            self.eqlx_ch_pass =  self.cluster_settings_map['eqlx_ch_pass']
            self.eqlx_group_n =  self.cluster_settings_map['eqlx_group_n']
            self.eqlx_thin_provisioning =  self.cluster_settings_map['eqlx_thin_provisioning']
            self.eqlx_pool =  self.cluster_settings_map['eqlx_pool']
            self.eqlx_use_chap =  self.cluster_settings_map['eqlx_use_chap']
	else:
	    self.enable_eqlx_backend = False

    
	if self.cluster_settings_map['enable_dellsc_backend'].lower() == 'true':
	    self.enable_dellsc_backend = True
	    self.dellsc_backend_name =  self.cluster_settings_map['dellsc_backend_name']
	    self.dellsc_san_ip =  self.cluster_settings_map['dellsc_san_ip']
            self.dellsc_san_login =  self.cluster_settings_map['dellsc_san_login']
            self.dellsc_san_password =  self.cluster_settings_map['dellsc_san_password']
            self.dellsc_iscsi_ip_address =  self.cluster_settings_map['dellsc_iscsi_ip_address']
            self.dellsc_iscsi_port =  self.cluster_settings_map['dellsc_iscsi_port']
            self.dellsc_api_port =  self.cluster_settings_map['dellsc_api_port']
            self.dellsc_ssn =  self.cluster_settings_map['dellsc_ssn']
            self.dellsc_server_folder =  self.cluster_settings_map['dellsc_server_folder']
            self.dellsc_volume_folder =  self.cluster_settings_map['dellsc_volume_folder']
	else:
	    self.enable_dellsc_backend = False
		
		
        self.bastion_settings_map = self.getSettingsSection("Bastion Settings")
        self.rhl72_iso = self.bastion_settings_map['rhl72_iso']
        if sys.platform.startswith('linux'):
            self.cygwin_installdir = 'n/a'
        else:
            self.cygwin_installdir = self.bastion_settings_map['cygwin_installdir']
        self.rhel_install_location = self.bastion_settings_map['rhel_install_location']
        self.sah_kickstart= self.bastion_settings_map['sah_kickstart']
        self.cloud_repo_dir = self.bastion_settings_map['cloud_repo_dir']
	
	try:
	   if self.bastion_settings_map['run_sanity'].lower() == 'true':
              self.run_sanity = True
	      self.sanity_test = self.bastion_settings_map['sanity_test']
           else:
              self.run_sanity = False
	except:
	      self.run_sanity = False

	try:
           if self.bastion_settings_map['run_tempest'].lower() == 'true':
              self.run_tempest = True
	      if self.bastion_settings_map['tempest_smoke_only'].lower() == 'true':
	         self.tempest_smoke_only = True
	      else:
		 self.tempest_smoke_only = False
           else:
              self.run_tempest = False
	      self.tempest_smoke_only = False
        except:
              self.run_tempest = False
	      self.tempest_smoke_only = False
	
        self.deploy_ram_disk_image =self.bastion_settings_map['deploy_ram_disk_image']
        self.discovery_ram_disk_image =self.bastion_settings_map['discovery_ram_disk_image']
        self.overcloud_image = self.bastion_settings_map['overcloud_image']

        if sys.platform.startswith('linux'):
            self.lock_files_dir = self.cloud_repo_dir + "/data/vlock_files"
            self.foreman_configuration_scripts = self.cloud_repo_dir + "/src"
            self.director_deploy_sh = self.foreman_configuration_scripts + '/mgmt/deploy-director-vm.sh'
            self.undercloud_conf = self.foreman_configuration_scripts + '/pilot/undercloud.conf'
            self.sah_ks = self.foreman_configuration_scripts + "/mgmt/osp-sah.ks"
            self.ceph_deploy_sh = self.foreman_configuration_scripts + '/mgmt/deploy-ceph-vm.sh'
            self.install_director_sh = self.foreman_configuration_scripts + '/pilot/install-director.sh'
            self.deploy_overcloud_sh = self.foreman_configuration_scripts + '/pilot/deploy-overcloud.py'
            self.assign_role_py = self.foreman_configuration_scripts + '/pilot/assign_role.py'
            self.network_env_yaml = self.foreman_configuration_scripts + '/pilot/templates/network-environment.yaml'
	    self.eqlx_yaml = self.foreman_configuration_scripts + '/pilot/templates/dell-eqlx-environment.yaml'
            self.dellsc_yaml = self.foreman_configuration_scripts + '/pilot/templates/dell-dellsc-environment.yaml'
            self.ceph_storage_yaml = self.foreman_configuration_scripts + '/pilot/templates/nic-configs/ceph-storage.yaml'
            self.compute_yaml = self.foreman_configuration_scripts + '/pilot/templates/nic-configs/compute.yaml'
            self.controller_yaml = self.foreman_configuration_scripts + '/pilot/templates/nic-configs/controller.yaml'
            self.controller_yaml = self.foreman_configuration_scripts + '/pilot/templates/nic-configs/controller.yaml'
            self.ipxe_rpm = self.foreman_configuration_scripts + '/pilot/ipxe/ipxe-bootimgs-20151005-1.git6847232.el7.test.noarch.rpm'



            self.hammer_configure_hostgroups_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-configure-hostgroups.sh'
            self.hammer_deploy_compute_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-deploy-compute.sh'
            self.hammer_deploy_controller_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-deploy-controller.sh'
            self.hammer_deploy_storage_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-deploy-storage.sh'
            self.hammer_get_ids_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-get-ids.sh'
            self.hammer_dump_ids_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-dump-ids.sh'
        else:
            self.lock_files_dir = self.cloud_repo_dir + "\\data\\vlock_files"
            self.foreman_configuration_scripts = self.cloud_repo_dir + "\\src"
            self.director_deploy_sh = self.foreman_configuration_scripts + "\\mgmt\\deploy-director-vm.sh"
            self.undercloud_conf = self.foreman_configuration_scripts + '\\pilot\\undercloud.conf'
            self.sah_ks = self.foreman_configuration_scripts + "\\mgmt\\osp-sah.ks"
            self.ceph_deploy_sh = self.foreman_configuration_scripts + "\\mgmt\\deploy-ceph-vm.sh"
            self.install_director_sh = self.foreman_configuration_scripts + '\\pilot\\install-director.sh'
            self.deploy_overcloud_sh = self.foreman_configuration_scripts + '\\pilot\\deploy-overcloud.py'
            self.assign_role_py = self.foreman_configuration_scripts + '\\pilot\\assign_role.py'
            self.network_env_yaml = self.foreman_configuration_scripts + '\\pilot\\templates\\network-environment.yaml'
            self.ceph_storage_yaml = self.foreman_configuration_scripts + '\\pilot\\templates\\nic-configs\\ceph-storage.yaml'
            self.compute_yaml = self.foreman_configuration_scripts + '\\pilot\\templates\\nic-configs\\compute.yaml'
            self.controller_yaml = self.foreman_configuration_scripts + '\\pilot\\templates\\nic-configs\\controller.yaml'
            self.ipxe_rpm = self.foreman_configuration_scripts + '\\pilot\\ipxe\\ipxe-bootimgs-20151005-1.git6847232.el7.test.noarch.rpm'

        self.controller_nodes = []
        self.compute_nodes = []
        self.ceph_nodes = []

        with open(self.network_conf) as config_file:
            json_data = json.load(config_file)
            for each in json_data:
                node = Node_Conf(each)

                try:
                    if node.is_sah == "true":
                        self.sah_node = node
                except:
                    pass
                try:
                    if node.is_director == "true":
                        self.director_node = node
                except:
                    pass
                try:
                    if node.is_ceph == "true":
                        self.ceph_node = node
                except:
                    pass
                try:
                    if node.is_controller == "true":
                        node.is_controller = True
                        self.controller_nodes.append(node)
                except:
                    node.is_controller = False
                    pass

                try:
                    if node.is_compute == "true":
                        node.is_compute = True
                        self.compute_nodes.append(node)
                except:
                    node.is_compute = False
                    pass
                try:
                    if node.is_ceph_storage == "true":
                        self.ceph_nodes.append(node)
                        node.is_storage = True
                except:
                    node.is_storage = False
                    pass


        Settings.settings = self

    def getSettingsSection(self, section):
        dictr = {}
        options = self.conf.options(section)
        for option in options:
            try:
                dictr[option] = self.conf.get(section, option)
                if dictr[option] == -1:
                    logger.debug("skip: %s" % option)
            except:
                logger.debug("exception on %s!" % option)
                dictr[option] = None
        return dictr
