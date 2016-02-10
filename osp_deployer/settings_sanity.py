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

import sys, getopt, time, subprocess, paramiko,logging, traceback, os.path, urllib2, shutil, socket
from osp_deployer.ceph import Ceph
from auto_common import Ipmi, Ssh, FileHelper, Scp, UI_Manager
from osp_deployer import Settings

logger = logging.getLogger("osp_deployer")



class Deployer_sanity():
    '''
    '''


    def __init__(self):
        self.settings = Settings.settings

    def isValidIp(self, address):
        try:
            socket.inet_aton(address)
            ip = True
        except socket.error:
            ip = False

        return ip


    def check_files(self):

        logger.debug("Check settings ip's are valid.")
        shouldBeValidIPs = [
            'external_netmask','public_gateway','external_gateway',
            'public_api_netmask','external_allocation_pool_start','external_allocation_pool_end',
            'private_api_vlanid','private_api_netmask','private_api_allocation_pool_start','private_api_allocation_pool_end',
            'storage_netmask','storage_allocation_pool_start','storage_allocation_pool_end',
            'provisioning_netmask','provisioning_net_dhcp_start','provisioning_net_dhcp_end','provisioning_gateway',
            'storage_cluster_allocation_pool_start','storage_cluster_allocation_pool_end',
            'managment_netmask','name_server',
            'ipmi_discovery_range_start','ipmi_discovery_range_end',
        ]
        for ip in getattr(self.settings, 'discovery_ip_range').split(","):
            self.isValidIp(ip), "Setting for discovery_ip_range " + ip + " is not a valid ip "
        for each in shouldBeValidIPs:
            assert self.isValidIp(getattr(self.settings, each)), "Setting for " + each + " is not a valid ip " + getattr(self.settings, each)

        assert os.path.isfile(self.settings.rhl72_iso) , self.settings.rhl722_iso + "ISO doesn't seem to exist"
        assert os.path.isfile(self.settings.sah_kickstart) , self.settings.sah_kickstart + "kickstart file doesnn't seem to exist"
        assert os.path.isfile(self.settings.director_deploy_sh) , self.settings.director_deploy_sh + " script doesn't seem to exist"
        assert os.path.isfile(self.settings.undercloud_conf) , self.settings.undercloud_conf + " file doesn't seem to exist"
        if self.settings.use_custom_instack_json is True:
            assert os.path.isfile(self.settings.custom_instack_json) , self.settings.custom_instack_json + " file doesn't seem to exist"

        assert os.path.isfile(self.settings.deploy_ram_disk_image) , self.settings.deploy_ram_disk_image + " file doesn't seem to exist"
        assert os.path.isfile(self.settings.discovery_ram_disk_image) , self.settings.discovery_ram_disk_image + " file doesn't seem to exist"
        assert os.path.isfile(self.settings.overcloud_image) , self.settings.overcloud_image + " file doesn't seem to exist"
        assert os.path.isfile(self.settings.install_director_sh) , self.settings.install_director_sh + " file doesn't seem to exist"


        try:
                urllib2.urlopen(self.settings.rhel_install_location +"/EULA").read()
        except:
            raise AssertionError(self.settings.rhel_install_location + "/EULA is not reachable")

        if sys.platform.startswith('linux') == False:
            if "RUNNING" in subprocess.check_output("sc query Tftpd32_svc",stderr=subprocess.STDOUT, shell=True):
                subprocess.check_output("net stop Tftpd32_svc",stderr=subprocess.STDOUT, shell=True)
        else:
            subprocess.check_output("service tftp stop",stderr=subprocess.STDOUT, shell=True)

    def check_ipmi_to_nodes(self):
        hdw_nodes = self.settings.controller_nodes + self.settings.compute_nodes + self.settings.ceph_nodes
        hdw_nodes.append(self.settings.sah_node)
        for node in hdw_nodes:
            try:
		logger.debug( node.idrac_ip)
                ipmi_session = Ipmi(self.settings.cygwin_installdir, self.settings.ipmi_user, self.settings.ipmi_password, node.idrac_ip)
                logger.debug( node.hostname +" :: "+ ipmi_session.get_power_state())
            except:
                raise AssertionError("Could not impi to host " + node.hostname)

    def check_network_settings(self):
        #

        # Verify SAH node network definition
        logger.debug( "verifying sah network settings")
        shouldHaveAttrbutes = [ 'hostname','idrac_ip','root_password','anaconda_ip','anaconda_iface',
                                'external_bond','external_slaves','external_ip',
                                'private_bond','private_slaves',
                                'provisioning_ip','storage_ip','public_api_ip','private_api_ip','managment_ip'
                              ]
        for each in shouldHaveAttrbutes :
            assert hasattr(self.settings.sah_node, each), self.settings.network_conf + " SAH node has no " + each + " attribute"

        shouldBeValidIps = ['idrac_ip','anaconda_ip','external_ip',
                            'provisioning_ip','storage_ip','public_api_ip','private_api_ip','managment_ip'
                            ]
        for each in shouldBeValidIps:
            assert self.isValidIp(getattr(self.settings.sah_node, each)), "SAH node " + each + " is not a valid ip"

        # Verify director network definition
        logger.debug( "verifying director vm network settings")
        shouldHaveAttrbutes = [ 'hostname','root_password','external_ip','provisioning_ip',
                                'managment_ip','public_api_ip','private_api_ip'
                              ]
        for each in shouldHaveAttrbutes :
            assert hasattr(self.settings.director_node, each), self.settings.network_conf + " director node has no " + each + " attribute"
            shouldBeValidIps = ['external_ip','provisioning_ip', 'managment_ip','public_api_ip','private_api_ip'
                                ]
        for each in shouldBeValidIps:
            assert self.isValidIp(getattr(self.settings.director_node, each)), "director_node node " + each + " is not a valid ip"

        # Verify Ceph vm node network definition
        logger.debug( "verifying ceph vm network settings")
        shouldHaveAttrbutes = [  'hostname','root_password','external_ip','storage_ip'
                              ]
        for each in shouldHaveAttrbutes :
            assert hasattr(self.settings.ceph_node, each), self.settings.network_conf + " Ceph Vm node has no " + each + " attribute"
        shouldBeValidIps = ['external_ip','storage_ip']
        for each in shouldBeValidIps:
            assert hasattr(self.settings.ceph_node, each), self.settings.network_conf + " Ceph Vm node has no " + each + " attribute"
        # Verify Controller nodes network definitioncls
        logger.debug( "verifying controller nodes network settings")
        for controller in self.settings.controller_nodes:
            shouldHaveAttrbutes = [ 'hostname','idrac_ip','provisioning_mac_address'
                                    ]
            for each in shouldHaveAttrbutes :
                assert hasattr(controller, each), controller.hostname + " node has no " + each + " attribute"
                shouldBeValidIps = ['idrac_ip']
            for each in shouldBeValidIps:
                assert self.isValidIp(getattr(controller, each)), controller.hostname + " node " + each + " is not a valid ip"


        # Verify Compute nodes network definition
        logger.debug( "verifying compute nodes network settings")
        for compute in self.settings.compute_nodes:
            shouldHaveAttrbutes = ['hostname','idrac_ip','provisioning_mac_address'
                                     ]
            for each in shouldHaveAttrbutes :
                assert hasattr(compute, each), compute.hostname + " node has no " + each + " attribute"
                shouldBeValidIps = ['idrac_ip']
            for each in shouldBeValidIps:
                assert self.isValidIp(getattr(compute, each)), compute.hostname + " node " + each + " is not a valid ip"


        # Verify Storage nodes network definition
        logger.debug( "verifying storage nodes network settings")
        for storage in self.settings.ceph_nodes:
            shouldHaveAttrbutes = ['hostname','idrac_ip','provisioning_mac_address','journal_disks', 'osd_disks'
                                     ]
            for each in shouldHaveAttrbutes :
                assert hasattr(storage, each), storage.hostname + " node has no " + each + " attribute"
                shouldBeValidIps = ['idrac_ip',]
            for each in shouldBeValidIps:
                assert self.isValidIp(getattr(storage, each)), storage.hostname + " node " + each + " is not a valid ip"





