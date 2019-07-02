# Copyright (c) 2018-2019 Dell Inc. or its subsidiaries.
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

from credential_helper import CredentialHelper
from ironic_helper import IronicHelper
from keystoneauth1.identity import v3
from keystoneauth1 import session
import ironicclient
from keystoneclient.v3 import client
import ironic_inspector_client
from dracclient import client as drac_client
import math
from itertools import groupby
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import logging
import os
import sys

logging.basicConfig()
logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class NfvParameters(object):
    def __init__(self):
        self.data = {'nics': {}, 'cpus': {}}
        self.inspector = None
        self.total_cpus = None
        self.host_cpus = None
        self.pmd_cpus = None
        self.nova_cpus = None
        self.isol_cpus = None
        self.socket_mem = None
        self.get_inspector_client()
        self.ironic = IronicHelper.get_ironic_client()

    def get_inspector_client(self):
        os_auth_url, os_tenant_name, os_username, os_password, \
            os_user_domain_name, os_project_domain_name = \
            CredentialHelper.get_undercloud_creds()
        auth_url = os_auth_url + "v3"

        kwargs = {
                'username': os_username,
                'password': os_password,
                'auth_url': os_auth_url,
                'project_id': os_tenant_name,
                'user_domain_name': os_user_domain_name,
                'project_domain_name': os_project_domain_name
                }
        auth = v3.Password(
            auth_url=auth_url,
            username=os_username,
            password=os_password,
            project_name=os_tenant_name,
            user_domain_name=os_user_domain_name,
            project_domain_name=os_project_domain_name
            )
        sess = session.Session(auth=auth)
        self.inspector = ironic_inspector_client.ClientV1(session=sess)

    def check_ht_status(self, node):
        drac_ip, drac_user, drac_password = \
            CredentialHelper.get_drac_creds(self.ironic, node)
        stor = drac_client.DRACClient(drac_ip, drac_user, drac_password)
        # cpu socket information for every compute node
        sockets = stor.list_cpus()
        for socket in sockets:
            if not socket.ht_enabled:
                raise Exception("Hyperthreading is not enabled in "
                                + str(node))
        print "Hyperthreading enabled on %s" % node
        return True

    def get_nodes_uuids(self, nodetype):
        nodes = []
        # ironic = IronicHelper.get_ironic_client()
        for node in self.ironic.node.list(detail=True):
            if nodetype in node.properties['capabilities']:
                nodes.append(node.uuid)
        return nodes

    def get_numa_nics(self, node_data):
        numa_nics = {0: [], 1: []}
        for d in node_data['numa_topology']['nics']:
            numa_nics[d['numa_node']].append(d['name'])
        return numa_nics

    def get_numa_cpus(self, node_data):
        numa_cpus = {0: {}, 1: {}}
        for d in node_data['numa_topology']['cpus']:
            numa_cpus[d['numa_node']][d['thread_siblings'][0]] = d['thread_siblings']  # noqa: E501
        return numa_cpus

    def parse_data(self, node_data):
        self.data['nics'] = self.get_numa_nics(node_data)
        self.data['cpus'] = self.get_numa_cpus(node_data)

    def get_all_cpus(self):
        try:
            total_cpus = []
            assert self.data.has_key('cpus'),\
                "Unable to fetch total number " \
                "of CPUs. Parse CPU data first"
            for node in self.data['cpus'].keys():
                for cpus in self.data['cpus'][node].values():
                    total_cpus.append(cpus)
            total_cpus = [item for sublist in total_cpus for item in sublist]
            total_cpus = self.range_extract(sorted(total_cpus, key=int))
            self.total_cpus = ','.join(map(str, total_cpus))
        except AssertionError:
            raise

    def get_host_cpus(self, host_cpus_count):
        host_cpus = []
        pairs = int(math.ceil(int(host_cpus_count)/2.0))
        for i in range(0, pairs):
            host_cpus.append(self.data['cpus'][i % 2][i][0])
            host_cpus.append(self.data['cpus'][i % 2][i][1])
            self.data['cpus'][i % 2].pop(i, None)
            i += 1
        host_cpus = self.range_extract(sorted(host_cpus, key=int))
        self.host_cpus = ','.join(map(str, host_cpus))

    def get_pmd_cpus(self, mtu, dpdk_nics):
        pmd_cpus = []
        nics_numa_distribution = {}
        nodes = self.data['nics'].keys()
        for node in nodes:
            # if not nics_numa_distribution.has_key(node):
            nics_numa_distribution[node] = False
            for nic in dpdk_nics:
                if nic in self.data['nics'][node]:
                    cpu_pair = next(iter(self.data['cpus'][node]))
                    pmd_cpus.append(self.data['cpus'][node][cpu_pair])
                    self.data['cpus'][node].pop(cpu_pair, None)
                    nics_numa_distribution[node] = True
        for node in nics_numa_distribution.keys():
            if nics_numa_distribution[node] is False:
                cpu_pair = next(iter(self.data['cpus'][node]))
                pmd_cpus.append(self.data['cpus'][node][cpu_pair])
                self.data['cpus'][node].pop(cpu_pair, None)
        pmd_cpus = [item for sublist in pmd_cpus for item in sublist]
        pmd_cpus = self.range_extract(sorted(pmd_cpus, key=int))
        self.pmd_cpus = ','.join(map(str, pmd_cpus))

    def get_nova_cpus(self):
        nova_cpus = []
        nodes = self.data['nics'].keys()
        for node in nodes:
            cpu_pairs = self.data['cpus'][node].values()
            cpu_pairs = [item for sublist in cpu_pairs for item in sublist]
            nova_cpus.append(cpu_pairs)
        nova_cpus = [item for sublist in nova_cpus for item in sublist]
        nova_cpus = self.range_extract(sorted(nova_cpus, key=int))
        self.nova_cpus = ','.join(map(str, nova_cpus))

    def get_isol_cpus(self):
        isol_cpus = []
        total = self.parse_range(self.total_cpus).split(',')
        host = self.parse_range(self.host_cpus).split(',')
        isol_cpus = set(total) - set(host)
        isol_cpus = sorted(map(int, isol_cpus), key=int)
        isol_cpus = self.range_extract(isol_cpus)
        self.isol_cpus = ','.join(map(str, isol_cpus))

    def get_socket_memory(self, mtu, dpdk_nics):
        nodes = self.data['nics'].keys()
        numa_mem = {el: 1024 for el in nodes}
        mtu = self.round_to_nearest(mtu, 1024)
        for n in nodes:
            mem = 536870912
            for nic in dpdk_nics:
                if nic in self.data['nics'][n]:
                    mem += (mtu + 800) * (4096*64)
                    break
            mem = mem / (1024*1024)
            numa_mem[n] = self.round_to_nearest(mem, 1024)
        self.socket_mem = ','.join(map(str, numa_mem.values()))

    def round_to_nearest(self, n, m):
        return m if n <= m else ((n / m) + 1) * m

    def subtract(self, x):
        return x[1] - x[0]

    def range_extract(self, a):
        ranges = []
        for k, iterable in groupby(enumerate(sorted(a)), self.subtract):
            rng = list(iterable)
            if len(rng) == 1:
                s = str(rng[0][1])
            else:
                s = "%s-%s" % (rng[0][1], rng[-1][1])
            ranges.append(s)
        return ranges

    def parse_range(self, s):
        s = "".join(s.split())
        r = set()
        for x in s.split(','):
            t = x.split('-')
            if len(t) not in [1, 2]:
                raise SyntaxError("hash_range is given its arguement as " +
                                  s +
                                  " which seems not correctly formated.")
            r.add(int(t[0])) if len(t) == 1 else r.update(set(range(int(t[0]), int(t[1]) + 1)))  # noqa: E501
        ls = list(r)
        ls.sort()
        return ','.join(map(str, ls))

    def select_compute_node(self):
        ref_node = {"uuid": None, "cpus": None, "data": None}
        for node in self.get_nodes_uuids("compute"):
            self.check_ht_status(node)
            data = self.get_introspection_data(node)
            if not ref_node["uuid"]:
                ref_node["uuid"] = node
                ref_node["data"] = data
                ref_node["cpus"] = ref_node["data"]["cpus"]
                continue
            if data['cpus'] < ref_node["cpus"]:
                ref_node["uuid"] = node
                ref_node["data"] = data
                ref_node["cpus"] = data["cpus"]
        if ref_node["cpus"] not in [40, 48, 56, 64, 72, 80, 128]:
            raise Exception("The number of vCPUs, as specified in the"
                            " reference architecture, must be one of"
                            " [40, 48, 56, 64, 72, 80, 128]"
                            " but number of vCPUs are " + str(
                                ref_node["cpus"]))
        return ref_node["uuid"], ref_node["data"]

    def get_introspection_data(self, node):
        return self.inspector.get_data(node)

    def get_minimum_memory_size(self, node_type):
        try:
            memory_size = []
            for node_uuid in self.get_nodes_uuids(node_type):
                # Get the details of a node
                node_details = self.ironic.node.get(node_uuid)
                # Get the memory count or size
                memory_count = node_details.properties['memory_mb']
                # Get the type details of the node
                node_properties_capabilities = node_details.properties[
                    'capabilities'].split(',')[0].split(':')[1]
                if node_type in node_properties_capabilities:
                    memory_size.append(memory_count)
            return min(memory_size)
        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            raise Exception("Failed to get memory size {}".format(message))

    def calculate_hugepage_count(self, hugepage_size):
        try:
            memory_count = int(self.get_minimum_memory_size("compute"))
            # RAM size should be more than 128G
            if memory_count < 128000:
                raise Exception("RAM size is less than 128GB"
                                "make sure to have all prerequisites")
            # Subtracting
            # 16384MB = (Host Memory 12GB + Kernel Memory 4GB)
            memory_count = (memory_count - 16384)
            if hugepage_size == "2MB":
                hugepage_count = (memory_count / 2)
            if hugepage_size == "1GB":
                hugepage_count = (memory_count / 1024)
            logger.info("hugepage_size {}".format(hugepage_size))
            logger.info("hugepage_count {}".format(hugepage_count))
            return hugepage_count
        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            raise Exception("Failed to calculate"
                            " hugepage count {}".format(message))
