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
from auto_common import Ssh, Scp,  Widget, UI_Manager, FileHelper
import sys, logging, threading, time, shutil, os
logger = logging.getLogger(__name__)


exitFlag = 0


class Sah():
    '''
    '''


    def __init__(self):
        self.settings = Settings.settings


    def update_kickstart(self):

        shutil.copyfile(self.settings.sah_ks , self.settings.sah_kickstart)
        FileHelper.replaceExpression(self.settings.sah_kickstart, "^cdrom",'url --url='+self.settings.rhel_install_location )
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^url --url=.*','url --url='+self.settings.rhel_install_location )
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^HostName=.*','HostName="'+self.settings.sah_node.hostname + "." + self.settings.domain + '"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^SystemPassword=.*','SystemPassword="'+self.settings.sah_node.root_password +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^SubscriptionManagerUser=.*','SubscriptionManagerUser="'+self.settings.subscription_manager_user +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^SubscriptionManagerPassword=.*','SubscriptionManagerPassword="'+self.settings.subscription_manager_password +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^SubscriptionManagerPool=.*','SubscriptionManagerPool="'+ self.settings.subscription_manager_pool_sah +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^Gateway=.*','Gateway="'+self.settings.public_gateway +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^NameServers=.*','NameServers="'+self.settings.name_server +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^NTPServers=.*','NTPServers="'+self.settings.ntp_server +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^TimeZone=.*','TimeZone="'+self.settings.time_zone +'"')

        FileHelper.replaceExpression(self.settings.sah_kickstart, '^anaconda_interface=.*','anaconda_interface="'+self.settings.sah_node.anaconda_ip+ '/'+ self.settings.external_netmask+' '+self.settings.sah_node.anaconda_iface+' no"')

        FileHelper.replaceExpression(self.settings.sah_kickstart, '^extern_bond_name=.*','extern_bond_name="'+self.settings.sah_node.external_bond +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^extern_ifaces=.*','extern_ifaces="'+self.settings.sah_node.external_slaves +'"')

        FileHelper.replaceExpression(self.settings.sah_kickstart, '^internal_bond_name=.*','internal_bond_name="'+self.settings.sah_node.private_bond +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^internal_ifaces=.*','internal_ifaces="'+self.settings.sah_node.private_slaves +'"')

        FileHelper.replaceExpression(self.settings.sah_kickstart, '^prov_bond_name=.*','prov_bond_name=bond0."'+self.settings.provisioning_vlanid +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^stor_bond_name=.*','stor_bond_name=bond0."'+self.settings.storage_vlanid +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^mgmt_bond_name=.*','mgmt_bond_name=bond0."'+self.settings.managment_vlanid +'"')

        FileHelper.replaceExpression(self.settings.sah_kickstart, '^pub_api_bond_name=.*','pub_api_bond_name=bond0."'+self.settings.public_api_vlanid +'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^priv_api_bond_name=.*','priv_api_bond_name=bond0."'+self.settings.private_api_vlanid +'"')

        FileHelper.replaceExpression(self.settings.sah_kickstart, '^br_extern_boot_opts=.*','br_extern_boot_opts="onboot static '+self.settings.sah_node.external_ip + '/'+ self.settings.external_netmask+'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^br_prov_boot_opts=.*','br_prov_boot_opts="onboot static '+self.settings.sah_node.provisioning_ip+ '/'+ self.settings.provisioning_netmask+'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^br_stor_boot_opts=.*','br_stor_boot_opts="onboot static '+self.settings.sah_node.storage_ip+ '/'+ self.settings.storage_netmask+'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^br_mgmt_boot_opts=.*','br_mgmt_boot_opts="onboot static '+self.settings.sah_node.managment_ip+ '/'+ self.settings.managment_netmask+'"')

        FileHelper.replaceExpression(self.settings.sah_kickstart, '^br_pub_api_boot_opts=.*','br_pub_api_boot_opts="onboot static '+self.settings.sah_node.public_api_ip+ '/'+ self.settings.external_netmask+'"')
        FileHelper.replaceExpression(self.settings.sah_kickstart, '^br_priv_api_boot_opts=.*','br_priv_api_boot_opts="onboot static '+self.settings.sah_node.private_api_ip+ '/'+ self.settings.private_api_netmask+'"')

    def upload_iso(self):
        Scp.put_file( self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, self.settings.rhl72_iso, "/store/data/iso/RHEL7.iso")

    def upload_lock_files(self):
        isLinux = False
        if sys.platform.startswith('linux'):
            isLinux = True
        files  = [
                'ceph_vm.vlock',
                'director_vm.vlock',
                ]
        for file in files :
            if isLinux == False:
                localfile = self.settings.lock_files_dir + "\\" + file
            else:
                localfile = self.settings.lock_files_dir + "/" + file
            remotefile = '/root/' + file
            print localfile + " >> " + remotefile
            Scp.put_file( self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, localfile, remotefile)

    def upload_director_scripts(self):
        remoteSh = "/root/deploy-director-vm.sh";
        Scp.put_file( self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, self.settings.director_deploy_sh, remoteSh);
        cmd = "chmod 777 /root/deploy-director-vm.sh";
        Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, cmd)

    def create_director_vm(self):
        install_admin_user = self.settings.director_install_account_user
        install_admin_password = self.settings.director_install_account_pwd
        remoteSh = "/root/deploy-director-vm.sh";
        directorConf = "/root/director.cfg"
        Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "rm " + directorConf + " -f")
        Conf =  ("rootpassword " + self.settings.director_node.root_password,
                "timezone " + self.settings.time_zone,
                "smuser " + self.settings.subscription_manager_user ,
                "smpassword "+self.settings.subscription_manager_password ,
                "smpool " + self.settings.subscription_manager_pool_vm_rhel ,
                "hostname "+ self.settings.director_node.hostname + "." + self.settings.domain ,
                "gateway " + self.settings.public_gateway ,
                "nameserver " + self.settings.name_server ,
                "ntpserver "+ self.settings.ntp_server ,
                "user " + install_admin_user,
                "password " + install_admin_password,
                "# Iface     IP               NETMASK    " ,
                "eth0        "+ self.settings.director_node.external_ip +"     "+ self.settings.external_netmask ,
                "eth1        "+ self.settings.director_node.provisioning_ip +"    "+ self.settings.provisioning_netmask,
                "eth2        "+ self.settings.director_node.managment_ip +"    "+ self.settings.managment_netmask,
                "eth3        "+ self.settings.director_node.private_api_ip +"    "+ self.settings.private_api_netmask,
                "eth4        "+ self.settings.director_node.public_api_ip +"    "+ self.settings.public_api_netmask,
                 )
        for comd in Conf:
            Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "echo '"+ comd+"' >> "+ directorConf)
        sH = "sh " + remoteSh + " /root/director.cfg /store/data/iso/RHEL7.iso";
        Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, sH)

        logger.info("=== wait for the director vm install to be complete & power it on")
        while (not "shut off" in Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "virsh list --all")[0]):
            logger.info ("...")
            time.sleep(60);
        logger.info ("=== power on the director VM ")
        Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "virsh start director")
        while (not "root" in Ssh.execute_command(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password, "whoami")[0]):
            logger.info ("...")
            time.sleep(30);
        logger.info("director host is up")

    def delete_director_vm(self):
        while "director" in Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "virsh list --all")[0]:
            Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "virsh destroy director")
            time.sleep(20)
            Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "virsh undefine director")
            time.sleep(20)

    def create_ceph_vm(self):
        remoteSh = "/root/deploy-ceph-vm.sh";
        Scp.put_file(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, self.settings.ceph_deploy_sh, remoteSh)

        logger.info("=== create ceph.cfg")
        cephConf = "/root/ceph.cfg"
        Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "rm " + cephConf + " -f")
        Conf =  ("rootpassword " + self.settings.ceph_node.root_password,
                "timezone " + self.settings.time_zone,
                "smuser " + self.settings.subscription_manager_user ,
                "smpassword "+self.settings.subscription_manager_password ,
                "smpool " + self.settings.subscription_manager_vm_ceph ,
                "hostname "+ self.settings.ceph_node.hostname + "." + self.settings.domain ,
                "gateway " + self.settings.public_gateway ,
                "nameserver " + self.settings.name_server ,
                "ntpserver "+ self.settings.ntp_server ,
                "# Iface     IP               NETMASK    " ,
                "eth0        "+ self.settings.ceph_node.external_ip +"     "+ self.settings.external_netmask ,
                "eth1        "+ self.settings.ceph_node.storage_ip +"    "+ self.settings.storage_netmask,
                )
        for comd in Conf:
            Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "echo '"+ comd+"' >> "+ cephConf)
        logger.info("=== kick off the ceph vm deployment")
        sH = "sh " + remoteSh + " /root/ceph.cfg /store/data/iso/RHEL7.iso";
        logger.info( Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, sH))

        logger.info("=== wait for the ceph vm install to be complete & power it on")
        while (not "shut off" in Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "virsh list --all")[0]):
            logger.info ("...")
            time.sleep(60)
        logger.info ("=== power on the ceph VM ")
        Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "virsh start ceph")
        while (not "root" in Ssh.execute_command(self.settings.ceph_node.external_ip, "root", self.settings.ceph_node.root_password, "whoami")[0]):
            logger.info ("...")
            time.sleep(30);
        logger.info("ceph host is up")

    def delete_ceph_vm(self):
        if "ceph" in Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "virsh list --all")[0]:
            Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "virsh destroy ceph")
            time.sleep(20)
            Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "virsh undefine ceph")
            time.sleep(20)
