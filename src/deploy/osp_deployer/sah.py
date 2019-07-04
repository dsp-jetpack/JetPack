#!/usr/bin/env python

# Copyright (c) 2015-2019 Dell Inc. or its subsidiaries.
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
from osp_deployer.checkpoints import Checkpoints
from infra_host import InfraHost
from auto_common import Scp, Ssh, FileHelper
import logging
import time
import shutil
import os
import subprocess

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
        tester = Checkpoints()
        tester.verify_deployer_settings()
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
                                      '^extern_bond_name=.*',
                                      'extern_bond_name="' +
                                      sets.sah_node.public_bond +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^extern_bond_opts=.*',
                                      'extern_bond_opts="' +
                                      sets.sah_bond_opts +
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
                                      '^internal_bond_opts=.*',
                                      'internal_bond_opts="' +
                                      sets.sah_bond_opts +
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
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^prov_network=.*',
                                      'prov_network="' +
                                      sets.provisioning_network.split("/")[0] +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^prov_netmask=.*',
                                      'prov_netmask="' +
                                      sets.provisioning_netmask +
                                      '"')
        # mtu_settings
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^extern_bond_mtu=.*',
                                      'extern_bond_mtu="' +
                                      sets.default_bond_mtu +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^internal_bond_mtu=.*',
                                      'internal_bond_mtu="' +
                                      sets.default_bond_mtu +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^mgmt_bond_mtu=.*',
                                      'mgmt_bond_mtu="' +
                                      sets.management_network_mtu +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_mgmt_mtu=.*',
                                      'br_mgmt_mtu="' +
                                      sets.management_network_mtu +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^prov_bond_mtu=.*',
                                      'prov_bond_mtu="' +
                                      sets.provisioning_network_mtu +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_prov_mtu=.*',
                                      'br_prov_mtu="' +
                                      sets.provisioning_network_mtu +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^stor_bond_mtu=.*',
                                      'stor_bond_mtu="' +
                                      sets.storage_network_mtu +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_stor_mtu=.*',
                                      'br_stor_mtu="' +
                                      sets.storage_network_mtu +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_pub_api_mtu=.*',
                                      'br_pub_api_mtu="' +
                                      sets.public_api_network_mtu +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^pub_api_bond_mtu=.*',
                                      'pub_api_bond_mtu="' +
                                      sets.public_api_network_mtu +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^priv_api_bond_mtu=.*',
                                      'priv_api_bond_mtu="' +
                                      sets.private_api_network_mtu +
                                      '"')
        FileHelper.replace_expression(sets.sah_kickstart,
                                      '^br_priv_api_mtu=.*',
                                      'br_priv_api_mtu="' +
                                      sets.private_api_network_mtu +
                                      '"')

        if sets.use_satellite is True:
            FileHelper.replace_expression(sets.sah_kickstart,
                                          '^SatelliteHostname=.*',
                                          'SatelliteHostname="' +
                                          sets.satellite_hostname +
                                          '"')
            FileHelper.replace_expression(sets.sah_kickstart,
                                          '^SatelliteIp=.*',
                                          'SatelliteIp="' +
                                          sets.satellite_ip +
                                          '"')
            FileHelper.replace_expression(sets.sah_kickstart,
                                          '^SatelliteOrganization=.*',
                                          'SatelliteOrganization="' +
                                          sets.satellite_org +
                                          '"')
            FileHelper.replace_expression(sets.sah_kickstart,
                                          '^SatelliteActivationKey=.*',
                                          'SatelliteActivationKey="' +
                                          sets.satellite_activation_key +
                                          '"')

        time.sleep(3)

    def upload_iso(self):
        shutil.copyfile(self.settings.rhel_iso,
                        "/store/data/iso/RHEL7.iso")

    def clear_known_hosts(self):
        hosts = [
            self.settings.director_node.public_api_ip,
            self.settings.dashboard_node.public_api_ip
        ]

        if self.is_running_from_sah() is True:
            for host in hosts:
                cmd = 'ssh-keygen -R ' + host
                self.run(cmd)
        else:
            for host in hosts:
                subprocess.check_output('ssh-keygen -R ' + host,
                                        stderr=subprocess.STDOUT,
                                        shell=True)

    def handle_lock_files(self):
        files = [
            'dashboard_vm.vlock',
            'director_vm.vlock',
        ]

        # Delete any staged locking files to prevent accidental reuse
        for eachone in files:
            staged_file_name = '/root/' + eachone
            if self.is_running_from_sah() is False:
                self.run("rm -rf " + staged_file_name)
            else:
                if os.path.isfile(staged_file_name):
                    os.remove(staged_file_name)

        if self.settings.version_locking_enabled is True:
            logger.debug(
                "Uploading version locking files for director & dashboard VMs")

            for eachone in files:
                source_file_name = self.settings.lock_files_dir + "/" + eachone
                dest_file_name = '/root/' + eachone
                self.upload_file(source_file_name, dest_file_name)

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
                "ntpserver " + self.settings.sah_node.provisioning_ip,
                "user " + self.settings.director_install_account_user,
                "password " + self.settings.director_install_account_pwd,)
        if self.settings.use_satellite is True:
            conf = conf + ("satellite_ip " + self.settings.satellite_ip,)
            conf = conf + ("satellite_hostname " +
                           self.settings.satellite_hostname,)
            conf = conf + ("satellite_org " + self.settings.satellite_org,)
            conf = conf + ("satellite_activation_key " +
                           self.settings.satellite_activation_key,)

        conf = conf + ("# Iface     IP" +
                       "               NETMASK" +
                       "              MTU",)
        conf = conf + ("eth0        " +
                       self.settings.director_node.public_api_ip +
                       "    " + self.settings.public_api_netmask +
                       "     " + self.settings.public_api_network_mtu,)
        conf = conf + ("eth1        " +
                       self.settings.director_node.provisioning_ip +
                       "    " + self.settings.provisioning_netmask +
                       "     " + self.settings.provisioning_network_mtu,)
        conf = conf + ("eth2        " +
                       self.settings.director_node.management_ip +
                       "    " + self.settings.management_netmask +
                       "     " + self.settings.management_network_mtu,)
        conf = conf + ("eth3        " +
                       self.settings.director_node.private_api_ip +
                       "    " + self.settings.private_api_netmask +
                       "     " + self.settings.private_api_network_mtu,)

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
        logger.debug("=== waiting for the director vm to boot up")
        self.wait_for_vm_to_come_up(self.settings.director_node.public_api_ip,
                                    "root",
                                    self.settings.director_node.root_password)
        logger.debug("director host is up")

    def wait_for_vm_to_come_up(self, target_ip, user, password):
        while True:
            status = Ssh.execute_command(
                target_ip,
                user,
                password,
                "ps")[0]

            if status != "host not up":
                break

            logger.debug("vm is not up.  Sleeping...")
            time.sleep(10)

    def delete_director_vm(self):
        while "director" in \
                self.run("virsh list --all | grep director")[0]:
            self.run("virsh destroy director")
            time.sleep(20)
            self.run("virsh undefine director")
            time.sleep(20)

    def create_dashboard_vm(self):
        remote_file = "/root/deploy-dashboard-vm.py"
        self.upload_file(self.settings.dashboard_deploy_py,
                         remote_file)

        logger.debug("=== create dashboard.cfg")
        dashboard_conf = "/root/dashboard.cfg"
        self.run("rm " + dashboard_conf + " -f")
        conf = ("rootpassword " + self.settings.dashboard_node.root_password,
                "timezone " + self.settings.time_zone,
                "smuser " + self.settings.subscription_manager_user,
                "smpassword " + self.settings.subscription_manager_password,
                "smpool " + self.settings.subscription_manager_vm_ceph,
                "hostname " + self.settings.dashboard_node.hostname + "." +
                self.settings.domain,
                "gateway " + self.settings.public_api_gateway,
                "nameserver " + self.settings.name_server,
                "ntpserver " + self.settings.sah_node.provisioning_ip,
                "# Iface     IP               NETMASK              MTU",)
        if self.settings.use_satellite is True:
            conf = conf + ("satellite_ip " + self.settings.satellite_ip,)
            conf = conf + ("satellite_hostname " +
                           self.settings.satellite_hostname,)
            conf = conf + ("satellite_org " +
                           self.settings.satellite_org,)
            conf = conf + ("satellite_activation_key " +
                           self.settings.satellite_activation_key,)

        conf = conf + ("eth0        " +
                       self.settings.dashboard_node.public_api_ip +
                       "    " + self.settings.public_api_netmask +
                       "     " + self.settings.public_api_network_mtu,)
        conf = conf + ("eth1        " +
                       self.settings.dashboard_node.storage_ip +
                       "    " + self.settings.storage_netmask +
                       "     " + self.settings.storage_network_mtu,)

        for comd in conf:
            self.run("echo '" + comd + "' >> " + dashboard_conf)
        logger.debug("=== kick off the Dashboard VM deployment")

        re = self.run_tty("python " +
                          remote_file +
                          " /root/dashboard.cfg " +
                          "/store/data/iso/RHEL7.iso")
        startVM = True
        for ln in re[0].split("\n"):
            if "Restarting guest" in ln:
                startVM = False
        if startVM:
            logger.debug(
                "=== wait for the Dashboard VM install to be complete \
                & power it on")
            while "shut off" \
                  not in self.run("virsh list --all | grep dashboard")[0]:
                time.sleep(60)
            logger.debug("=== power on the Dashboard VM ")
            self.run("virsh start dashboard")
        logger.debug("=== waiting for the Dashboard vm to boot up")
        self.wait_for_vm_to_come_up(self.settings.dashboard_node.public_api_ip,
                                    "root",
                                    self.settings.dashboard_node.root_password)
        logger.debug("Dashboard VM is up")

    def delete_dashboard_vm(self):
        # Also delete any leftover "ceph" VM so that it cannot interfere
        # with the new "dashboard" VM that replaces it.
        for vm in "ceph", "dashboard":
            if vm in self.run("virsh list --all | grep {}".format(vm))[0]:
                if vm == "ceph":
                    logger.info("=== deleting deprecated ceph VM")

                if "running" in self.run("virsh domstate {}".format(vm))[0]:
                    self.run("virsh destroy {}".format(vm))
                    time.sleep(20)

                self.run("virsh undefine {}".format(vm))
                time.sleep(20)

    def is_running_from_sah(self):
        # Check whether we're running from the SAH node
        out = subprocess.check_output("ip addr",
                                      stderr=subprocess.STDOUT,
                                      shell=True)

        if self.settings.sah_node.public_api_ip in out:
            return True
        else:
            return False
