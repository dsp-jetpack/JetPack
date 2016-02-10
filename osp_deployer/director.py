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
from auto_common import Ssh, Scp, Ipmi
import sys,logging, time
logger = logging.getLogger("osp_deployer")


exitFlag = 0


class Director():
    '''
    '''


    def __init__(self):
        self.settings = Settings.settings

        install_admin_user = self.settings.director_install_account_user
        install_admin_password = self.settings.director_install_account_pwd

        cmd = "mkdir /home/"+install_admin_user+"/pilot"
        logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, install_admin_user, install_admin_password,cmd))

        cmd = "mkdir /home/"+install_admin_user+"/pilot/probe_idrac"
        logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, install_admin_user, install_admin_password,cmd))

        cmd = "mkdir /home/"+install_admin_user+"/pilot/probe_idrac/probe_idrac"
        logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, install_admin_user, install_admin_password,cmd))


        cmd = "mkdir /home/"+install_admin_user+"/pilot/templates"
        logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, install_admin_user, install_admin_password,cmd))

        cmd = "mkdir /home/"+install_admin_user+"/pilot/templates/nic-configs"
        logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, install_admin_user, install_admin_password,cmd))


    def apply_internal_repos(self):
        ### Add the internal repo. & if going down that road, and re pull down foreman with the new version
        if self.settings.internal_repos is True:
            logger.debug("Applying internal repo's to the director vm & reinstall rdo manager")
            count = 1
            for repo in self.settings.internal_repos_urls:
                cmd = 'curl ' + repo + " > /etc/yum.repos.d/internal_" + str(count) + ".repo"
                logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password,cmd))
                logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password,"sed -i '/enabled=1/a priority=1' /etc/yum.repos.d/internal_" + str(count) + ".repo"))
                count += 1

            cmds = [
                'subscription-manager repos --enable=rhel-7-server-openstack-8.0-rpms',
                'subscription-manager repos --enable=rhel-7-server-openstack-8.0-director-rpms',
                'yum-config-manager --enable RH7-RHOS-8.0 --setopt="RH7-RHOS-8.0.priority=1"',
                'yum-config-manager --enable RH7-RHOS-8.0-director --setopt="RH7-RHOS-8.0-director.priority=1"',
                'yum remove python-rdomanager-oscplugin -y',
                'yum remove ahc-tools -y',
                'yum clean all',
                'yum makecache',
                'yum repolist all',
                'yum install python-rdomanager-oscplugin -y',
                'yum update -y',
            ]
            for cmd in cmds:
                logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password,cmd))
        for repo in self.settings.internal_repos_urls:
            if "Beta-4" in repo or "Beta-5" in repo:
                    logger.debug("Workaroud for https://bugzilla.redhat.com/show_bug.cgi?id=1298189")
                    cmd = "sudo sed -i \"s/.*Keystone_domain\['heat_domain'\].*/Service\['keystone'\] -> Class\['::keystone::roles::admin'\] -> Class\['::heat::keystone::domain'\]/\" /usr/share/instack-undercloud/puppet-stack-config/puppet-stack-config.pp"
                    logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password,cmd))

    def upload_update_conf_files(self):

        install_admin_user = self.settings.director_install_account_user
        install_admin_password = self.settings.director_install_account_pwd

        remoteSh = "/home/"+install_admin_user+"/pilot/undercloud.conf";
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.undercloud_conf, remoteSh);

        remoteSh = "/home/"+install_admin_user+"/pilot/templates/network-environment.yaml";
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.network_env_yaml, remoteSh);

        #cmd = "sudo chmod 777 " +remoteSh
        #logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))


        remoteSh = "/home/"+install_admin_user+"/pilot/templates/nic-configs/ceph-storage.yaml";
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.network_env_yaml, remoteSh);

        remoteSh = "/home/"+install_admin_user+"/pilot/templates/nic-configs/compute.yaml";
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.network_env_yaml, remoteSh);

        remoteSh = "/home/"+install_admin_user+"/pilot/templates/nic-configs/controller.yaml";
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.network_env_yaml, remoteSh);




        cmds = [
            'sed -i "s|local_ip = .*|local_ip = '+ self.settings.director_node.provisioning_ip +'/24|" pilot/undercloud.conf',
            'sed -i "s|local_interface = .*|local_interface = eth1|" pilot/undercloud.conf',
            'sed -i "s|masquerade_network = .*|masquerade_network = '+ self.settings.provisioning_network +'|" pilot/undercloud.conf',
            'sed -i "s|dhcp_start = .*|dhcp_start = '+ self.settings.provisioning_net_dhcp_start +'|" pilot/undercloud.conf',
            'sed -i "s|dhcp_end = .*|dhcp_end = '+ self.settings.provisioning_net_dhcp_end +'|" pilot/undercloud.conf',
            'sed -i "s|network_cidr = .*|network_cidr = '+self. settings.provisioning_network +'|" pilot/undercloud.conf',
            'sed -i "s|network_gateway = .*|network_gateway = '+ self.settings.director_node.provisioning_ip +'|" pilot/undercloud.conf',
            'sed -i "s|inspection_iprange = .*|inspection_iprange = '+ self.settings.discovery_ip_range +'|" pilot/undercloud.conf',
     ]
        for cmd in cmds:
            logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, install_admin_user, install_admin_password,cmd))

    def install_director(self):
        logger.debug("uploading & executing sh script")

        install_admin_user = self.settings.director_install_account_user
        install_admin_password = self.settings.director_install_account_pwd


        networkYaml = "/home/"+install_admin_user+"/pilot/templates/network-environment.yaml"
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.network_env_yaml, networkYaml)

        storageYaml = "/home/"+install_admin_user+"/pilot/templates/nic-configs/ceph-storage.yaml"
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.ceph_storage_yaml, storageYaml)

        computeYaml = "/home/"+install_admin_user+"/pilot/templates/nic-configs/compute.yaml"
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.compute_yaml, computeYaml)

        controllerYaml = "/home/"+install_admin_user+"/pilot/templates/nic-configs/controller.yaml"
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.controller_yaml, controllerYaml)


        installProbe = "/home/"+install_admin_user+"/pilot/install_probe_idrac.sh"
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.foreman_configuration_scripts + '/pilot/install_probe_idrac.sh', installProbe)
        cmd = "chmod 777 " + installProbe
        logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        probFiles1 = [
                'README.rst',
                'requirements.txt',
                'setup.cfg',
                'setup.py',
        ]
        for each in probFiles1:
            remote = "/home/"+install_admin_user+"/pilot/probe_idrac/" + each
            local = '/pilot/probe_idrac/' + each
            Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.foreman_configuration_scripts + local, remote)
            cmd = "chmod 777 " + remote
            logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))
        probFiles2 = [
                '__init__.py',
                'probe_idrac.py',
        ]
        for each in probFiles2:
            remote = "/home/"+install_admin_user+"/pilot/probe_idrac/probe_idrac/" + each
            local = '/pilot/probe_idrac/probe_idrac/' + each
            Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.foreman_configuration_scripts + local, remote)
            cmd = "chmod 777 " + remote
            logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        remoteSh = "/home/"+self.settings.director_install_account_user+"/pilot/install-director.sh";
        Scp.put_file( self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd, self.settings.install_director_sh, remoteSh);

        cmd = "chmod 777 /home/"+self.settings.director_install_account_user + "/pilot/install-director.sh"
        logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))


        cmd = '~/pilot/install-director.sh ' + self.settings.name_server
        logger.debug(Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))


    def upload_cloud_images(self):

        logger.debug("Uploading cloud images to the Director vm")

        cmd = "mkdir /home/"+self.settings.director_install_account_user+"/pilot/images"
        logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        remoteSh = "/home/"+self.settings.director_install_account_user+"/pilot/images/deploy-ramdisk-ironic.tar";
        Scp.put_file( self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd, self.settings.deploy_ram_disk_image, remoteSh);

        remoteSh = "/home/"+self.settings.director_install_account_user+"/pilot/images/discovery-ramdisk.tar";
        Scp.put_file( self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd, self.settings.discovery_ram_disk_image, remoteSh);

        remoteSh = "/home/"+self.settings.director_install_account_user+"/pilot/images/overcloud-full.tar";
        Scp.put_file( self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd, self.settings.overcloud_image, remoteSh);


    def node_discovery(self):

        if self.settings.use_custom_instack_json is True:
            logger.debug("Using custom instack.json file - NOT scannings nodes")
            cmd = "rm /home/"+self.settings.director_install_account_user+"/instackenv.json -f"
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

            remoteSh = "/home/"+self.settings.director_install_account_user+"/instackenv.json"
            Scp.put_file( self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd, self.settings.custom_instack_json, remoteSh);
        else :
            cmds = [
                "echo 'export GOPATH=$HOME/go' >>$HOME/.bash_profile",
                "echo 'export PATH=$PATH:$HOME/go/bin' >> $HOME/.bash_profile",
                'sudo yum -y install golang -y',
                '. $HOME/.bash_profile;go get get github.com/dell-esg/idracula',
                '. $HOME/.bash_profile;go install github.com/dell-esg/idracula'
                ]
            for cmd in cmds:
                logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))


            # Idrac doesn't always play nice .. so working around cases where nic's dont get detected .. resetting idrac & powering on the node seems to do it.
            for node in (self.settings.controller_nodes + self.settings.compute_nodes + self.settings.ceph_nodes) :
                    while 1:
                        cmd = ". $HOME/.bash_profile;idracula -u "+ self.settings.ipmi_user + " -p '" + self.settings.ipmi_password  +"' -scan '"+ node.idrac_ip+"-"+node.idrac_ip+"'"
                        out = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)[0]
                        if "No integrated 1 GB nics" in out or "No WSMAN endpoint at" in out:
                            logger.warning(node.hostname +" did not get discovered properly")
                            if "No integrated 1 GB nics" in out:
                                logger.debug("grabbing drac informations in " + node.idrac_ip+".dump")
                                cmd = "cd ~/pilot/probe_idrac/probe_idrac/;./probe_idrac.py -l "+self.settings.ipmi_user+" -p "+self.settings.ipmi_password+" "+node.idrac_ip+" > "+node.idrac_ip+".dump"
                                Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

                            logger.debug("reseting idrac")
                            ipmi_session = Ipmi(self.settings.cygwin_installdir, self.settings.ipmi_user, self.settings.ipmi_password, node.idrac_ip)
                            logger.debug(ipmi_session.drac_reset())
                            time.sleep(120)
                            backToLife = False
                            while backToLife == False :
                                try:
                                    logger.debug(ipmi_session.get_power_state())
                                    backToLife = True
                                    time.sleep(20)
                                except:
                                    pass
                            ipmi_session.power_on()
                            time.sleep(120)
                            ipmi_session.power_off()
                            ipmi_session.set_boot_to_pxe()
                        else:
                            break


            cmd = ". $HOME/.bash_profile;idracula -u "+ self.settings.ipmi_user + " -p '" + self.settings.ipmi_password  +"' -scan '"+self.settings.ipmi_discovery_range_start+"-"+self.settings.ipmi_discovery_range_end+"' > ~/instackenv.json"
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

            cmd = "ls -la ~/instackenv.json | awk '{print $5;}'"
            size = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)[0]
            if int(size) <= 50:
                logger.fatal("did not manage to pick up the nodes..")
                raise AssertionError("Unable to scan all the nodes ... need to go & pull the plug(s) - " + size + " - " +size[0])

            else:
                logger.debug("nodes appear to have been picked up")

        for node in (self.settings.controller_nodes + self.settings.compute_nodes + self.settings.ceph_nodes) :
                    ipmi_session = Ipmi(self.settings.cygwin_installdir, self.settings.ipmi_user, self.settings.ipmi_password, node.idrac_ip)
                    ipmi_session.power_off()
                    time.sleep(60)

        if self.settings.use_ipmi_driver is True:
            logger.debug("Using pxe_ipmi driver")
            cmd = 'sed -i "s|pxe_drac|pxe_ipmitool|" ~/instackenv.json'
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))


        cmd = "source stackrc;openstack baremetal import --json ~/instackenv.json"
        logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))


        cmd = "source stackrc;openstack baremetal configure boot"
        logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        cmd = "source stackrc;openstack baremetal introspection bulk start"
        logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))


    def assign_node_roles(self):
        logger.debug("uploading assign script")

        remoteSh = "/home/"+self.settings.director_install_account_user+"/assign_role.py";
        Scp.put_file( self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd, self.settings.assign_role_py, remoteSh);

        cmd = "chmod 777 /home/"+self.settings.director_install_account_user + "/assign_role.py"
        logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        logger.debug("Assigning roles to nodes")

        for node in self.settings.controller_nodes:
            cmd = 'cd ' + "/home/"+self.settings.director_install_account_user + ";source stackrc;./assign_role.py " + node.provisioning_mac_address + " controller"
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        for node in self.settings.compute_nodes:
            cmd = 'cd ' + "/home/"+self.settings.director_install_account_user + ";source stackrc;./assign_role.py " + node.provisioning_mac_address + " compute"
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        for node in self.settings.ceph_nodes:
            cmd = 'cd ' + "/home/"+self.settings.director_install_account_user + ";source stackrc;./assign_role.py " + node.provisioning_mac_address + " storage"
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))


    def setup_networking(self):

        install_admin_user = self.settings.director_install_account_user
        install_admin_password = self.settings.director_install_account_pwd

        logger.debug("Configuring network settings for overcloud")

        networkYaml = "/home/"+install_admin_user+"/pilot/templates/network-environment.yaml";
	storageYaml = "/home/"+install_admin_user+"/pilot/templates/nic-configs/ceph-storage.yaml";
        computeYaml = "/home/"+install_admin_user+"/pilot/templates/nic-configs/compute.yaml";
        controllerYaml = "/home/"+install_admin_user+"/pilot/templates/nic-configs/controller.yaml";
		
	#Re - Upload the yaml files in case we're trying to leave the undercloud intact but want to redeploy with a different config
	#and replace the HOME in the netwrk env that install director would have previously updated
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.network_env_yaml, networkYaml)
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.ceph_storage_yaml, storageYaml)
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.compute_yaml, computeYaml)
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.controller_yaml, controllerYaml)

        #cmd = "sudo chmod 777 " +networkYaml
        #logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))
	
	cmd ="sed -i 's/HOME\\//\\/home\\/osp_admin\\//' " + networkYaml
	logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        cmds = [
            'sed -i "s|ControlPlaneDefaultRoute:.*|ControlPlaneDefaultRoute: ' + self.settings.director_node.provisioning_ip + '|" ' + networkYaml,
            'sed -i "s|EC2MetadataIp:.*|EC2MetadataIp: ' + self.settings.director_node.provisioning_ip + '|" ' + networkYaml,
            'sed -i "s|InternalApiNetCidr:.*|InternalApiNetCidr: ' + self.settings.private_api_network + '|" ' + networkYaml,
            'sed -i "s|StorageNetCidr:.*|StorageNetCidr: ' + self.settings.storage_network + '|" ' + networkYaml,
            'sed -i "s|StorageMgmtNetCidr:.*|StorageMgmtNetCidr: ' + self.settings.storage_cluster_network + '|" ' + networkYaml,
            'sed -i "s|ExternalNetCidr:.*|ExternalNetCidr: ' + self.settings.external_network + '|" ' + networkYaml,
            'sed -i "s|InternalApiAllocationPools:.*|InternalApiAllocationPools: ' + "[{'start': '" + self.settings.private_api_allocation_pool_start + "', 'end': '"+ self.settings.private_api_allocation_pool_end +"'}]"   '|" ' + networkYaml,
            'sed -i "s|StorageAllocationPools:.*|StorageAllocationPools: ' + "[{'start': '" + self.settings.storage_allocation_pool_start + "', 'end': '"+ self.settings.storage_allocation_pool_end +"'}]"   '|" ' + networkYaml,
            'sed -i "s|StorageMgmtAllocationPools:.*|StorageMgmtAllocationPools: ' + "[{'start': '" + self.settings.storage_cluster_allocation_pool_start + "', 'end': '"+ self.settings.storage_cluster_allocation_pool_end +"'}]"   '|" ' + networkYaml,
            'sed -i "s|ExternalAllocationPools:.*|ExternalAllocationPools: ' + "[{'start': '" + self.settings.external_allocation_pool_start + "', 'end': '"+ self.settings.external_allocation_pool_end +"'}]"   '|" ' + networkYaml,
            'sed -i "s|ExternalInterfaceDefaultRoute:.*|ExternalInterfaceDefaultRoute: ' + self.settings.external_gateway + '|" ' + networkYaml,
            'sed -i "s|ManagementNetCidr:.*|ManagementNetCidr: ' + self.settings.management_network + '|" ' + networkYaml,
            'sed -i "s|ProvisioningNetworkGateway:.*|ProvisioningNetworkGateway: ' + self.settings.provisioning_gateway + '|" ' + networkYaml,
            'sed -i "s|ControlPlaneDefaultRoute:.*|ControlPlaneDefaultRoute: ' + self.settings.director_node.provisioning_ip + '|" ' + networkYaml,
            "sed -i 's|ControlPlaneSubnetCidr:.*|ControlPlaneSubnetCidr: " + '"' + self.settings.provisioning_network.split("/")[1] + '"' +  "|' " + networkYaml,
            'sed -i "s|EC2MetadataIp:.*|EC2MetadataIp: ' + self.settings.director_node.provisioning_ip + '|" ' + networkYaml,
            "sed -i 's|DnsServers:.*|DnsServers: " + '["' + self.settings.name_server + '"]|' + "' " + networkYaml,
            'sed -i "s|InternalApiNetworkVlanID:.*|InternalApiNetworkVlanID: ' + self.settings.private_api_vlanid + '|" ' + networkYaml,
            'sed -i "s|StorageNetworkVlanID:.*|StorageNetworkVlanID: ' + self.settings.storage_vlanid + '|" ' + networkYaml,
            'sed -i "s|StorageMgmtNetworkVlanID:.*|StorageMgmtNetworkVlanID: ' + self.settings.storage_cluster_vlanid + '|" ' + networkYaml,
            'sed -i "s|ExternalNetworkVlanID:.*|ExternalNetworkVlanID: ' + self.settings.public_api_vlanid + '|" ' + networkYaml,
        ]
        for cmd in cmds:
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

	if self.settings.controller_bond_opts == self.settings.compute_bond_opts and self.settings.compute_bond_opts == self.settings.storage_bond_opts:
                logger.debug("applying " + self.settings.settings.compute_bond_opts + " bond mode to all the nodes (network-environment.yaml)")
                cmds = [
			 'sed -i "s|      \\"mode=802.3ad miimon=100\\"|      \\"mode='+ self.settings.compute_bond_opts +'\\"|" ' + networkYaml,
			]
		for cmd in cmds:
                	logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))
        else:
		logger.debug("applying bond mode on a per type basis")
		cmds = [
		       "sed -i '/BondInterfaceOptions:/d' " + networkYaml,
                       "sed -i '/mode=802.3ad miimon=100/d' " + networkYaml,
		       'sed -i "/BondInterfaceOptions:/{n;s/.*/    default: \'mode='+ self.settings.settings.compute_bond_opts +"'\\n/;}\" " + computeYaml,
		       'sed -i "/BondInterfaceOptions:/{n;s/.*/    default: \'mode='+ self.settings.controller_bond_opts +"'\\n/;}\" " + controllerYaml,
 		       'sed -i "/BondInterfaceOptions:/{n;s/.*/    default: \'mode='+ self.settings.storage_bond_opts +"'\\n/;}\" " + storageYaml,	
		]
		for cmd in cmds:
            		logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        logger.debug("updating controller yaml")
        cmds = ['sed -i "s|em1|'+ self.settings.controller_bond0_interfaces.split(" ")[0] +'|" ' + controllerYaml,
                'sed -i "s|p3p1|'+ self.settings.controller_bond0_interfaces.split(" ")[1] +'|" ' + controllerYaml,
                'sed -i "s|em2|'+ self.settings.controller_bond1_interfaces.split(" ")[0] +'|" ' + controllerYaml,
                'sed -i "s|p3p2|'+ self.settings.controller_bond1_interfaces.split(" ")[1] +'|" ' + controllerYaml,
                'sed -i "s|em3|'+ self.settings.controller_provisioning_interface +'|" ' + controllerYaml,
                'sed -i "s|192.168.110.0/24|'+ self.settings.management_network +'|" ' + controllerYaml,
                'sed -i "s|192.168.120.1|'+ self.settings.provisioning_gateway +'|" ' + controllerYaml,

                ]
        for cmd in cmds :
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        logger.debug("updating compute yaml")
        cmds = ['sed -i "s|em1|'+ self.settings.compute_bond0_interfaces.split(" ")[0] +'|" ' + computeYaml,
                'sed -i "s|p3p1|'+ self.settings.compute_bond0_interfaces.split(" ")[1] +'|" ' + computeYaml,
                'sed -i "s|em2|'+ self.settings.compute_bond1_interfaces.split(" ")[0] +'|" ' + computeYaml,
                'sed -i "s|p3p2|'+ self.settings.compute_bond1_interfaces.split(" ")[1] +'|" ' + computeYaml,
                'sed -i "s|em3|'+ self.settings.compute_provisioning_interface +'|" ' + computeYaml,

                ]
        for cmd in cmds:
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        logger.debug("updating storage yaml")
        cmds = ['sed -i "s|em1|'+ self.settings.storage_bond0_interfaces.split(" ")[0] +'|" ' + storageYaml,
                'sed -i "s|p2p1|'+ self.settings.storage_bond0_interfaces.split(" ")[1] +'|" ' + storageYaml,
                'sed -i "s|em2|'+ self.settings.storage_bond1_interfaces.split(" ")[0] +'|" ' + storageYaml,
                'sed -i "s|p2p2|'+ self.settings.storage_bond1_interfaces.split(" ")[1] +'|" ' + storageYaml,
                'sed -i "s|em3|'+ self.settings.storage_provisioning_interface + '|" ' + storageYaml,

                ]
        for cmd in cmds :
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))


    def deploy_overcloud(self):

        install_admin_user = self.settings.director_install_account_user
        install_admin_password = self.settings.director_install_account_pwd

        logger.debug("Configuring network settings for overcloud")

        deployOvercloud_sh = "/home/"+install_admin_user+"/pilot/deploy-overcloud.py"
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.deploy_overcloud_sh, deployOvercloud_sh);

        cmd = "sudo chmod 777 " + deployOvercloud_sh
        logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        logger.debug("Starting overcloud deployment .. you can monitor the progress from the director vm running heat resource-list overcloud")
        cmd = "cd ~/pilot;source ~/stackrc;./deploy-overcloud.py" + " --computes " + str(len(self.settings.compute_nodes)) + " --controllers " + str(len(self.settings.controller_nodes))  +" --storage " + str(len(self.settings.ceph_nodes)) + " --vlan " + self.settings.tenant_vlan_range
        logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

    def delete_overcloud(self):

        install_admin_user = self.settings.director_install_account_user
        install_admin_password = self.settings.director_install_account_pwd

        logger.debug("Deleting the overcloud stack")
        cmd = "cd ~/pilot;source ~/stackrc;heat stack-delete overcloud"
        logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        cmd = "cd ~/pilot;source ~/stackrc;heat stack-list"
        while 1 :

            if "overcloud" in Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)[0]:
                time.sleep(60)
            else :
                return

    def sanity_test(self):
        #TODO .. upload & prep sanity tests // run it & clean up ?
        print "todo"


    def fix_controllers_vlan_range(self):
        logger.debug("Workaround for known beta2 issue where neutron tenant vlan configuration is not applied properly")
        cmd = "source ~/stackrc;nova list | grep controller"
        re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

        controllers = re[0].split("\n")
        controllers.pop()
        for each in controllers:
            provisioning_ip = each.split("|")[6].split("=")[1]
            cmd = "ssh heat-admin@" + provisioning_ip + " \"sudo sed -i 's/network_vlan_ranges =datacentre/network_vlan_ranges =datacentre:"+self.settings.tenant_vlan_range+"/' /etc/neutron/plugin.ini\""
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) )
        for each in self.settings.controller_nodes:
            ipmi_session = Ipmi(self.settings.cygwin_installdir, self.settings.ipmi_user, self.settings.ipmi_password, each.idrac_ip)
            ipmi_session.power_off()
            time.sleep(20)
            ipmi_session.power_on()
            logger.debug("Controller nodes booting up .. might take a few minutes")


