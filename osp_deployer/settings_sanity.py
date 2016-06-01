#!/usr/bin/env python

# (c) 2015-2016 Dell
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

from auto_common import Ipmi
from osp_deployer import Settings
import sys
import subprocess
import logging
import os.path
import urllib2
import socket


logger = logging.getLogger("osp_deployer")


class DeployerSanity():
    def __init__(self):
        self.settings = Settings.settings

    @staticmethod
    def is_valid_ip(address):
        try:
            socket.inet_aton(address)
            ip = True
        except socket.error:
            ip = False

        return ip

    def check_files(self):

        logger.debug("Check settings ip's are valid.")
        shouldbbevalidips = [
            'external_netmask', 'public_api_gateway', 'public_api_gateway',
            'public_api_netmask', 'public_api_allocation_pool_start',
            'public_api_allocation_pool_end',
            'private_api_vlanid', 'private_api_netmask',
            'private_api_allocation_pool_start',
            'private_api_allocation_pool_end',
            'storage_netmask', 'storage_allocation_pool_start',
            'storage_allocation_pool_end',
            'provisioning_netmask', 'provisioning_net_dhcp_start',
            'provisioning_net_dhcp_end', 'provisioning_gateway',
            'storage_cluster_allocation_pool_start',
            'storage_cluster_allocation_pool_end',
            'managment_netmask', 'name_server',
        ]
        for ip in getattr(self.settings, 'discovery_ip_range').split(","):
            self.is_valid_ip(ip),\
                "Setting for discovery_ip_range " + \
                ip + " is not a valid ip "
        for each in shouldbbevalidips:
            assert self.is_valid_ip(getattr(self.settings, each)),\
                "Setting for " + each + " is not a valid ip " +\
                getattr(self.settings, each)

        assert os.path.isfile(
            self.settings.rhl72_iso), \
            self.settings.rhl72_iso + \
            "ISO doesn't seem to exist"
        assert os.path.isfile(
            self.settings.director_deploy_sh), \
            self.settings.director_deploy_sh + \
            " script doesn't seem to exist"
        assert os.path.isfile(
            self.settings.undercloud_conf), \
            self.settings.undercloud_conf + \
            " file doesn't seem to exist"
        if self.settings.use_custom_instack_json is True:
            assert os.path.isfile(
                self.settings.custom_instack_json),\
                self.settings.custom_instack_json + \
                " file doesn't seem to exist"
        if self.settings.pull_images_from_cnd is False:
            assert os.path.isfile(
                self.settings.discovery_ram_disk_image),\
                self.settings.discovery_ram_disk_image +\
                " file doesn't seem to exist"
            assert os.path.isfile(
                self.settings.overcloud_image), \
                self.settings.overcloud_image + \
                " file doesn't seem to exist"
        assert os.path.isfile(
            self.settings.install_director_sh), \
            self.settings.install_director_sh +\
            " file doesn't seem to exist"

        try:
            urllib2.urlopen(
                self.settings.rhel_install_location + "/EULA").read()
        except:
            raise AssertionError(
                                 self.settings.rhel_install_location +
                                 "/EULA is not reachable")
        subprocess.check_output("service tftp stop",
                                stderr=subprocess.STDOUT,
                                shell=True)

    def check_ipmi_to_nodes(self):
        hdw_nodes = (self.settings.controller_nodes +
                     self.settings.compute_nodes +
                     self.settings.ceph_nodes)

        hdw_nodes.append(self.settings.sah_node)
        for node in hdw_nodes:
            try:
                logger.debug(node.idrac_ip)
                ipmi_session = Ipmi(self.settings.cygwin_installdir,
                                    self.settings.ipmi_user,
                                    self.settings.ipmi_password,
                                    node.idrac_ip)
                logger.debug(
                    node.hostname + " :: " + ipmi_session.get_power_state())
            except:
                raise AssertionError("Could not impi to host " + node.hostname)

    def check_network_settings(self):
        #

        # Verify SAH node network definition
        logger.debug("verifying sah network settings")
        shouldhaveattributes = ['hostname', 'idrac_ip', 'root_password',
                                'anaconda_ip', 'anaconda_iface',
                                'external_bond', 'external_slaves',
                                'external_ip',
                                'private_bond', 'private_slaves',
                                'provisioning_ip', 'storage_ip',
                                'public_api_ip', 'private_api_ip',
                                'managment_ip']
        for each in shouldhaveattributes:
            assert hasattr(self.settings.sah_node, each),\
                self.settings.network_conf + \
                " SAH node has no " + each + " attribute"

        shouldbbevalidips = ['idrac_ip', 'anaconda_ip', 'external_ip',
                             'provisioning_ip', 'storage_ip', 'public_api_ip',
                             'private_api_ip', 'managment_ip']
        for each in shouldbbevalidips:
            assert self.is_valid_ip(getattr(self.settings.sah_node,
                                            each)), "SAH node " + each \
                                                    + " is not a valid ip"

        # Verify director network definition
        logger.debug("verifying director vm network settings")
        shouldhaveattributes = ['hostname', 'root_password', 'external_ip',
                                'provisioning_ip',
                                'managment_ip', 'public_api_ip',
                                'private_api_ip']
        for each in shouldhaveattributes:
            assert hasattr(self.settings.director_node, each),\
                self.settings.network_conf \
                + " director node has no " + each + " attribute"
            shouldbbevalidips = ['external_ip', 'provisioning_ip',
                                 'managment_ip', 'public_api_ip',
                                 'private_api_ip']
        for each in shouldbbevalidips:
            assert self.is_valid_ip(
                getattr(self.settings.director_node, each)), \
                "director_node node " + each + " is not a valid ip"

        # Verify Ceph vm node network definition
        logger.debug("verifying ceph vm network settings")
        shouldhaveattributes = ['hostname', 'root_password', 'external_ip',
                                'storage_ip']
        for each in shouldhaveattributes:
            assert hasattr(self.settings.ceph_node, each), \
                self.settings.network_conf + " Ceph Vm node has no " +\
                each + " attribute"
        shouldbbevalidips = ['external_ip', 'storage_ip']
        for each in shouldbbevalidips:
            assert hasattr(self.settings.ceph_node, each), \
                self.settings.network_conf +\
                " Ceph Vm node has no " + each + " attribute"
        # Verify Controller nodes network definitioncls
        logger.debug("verifying controller nodes network settings")
        for controller in self.settings.controller_nodes:
            shouldhaveattributes = ['hostname', 'idrac_ip',
                                    'provisioning_mac_address']
            for each in shouldhaveattributes:
                assert hasattr(controller, each), \
                    controller.hostname + " node has no " + each + " attribute"
                shouldbbevalidips = ['idrac_ip']
            for each in shouldbbevalidips:
                assert self.is_valid_ip(
                    getattr(controller, each)), \
                    controller.hostname +\
                    " node " + each + " is not a valid ip"

        # Verify Compute nodes network definition
        logger.debug("verifying compute nodes network settings")
        for compute in self.settings.compute_nodes:
            shouldhaveattributes = ['hostname', 'idrac_ip',
                                    'provisioning_mac_address']
            for each in shouldhaveattributes:
                assert hasattr(compute, each), \
                    compute.hostname + \
                    " node has no " + each + " attribute"
            shouldbbevalidips = ['idrac_ip']
            for each in shouldbbevalidips:
                assert self.is_valid_ip(
                    getattr(compute, each)), \
                    compute.hostname + " node " \
                    + each + " is not a valid ip"

        # Verify Storage nodes network definition
        logger.debug("verifying storage nodes network settings")
        for storage in self.settings.ceph_nodes:
            shouldhaveattributes = ['hostname', 'idrac_ip',
                                    'provisioning_mac_address', 'osd_disks']
            for each in shouldhaveattributes:
                assert hasattr(storage, each),\
                    storage.hostname +\
                    " node has no " + each + " attribute"
                shouldbbevalidips = ['idrac_ip', ]
            for each in shouldbbevalidips:
                assert self.is_valid_ip(
                    getattr(storage, each)),\
                    storage.hostname + " node " +\
                    each + " is not a valid ip"
