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

from osp_deployer.settings.config import Settings
from infra_host import InfraHost
from auto_common import Scp, FileHelper
import logging
import time
import shutil
import os 

logger = logging.getLogger("osp_deployer")

exitFlag = 0


class Sah(InfraHost):

    def __init__(self):

        self.settings = Settings.settings
        self.user = "root"
        self.ip = self.settings.sah_node.public_api_ip
        self.pwd = self.settings.sah_node.root_password
        self.root_pwd = self.settings.sah_node.root_password

    def update_kickstart_usb(self):
        sets = self.settings
        shutil.copyfile(sets.sah_kickstart, sets.cloud_repo_dir +
                        "/../osp-sah.ks")
        sets.sah_kickstart = sets.cloud_repo_dir + "/../osp-sah.ks"

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
                                      sets.public_api_gateway +
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
                                      sets.public_api_netmask + ' ' +
                                      sets.sah_node.anaconda_iface +
                                      ' no"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^anaconda_vlanid=.*',
                                      'anaconda_vlanid="' +
                                      sets.public_api_vlanid +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^extern_bond_name=.*',
                                      'extern_bond_name="' +
                                      sets.sah_node.public_bond +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^extern_ifaces=.*',
                                      'extern_ifaces="' +
                                      sets.sah_node.public_slaves +
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
                                      'prov_bond_name="bond0.' +
                                      sets.provisioning_vlanid +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^stor_bond_name=.*',
                                      'stor_bond_name="bond0.' +
                                      sets.storage_vlanid + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^mgmt_bond_name=.*',
                                      'mgmt_bond_name="bond0.' +
                                      sets.management_vlanid + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^pub_api_bond_name=.*',
                                      'pub_api_bond_name="bond1.' +
                                      sets.public_api_vlanid + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^priv_api_bond_name=.*',
                                      'priv_api_bond_name="bond0.' +
                                      sets.private_api_vlanid + '"')
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
                                      sets.sah_node.management_ip + '/' +
                                      sets.management_netmask + '"')

        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_pub_api_boot_opts=.*',
                                      'br_pub_api_boot_opts="onboot static ' +
                                      sets.sah_node.public_api_ip + '/' +
                                      sets.public_api_netmask + '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_priv_api_boot_opts=.*',
                                      'br_priv_api_boot_opts="onboot static ' +
                                      sets.sah_node.private_api_ip + '/' +
                                      sets.private_api_netmask + '"')
        time.sleep(3)
        if self.settings.is_fx is True:
            cmds = ["sed -i 's/{AnacondaIface_device}/{AnacondaIface_device}." +
                    self.settings.public_api_vlanid +
                    "/' " + sets.sah_kickstart,
                    "sed -i 's/bootproto=static/vlanid=" +
                    self.settings.public_api_vlanid + " --bootproto=static/' " + sets.sah_kickstart]
            for cmd in cmds:
                os.system(cmd)

    def upload_iso(self):
        shutil.copyfile(self.settings.rhel_iso,
                        "/store/data/iso/RHEL7.iso")

    def handle_lock_files(self):
        files = [
            'rhscon_vm.vlock',
            'director_vm.vlock',
        ]

        # Delete any staged locking files to prevent accidental reuse
        for eachone in files:
            staged_file_name = '/root/' + eachone
            if os.path.isfile(staged_file_name):
                os.remove(staged_file_name)

        if self.settings.version_locking_enabled is True:
            logger.debug(
                "Uploading version locking files for director & rhscon VMs")

            for eachone in files:
                source_file_name = self.settings.lock_files_dir + "/" + eachone
                dest_file_name = '/root/' + eachone
                shutil.copyfile(source_file_name, dest_file_name)

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
                "gateway " + self.settings.public_api_gateway,
                "nameserver " + self.settings.name_server,
                "ntpserver " + self.settings.ntp_server,
                "user " + self.settings.director_install_account_user,
                "password " + self.settings.director_install_account_pwd,
                "# Iface     IP               NETMASK    ",)
        conf = conf + ("eth0        " +
                       self.settings.director_node.public_api_ip +
                       "    " + self.settings.public_api_netmask,)
        conf = conf + ("eth1        " +
                       self.settings.director_node.provisioning_ip +
                       "    " + self.settings.provisioning_netmask,)
        conf = conf + ("eth2        " +
                       self.settings.director_node.management_ip +
                       "    " + self.settings.management_netmask,)
        conf = conf + ("eth3        " +
                       self.settings.director_node.private_api_ip +
                       "    " + self.settings.private_api_netmask,)

        for line in conf:
            self.run("echo '" +
                     line +
                     "' >> " +
                     director_conf)
        remote_file = "sh /root/deploy-director-vm.sh " + \
                      director_conf + " " + \
                      "/store/data/iso/RHEL7.iso"
        re = self.run_tty(remote_file)
        startVM = True
        for ln in re[0].split("\n"):
            if "Restarting guest" in ln:
                startVM = False
        if startVM:
            logger.debug(
                "=== wait for the director vm install "
                "to be complete")
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

    def create_rhscon_vm(self):
        remote_file = "/root/deploy-rhscon-vm.py"
        self.upload_file(self.settings.rhscon_deploy_py,
                         remote_file)

        logger.debug("=== create rhscon.cfg")
        rhscon_conf = "/root/rhscon.cfg"
        self.run("rm " + rhscon_conf + " -f")
        conf = ("rootpassword " + self.settings.rhscon_node.root_password,
                "timezone " + self.settings.time_zone,
                "smuser " + self.settings.subscription_manager_user,
                "smpassword " + self.settings.subscription_manager_password,
                "smpool " + self.settings.subscription_manager_vm_ceph,
                "hostname " + self.settings.rhscon_node.hostname + "." +
                self.settings.domain,
                "gateway " + self.settings.public_api_gateway,
                "nameserver " + self.settings.name_server,
                "ntpserver " + self.settings.ntp_server,
                "# Iface     IP               NETMASK    ",)
        conf = conf + ("eth0        " +
                       self.settings.rhscon_node.public_api_ip +
                       "    " + self.settings.public_api_netmask,)
        conf = conf + ("eth1        " +
                       self.settings.rhscon_node.storage_ip +
                       "    " + self.settings.storage_netmask,)

        for comd in conf:
            self.run("echo '" + comd + "' >> " + rhscon_conf)
        logger.debug("=== kick off the Storage Console VM deployment")

        re = self.run_tty("python " +
                          remote_file +
                          " /root/rhscon.cfg " +
                          "/store/data/iso/RHEL7.iso")
        startVM = True
        for ln in re[0].split("\n"):
            if "Restarting guest" in ln:
                startVM = False
        if startVM:
            logger.debug(
                "=== wait for the Storage Console VM install to be complete \
                & power it on")
            while "shut off" \
                  not in self.run("virsh list --all | grep rhscon")[0]:
                time.sleep(60)
            logger.debug("=== power on the Storage Console VM ")
            self.run("virsh start rhscon")
        while "root" not in \
                self.run("whoami")[0]:
            time.sleep(40)
        logger.debug("Storage Console VM is up")

    def delete_rhscon_vm(self):
        # Also delete any leftover "ceph" VM so that it cannot interfere
        # with the new "rhscon" VM that replaces it.
        for vm in "ceph", "rhscon":
            if vm in self.run("virsh list --all | grep {}".format(vm))[0]:
                if vm == "ceph":
                    logger.info("=== deleting deprecated ceph VM")

                if "running" in self.run("virsh domstate {}".format(vm))[0]:
                    self.run("virsh destroy {}".format(vm))
                    time.sleep(20)

                self.run("virsh undefine {}".format(vm))
                time.sleep(20)
