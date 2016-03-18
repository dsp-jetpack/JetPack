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
import sys,logging, time, os
from checkpoints import Checkpoints
logger = logging.getLogger("osp_deployer")


exitFlag = 0


class Director():
    '''
    '''


    def __init__(self):
        self.settings = Settings.settings

        install_admin_user = self.settings.director_install_account_user
        install_admin_password = self.settings.director_install_account_pwd
	
        cmd = "mkdir /home/"+self.settings.director_install_account_user+"/pilot"
        logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

	cmd = "mkdir /home/"+self.settings.director_install_account_user+"/pilot/images"
        logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

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
        logger.debug("Workaroud for https://bugzilla.redhat.com/show_bug.cgi?id=1298189")
        cmd = "sudo sed -i \"s/.*Keystone_domain\['heat_domain'\].*/Service\['keystone'\] -> Class\['::keystone::roles::admin'\] -> Class\['::heat::keystone::domain'\]/\" /usr/share/instack-undercloud/puppet-stack-config/puppet-stack-config.pp"
        logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password,cmd))

    def upload_update_conf_files(self):

        install_admin_user = self.settings.director_install_account_user
        install_admin_password = self.settings.director_install_account_pwd


	logger.debug("tar up the required pilot files")
	os.system(" cd "+ self.settings.foreman_configuration_scripts + "/pilot/;tar -zcvf /root/pilot.tar.gz *")

        remoteSh = "/home/"+install_admin_user+"/pilot.tar.gz";
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, "/root/pilot.tar.gz", remoteSh);
	
	cmd = 'cd;tar zxvf pilot.tar.gz -C pilot'
	logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, install_admin_user, install_admin_password,cmd))


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

        cmd = '~/pilot/install-director.sh ' + self.settings.name_server
        logger.debug(Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        tester = Checkpoints()
        tester.verify_undercloud_installed()

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
                '. $HOME/.bash_profile;go get github.com/dell-esg/idracula',
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
        tester = Checkpoints()
        tester.verify_nodes_registered_in_ironic()

        cmd = "source stackrc;openstack baremetal configure boot"
        logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))

        cmd = "source stackrc;openstack baremetal introspection bulk start"
        logger.debug(Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))
        tester.verify_introspection_sucessfull()



    def assign_node_roles(self):
        logger.debug("uploading assign script")

        logger.debug("Assigning roles to nodes")

        for node in self.settings.controller_nodes:
            cmd = 'cd ' + "/home/"+self.settings.director_install_account_user + ";source stackrc;cd ~/pilot;./assign_role.py " + node.provisioning_mac_address + " controller"
            out =  Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
            if "Not Found" in out[0]:
                raise AssertionError("Failed to assign Controller node role to mac " + node.provisioning_mac_address )

        for node in self.settings.compute_nodes:
            cmd = 'cd ' + "/home/"+self.settings.director_install_account_user + ";source stackrc;cd ~/pilot;./assign_role.py " + node.provisioning_mac_address + " compute"
            out = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
            if "Not Found" in out[0]:
                raise AssertionError("Failed to assign Compute node role to mac " + node.provisioning_mac_address )

        for node in self.settings.ceph_nodes:
            cmd = 'cd ' + "/home/"+self.settings.director_install_account_user + ";source stackrc;cd ~/pilot;./assign_role.py " + node.provisioning_mac_address + " storage"
            out = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
            if "Not Found" in out[0]:
                raise AssertionError("Failed to assign Storage node role to mac " + node.provisioning_mac_address )

    def setup_templates(self):
	 # Re-upload the yaml files in case we're trying to leave the undercloud
         # intact but want to redeploy with a different config.
 
         install_admin_user = self.settings.director_install_account_user
         install_admin_password = self.settings.director_install_account_pwd
	 self.setup_networking()
	 self.setup_storage()
	 self.setup_eqlx()
	 self.setup_dellsc()

    def setup_storage(self):
         if len(self.settings.ceph_nodes) == 0:
             logger.debug("Skipping Ceph storage setup because there are no storage nodes")
             return
 
         logger.debug("Configuring Ceph storage settings for overcloud")
 
         # Set up the Ceph OSDs using the 'osd_disks' defined for the first
         # storage node. This is the best we can do until the OSP Director
         # supports more than a single, global OSD configuration.
         osd_disks = self.settings.ceph_nodes[0].osd_disks
 
         cephYaml = os.path.join("pilot", "templates", "overrides", "puppet", "hieradata", "ceph.yaml")
         src_name = os.path.join(self.settings.foreman_configuration_scripts, cephYaml)
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
                 if len(tokens) > 0 and (tokens[0].startswith("#") or tokens[0].startswith("'") or tokens[0].startswith("journal:")):
                     continue
 
                 # End of original Ceph OSD configuration: now write the new one
                 tmp_file.write("{}\n".format(osds_param))
                 for osd in osd_disks:
                     # Format is ":OSD_DRIVE" or ":OSD_DRIVE:JOURNAL_DRIVE",
                     # so split on the ':'
                     tokens = osd.split(':')
 
                     # Make sure OSD_DRIVE begins with "/dev/"
                     if not tokens[1].startswith("/dev/"):
                         tokens[1] = "/dev/" + tokens[1]
 
                     if len(tokens) == 3:
                         # This OSD specifies a separate journal drive
                         tmp_file.write("  '{}':\n    journal: '{}'\n".format(tokens[1], tokens[2]))
                     elif len(tokens) == 2:
                         # This OSD does not specify a separate journal
                         tmp_file.write("  '{}': {{}}\n".format(tokens[1]))
                     else:
                         logger.warning("Bad entry in osd_disks: {}".format(osd))
 
                 # This is the line that follows the original Ceph OSD config
                 tmp_file.write(line)
                 found_osds_param = False
 
             else:
                 tmp_file.write(line)
 
         src_file.close()
         tmp_file.close()
 
         install_admin_user = self.settings.director_install_account_user
         install_admin_password = self.settings.director_install_account_pwd
 
         dst_name = os.path.join(os.path.join("/home", install_admin_user, cephYaml))
         Scp.put_file(self.settings.director_node.external_ip, install_admin_user, install_admin_password, tmp_name, dst_name)
         os.remove(tmp_name)

    def setup_eqlx(self):
	
	if self.settings.enable_eqlx_backend is False:
	   logger.debug("not setting up eqlx backend")
	   return

	logger.debug("configuring eql backend")
	#Re - Upload the yaml files in case we're trying to leave the undercloud intact but want to redeploy with a different config
	eqlx_yaml = "/home/"+ self.settings.director_install_account_user +"/pilot/templates/dell-eqlx-environment.yaml"
	Scp.put_file( self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd, self.settings.eqlx_yaml, eqlx_yaml)

	cmds = [
	   'sed -i "s|CinderEnableEqlxBackend: .*|CinderEnableEqlxBackend: true|" ' + eqlx_yaml,
           'sed -i "s|CinderEqlxBackendName: .*|CinderEqlxBackendName: ' + "'" +  self.settings.eqlx_backend_name + "'" + '|" ' + eqlx_yaml,
           'sed -i "s|CinderEqlxSanIp: .*|CinderEqlxSanIp: ' + "'" +  self.settings.eqlx_san_ip + "'" + '|" ' + eqlx_yaml,
           'sed -i "s|CinderEqlxSanLogin: .*|CinderEqlxSanLogin: ' + "'" +  self.settings.eqlx_san_login + "'" + '|" ' + eqlx_yaml,
           'sed -i "s|CinderEqlxSanPassword: .*|CinderEqlxSanPassword: ' + "'" +  self.settings.eqlx_san_password + "'" + '|" ' + eqlx_yaml,
           'sed -i "s|CinderEqlxSanThinProvision: .*|CinderEqlxSanThinProvision: ' +  self.settings.eqlx_thin_provisioning + '|" ' + eqlx_yaml,
           'sed -i "s|CinderEqlxGroupname: .*|CinderEqlxGroupname: ' + "'" +  self.settings.eqlx_group_n + "'" + '|" ' + eqlx_yaml,
           'sed -i "s|CinderEqlxPool: .*|CinderEqlxPool: ' + "'" +  self.settings.eqlx_pool + "'" + '|" ' + eqlx_yaml,
           'sed -i "s|CinderEqlxChapLogin: .*|CinderEqlxChapLogin: ' + "'" +  self.settings.eqlx_ch_login + "'" + '|" ' + eqlx_yaml,
           'sed -i "s|CinderEqlxChapPassword: .*|CinderEqlxChapPassword: ' + "'" +  self.settings.eqlx_ch_pass + "'" + '|" ' + eqlx_yaml,
           'sed -i "s|CinderEqlxUseChap: .*|CinderEqlxUseChap: ' +  self.settings.eqlx_use_chap + '|" ' + eqlx_yaml,
	]
	for cmd in cmds:
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))
	logger.info("Applying workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1314073")
	cmd = "sudo sed -i 's|2015-11-06|2015-10-15|' /home/"+ self.settings.director_install_account_user +"/pilot/templates/overcloud/puppet/extraconfig/pre_deploy/controller/cinder-eqlx.yaml"
	Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
	cmd = "sudo sed -i 's|2015-11-06|2015-10-15|' /usr/share/openstack-tripleo-heat-templates/puppet/extraconfig/pre_deploy/controller/cinder-eqlx.yaml"
	Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

    def setup_dellsc(self):
	
	if self.settings.enable_dellsc_backend is False:
	   logger.debug("not setting up dellsc backend")
	   return

	logger.debug("configuring dell sc backend")
	#Re - Upload the yaml files in case we're trying to leave the undercloud intact but want to redeploy with a different config
	dellsc_yaml = "/home/"+ self.settings.director_install_account_user +"/pilot/templates/dell-dellsc-environment.yaml"
	Scp.put_file( self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd, self.settings.dellsc_yaml, dellsc_yaml)

	cmds = [
	   'sed -i "s|CinderEnableDellScBackend: .*|CinderEnableDellScBackend: true|" ' + dellsc_yaml,
       'sed -i "s|CinderDellScBackendName: .*|CinderDellScBackendName: ' + "'" +  self.settings.dellsc_backend_name + "'" + '|" ' + dellsc_yaml,
	   'sed -i "s|CinderDellScSanIp: .*|CinderDellScSanIp: ' + "'" +  self.settings.dellsc_san_ip + "'" + '|" ' + dellsc_yaml,
	   'sed -i "s|CinderDellScSanLogin: .*|CinderDellScSanLogin: ' + "'" +  self.settings.dellsc_san_login + "'" + '|" ' + dellsc_yaml,
	   'sed -i "s|CinderDellScSanPassword: .*|CinderDellScSanPassword: ' +  self.settings.dellsc_san_password + '|" ' + dellsc_yaml,
	   'sed -i "s|CinderDellScSsn: .*|CinderDellScSsn: ' + "'" +  self.settings.dellsc_ssn + "'" + '|" ' + dellsc_yaml,
	   'sed -i "s|CinderDellScIscsiIpAddress: .*|CinderDellScIscsiIpAddress: ' +  self.settings.dellsc_iscsi_ip_address + '|" ' + dellsc_yaml,
	   'sed -i "s|CinderDellScIscsiPort: .*|CinderDellScIscsiPort: ' + "'" +  self.settings.dellsc_iscsi_port + "'" + '|" ' + dellsc_yaml,
	   'sed -i "s|CinderDellScApiPort: .*|CinderDellScApiPort: ' + "'" +  self.settings.dellsc_api_port + "'" + '|" ' + dellsc_yaml,
	   'sed -i "s|CinderDellScServerFolder: .*|CinderDellScServerFolder: ' + "'" +  self.settings.dellsc_server_folder + "'" + '|" ' + dellsc_yaml,
	   'sed -i "s|CinderDellScVolumeFolder: .*|CinderDellScVolumeFolder: ' + "'" +  self.settings.dellsc_volume_folder + "'" + '|" ' + dellsc_yaml,
	  
	]
	for cmd in cmds:
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))
	logger.info("Applying workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1314073")
	cmd = "sudo sed -i 's|2015-11-06|2015-10-15|' /usr/share/openstack-tripleo-heat-templates/puppet/extraconfig/pre_deploy/controller/cinder-dellsc.yaml"
	Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

    def setup_networking(self):

        install_admin_user = self.settings.director_install_account_user
        install_admin_password = self.settings.director_install_account_pwd

        logger.debug("Configuring network settings for overcloud")

        networkYaml = "/home/"+install_admin_user+"/pilot/templates/network-environment.yaml";
	storageYaml = "/home/"+install_admin_user+"/pilot/templates/nic-configs/ceph-storage.yaml";
        computeYaml = "/home/"+install_admin_user+"/pilot/templates/nic-configs/compute.yaml";
        controllerYaml = "/home/"+install_admin_user+"/pilot/templates/nic-configs/controller.yaml";

	#Re - Upload the yaml files in case we're trying to leave the undercloud intact but want to redeploy with a different config
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.network_env_yaml, networkYaml)
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.ceph_storage_yaml, storageYaml)
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.compute_yaml, computeYaml)
        Scp.put_file( self.settings.director_node.external_ip, install_admin_user, install_admin_password, self.settings.controller_yaml, controllerYaml)

        #cmd = "sudo chmod 777 " +networkYaml
        #logger.debug( Ssh.execute_command(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))
	
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

        cmd = "cd ~/pilot;source ~/stackrc;./deploy-overcloud.py" + " --computes " + str(len(self.settings.compute_nodes)) + " --controllers " + str(len(self.settings.controller_nodes))  +" --storage " + str(len(self.settings.ceph_nodes)) + " --vlan " + self.settings.tenant_vlan_range
        if self.settings.overcloud_deploy_timeout != "90":
            cmd += " --timeout "+ self.settings.overcloud_deploy_timeout
	    if self.settings.enable_eqlx_backend is True:
	        cmd += " --enable_eqlx"
     
	    if self.settings.enable_dellsc_backend is True:
	      cmd += " --enable_dellsc"
		  
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
                 break
        # Unregister the nodes from Ironic
        cmd = "source ~/stackrc;ironic node-list | grep None"
        re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
        list = re[0].split("\n")
        list.pop()
        for node in list:
            node_id = node.split("|")[1]
            cmd = "source ~/stackrc;ironic node-delete " + node_id
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd))




    def retreive_nodes_ips(self):
        logger.info  ("**** Retreiving nodes information ")
        ip_info = []
        try:
            logger.debug("retreiving node ip details ..")

            ip_info.append(  "====================================")
            ip_info.append(  "### nodes ip information ###")
            known_hosts_filename = "~/.ssh/known_hosts"
            cmd = "source ~/stackrc;nova list | grep controller"
            re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

            ip_info.append(  "### Controllers ###" )
            list = re[0].split("\n")
            list.pop()

            for each in list:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]
                cmd = "ssh-keyscan {} >> ~/.ssh/known_hosts".format(provisioning_ip)
                re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+self.settings.private_api_vlanid+".*netmask "+self.settings.private_api_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
                private_api = re[0].split("\n")[0]

                cmd = "ssh heat-admin@"+provisioning_ip+ "/sbin/ifconfig | grep \"inet.*"+self.settings.public_api_vlanid+".*netmask "+self.settings.public_api_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
                nova_public_ip = re[0].split("\n")[0]


                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+self.settings.storage_vlanid+".*netmask "+self.settings.storage_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
                storage_ip = re[0].split("\n")[0]

                ip_info.append(  hostname + ":")
                ip_info.append("     - provisioning ip  : " + provisioning_ip)
                ip_info.append("     - nova private ip  : " + private_api)
                ip_info.append("     - nova public ip   : " + nova_public_ip)
                ip_info.append("     - storage ip       : " + storage_ip)


            cmd = "source ~/stackrc;nova list | grep compute"
            re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

            ip_info.append(  "### Compute  ###" )
            list = re[0].split("\n")
            list.pop()
            for each in list:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]
                cmd = "ssh-keyscan {} >> ~/.ssh/known_hosts".format(provisioning_ip)
                re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+self.settings.private_api_vlanid+".*netmask "+self.settings.private_api_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
                private_api = re[0].split("\n")[0]

                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+self.settings.storage_vlanid+".*netmask "+self.settings.storage_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user,self. settings.director_install_account_pwd,cmd)
                storage_ip = re[0].split("\n")[0]

                ip_info.append( hostname + ":")
                ip_info.append( "     - provisioning ip  : " + provisioning_ip)
                ip_info.append( "     - nova private ip  : " + private_api)
                ip_info.append( "     - storage ip       : " + storage_ip)

            cmd = "source ~/stackrc;nova list | grep storage"
            re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

            ip_info.append ("### Storage  ###")
            list = re[0].split("\n")
            list.pop()
            for each in list:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]
                cmd = "ssh-keyscan {} >> ~/.ssh/known_hosts".format(provisioning_ip)
                re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+self.settings.storage_cluster_vlanid+".*netmask 255.255.255.0.*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
                cluster_ip = re[0].split("\n")[0]

                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+self.settings.storage_vlanid+".*netmask "+self.settings.storage_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
                storage_ip = re[0].split("\n")[0]

                ip_info.append ( hostname + ":")
                ip_info.append ("     - provisioning ip    : " + provisioning_ip)
                ip_info.append( "     - storage cluster ip : " + cluster_ip)
                ip_info.append ("     - storage ip         : " + storage_ip)
            ip_info.append ("====================================")

            try:
                overcloud_endpoint = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,'grep "OS_AUTH_URL=" ~/overcloudrc')[0].split('=')[1].replace(':5000/v2.0/','')
                overcloud_pass = Ssh.execute_command_tty(self.settings.director_node.external_ip,self. settings.director_install_account_user, self.settings.director_install_account_pwd,'grep "OS_PASSWORD=" ~/overcloudrc')[0].split('=')[1]
                ip_info.append("OverCloud Horizon        : " + overcloud_endpoint)
                ip_info.append("OverCloud admin password : " + overcloud_pass)
            except:
                pass
            ip_info.append ("====================================")
            for each in ip_info:
                logger.debug(each)

        except:
                for each in ip_info:
                    logger.debug(each)
                logger.debug(" Failed to retreive the nodes ip information ")

    def run_sanity_test(self):
	if self.settings.run_sanity is True:
	   logger.debug("Running sanity test")
	   remoteSh = "/home/"+self.settings.director_install_account_user+"/sanity_test.sh"
	   Scp.put_file(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd, self.settings.sanity_test, remoteSh)
	   
	   cmd = 'wget http://download.cirros-cloud.net/0.3.3/cirros-0.3.3-x86_64-disk.img'
           logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) )
	   cmd = 'cd ~;chmod ugo+x sanity_test.sh'
           logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) )
	   cmd = 'cd ~; ./sanity_test.sh'
	   re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) 
	   if "VALIDATION SUCCESS" in re[0]:
		logger.info("Sanity Test Passed")
           else:
		logger.fatal("Sanity Test failed")
		raise AssertionError("Sanity test failed - see log for details")	
	else:
	   logger.debug("NOT running sanity test")
	   pass
	
    def run_tempest(self):
	logger.debug("running tempest")
	cmds = [
	     "source ~/overcloudrc;mkdir /home/"+self.settings.director_install_account_user+"/tempest",
             'source ~/overcloudrc;cd ~/tempest;/usr/share/openstack-tempest-liberty/tools/configure-tempest-directory',
             'source ~/overcloudrc;cd ~/tempest;tools/config_tempest.py --deployer-input ~/tempest-deployer-input.conf --debug --create identity.uri $OS_AUTH_URL identity.admin_password $OS_PASSWORD'
	]
	for cmd in cmds :
                Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) 
	if self.settings.tempest_smoke_only is True:
		cmd = "source ~/overcloudrc;cd ~/tempest;tools/run-tests.sh '.*smoke'"
	else :
		cmd =  "source ~/overcloudrc;cd ~/tempest;tools/run-tests.sh"
	Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) 
	Scp.get_file(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,"/auto_results/tempest.xml", "/home/"+self.settings.director_install_account_user+"/tempest/tempest.xml")
	Scp.get_file(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,"/auto_results/tempest.log", "/home/"+self.settings.director_install_account_user+"/tempest/tempest.log")
	logger.debug("Finished running tempest")
    
    def fix_controllers_admin_auth_url(self):
	logger.debug("Workaround for known issue https://bugzilla.redhat.com/show_bug.cgi?id=1308422")
	cmd = "source ~/stackrc;nova list | grep controller"
        re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
	controllers = re[0].split("\n")
        controllers.pop()
        for each in controllers:
		provisioning_ip = each.split("|")[6].split("=")[1]
		cmd = "ssh heat-admin@" + provisioning_ip + " \"sudo sed -i '/^admin_auth_url=/ s/$/\\/v2.0/' /etc/nova/nova.conf\""
		logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) )
		cmd = "ssh heat-admin@" + provisioning_ip + " \"sudo pcs resource restart openstack-nova-api-clone\""
		logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) )


    def fix_controllers_vlan_range(self):
        logger.debug("Workaround for know issue https://bugzilla.redhat.com/show_bug.cgi?id=1282963")
        cmd = "source ~/stackrc;nova list | grep controller"
        re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

        controllers = re[0].split("\n")
        controllers.pop()
        for each in controllers:
            provisioning_ip = each.split("|")[6].split("=")[1]
            cmd = "ssh heat-admin@" + provisioning_ip + " \"sudo sed -i 's/^network_vlan_ranges.*/network_vlan_ranges=physint:"+self.settings.tenant_vlan_range+",physext/' /etc/neutron/plugin.ini\""
            logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) )
        
	    cmds = [
		'sudo systemctl restart neutron-dhcp-agent.service',
		'sudo systemctl restart neutron-l3-agent.service',
		'sudo systemctl restart neutron-metadata-agent.service',
		'sudo systemctl restart neutron-openvswitch-agent.service',
		'sudo systemctl restart neutron-server.service'
		]
	    for cmd in cmds :
		cmd = "ssh heat-admin@" + provisioning_ip + " \" " + cmd + "\""
		logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) )

	cmd = "source ~/stackrc;nova list | grep compute"
        re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

        computes = re[0].split("\n")
        computes.pop()
        for each in computes:
            provisioning_ip = each.split("|")[6].split("=")[1]
	    cmds = [
               	   'sudo systemctl restart neutron-openvswitch-agent.service'
                 ]
            for cmd in cmds :
                cmd = "ssh heat-admin@" + provisioning_ip + " \" " + cmd + "\""
                logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) )   

    def fix_cinder_conf(self):
	logger.debug(" Workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1272572")
        cmd = "source ~/stackrc;nova list | grep controller"
        re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)

        controllers = re[0].split("\n")
        controllers.pop()
        for each in controllers:
            provisioning_ip = each.split("|")[6].split("=")[1]
            cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*\."+self.settings.private_api_vlanid+"\..*netmask "+self.settings.private_api_netmask+".*\" | awk '{print $2}'"
            re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
            private_api = re[0].split("\n")[0].rstrip()

            cmds = [
		" ssh heat-admin@" + provisioning_ip + " \"sudo sh -c 'echo \\\"[keymgr]\\\" >> /etc/cinder/cinder.conf'\"",
		" ssh heat-admin@" + provisioning_ip + " \"sudo sh -c 'echo \\\"encryption_auth_url=http://"+ private_api +":5000/v3\\\" >> /etc/cinder/cinder.conf'\""
		]
	    for cmd in cmds:	
		logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) )
	    
            cmds = [
                'sudo systemctl restart openstack-cinder-api.service',
                'sudo systemctl restart openstack-cinder-scheduler.service',
                'sudo systemctl restart openstack-cinder-volume.service'
                ]
            for cmd in cmds :
                cmd = "ssh heat-admin@" + provisioning_ip + " \" " + cmd + "\""
                logger.debug( Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd) )


