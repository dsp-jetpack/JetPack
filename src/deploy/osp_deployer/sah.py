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

from osp_deployer.settings.config import Settings
from osp_deployer.checkpoints import Checkpoints
from .infra_host import InfraHost
from auto_common import Scp, Ssh, FileHelper
from auto_common.constants import *
import logging
import time
import shutil
import os
import subprocess
import re

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
                        "/store/data/iso/RHEL8.iso")

    def clear_known_hosts(self):
        hosts = [
            self.settings.director_node.public_api_ip
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
            'director_vm.vlock'
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
                "Uploading version locking files for the director VM")

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

        conf = conf + ("# Iface     IP"
                       + "               NETMASK"
                       + "              MTU",)
        conf = conf + (PUBLIC_API_IF
                       + "        "
                       + self.settings.director_node.public_api_ip
                       + "    " + self.settings.public_api_netmask
                       + "     " + self.settings.public_api_network_mtu,)
        conf = conf + (PROVISIONING_IF
                       + "        "
                       + self.settings.director_node.provisioning_ip
                       + "    " + self.settings.provisioning_netmask
                       + "     " + self.settings.provisioning_network_mtu,)
        conf = conf + (MANAGEMENT_IF
                       + "        "
                       + self.settings.director_node.management_ip
                       + "    " + self.settings.management_netmask
                       + "     " + self.settings.management_network_mtu,)
        conf = conf + (PRIVATE_API_IF
                       + "        "
                       + self.settings.director_node.private_api_ip
                       + "    " + self.settings.private_api_netmask
                       + "     " + self.settings.private_api_network_mtu,)

        for line in conf:
            self.run("echo '" +
                     line +
                     "' >> " +
                     director_conf)
        remote_file = "sh /root/deploy-director-vm.sh " + \
                      director_conf + " " + \
                      "/store/data/iso/RHEL8.iso"
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

    def delete_director_vm(self):
        while "director" in \
                self.run("virsh list --all | grep director")[0]:
            self.run("virsh destroy director")
            time.sleep(20)
            self.run("virsh undefine director")
            time.sleep(20)

    def is_running_from_sah(self):
        # Check whether we're running from the SAH node
        out = subprocess.check_output("ip addr",
                                      stderr=subprocess.STDOUT,
                                      shell=True).decode('utf-8')

        if self.settings.sah_node.public_api_ip in out:
            return True
        else:
            return False

    def enable_chrony_ports(self):
        cmds = ["firewall-cmd --permanent --zone=public --add-port=123/udp",
                "sudo firewall-cmd --reload"
               ]
        for cmd in cmds:
            self.run_as_root(cmd)


    def subnet_routes_edge(self, node_type, add=True):
        """
        Example nmcli command:
            nmcli connection modify br-mgmt +ipv4.routes
            "192.168.112.0/24 192.168.110.1"
        """
        logger.info("Adding?: {} route for edge subnet for "
                    "node_type: {}".format(add, node_type))
        setts = self.settings
        node_type_data = setts.node_type_data_map[node_type]
        mgmt_cidr = node_type_data['mgmt_cidr']
        prov_cidr = node_type_data['cidr']
        add_remove = "+" if add else "-"

        mgmt_cmd = NWM_ROUTE_CMD.format(dev=MGMT_BRIDGE,
                                        add_rem=add_remove,
                                        cidr=mgmt_cidr,
                                        gw=setts.management_gateway)
        prov_cmd = NWM_ROUTE_CMD.format(dev=PROV_BRIDGE,
                                        add_rem=add_remove,
                                        cidr=prov_cidr,
                                        gw=setts.provisioning_gateway)
        _is_mgmt_route = self._does_route_exist(mgmt_cidr)
        _is_prov_route = self._does_route_exist(prov_cidr)
        if ((not _is_mgmt_route and add) or (_is_mgmt_route and not add)):
            subprocess.check_output(mgmt_cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            up_cmd = NWM_UP_CMD.format(dev=MGMT_BRIDGE)
            subprocess.check_output(up_cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
        if ((not _is_prov_route and add) or (_is_prov_route and not add)):
            subprocess.check_output(prov_cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
            up_cmd = NWM_UP_CMD.format(dev=PROV_BRIDGE)
            subprocess.check_output(up_cmd,
                                    stderr=subprocess.STDOUT,
                                    shell=True)
        logger.info("Routes for edge site {} "
                    "subnets on SAH updated".format(node_type))

    def get_virsh_interface_map(self):
        '''
        Transform output from:
        virsh -r domiflist director
        Interface  Type       Source     Model       MAC
        -------------------------------------------------------
        vnet0      bridge     br-pub-api virtio      52:54:00:b6:88:f9
        vnet1      bridge     br-prov    virtio      52:54:00:2b:c7:12
        ...
        Return dict with source as key:
        {'br-pub-api': ['vnet0', 'bridge', 'virtio', '52:54:00:b6:88:f9'], ...}
        '''
        if_map = {}
        res = self.run("virsh -r domiflist director")[0]
        lines = res.splitlines()
        del lines[:2]  # delete header rows
        del lines[-1]  # delete trailing empty line
        for line in lines:
            _l_arr = line.split()
            src = _l_arr[2]
            del _l_arr[2]
            if_map[src] = _l_arr
        logger.debug("virsh domain interface "
                     "map for director vm: {}".format(str(if_map)))
