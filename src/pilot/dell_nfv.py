#!/usr/bin/python3

# Copyright (c) 2018-2020 Dell Inc. or its subsidiaries.
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


import os
import re
import sys
import time
import subprocess
import string
import logging
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from novaclient.v2 import aggregates
from novaclient.v2 import servers
from credential_helper import CredentialHelper
from datetime import datetime
import novaclient.client as nova_client
from novaclient import client as nvclient
from ironic_helper import IronicHelper
from dracclient import client
from command_helper import Ssh
from nfv_parameters import NfvParameters


logging.basicConfig()
logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
home_dir = os.path.expanduser('~')
UC_USERNAME = UC_PASSWORD = UC_PROJECT_ID = UC_AUTH_URL = ''


class ConfigOvercloud(object):
    """
    Description: Class responsible for overcloud configurations.
    """
    ironic = IronicHelper()
    ironic_client = ironic.get_ironic_client()
    nodes = ironic_client.node.list()
    get_drac_credential = CredentialHelper()

    def __init__(self, overcloud_name):
        self.overcloud_name = overcloud_name
        self.overcloudrc = "source " + home_dir + "/"\
            + self.overcloud_name + "rc;"
        self.nfv_params = NfvParameters()

    def find_ifaces_by_keyword(self, yaml_file, keyword):
        nics = []
        with open(yaml_file, 'r') as f:
            content = f.readlines()
            for line in content:
                if keyword in line:
                    nics.append(line.split(':')[1].strip())
        return nics

    def edit_environment_files(
            self,
            mtu,
            enable_hugepage,
            enable_numa,
            hugepage_size,
            hostos_cpu_count,
            ovs_dpdk,
            sriov,
            hw_offload,
            sriov_interfaces,
            nic_env_file,
            controller_count,
            ceph_storage_count,
            controller_flavor,
            ceph_storage_flavor,
            swift_storage_flavor,
            block_storage_flavor,
            vlan_range,
            dell_compute_count=0,
            dell_computehci_count=0,
            dell_powerflex_count=0):
        try:
            logger.info("Editing dell environment file")
            file_path = home_dir + '/pilot/templates/dell-environment.yaml'
            dpdk_file = home_dir + '/pilot/templates/neutron-ovs-dpdk.yaml'
            hw_off_file = home_dir + '/pilot/templates/ovs-hw-offload.yaml'
            cmds = []
            if not os.path.isfile(file_path):
                raise Exception(
                    "The dell-environment.yaml file does not exist")
            if not os.path.isfile(dpdk_file):
                raise Exception(
                    "The neutron-ovs-dpdk.yaml file does not exist")
            if not ovs_dpdk:
                cmds.append('sed -i "s|  # NovaSchedulerDefaultFilters|  ' +
                            'NovaSchedulerDefaultFilters|" ' + file_path)
            cmds.extend((
                'sed -i "s|DellComputeCount:.*|DellComputeCount: ' +
                str(dell_compute_count) +
                '|" ' +
                file_path,
                'sed -i "s|DellComputeHCICount:.*|DellComputeHCICount: ' +
                str(dell_computehci_count) +
                '|" ' +
                file_path,
                'sed -i "s|ControllerCount:.*|ControllerCount: ' +
                str(controller_count) +
                '|" ' +
                file_path,
                'sed -i "s|CephStorageCount:.*|CephStorageCount: ' +
                str(ceph_storage_count) +
                '|" ' +
                file_path,
                'sed -i "s|PowerflexStorageCount:.*|PowerflexStorageCount: ' +
                str(dell_powerflex_count) +
                '|" ' +
                file_path,
                'sed -i "s|OvercloudControllerFlavor:.*' +
                '|OvercloudControllerFlavor: ' +
                str(controller_flavor) +
                '|" ' +
                file_path,
                'sed -i "s|OvercloudCephStorageFlavor:.*' +
                '|OvercloudCephStorageFlavor: ' +
                str(ceph_storage_flavor) +
                '|" ' +
                file_path,
                'sed -i "s|OvercloudSwiftStorageFlavor:.*' +
                '|OvercloudSwiftStorageFlavor: ' +
                str(swift_storage_flavor) +
                '|" ' +
                file_path,
                'sed -i "s|OvercloudBlockStorageFlavor:.*' +
                '|OvercloudBlockStorageFlavor: ' +
                str(block_storage_flavor) +
                '|" ' +
                file_path,
                'sed -i "s|NeutronNetworkVLANRanges:.*' +
                '|NeutronNetworkVLANRanges: ' +
                'physint:' + str(vlan_range) + ',physext'
                '|" ' +
                file_path))
            kernel_args = ''
            if sriov or ovs_dpdk:
                kernel_args = "iommu=pt intel_iommu=on"

            if enable_hugepage:
                hpg_num = self.nfv_params.calculate_hugepage_count(
                    hugepage_size)
                kernel_args += " default_hugepagesz=%s hugepagesz=%s" \
                    " hugepages=%s" \
                    % (hugepage_size, hugepage_size[0:-1], str(hpg_num))

            if enable_numa:
                node_uuid, node_data = self.nfv_params.select_compute_node()
                self.nfv_params.parse_data(node_data)
                self.nfv_params.get_all_cpus()
                self.nfv_params.get_host_cpus(hostos_cpu_count)
                if ovs_dpdk:
                    dpdk_nics = self.find_ifaces_by_keyword(nic_env_file,
                                                            'Dpdk')
                    logger.debug("DPDK-NICs >>" + str(dpdk_nics))
                    self.nfv_params.get_pmd_cpus(mtu, dpdk_nics)
                    self.nfv_params.get_socket_memory(mtu, dpdk_nics)
                self.nfv_params.get_nova_cpus()
                self.nfv_params.get_isol_cpus()
                kernel_args += " isolcpus=%s" % self.nfv_params.isol_cpus
                cmds.append(
                    'sed -i "s|# NovaComputeCpuDedicatedSet:.*|NovaComputeCpuDedicatedSet: ' +
                    self.nfv_params.nova_cpus + '|" ' + file_path)
            if kernel_args:
                cmds.append(
                    'sed -i "s|# DellComputeParameters:' +
                    '|DellComputeParameters:|" ' +
                    file_path)
                cmds.append(
                    'sed -i "s|# KernelArgs:.*|KernelArgs: \\"' +
                    kernel_args + '\\" |" ' + file_path)
            if ovs_dpdk:
                cmds.append(
                    'sed -i "s|OvsDpdkCoreList:.*|OvsDpdkCoreList: \\"' +
                    self.nfv_params.host_cpus +
                    '\\" |" ' +
                    dpdk_file)
                cmds.append(
                    'sed -i "s|NovaComputeCpuSharedSet:.*|NovaComputeCpuSharedSet: \\"' +
                    self.nfv_params.host_cpus +
                    '\\" |" ' +
                    dpdk_file)
                cmds.append(
                    'sed -i "s|OvsPmdCoreList:.*|OvsPmdCoreList: \\"' +
                    self.nfv_params.pmd_cpus +
                    '\\" |" ' +
                    dpdk_file)
                cmds.append(
                    'sed -i "s|OvsDpdkSocketMemory:' +
                    '.*|OvsDpdkSocketMemory: \\"' +
                    self.nfv_params.socket_mem +
                    '\\" |" ' +
                    dpdk_file)
                cmds.append(
                    'sed -i "s|IsolCpusList:.*|IsolCpusList: \\"' +
                    self.nfv_params.isol_cpus + '\\" |" ' + dpdk_file)

            if dell_powerflex_count > 0 :
                cmds.append(
                     'sed -i "s|NovaEnableRbdBackend:.*' +
                     '|NovaEnableRbdBackend: false |" ' +
                     file_path)
                cmds.append(
                    'sed -i "s|CinderEnableRbdBackend:.*' +
                    '|CinderEnableRbdBackend: false |" ' +
                    file_path)
                cmds.append(
                    'sed -i "s|GlanceBackend:.*' +
                    '|GlanceBackend: cinder|" ' +
                    file_path)


            for cmd in cmds:
                status = os.system(cmd)
                if status != 0:
                    raise Exception(
                        "Failed to execute the command {}"
                        " with error code {}".format(
                            cmd, status))
                logger.debug("cmd: {}".format(cmd))

        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            logger.error(message)
            raise Exception(
                "Failed to modify the dell_environment.yaml"
                " at location {}".format(file_path))

    def get_dell_compute_nodes_hostnames(self, nova):
        try:
            logger.info("Getting dellnfv compute node hostnames")

            # Get list of dell nfv nodes
            dell_hosts = []

            for host in nova.servers.list():
                if "dell-compute" in host.name:
                    hostname = str(host.name)
                    dell_hosts.append(hostname)

            return dell_hosts
        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            logger.error(message)
            raise Exception("Failed to get the Dell Compute nodes.")
