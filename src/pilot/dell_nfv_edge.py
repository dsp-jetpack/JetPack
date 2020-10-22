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


import argparse
import json
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
from logging_helper import LoggingHelper
from dracclient import client
from command_helper import Ssh
from nfv_parameters import NfvParameters
from utils import Utils
logging.basicConfig()
logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
home_dir = os.path.expanduser('~')
UC_USERNAME = UC_PASSWORD = UC_PROJECT_ID = UC_AUTH_URL = ''


class ConfigEdge(object):
    """
    Description: Class responsible for overcloud configurations.
    """
    ironic = IronicHelper()
    ironic_client = ironic.get_ironic_client()
    nodes = ironic_client.node.list()
    get_drac_credential = CredentialHelper()

    def __init__(self, overcloud_name, node_type, node_type_data):
        self.overcloud_name = overcloud_name
        self.node_type = node_type
        self.node_type_data = json.loads(node_type_data)
        self.mtu = int(self.node_type_data["nfv_mtu"])
        _dir = (re.sub(r'[^a-z0-9]', " ", node_type.lower()).replace(" ", "_"))
        ntl = re.sub(r'[^a-z0-9]', "", node_type.lower())
        # nic_environment_edgespain.yaml
        ne_name = "nic_environment_{}.yaml".format(ntl)
        instack_name = "instackenv_{}.json".format(ntl)
        nic_env_file = os.path.join(home_dir, _dir, ne_name)
        instackenv_file = os.path.join(home_dir, _dir, instack_name)
        self.instackenv = instackenv_file
        self.nic_env = nic_env_file
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

    def fetch_nfv_parameters(self):
        logger.debug("Retrieving NFV parameters")
        ntd = self.node_type_data
        enable_hugepage = Utils.string_to_bool(ntd["hpg_enable"])
        enable_numa = Utils.string_to_bool(ntd["numa_enable"])
        ovs_dpdk = ntd["nfv_type"] == "dpdk" or ntd["nfv_type"] == "both"
        hostos_cpu_count = int(ntd["numa_hostos_cpu_count"])
        _dir = (re.sub(r'[^a-z0-9]', " ",
                       self.node_type.lower()).replace(" ", "_"))
        ntl = re.sub(r'[^a-z0-9]', "", self.node_type.lower())
        # nic_environment_edgespain.yaml
        _f_name = "nic_environment_{}.yaml".format(ntl)
        nic_env_file = os.path.join(home_dir, _dir, _f_name)
        params = {}
        '''
# NFV site settings
# nfv_type must be one of dpdk, sriov or both
nfv_type=dpdk
# the number of NfvInterfaceN attributes is dependent on the number of Ports
# If ports are <= 7 you only need two NFVInterfaces > 7 implies four
# The order is important, pairs need to be across nics.
nfv_interfaces=ens4f0,ens5f0,ens4f1,ens5f1
HostNicDriver=vfio-pci
BondInterfaceOvsOptions=bond_mode=balance-tcp lacp=active
BondInterfaceSriovOptions=mode=802.3ad miimon=100 xmit_hash_policy=layer3+4 lacp_rate=1
NumDpdkInterfaceRxQueues = 1
hpg_enable=true
hpg_size=1GB
numa_enable=true
numa_hostos_cpu_count=4
sriov_vf_count=64
    '''
        # need to make sure dell-environment_[role].yaml has filters enabled
        # if no dpdk
        # if not ovs_dpdk:
        #    cmds.append('sed -i "s|  # NovaSchedulerDefaultFilters|  ' +
        #                'NovaSchedulerDefaultFilters|" ' + file_path)
        # both SRIOV and DPDK require at least these kernel args
        kernel_args = "iommu=pt intel_iommu=on"

        if enable_hugepage:
            hpg_num = self.nfv_params.calculate_hugepage_count(
                ntd["hpg_size"])
            kernel_args += (" default_hugepagesz={} hugepagesz={}"
                            " hugepages={}").format(ntd["hpg_size"],
                                                    ntd["hpg_size"][0:-1],
                                                    str(hpg_num))
        if enable_numa:
            _, node_data = self.nfv_params.select_compute_node(self.node_type,
                                                               self.instackenv)
            self.nfv_params.parse_data(node_data)
            self.nfv_params.get_all_cpus()
            self.nfv_params.get_host_cpus(hostos_cpu_count)
            if ovs_dpdk:
                dpdk_nics = self.find_ifaces_by_keyword(nic_env_file,
                                                        'Dpdk')
                logger.debug("DPDK-NICs >>" + str(dpdk_nics))
                self.nfv_params.get_pmd_cpus(self.mtu, dpdk_nics)
                self.nfv_params.get_socket_memory(self.mtu, dpdk_nics)
            self.nfv_params.get_nova_cpus()
            self.nfv_params.get_isol_cpus()
            kernel_args += " isolcpus={}".format(self.nfv_params.isol_cpus)
            # dell-environmment
            params_dell_env = params["dell_env"] = {}
            nova_cpus = self.nfv_params.nova_cpus
            params_dell_env["NovaComputeCpuDedicatedSet"] = nova_cpus
            params_dell_env["KernelArgs"] = kernel_args
        if ovs_dpdk:
            params_dpdk = params["dpdk"] = {}
            params_dpdk["OvsDpdkCoreList"] = self.nfv_params.host_cpus
            params_dpdk["NovaComputeCpuSharedSet"] = self.nfv_params.host_cpus
            params_dpdk["OvsPmdCoreList"] = self.nfv_params.pmd_cpus
            params_dpdk["OvsDpdkSocketMemory"] = self.nfv_params.socket_mem
            params_dpdk["IsolCpusList"] = self.nfv_params.isol_cpus
        return params

    def get_dell_compute_nodes_hostnames(self, nova):
        try:
            logger.debug("Getting dellnfv compute node hostnames")

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overcloud_name",
                        default=None,
                        help="The name of the overcloud")
    parser.add_argument("--edge_site",
                        default=None,
                        dest="node_type",
                        help="The name of edge site being configured")
    parser.add_argument("--edge_site_data",
                        default=None,
                        dest="node_type_data",
                        help="The edge site metadata")
    parser.add_argument("--debug",
                        default=False,
                        action='store_true',
                        help="Turn on debugging for this script")

    LoggingHelper.add_argument(parser)
    args = parser.parse_args()
    LoggingHelper.configure_logging(args.logging_level)
    config_edge = ConfigEdge(args.overcloud_name, args.node_type,
                             args.node_type_data)
    params = config_edge.fetch_nfv_parameters()
    logger.debug(">>>>>> nfv parameters {}".format(str(params)))
    return json.dumps(params)
    '''
    _res = config_edge.res
    ntd = config_edge.node_type_data
    nfv_p = config_edge.nfv_params

    node_uuid, node_data = nfv_p.select_compute_node(config_edge.node_type,
                                                     config_edge.instackenv)
    hostos_cpu_count = ntd["numa_hostos_cpu_count"]
    nfv_p.parse_data(node_data)
    nfv_p.get_all_cpus()
    nfv_p.get_host_cpus(hostos_cpu_count)
    _dir = (re.sub(r'[^a-z0-9]', " ",
            config_edge.node_type.lower()).replace(" ", "_"))
    ntl = re.sub(r'[^a-z0-9]', "", config_edge.node_type.lower())
    # nic_environment_edgespain.yaml
    f_name = "nic_environment_{}.yaml".format(ntl)
    nic_env_file = os.path.join(home_dir, _dir, f_name)
    dpdk_nics = config_edge.find_ifaces_by_keyword(nic_env_file,
                                                   'Dpdk')
    logger.debug("DPDK-NICs >>" + str(dpdk_nics))
    nfv_p.get_pmd_cpus(config_edge.mtu, dpdk_nics)
    nfv_p.get_socket_memory(config_edge.mtu, dpdk_nics)
    nfv_p.get_nova_cpus()
    nfv_p.get_isol_cpus()
    nfv_p.get_host_cpus(ntd["numa_hostos_cpu_count"])
    _res["host_cpus"] = nfv_p.host_cpus
    return json.dumps(_res)
    '''


if __name__ == "__main__":
    res = main()
    logger.debug(">>>>>> res {}".format(str(res)))
    sys.stdout.write(res)
