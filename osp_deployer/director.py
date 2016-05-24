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

from osp_deployer.config import Settings
from checkpoints import Checkpoints
from infra_host import InfraHost
from auto_common import Scp, Ipmi
import logging
import time
import os
import re
import errno

logger = logging.getLogger("osp_deployer")

exitFlag = 0


class Director(InfraHost):

    def __init__(self):

        self.settings = Settings.settings
        self.user = self.settings.director_install_account_user
        self.ip = self.settings.director_node.external_ip
        self.pwd = self.settings.director_install_account_pwd
        self.root_pwd = self.settings.director_node.root_password

        self.home_dir = "/home/" + self.user
        self.pilot_dir = os.path.join(self.home_dir, "pilot")
        self.images_dir = os.path.join(self.pilot_dir, "images")
        self.templates_dir = os.path.join(self.pilot_dir, "templates")
        self.nic_configs_dir = os.path.join(self.templates_dir, "nic-configs")
        self.validation_dir = os.path.join(self.pilot_dir,
                                           "deployment-validation")
        self.source_stackrc = 'source ' + self.home_dir + "/stackrc;"

        cmd = "mkdir -p " + self.pilot_dir
        self.run(cmd)

    def apply_internal_repos(self):
        # Add the internal repo. if going down that road,
        if self.settings.internal_repos is True:
            logger.debug(
                "Applying internal repo's to the "
                "director vm & reinstall rdo manager")
            count = 1
            for repo in self.settings.internal_repos_urls:
                cmd = 'curl ' + \
                      repo + \
                      " > /etc/yum.repos.d/internal_" + \
                      str(count) + \
                      ".repo"
                self.run_as_root(cmd)
                self.run_as_root("sed -i '/enabled=1/a priority=1' "
                                 "/etc/yum.repos.d/internal_" +
                                 str(count) + ".repo")
                count += 1

            cmds = [
                'subscription-manager repos '
                '--enable=rhel-7-server-openstack-8.0-rpms',
                'subscription-manager repos '
                '--enable=rhel-7-server-openstack-8.0-director-rpms',
                'yum-config-manager '
                '--enable RH7-RHOS-8.0 --setopt="RH7-RHOS-8.0.priority=1"',
                'yum-config-manager '
                '--enable RH7-RHOS-8.0-director '
                '--setopt="RH7-RHOS-8.0-director.priority=1"',
                'yum remove python-rdomanager-oscplugin -y',
                'yum remove ahc-tools -y',
                'yum clean all',
                'yum makecache',
                'yum repolist all',
                'yum install python-rdomanager-oscplugin -y',
                'yum update -y',
            ]
            for cmd in cmds:
                self.run_as_root(cmd)

    def upload_update_conf_files(self):

        logger.debug("tar up the required pilot files")
        os.system("cd " +
                  self.settings.foreman_configuration_scripts +
                  "/pilot/;tar -zcvf /root/pilot.tar.gz *")
        self.upload_file("/root/pilot.tar.gz",
                         self.home_dir + "/pilot.tar.gz")

        self.run('cd;tar zxvf pilot.tar.gz -C pilot')

        cmds = [
            'sed -i "s|local_ip = .*|local_ip = ' +
            self.settings.director_node.provisioning_ip +
            '/24|" pilot/undercloud.conf',
            'sed -i "s|local_interface = .*|'
            'local_interface = eth1|" pilot/undercloud.conf',
            'sed -i "s|masquerade_network = .*|masquerade_network = ' +
            self.settings.provisioning_network +
            '|" pilot/undercloud.conf',
            'sed -i "s|dhcp_start = .*|dhcp_start = ' +
            self.settings.provisioning_net_dhcp_start +
            '|" pilot/undercloud.conf',
            'sed -i "s|dhcp_end = .*|dhcp_end = ' +
            self.settings.provisioning_net_dhcp_end +
            '|" pilot/undercloud.conf',
            'sed -i "s|network_cidr = .*|network_cidr = ' +
            self.settings.provisioning_network +
            '|" pilot/undercloud.conf',
            'sed -i "s|network_gateway = .*|network_gateway = ' +
            self.settings.director_node.provisioning_ip +
            '|" pilot/undercloud.conf',
            'sed -i "s|inspection_iprange = .*|inspection_iprange = ' +
            self.settings.discovery_ip_range +
            '|" pilot/undercloud.conf',
        ]
        for cmd in cmds:
            self.run(cmd)

    def install_director(self):
        logger.debug("uploading & executing sh script")

        self.run_tty('~/pilot/install-director.sh ' +
                     self.settings.name_server + " " +
                     self.settings.subscription_manager_user + " " +
                     self.settings.subscription_manager_password + " " +
                     self.settings.subscription_manager_vm_ceph)

        tester = Checkpoints()
        tester.verify_undercloud_installed()

    def upload_cloud_images(self):
        if self.settings.pull_images_from_cnd is False:
            logger.debug("Uploading cloud images to the Director vm")
            self.run("mkdir -p " + self.images_dir)

            self.upload_file(self.settings.discovery_ram_disk_image,
                             self.images_dir + "/discovery-ramdisk.tar")

            self.upload_file(self.settings.overcloud_image,
                             self.images_dir + "/overcloud-full.tar")
        else:
            logger.info("will pull images from the cdn")

    def node_discovery(self):
        setts = self.settings
        if setts.use_custom_instack_json is True:
            logger.debug(
                "Using custom instack.json file - NOT scannings nodes")
            cmd = "rm " + self.home_dir + "/instackenv.json -f"
            self.run_tty(cmd)

            remote_file = self.home_dir + "/instackenv.json"
            self.upload_file(setts.custom_instack_json,
                             remote_file)
        else:
            self.check_idracs()
            setts = self.settings
            cmd = "cd ~/pilot/discover_nodes;./discover_nodes.py  -u " + \
                  setts.ipmi_user + \
                  " -p '" + setts.ipmi_password + "'"
            for node in (self.settings.controller_nodes +
                         self.settings.compute_nodes +
                         self.settings.ceph_nodes):
                cmd += ' ' + node.idrac_ip
            cmd += '> ~/instackenv.json'

            self.run_tty(cmd)

            cmd = "ls -la ~/instackenv.json | awk '{print $5;}'"
            size = \
                self.run_tty(cmd)[0]
            if int(size) <= 50:
                logger.fatal("did not manage to pick up the nodes..")
                raise AssertionError(
                    "Unable to scan all the nodes ... need to go & pull "
                    "the plug(s) - " +
                    size + " - " +
                    size[0])

            else:
                logger.debug("nodes appear to have been picked up")

        for node in (setts.controller_nodes +
                     setts.compute_nodes +
                     setts.ceph_nodes):
            ipmi_session = Ipmi(setts.cygwin_installdir,
                                setts.ipmi_user,
                                setts.ipmi_password,
                                node.idrac_ip)
            ipmi_session.power_off()
            time.sleep(60)

        if setts.use_ipmi_driver is True:
            logger.debug("Using pxe_ipmi driver")
            cmd = 'sed -i "s|pxe_drac|pxe_ipmitool|" ~/instackenv.json'
            self.run_tty(cmd)

        cmd = self.source_stackrc + "openstack " \
                                    "baremetal import --json ~/instackenv.json"
        logger.debug(
            self.run_tty(cmd))
        tester = Checkpoints()
        tester.verify_nodes_registered_in_ironic()

        cmd = self.source_stackrc + "openstack" \
                                    " baremetal configure boot"
        self.run_tty(cmd)

        cmd = self.source_stackrc + "openstack " \
                                    "baremetal introspection bulk start"
        self.run_tty(cmd)
        tester.verify_introspection_sucessfull()

    def check_idracs(self):
        # Idrac doesn't always play nice ..
        # working around cases where nic's dont get detected
        for node in (self.settings.controller_nodes +
                     self.settings.compute_nodes +
                     self.settings.ceph_nodes):
                while 1:
                    cmd = 'ipmitool -I lanplus -H ' + \
                          self.settings.controller_nodes[0].idrac_ip + \
                          ' -U ' + \
                          self.settings.ipmi_user + \
                          ' -P ' + \
                          self.settings.ipmi_password + \
                          ' power status'

                    self.run_tty(cmd)
                    cmd = "cd ~/pilot/discover_nodes;./discover_nodes.py" \
                          " -u " + \
                          self.settings.ipmi_user + \
                          " -p '" + \
                          self.settings.ipmi_password + "' " + \
                          node.idrac_ip
                    self.run_tty(cmd)[0]
                    # yes, running it twice - throws errors on first attempts
                    # depending on the state of the node
                    out = self.run_tty(cmd)[0]
                    if ("FIXME" in out) or ("WSMan request failed" in out):
                        logger.warning(
                                       node.hostname +
                                       " did not get discovered properly")
                        logger.debug("reseting idrac")
                        ipmi_session = Ipmi(
                                            self.settings.cygwin_installdir,
                                            self.settings.ipmi_user,
                                            self.settings.ipmi_password,
                                            node.idrac_ip)
                        ipmi_session.drac_reset()
                        time.sleep(120)
                        back2life = False
                        while back2life is False:
                            try:
                                ipmi_session.get_power_state()
                                back2life = True
                                time.sleep(20)
                            except:
                                pass
                        ipmi_session.power_on()
                        time.sleep(120)
                        ipmi_session.set_boot_to_pxe()
                        time.sleep(120)
                    else:
                        break

    def assign_node_roles(self):

        logger.debug("Assigning roles to nodes")

        for node in self.settings.controller_nodes:
            out = self.run_tty(self.source_stackrc +
                               "cd ~/pilot;./assign_role.py " +
                               node.provisioning_mac_address +
                               " controller")
            if "Not Found" in out[0]:
                raise AssertionError(
                    "Failed to assign Controller node role to mac " +
                    node.provisioning_mac_address)

        for node in self.settings.compute_nodes:
            out = self.run_tty(self.source_stackrc +
                               "cd ~/pilot;./assign_role.py " +
                               node.provisioning_mac_address +
                               " compute")
            if "Not Found" in out[0]:
                raise AssertionError(
                    "Failed to assign Compute node role to mac " +
                    node.provisioning_mac_address)

        for node in self.settings.ceph_nodes:
            out = self.run_tty(self.source_stackrc +
                               "cd ~/pilot;./assign_role.py " +
                               node.provisioning_mac_address +
                               " storage")
            if "Not Found" in out[0]:
                raise AssertionError(
                    "Failed to assign Storage node role to mac " +
                    node.provisioning_mac_address)

    def setup_templates(self):
        # Re-upload the yaml files in case we're trying to leave the undercloud
        # intact but want to redeploy with a different config.

        self.setup_networking()
        self.setup_storage()
        self.setup_dell_storage()
        self.setup_environment()

    def setup_environment(self):

        env_yaml = os.path.join(self.templates_dir + "/dell-environment.yaml")

        # reupload the file if this is an overcloud only install
        self.upload_file(self.settings.dell_env_yaml,
                         env_yaml)
        self.run_tty('sed -i "s|NovaEnableRbdBackend: .*|'
                     'NovaEnableRbdBackend: ' +
                     str(self.settings.enable_rbd_backend).lower() +
                     '|" ' +
                     env_yaml)

    def setup_storage(self):
        if len(self.settings.ceph_nodes) == 0:
            logger.debug(
                "Skipping Ceph storage setup because there are no "
                "storage nodes")
            return

        logger.debug("Configuring Ceph storage settings for overcloud")

        # Set up the Ceph OSDs using the 'osd_disks' defined for the first
        # storage node. This is the best we can do until the OSP Director
        # supports more than a single, global OSD configuration.
        osd_disks = self.settings.ceph_nodes[0].osd_disks

        ceph_yaml = os.path.join("pilot", "templates", "overrides", "puppet",
                                 "hieradata", "ceph.yaml")
        src_name = os.path.join(self.settings.foreman_configuration_scripts,
                                ceph_yaml)
        src_file = open(src_name, 'r')

        # Temporary local file used to stage the modified ceph.yaml file
        tmp_name = src_name + ".tmp"
        tmp_file = open(tmp_name, 'w')

        osds_param = 'ceph::profile::params::osds:'
        found_osds_param = False
        for line in src_file:
            if line.startswith(osds_param):
                found_osds_param = True

            elif found_osds_param:
                # Discard lines that begin with "#", "'" or "journal:" because
                # these lines represent the original ceph.yaml file's OSD
                # configuration.
                tokens = line.split()
                if len(tokens) > 0 and (tokens[0].startswith("#") or
                                        tokens[0].startswith("'") or
                                        tokens[0].startswith("journal:")):
                    continue

                # End of original Ceph OSD configuration: now write the new one
                tmp_file.write("{}\n".format(osds_param))
                for osd in osd_disks:
                    # Format is ":OSD_DRIVE" or ":OSD_DRIVE:JOURNAL_DRIVE",
                    # so split on the ':'
                    tokens = osd.split(':')

                    # Make sure OSD_DRIVE begins with "/dev/"
                    if not tokens[1].startswith("/dev/"):
                        tokens[1] += "/dev/"

                    if len(tokens) == 3:
                        # This OSD specifies a separate journal drive
                        tmp_file.write(
                            "  '{}':\n    journal: '{}'\n".format(tokens[1],
                                                                  tokens[2]))
                    elif len(tokens) == 2:
                        # This OSD does not specify a separate journal
                        tmp_file.write("  '{}': {{}}\n".format(tokens[1]))
                    else:
                        logger.warning(
                            "Bad entry in osd_disks: {}".format(osd))

                # This is the line that follows the original Ceph OSD config
                tmp_file.write(line)
                found_osds_param = False

            else:
                tmp_file.write(line)

        src_file.close()
        tmp_file.close()

        install_admin_user = self.user

        dst_name = os.path.join(
            os.path.join("/home", install_admin_user, ceph_yaml))
        self.upload_file(tmp_name,
                         dst_name)
        os.remove(tmp_name)
		

    def setup_dell_storage(self):
        # Re - Upload the yaml files in case we're trying to
        # leave the undercloud intact but want to redeploy with
        # a different config
        dell_storage_yaml = self.templates_dir + "/dell-cinder-backends.yaml"
        self.upload_file(self.settings.dell_storage_yaml,
                         dell_storage_yaml)
        # Backup before modifying
        self.run_tty("cp " + dell_storage_yaml + " " + dell_storage_yaml + ".bak")

        self.setup_eqlx(dell_storage_yaml)
        self.setup_dellsc(dell_storage_yaml)
        enabled_backends = "["
        if self.settings.enable_eqlx_backend is True:
           index = 1
           eqlx_san_ip_array = self.settings.eqlx_san_ip.split(",")
	   for san_ip in eqlx_san_ip_array:
	       enabled_backends += "'eqlx" + str(index) + "'," 
	       index = index +1	
				
        if self.settings.enable_dellsc_backend is True:
            enabled_backends += "'dellsc'" 
                
        enabled_backends += "]"
		
        cmd = 'sed -i "s|cinder_user_enabled_backends:.*|cinder_user_enabled_backends: ' + \
        enabled_backends +  '|" ' + dell_storage_yaml
        self.run_tty(cmd)



    def setup_eqlx(self,dell_storage_yaml):

        if self.settings.enable_eqlx_backend is False:
            logger.debug("not setting up eqlx backend")
            return

        logger.debug("configuring eql backend")
	eqlx_san_ip_array = self.settings.eqlx_san_ip.split(",")
	eqlx_san_login_array  = self.settings.eqlx_san_login.split(",")
	eqlx_san_password_array  = self.settings.eqlx_san_password.split(",")
	eqlx_thin_provisioning_array  = self.settings.eqlx_thin_provisioning.split(",")
	eqlx_group_n_array  = self.settings.eqlx_group_n.split(",")
	eqlx_pool_array  = self.settings.eqlx_pool.split(",")
	eqlx_use_chap_array  = self.settings.eqlx_use_chap.split(",")
	eqlx_ch_login_array  = self.settings.eqlx_ch_login.split(",")
	eqlx_ch_pass_array  = self.settings.eqlx_ch_pass.split(",")
		
	if( len(eqlx_san_ip_array) < len(eqlx_san_login_array) or
	   len(eqlx_san_ip_array) < len(eqlx_san_password_array) or
	   len(eqlx_san_ip_array) < len(eqlx_thin_provisioning_array) or
	   len(eqlx_san_ip_array) < len(eqlx_group_n_array) or
	   len(eqlx_san_ip_array) < len(eqlx_pool_array) or
	   len(eqlx_san_ip_array) < len(eqlx_use_chap_array) or
	   len(eqlx_san_ip_array) < len(eqlx_ch_login_array) or
	   len(eqlx_san_ip_array) < len(eqlx_ch_pass_array)) :
	        self.settings.enable_eqlx_backend = false
	        logger.debug("not setting up eqlx backend, data missing")
                return
			
	eqlx_configs = ""
        index = 0		
	for san_ip in eqlx_san_ip_array:
	    eqlx_config = """
      eqlx/volume_backend_name:
        value: {}	
      eqlx/volume_driver:
        value: cinder.volume.drivers.eqlx.DellEQLSanISCSIDriver		
      eqlx/san_ip:
        value: {}
      eqlx/san_login:
        value: {}
      eqlx/san_password:
        value: {}
      eqlx/san_thin_provision:
        value: {}     
      eqlx/eqlx_group_name:
        value: {}  
      eqlx/eqlx_pool:
        value: {}     
      eqlx/eqlx_use_chap:
        value: {}     	
      eqlx/eqlx_chap_login:
        value: {}     
      eqlx/eqlx_chap_password:
        value: {}""".format("eqlx" +str(index+1),
			      eqlx_san_ip_array[index],
			      eqlx_san_login_array[index],
			      eqlx_san_password_array[index],
			      eqlx_thin_provisioning_array[index],
			      eqlx_group_n_array[index],
			      eqlx_pool_array[index],
			      eqlx_use_chap_array[index],
			      eqlx_ch_login_array[index],
			      eqlx_ch_pass_array[index]
			)
            eql_backend = "eqlx" + str(index+1) 
            pattern = re.compile("eqlx\/", re.MULTILINE|re.DOTALL)
            eqlx_config = pattern.sub(eql_backend+"/",eqlx_config)
            eqlx_configs += eqlx_config	           
            index = index +1		
	
        eqlx_configs = "#EQLX" + eqlx_configs + "\n      #EQLX-END"
        logger.info("****EQLX Config:\n" + eqlx_configs)
        self.run_ssh_edit(dell_storage_yaml,"#EQLX.*?#EQLX-END",eqlx_configs)

    def setup_dellsc(self,dell_storage_yaml):

        if self.settings.enable_dellsc_backend is False:
            logger.debug("not setting up dellsc backend")
            return

        logger.debug("configuring dell sc backend")

        cmds = [
            'sed -i "s|<dellsc_san_ip>|' + self.settings.dellsc_san_ip + '|" ' + dell_storage_yaml,
            'sed -i "s|<dellsc_san_login>|' + self.settings.dellsc_san_login + '|" ' + dell_storage_yaml,
            'sed -i "s|<dellsc_san_password>|' + self.settings.dellsc_san_password + '|" ' + dell_storage_yaml,
            'sed -i "s|<dellsc_sc_ssn>|' + self.settings.dellsc_ssn + '|" ' + dell_storage_yaml,
            'sed -i "s|<dellsc_iscsi_ip_address>|' + self.settings.dellsc_iscsi_ip_address + '|" ' + dell_storage_yaml,
            'sed -i "s|<dellsc_iscsi_port>|' + self.settings.dellsc_iscsi_port + '|" ' + dell_storage_yaml,
            'sed -i "s|<dellsc_sc_api_port>|' + self.settings.dellsc_api_port + '|" ' + dell_storage_yaml,
            'sed -i "s|dellsc_osp8_server_folder|' + self.settings.dellsc_server_folder + '|" ' + dell_storage_yaml,
            'sed -i "s|dellsc_osp8_volume_folder|' + self.settings.dellsc_volume_folder + '|" ' + dell_storage_yaml,

        ]
        for cmd in cmds:
            self.run_tty(cmd)

    def setup_networking(self):

        logger.debug("Configuring network settings for overcloud")

        network_yaml = self.templates_dir + "/network-environment.yaml"
        storage_yaml = self.nic_configs_dir + "/ceph-storage.yaml"
        compute_yaml = self.nic_configs_dir + "/compute.yaml"
        controller_yaml = self.nic_configs_dir + "/controller.yaml"

        # Re - Upload the yaml files in case we're trying to
        # leave the undercloud intact but want to redeploy
        # with a different config
        self.upload_file(self.settings.network_env_yaml,
                         network_yaml)
        self.upload_file(self.settings.ceph_storage_yaml,
                         storage_yaml)
        self.upload_file(self.settings.compute_yaml, compute_yaml)
        self.upload_file(self.settings.controller_yaml,
                         controller_yaml)

        cmds = [
            'sed -i "s|ControlPlaneDefaultRoute:.*|' +
            'ControlPlaneDefaultRoute: ' +
            self.settings.director_node.provisioning_ip + '|" ' +
            network_yaml,
            'sed -i "s|EC2MetadataIp:.*|EC2MetadataIp: ' +
            self.settings.director_node.provisioning_ip + '|" ' +
            network_yaml,
            'sed -i "s|InternalApiNetCidr:.*|InternalApiNetCidr: ' +
            self.settings.private_api_network + '|" ' + network_yaml,
            'sed -i "s|StorageNetCidr:.*|StorageNetCidr: ' +
            self.settings.storage_network + '|" ' + network_yaml,
            'sed -i "s|StorageMgmtNetCidr:.*|StorageMgmtNetCidr: ' +
            self.settings.storage_cluster_network + '|" ' + network_yaml,
            'sed -i "s|ExternalNetCidr:.*|ExternalNetCidr: ' +
            self.settings.public_api_network + '|" ' + network_yaml,
            'sed -i "s|InternalApiAllocationPools:.*|'
            'InternalApiAllocationPools: ' +
            "[{'start': '" + self.settings.private_api_allocation_pool_start +
            "', 'end': '" + self.settings.private_api_allocation_pool_end +
            "'}]"   '|" ' + network_yaml,
            'sed -i "s|StorageAllocationPools:.*|StorageAllocationPools: ' +
            "[{'start': '" + self.settings.storage_allocation_pool_start +
            "', 'end': '" +
            self.settings.storage_allocation_pool_end + "'}]"   '|" ' +
            network_yaml,
            'sed -i "s|StorageMgmtAllocationPools:.*|'
            'StorageMgmtAllocationPools: ' +
            "[{'start': '" +
            self.settings.storage_cluster_allocation_pool_start +
            "', 'end': '" +
            self.settings.storage_cluster_allocation_pool_end + "'}]"   '|" ' +
            network_yaml,
            'sed -i "s|ExternalAllocationPools:.*|ExternalAllocationPools: ' +
            "[{'start': '" + self.settings.public_api_allocation_pool_start +
            "', 'end': '" +
            self.settings.public_api_allocation_pool_end + "'}]"   '|" ' +
            network_yaml,
            'sed -i "s|ExternalInterfaceDefaultRoute:.*|'
            'ExternalInterfaceDefaultRoute: ' +
            self.settings.public_api_gateway + '|" ' + network_yaml,
            'sed -i "s|ManagementNetCidr:.*|ManagementNetCidr: ' +
            self.settings.management_network + '|" ' + network_yaml,
            'sed -i "s|ProvisioningNetworkGateway:.*|'
            'ProvisioningNetworkGateway: ' +
            self.settings.provisioning_gateway + '|" ' + network_yaml,
            'sed -i "s|ControlPlaneDefaultRoute:.*|' +
            'ControlPlaneDefaultRoute: ' +
            self.settings.director_node.provisioning_ip +
            '|" ' + network_yaml,
            "sed -i 's|ControlPlaneSubnetCidr:.*|ControlPlaneSubnetCidr: " +
            '"' +
            self.settings.provisioning_network.split("/")[
                1] + '"' + "|' " + network_yaml,
            'sed -i "s|EC2MetadataIp:.*|EC2MetadataIp: ' +
            self.settings.director_node.provisioning_ip + '|" ' + network_yaml,
            "sed -i 's|DnsServers:.*|DnsServers: " + '["' +
            self.settings.name_server + '"]|' + "' " + network_yaml,
            'sed -i "s|InternalApiNetworkVlanID:.*|' +
            'InternalApiNetworkVlanID: ' +
            self.settings.private_api_vlanid + '|" ' + network_yaml,
            'sed -i "s|StorageNetworkVlanID:.*|StorageNetworkVlanID: ' +
            self.settings.storage_vlanid + '|" ' + network_yaml,
            'sed -i "s|StorageMgmtNetworkVlanID:.*|' +
            'StorageMgmtNetworkVlanID: ' +
            self.settings.storage_cluster_vlanid + '|" ' + network_yaml,
            'sed -i "s|ExternalNetworkVlanID:.*|ExternalNetworkVlanID: ' +
            self.settings.public_api_vlanid + '|" ' + network_yaml,
        ]
        for cmd in cmds:
            self.run_tty(cmd)

        if self.settings.controller_bond_opts == \
           self.settings.compute_bond_opts \
           and self.settings.compute_bond_opts == \
           self.settings.storage_bond_opts:
            logger.debug(
                "applying " +
                self.settings.settings.compute_bond_opts +
                " bond mode to all the nodes (network-environment.yaml)")
            cmds = [
                'sed -i "s|      \\"mode=802.3ad miimon=100\\"' +
                '|      \\"mode=' +
                self.settings.compute_bond_opts + '\\"|" ' + network_yaml]
            for cmd in cmds:
                self.run_tty(cmd)
        else:
            logger.debug("applying bond mode on a per type basis")
            cmds = [
                "sed -i '/BondInterfaceOptions:/d' " + network_yaml,
                "sed -i '/mode=802.3ad miimon=100/d' " + network_yaml,
                'sed -i "/BondInterfaceOptions:/{n;s/.*/    default: \'mode=' +
                self.settings.settings.compute_bond_opts +
                "'\\n/;}\" " + compute_yaml,
                'sed -i "/BondInterfaceOptions:/{n;s/.*/    default: \'mode=' +
                self.settings.controller_bond_opts + "'\\n/;}\" " +
                controller_yaml,
                'sed -i "/BondInterfaceOptions:/{n;s/.*/    default: \'mode=' +
                self.settings.storage_bond_opts +
                "'\\n/;}\" " + storage_yaml,
            ]
            for cmd in cmds:
                self.run_tty(cmd)

        logger.debug("updating controller yaml")
        cmds = [
            'sed -i "s|em1|' +
            self.settings.controller_bond0_interfaces.split(" ")[
                0] + '|" ' + controller_yaml,
            'sed -i "s|p3p1|' +
            self.settings.controller_bond0_interfaces.split(" ")[
                1] + '|" ' + controller_yaml,
            'sed -i "s|em2|' +
            self.settings.controller_bond1_interfaces.split(" ")[
                0] + '|" ' + controller_yaml,
            'sed -i "s|p3p2|' +
            self.settings.controller_bond1_interfaces.split(" ")[
                1] + '|" ' + controller_yaml,
            'sed -i "s|em3|' +
            self.settings.controller_provisioning_interface +
            '|" ' + controller_yaml,
            'sed -i "s|192.168.110.0/24|' +
            self.settings.management_network + '|" ' + controller_yaml,
            'sed -i "s|192.168.120.1|' +
            self.settings.provisioning_gateway + '|" ' + controller_yaml
        ]
        for cmd in cmds:
            self.run_tty(cmd)

        logger.debug("updating compute yaml")
        cmds = ['sed -i "s|em1|' +
                self.settings.compute_bond0_interfaces.split(" ")[
                    0] + '|" ' + compute_yaml,
                'sed -i "s|p3p1|' +
                self.settings.compute_bond0_interfaces.split(" ")[
                    1] + '|" ' + compute_yaml,
                'sed -i "s|em2|' +
                self.settings.compute_bond1_interfaces.split(" ")[
                    0] + '|" ' + compute_yaml,
                'sed -i "s|p3p2|' +
                self.settings.compute_bond1_interfaces.split(" ")[
                    1] + '|" ' + compute_yaml,
                'sed -i "s|em3|' +
                self.settings.compute_provisioning_interface + '|" ' +
                compute_yaml
                ]
        for cmd in cmds:
            self.run_tty(cmd)

        logger.debug("updating storage yaml")
        cmds = ['sed -i "s|em1|' +
                self.settings.storage_bond0_interfaces.split(" ")[
                    0] + '|" ' + storage_yaml,
                'sed -i "s|p2p1|' +
                self.settings.storage_bond0_interfaces.split(" ")[
                    1] + '|" ' + storage_yaml,
                'sed -i "s|em2|' +
                self.settings.storage_bond1_interfaces.split(" ")[
                    0] + '|" ' + storage_yaml,
                'sed -i "s|p2p2|' +
                self.settings.storage_bond1_interfaces.split(" ")[
                    1] + '|" ' + storage_yaml,
                'sed -i "s|em3|' +
                self.settings.storage_provisioning_interface + '|" ' +
                storage_yaml
                ]
        for cmd in cmds:
            self.run_tty(cmd)

    def deploy_overcloud(self):

        logger.debug("Configuring network settings for overcloud")
        cmd = "rm -f " + self.home_dir + '/.ssh/known_hosts'
        self.run_tty(cmd)
        cmd = self.source_stackrc + "cd" \
                                    " ~/pilot;./deploy-overcloud.py" \
                                    " --computes " + \
                                    str(len(self.settings.compute_nodes)) + \
                                    " --controllers " + \
                                    str(len(
                                            self.settings.controller_nodes
                                            )) + \
                                    " --storage " + \
                                    str(len(self.settings.ceph_nodes)) + \
                                    " --vlan " + \
                                    self.settings.tenant_vlan_range + \
                                    " --overcloud_name " + \
                                    self.settings.overcloud_name  
        if self.settings.overcloud_deploy_timeout != "120":
            cmd += " --timeout " \
                   + self.settings.overcloud_deploy_timeout
        if self.settings.enable_eqlx_backend is True:
            cmd += " --enable_eqlx"

        if self.settings.enable_dellsc_backend is True:
            cmd += " --enable_dellsc"
	
	cmd += " > overcloud_deploy_out.log"
        
	self.run_tty(cmd)

    def delete_overcloud(self):

        logger.debug("Deleting the overcloud stack")
        self.run_tty(self.source_stackrc +
                     "heat stack-delete " +
                     self.settings.overcloud_name + 
                     " -y")
        while 1:
            if self.settings.overcloud_name in self.run_tty(self.source_stackrc +
                                           "heat stack-list")[0]:
                time.sleep(60)
            else:
                break
        # Unregister the nodes from Ironic
        re = self.run_tty(self.source_stackrc + "ironic node-list | grep None")
        ls_nodes = re[0].split("\n")
        ls_nodes.pop()
        for node in ls_nodes:
            node_id = node.split("|")[1]
            self.run_tty(self.source_stackrc +
                         "ironic node-delete " +
                         node_id)

    def retreive_nodes_ips(self):
        logger.info("**** Retreiving nodes information ")
        deployment_log = '/auto_results/deployment_summary.log'
        ip_info = []
        fi = open(deployment_log, "wb")
        try:
            logger.debug("retreiving node ip details ..")
            ip_info.append("====================================")
            ip_info.append("### nodes ip information ###")
            re = self.run_tty(self.source_stackrc +
                              "nova list | grep controller")
            ip_info.append("### Controllers ###")
            ls_nodes = re[0].split("\n")
            ls_nodes.pop()

            for each in ls_nodes:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]

                re = self.run_tty("ssh heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  self.settings.private_api_vlanid +
                                  ".*netmask " +
                                  self.settings.private_api_netmask +
                                  ".*\" | awk '{print $2}'")
                private_api = re[0].split("\n")[0]

                re = self.run_tty("ssh heat-admin@" +
                                  provisioning_ip +
                                  "/sbin/ifconfig | grep \"inet.*" +
                                  self.settings.public_api_vlanid +
                                  ".*netmask " +
                                  self.settings.public_api_netmask +
                                  ".*\" | awk '{print $2}'")
                nova_public_ip = re[0].split("\n")[0]

                re = self.run_tty("ssh heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  self.settings.storage_vlanid +
                                  ".*netmask " +
                                  self.settings.storage_netmask +
                                  ".*\" | awk '{print $2}'")
                storage_ip = re[0].split("\n")[0]

                ip_info.append(hostname + ":")
                ip_info.append("     - provisioning ip  : " + provisioning_ip)
                ip_info.append("     - nova private ip  : " + private_api)
                ip_info.append("     - nova public ip   : " + nova_public_ip)
                ip_info.append("     - storage ip       : " + storage_ip)

            re = self.run_tty(self.source_stackrc + "nova list | grep compute")

            ip_info.append("### Compute  ###")
            ls_nodes = re[0].split("\n")
            ls_nodes.pop()
            for each in ls_nodes:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]

                re = self.run_tty("ssh heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  self.settings.private_api_vlanid +
                                  ".*netmask " +
                                  self.settings.private_api_netmask +
                                  ".*\" | awk '{print $2}'")
                private_api = re[0].split("\n")[0]

                re = self.run_tty("ssh heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  self.settings.storage_vlanid +
                                  ".*netmask " +
                                  self.settings.storage_netmask +
                                  ".*\" | awk '{print $2}'")
                storage_ip = re[0].split("\n")[0]

                ip_info.append(hostname + ":")
                ip_info.append("     - provisioning ip  : " + provisioning_ip)
                ip_info.append("     - nova private ip  : " + private_api)
                ip_info.append("     - storage ip       : " + storage_ip)

            re = self.run_tty(self.source_stackrc + "nova list | grep storage")

            ip_info.append("### Storage  ###")
            ls_nodes = re[0].split("\n")
            ls_nodes.pop()
            for each in ls_nodes:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]

                re = self.run_tty("ssh heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  self.settings.storage_cluster_vlanid +
                                  ".*netmask 255.255.255.0.*\""
                                  " | awk '{print $2}'")
                cluster_ip = re[0].split("\n")[0]

                re = self.run_tty("ssh heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  self.settings.storage_vlanid +
                                  ".*netmask " +
                                  self.settings.storage_netmask +
                                  ".*\" | awk '{print $2}'")
                storage_ip = re[0].split("\n")[0]

                ip_info.append(hostname + ":")
                ip_info.append(
                    "     - provisioning ip    : " + provisioning_ip)
                ip_info.append("     - storage cluster ip : " + cluster_ip)
                ip_info.append("     - storage ip         : " + storage_ip)
            ip_info.append("====================================")

            # noinspection PyBroadException
            try:
               overcloud_endpoint = self.run_tty(
                    'grep "OS_AUTH_URL=" ~/' + self.settings.overcloud_name + 'rc')[0].split('=')[1].replace(':5000/v2.0/', '')
               overcloud_pass = self.run(
                                                        'grep "OS_PASSWORD=" ~/' + self.settings.overcloud_name + 'rc')[0].split('=')[1]
               ip_info.append("OverCloud Horizon        : " +
                              overcloud_endpoint)
               ip_info.append("OverCloud admin password : " + overcloud_pass)
            except:
                 pass
            ip_info.append("====================================")
        except:
            logger.debug(" Failed to retreive the nodes ip information ")
        finally:
            for each in ip_info:
                logger.debug(each)
                fi.write(each + "\n")
            fi.close()

    def run_sanity_test(self):
        if self.settings.run_sanity is True:
            logger.info("Running sanity test")
            cmd = 'rm -f ~/key_name.pem'
            self.run_tty(cmd)
            self.run_tty('wget '
                         'http://download.cirros-cloud.net/0.3.3/'
                         'cirros-0.3.3-x86_64-disk.img')
            self.run_tty(self.validation_dir +
                         ';chmod ugo+x sanity_test.sh')
            re = self.run_tty("cd " + self.validation_dir +
                              ';./sanity_test.sh')
            if "VALIDATION SUCCESS" in re[0]:
                logger.info("Sanity Test Passed")
            else:
                logger.fatal("Sanity Test failed")
                raise AssertionError(
                    "Sanity test failed - see log for details")
        else:
            logger.info("NOT running sanity test")
            pass

    def run_tempest(self):
        logger.debug("running tempest")
        setts = self.settings
        cmds = [
            "source ~/" + self.settings.overcloud_name + "rc;mkdir -p /home/" +
            setts.director_install_account_user +
            "/tempest",
            'source ~/' + self.settings.overcloud_name + 'rc;cd '
            '~/tempest;/usr/share/openstack-tempest-liberty/tools/'
            'configure-tempest-directory',
            'source ~/' + self.settings.overcloud_name + 'rc;cd ~/tempest;tools/config_tempest.py '
            '--deployer-input '
            '~/tempest-deployer-input.conf --debug '
            '--create identity.uri $OS_AUTH_URL '
            'identity.admin_password $OS_PASSWORD'
            ' object-storage-feature-enabled.discoverability False'
        ]
        for cmd in cmds:
            self.run_tty(cmd)
        if setts.tempest_smoke_only is True:
            cmd = "source ~/" + self.settings.overcloud_name + "rc;cd " \
                  "~/tempest;tools/run-tests.sh .*smoke"
        else:
            cmd = "source ~/" + self.settings.overcloud_name + "rc;cd ~/tempest;tools/run-tests.sh"
        self.run_tty(cmd)
        Scp.get_file(setts.director_node.external_ip,
                     setts.director_install_account_user,
                     setts.director_install_account_pwd,
                     "/auto_results/tempest.xml",
                     "/home/" + setts.director_install_account_user +
                     "/tempest/tempest.xml")
        Scp.get_file(setts.director_node.external_ip,
                     setts.director_install_account_user,
                     setts.director_install_account_pwd,
                     "/auto_results/tempest.log",
                     "/home/" + setts.director_install_account_user +
                     "/tempest/tempest.log")
        logger.debug("Finished running tempest")

    def configure_calamari(self):
        logger.info("Configure Calamari")
        self.run_tty(self.source_stackrc + 'cd ' +
                     self.pilot_dir +
                     ';./config_calamari_nodes.sh ' +
                     self.settings.ceph_node.external_ip +
                     ' ' + self.settings.ceph_node.root_password)

    def enable_fencing(self):
        if self.settings.enable_fencing is True:
            logger.info("enabling fencing")
            cmd = 'cd ' + \
                  self.pilot_dir + \
                  ';./agent_fencing.sh ' + \
                  self.settings.ipmi_user + \
                  ' ' + \
                  self.settings.ipmi_password + \
                  ' enable'
            self.run_tty(cmd)

    def enable_instance_ha(self):
        if self.settings.enable_instance_ha is True:
            logger.info("Enabling instance HA")
            if self.settings.enable_fencing is False:
                logger.error("Fencing NOT enabled, this is required for instance_ha")
            cmd = 'cd ' + \
                  self.pilot_dir + \
                  ';./install_instanceHA.sh ' + \
                  self.settings.ipmi_user + \
                  ' ' + \
                  self.settings.ipmi_password
            self.run_tty(cmd)
