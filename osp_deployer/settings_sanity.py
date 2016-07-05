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
import collections

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
                    " :: " + ipmi_session.get_power_state())
            except:
                raise AssertionError("Could not impi to host " + node.idrac_ip)
    
    def check_network_overlaps(self):
	# Verify the dhcp ranges defined in the ini don't overlap with static ips
	# defined in the .properties or with the VIPs if used.

        # public_api network allocation pool
        start = self.settings.public_api_allocation_pool_start.split(".")[-1] 
        end = self.settings.public_api_allocation_pool_end.split(".")[-1]
        for each in self.settings.nodes:
	    if hasattr(each, 'public_api_ip'):
	        ip = each.public_api_ip.split(".")[-1]
	    	if int(start) <= int(ip) <= int(end):
		    raise AssertionError(each.public_api_ip + " in .properties is in" \
				   "the public api allocation pool range definied in the .ini")
        if self.settings.use_static_vips is True:
            if not int(start) <= int(self.settings.public_api_vip.split(".")[-1]) <= int(end):
                raise AssertionError("public_api_vip should be within the public api allocation pool range")

        # private_api network allocation pool
        start = self.settings.private_api_allocation_pool_start.split(".")[-1]
        end = self.settings.private_api_allocation_pool_end.split(".")[-1]
        for each in self.settings.nodes:
            if hasattr(each, 'private_api_ip'):
                ip = each.private_api_ip.split(".")[-1]
                if int(start) <= int(ip) <= int(end):
                    raise AssertionError(each.private_api_ip + " in .properties is in" \
                                   "the private api allocation pool range definied in the .ini")
        if self.settings.use_static_vips is True:
            if int(start) <= int(self.settings.redis_vip.split(".")[-1]) <= int(end):
                raise AssertionError("redis_vip should be outside the private api allocation pool range")
            if not int(start) <= int(self.settings.private_api_vip.split(".")[-1]) <= int(end):
                raise AssertionError("private_api_vip should be within the private api allocation pool range")

        # storage_network allocation pool
        start = self.settings.storage_allocation_pool_start.split(".")[-1]
        end = self.settings.storage_allocation_pool_end.split(".")[-1]
        for each in self.settings.nodes:
            if hasattr(each, 'storage_ip'):
                ip = each.storage_ip.split(".")[-1]
                if int(start) <= int(ip) <= int(end):
                    raise AssertionError(each.storage_ip + " in .properties is in" \
                                   "the storage allocation pool range definied in the .ini")
        if self.settings.use_static_vips is True:
            if not int(start) <= int(self.settings.storage_vip.split(".")[-1]) <= int(end):
                raise AssertionError("storage_vip should be within the storage allocation pool range")

        # provisioning network allocation pool
        start = self.settings.provisioning_net_dhcp_start.split(".")[-1]
        end = self.settings.provisioning_net_dhcp_end.split(".")[-1]
        for each in self.settings.nodes:
            if hasattr(each, 'provisioning_ip'):
                ip = each.provisioning_ip.split(".")[-1]
                if int(start) <= int(ip) <= int(end):
                    raise AssertionError(each.provisioning_ip + " in .properties is in" \
                                   "the provisioning dhcp  allocation pool range definied in the .ini")
        if self.settings.use_static_vips is True:
            if not int(start) <= int(self.settings.storage_cluster_vip.split(".")[-1]) <= int(end):
                raise AssertionError("storage_cluster_vip should be within the provisioning  allocation pool range")
        if self.settings.use_static_vips is True:
            if not int(start) <= int(self.settings.provisioning_vip.split(".")[-1]) <= int(end):
                raise AssertionError("provisioning_vip should be within the provisioning  allocation pool range")

        # discovery_ip_range (provisioning network)
        start = self.settings.discovery_ip_range.split(",")[0].split(".")[-1]
        end = self.settings.discovery_ip_range.split(",")[1].split(".")[-1]
        for each in self.settings.nodes:
            if hasattr(each, 'provisioning_ip'):
                ip = each.provisioning_ip.split(".")[-1]
                if int(start) <= int(ip) <= int(end):
                    raise AssertionError(each.provisioning_ip + " in .properties is in" \
                                   "the discovery ip range definied in the .ini")

        # storage cluster allocation pool
        start = self.settings.storage_cluster_allocation_pool_start.split(".")[-1]
        end = self.settings.storage_cluster_allocation_pool_end.split(".")[-1]
        for each in self.settings.nodes:
            if hasattr(each, 'storage_cluster_ip'):
                ip = each.storage_cluster_ip.split(".")[-1]
                if int(start) <= int(ip) <= int(end):
                    raise AssertionError(each.storage_cluster_ip + " in .properties is in" \
                                   "the storage cluster allocation pool range definied in the .ini")

    def check_duplicate_ips(self):
        # Check for duplicate ip adresses in .properties and .ini
        ips = []
        for each in self.settings.__dict__:
            if "ip" in each and type(getattr(self.settings, each)) is str and self.is_valid_ip(getattr(self.settings, each)):
                ips.append(getattr(self.settings, each))
	for each in self.settings.nodes:
            for att in each.__dict__: 
                if self.is_valid_ip(str(getattr(each, att))):
                    ips.append(getattr(each, att))
        dups = [item for item, count in collections.Counter(ips).items() if count > 1]
        if len(dups) > 0:
             raise AssertionError("Duplicate ips found in your .properties/.ini :" + ', '.join(dups))


    def check_network_settings(self):
        # Verify SAH node network definition
        logger.debug("verifying sah network settings")
        shouldhaveattributes = [ 'hostname', 'idrac_ip', 'root_password',
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
        shouldhaveattributes = [ 'hostname', 'root_password', 'external_ip',
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
            shouldhaveattributes = ['idrac_ip']
            shouldbbevalidips = ['idrac_ip']
	    if self.settings.overcloud_static_ips is True:
	        shouldhaveattributes.extend(["public_api_ip","private_api_ip",
				           "storage_ip", "storage_cluster_ip", "tenant_ip"])
	        shouldbbevalidips.extend(["public_api_ip","private_api_ip",
                                           "storage_ip", "storage_cluster_ip", "tenant_ip"])
            for each in shouldhaveattributes:
                assert hasattr(controller, each), \
                    " node has no " + each + " attribute"
            for each in shouldbbevalidips:
                assert self.is_valid_ip(
                    getattr(controller, each)), \
                    " node " + each + " is not a valid ip"

        # Verify Compute nodes network definition
        logger.debug("verifying compute nodes network settings")
        for compute in self.settings.compute_nodes:
            shouldhaveattributes = [ 'idrac_ip']
	    shouldbbevalidips = ['idrac_ip']
            if self.settings.overcloud_static_ips is True:
                shouldhaveattributes.extend(["private_api_ip", "storage_ip", "tenant_ip"])
                shouldbbevalidips.extend(["private_api_ip", "storage_ip", "tenant_ip"])
            for each in shouldhaveattributes:
                assert hasattr(compute, each), \
                    " node has no " + each + " attribute"
            shouldbbevalidips = ['idrac_ip']
            for each in shouldbbevalidips:
                assert self.is_valid_ip(
                    getattr(compute, each)), \
 " node " \
                    + each + " is not a valid ip"

        # Verify Storage nodes network definition
        logger.debug("verifying storage nodes network settings")
        for storage in self.settings.ceph_nodes:
            shouldhaveattributes = ['idrac_ip',
                                    'osd_disks']
	    shouldbbevalidips = ['idrac_ip', ]
	    if self.settings.overcloud_static_ips is True:
                shouldhaveattributes.extend(["storage_ip", "storage_cluster_ip"])
                shouldbbevalidips.extend(["storage_ip", "storage_cluster_ip"])
            for each in shouldhaveattributes:
                assert hasattr(storage, each), +\
                    " node has no " + each + " attribute"
            for each in shouldbbevalidips:
                assert self.is_valid_ip(
                    getattr(storage, each)), + " node " +\
                    each + " is not a valid ip"
