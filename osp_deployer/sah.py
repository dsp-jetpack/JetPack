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
# GNU General Public License for more details.,
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.

from osp_deployer.config import Settings
from infra_host import InfraHost
from auto_common import Scp, FileHelper
import logging
import time
import shutil

logger = logging.getLogger("osp_deployer")

exitFlag = 0


class Sah(InfraHost):

    def __init__(self):

        self.settings = Settings.settings
        self.user = "root"
        self.ip = self.settings.sah_node.external_ip
        self.pwd = self.settings.sah_node.root_password
        self.root_pwd = self.settings.sah_node.root_password

    def update_kickstart(self):
        sets = self.settings
        shutil.copyfile(sets.sah_ks, sets.sah_kickstart)
        FileHelper.replace_expression(sets.sah_kickstart,
                                      "^cdrom",
                                      'url --url=' +
                                      sets.rhel_install_location)
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^url --url=.*',
                                      'url --url=' +
                                      sets.rhel_install_location)
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^HostName=.*',
                                      'HostName="' +
                                      sets.sah_node.hostname +
                                      "." + sets.domain + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^SystemPassword=.*',
                                      'SystemPassword="' +
                                      sets.sah_node.root_password +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^SubscriptionManagerUser=.*',
                                      'SubscriptionManagerUser="' +
                                      sets.subscription_manager_user +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^SubscriptionManagerPassword=.*',
                                      'SubscriptionManagerPassword="' +
                                      sets.subscription_manager_password +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^SubscriptionManagerPool=.*',
                                      'SubscriptionManagerPool="' +
                                      sets.subscription_manager_pool_sah +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^Gateway=.*',
                                      'Gateway="' +
                                      sets.public_gateway +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^NameServers=.*',
                                      'NameServers="' +
                                      sets.name_server +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^NTPServers=.*',
                                      'NTPServers="' +
                                      sets.ntp_server +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^TimeZone=.*',
                                      'TimeZone="' +
                                      sets.time_zone +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^anaconda_interface=.*',
                                      'anaconda_interface="' +
                                      sets.sah_node.anaconda_ip + '/' +
                                      sets.external_netmask + ' ' +
                                      sets.sah_node.anaconda_iface +
                                      ' no"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^extern_bond_name=.*',
                                      'extern_bond_name="' +
                                      sets.sah_node.external_bond +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^extern_ifaces=.*',
                                      'extern_ifaces="' +
                                      sets.sah_node.external_slaves +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^internal_bond_name=.*',
                                      'internal_bond_name="' +
                                      sets.sah_node.private_bond +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^internal_ifaces=.*',
                                      'internal_ifaces="' +
                                      sets.sah_node.private_slaves +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^prov_bond_name=.*',
                                      'prov_bond_name=bond0."' +
                                      sets.provisioning_vlanid +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^stor_bond_name=.*',
                                      'stor_bond_name=bond0."' +
                                      sets.storage_vlanid + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^mgmt_bond_name=.*',
                                      'mgmt_bond_name=bond0."' +
                                      sets.managment_vlanid + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^pub_api_bond_name=.*',
                                      'pub_api_bond_name=bond0."' +
                                      sets.public_api_vlanid + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^priv_api_bond_name=.*',
                                      'priv_api_bond_name=bond0."' +
                                      sets.private_api_vlanid + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_extern_boot_opts=.*',
                                      'br_extern_boot_opts="onboot static ' +
                                      sets.sah_node.external_ip + '/' +
                                      sets.external_netmask + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_prov_boot_opts=.*',
                                      'br_prov_boot_opts="onboot static ' +
                                      sets.sah_node.provisioning_ip + '/' +
                                      sets.provisioning_netmask + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_stor_boot_opts=.*',
                                      'br_stor_boot_opts="onboot static ' +
                                      sets.sah_node.storage_ip + '/' +
                                      sets.storage_netmask + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_mgmt_boot_opts=.*',
                                      'br_mgmt_boot_opts="onboot static ' +
                                      sets.sah_node.managment_ip + '/' +
                                      sets.managment_netmask + '"')

        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_pub_api_boot_opts=.*',
                                      'br_pub_api_boot_opts="onboot static ' +
                                      sets.sah_node.public_api_ip + '/' +
                                      sets.external_netmask + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_priv_api_boot_opts=.*',
                                      'br_priv_api_boot_opts="onboot static ' +
                                      sets.sah_node.private_api_ip + '/' +
                                      sets.private_api_netmask + '"')

    def upload_iso(self):
        self.upload_file(self.settings.rhl72_iso,
                         "/store/data/iso/RHEL7.iso")

    def upload_lock_files(self):

        files = [
            'ceph_vm.vlock',
            'director_vm.vlock',
        ]
        for eachone in files:
            localfile = self.settings.lock_files_dir + "/" + eachone
            remotefile = '/root/' + eachone
            Scp.put_file(self.settings.sah_node.external_ip,
                         "root",
                         self.settings.sah_node.root_password,
                         localfile,
                         remotefile)

    def upload_director_scripts(self):
        remote_file = "/root/deploy-director-vm.sh"
        self.upload_file(self.settings.director_deploy_sh,
                         remote_file)
        self.run("chmod 777 /root/deploy-director-vm.sh")

    def create_director_vm(self):
        director_conf = "/root/director.cfg"
        self.run("rm " + director_conf + " -f")
        conf = ("rootpassword " + self.settings.director_node.root_password,
                "timezone " + self.settings.time_zone,
                "smuser " + self.settings.subscription_manager_user,
                "smpassword " + self.settings.subscription_manager_password,
                "smpool " + self.settings.subscription_manager_pool_vm_rhel,
                "hostname " + self.settings.director_node.hostname + "." +
                self.settings.domain,
                "gateway " + self.settings.public_gateway,
                "nameserver " + self.settings.name_server,
                "ntpserver " + self.settings.ntp_server,
                "user " + self.settings.director_install_account_user,
                "password " + self.settings.director_install_account_pwd,
                "# Iface     IP               NETMASK    ",
                "eth0        " + self.settings.director_node.external_ip +
                "     " + self.settings.external_netmask,
                "eth1        " + self.settings.director_node.provisioning_ip +
                "    " + self.settings.provisioning_netmask,
                "eth2        " + self.settings.director_node.managment_ip +
                "    " + self.settings.managment_netmask,
                "eth3        " + self.settings.director_node.private_api_ip +
                "    " + self.settings.private_api_netmask,
                "eth4        " + self.settings.director_node.public_api_ip +
                "    " + self.settings.public_api_netmask
                )
        for line in conf:
            self.run("echo '" +
                     line +
                     "' >> " +
                     director_conf)
        remote_file = "sh /root/deploy-director-vm.sh " + \
                      director_conf + \
                      " /store/data/iso/RHEL7.iso"
        self.run(remote_file)

        logger.debug(
            "=== wait for the director vm install "
            "to be complete & power it on")
        while "shut off" not in \
                self.run("virsh list --all | grep director")[0]:
            time.sleep(60)
        logger.debug("=== power on the director VM ")
        self.run("virsh start director")
        while "root" not in \
                self.run("whoami")[0]:
            time.sleep(30)
        logger.debug("director host is up")

    def delete_director_vm(self):
        while "director" in \
                self.run("virsh list --all | grep director")[0]:
            self.run("virsh destroy director")
            time.sleep(20)
            self.run("virsh undefine director")
            time.sleep(20)

    def create_ceph_vm(self):
        remote_file = "/root/deploy-ceph-vm.sh"
        self.upload_file(self.settings.ceph_deploy_sh,
                         remote_file)

        logger.debug("=== create ceph.cfg")
        ceph_conf = "/root/ceph.cfg"
        self.run("rm " + ceph_conf + " -f")
        conf = ("rootpassword " + self.settings.ceph_node.root_password,
                "timezone " + self.settings.time_zone,
                "smuser " + self.settings.subscription_manager_user,
                "smpassword " + self.settings.subscription_manager_password,
                "smpool " + self.settings.subscription_manager_vm_ceph,
                "hostname " + self.settings.ceph_node.hostname + "." +
                self.settings.domain,
                "gateway " + self.settings.public_gateway,
                "nameserver " + self.settings.name_server,
                "ntpserver " + self.settings.ntp_server,
                "# Iface     IP               NETMASK    ",
                "eth0        " + self.settings.ceph_node.external_ip +
                "     " + self.settings.external_netmask,
                "eth1        " + self.settings.ceph_node.storage_ip +
                "    " + self.settings.storage_netmask,
                )
        for comd in conf:
            self.run("echo '" + comd + "' >> " + ceph_conf)
        logger.debug("=== kick off the ceph vm deployment")

        self.run("sh " +
                 remote_file +
                 " /root/ceph.cfg /store/data/iso/RHEL7.iso")

        logger.debug(
            "=== wait for the ceph vm install to be complete & power it on")
        while "shut off" not in \
                self.run("virsh list --all | grep ceph")[0]:
            time.sleep(60)
        logger.debug("=== power on the ceph VM ")
        self.run("virsh start ceph")
        while "root" not in \
                self.run("whoami")[0]:
            time.sleep(30)
        logger.debug("ceph host is up")

    def delete_ceph_vm(self):
        if "ceph" in \
                self.run("virsh list --all | grep ceph")[0]:
            self.run("virsh destroy ceph")
            time.sleep(20)
            self.run("virsh undefine ceph")
            time.sleep(20)
