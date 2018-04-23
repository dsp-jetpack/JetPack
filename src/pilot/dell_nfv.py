#!/usr/bin/python

# Copyright (c) 2018 Dell Inc. or its subsidiaries.
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


import cpu_siblings
import os
import sys
import time
import subprocess
import string
import logging
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from novaclient.v2 import aggregates
from novaclient.v2 import hosts
from novaclient.v2 import servers
from credential_helper import CredentialHelper
from datetime import datetime
import novaclient.client as nova_client
from novaclient import client as nvclient
from ironic_helper import IronicHelper
from dracclient import client
from command_helper import Ssh
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

    def reboot_compute_nodes(self):
        logger.info("Rebooting dell compute nodes")
        UC_AUTH_URL, UC_PROJECT_ID, UC_USERNAME, UC_PASSWORD = \
            CredentialHelper.get_undercloud_creds()
        kwargs = {'username': UC_USERNAME,
                  'password': UC_PASSWORD,
                  'auth_url': UC_AUTH_URL,
                  'project_id': UC_PROJECT_ID}
        n_client = nova_client.Client(2, **kwargs)
        dell_compute = []
        for compute in n_client.servers.list(detailed=False,
                                             search_opts={'name': 'compute'}):
            dell_compute.append(n_client.servers.ips(
                compute)['ctlplane'][0]['addr'])
            logger.info("Rebooting server with id: ".format(compute.id))
            n_client.servers.reboot(compute.id)
        # Wait for 30s for the nodes to be powered cycle then do the checks
        time.sleep(30)
        ssh_success_count = 0
        for ip in dell_compute:
            retries = 32
            while retries > 0:
                exit_code, _, std_err = Ssh.execute_command(ip,
                                                            "pwd",
                                                            user="heat-admin",
                                                            )
                retries -= 1
                if exit_code != 0:
                    logger.info("Server with IP: {}"
                                " is not responsive".format(ip))
                else:
                    logger.info("Server with IP: {}"
                                " is responsive".format(ip))
                    ssh_success_count += 1
                    break
                # Waiting 10s before the next attempt
                time.sleep(10)
        if ssh_success_count == len(dell_compute):
            logger.info("All compute nodes are now responsive. Continuing...")
        else:
            logger.error("Failed to reboot the nodes or at least "
                         "one node failed to get back up")
            raise Exception("At least one compute node failed to reboot")

    @classmethod
    def get_minimum_memory_size(self, node_type):
        try:
            memory_size = []
            for node in ConfigOvercloud.nodes:
                node_uuid = node.uuid
                # Get the details of a node
                node_details = ConfigOvercloud.ironic_client.node.get(
                    node_uuid)
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

    @classmethod
    def calculate_hostos_cpus(self, number_of_host_os_cpu):
        try:
            cpu_count_list = []
            for node in ConfigOvercloud.nodes:
                # for every compute node get the corresponding drac credentials
                # to fetch the cpu details
                node_uuid = node.uuid
                node_details = ConfigOvercloud.ironic_client.node.get(
                    node_uuid)
                node_type = node_details.properties['capabilities'].split(',')[
                    0].split(':')[1]
                if 'compute' not in node_type:
                    # filter for getting compute node
                    continue
                drac_ip, drac_user, drac_password = \
                    ConfigOvercloud.get_drac_credential.get_drac_creds(
                        ConfigOvercloud.ironic_client, node_uuid)
                stor = client.DRACClient(drac_ip, drac_user, drac_password)
                # cpu socket information for every compute node
                sockets = stor.list_cpus()
                cpu_count = 0
                for socket in sockets:
                    if socket.ht_enabled:
                        cpu_count += socket.cores * 2
                    else:
                        raise Exception("Hyperthreading is not enabled in "
                                        + str(node_uuid))
                cpu_count_list.append(cpu_count)

            min_cpu_count = min(cpu_count_list)
            if min_cpu_count not in [40, 48, 56, 64, 72, 128]:
                raise Exception("CPU count should be one of these"
                                " values : [40,48,56,64,72,128]"
                                " But number of cpu is " + str(
                                    min_cpu_count))
            number_of_host_os_cpu = int(number_of_host_os_cpu)
            logger.info("host_os_cpus {}".format(
                cpu_siblings.sibling_info[
                    min_cpu_count][number_of_host_os_cpu]["host_os_cpu"]))
            logger.info("vcpus {}".format(
                cpu_siblings.sibling_info[
                    min_cpu_count][number_of_host_os_cpu]["vcpu_pin_set"]))
            return cpu_siblings.sibling_info[
                min_cpu_count][number_of_host_os_cpu]["vcpu_pin_set"]
        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            raise Exception("Failed to calculate "
                            "Numa Vcpu list {}".format(message))

    @classmethod
    def calculate_hugepage_count(self, hugepage_size):
        try:
            memory_count = ConfigOvercloud.get_minimum_memory_size("compute")
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

    def edit_environment_files(
            self,
            enable_hugepage,
            enable_numa,
            hugepage_size,
            hostos_cpu_count,
            ovs_dpdk,
            mariadb_max_connections,
            innodb_buffer_pool_size,
            innodb_buffer_pool_instances,
            dell_compute_count=0):
        try:
            logger.info("Editing dell environment file")
            file_path = home_dir + '/pilot/templates/dell-environment.yaml'
            dpdk_file = home_dir + '/pilot/templates/neutron-ovs-dpdk.yaml'
            if not os.path.isfile(file_path):
                raise Exception(
                    "The dell-environment.yaml file does not exist")
            if not os.path.isfile(dpdk_file):
                raise Exception(
                    "The neutron-ovs-dpdk.yaml file does not exist")
            cmds = ['sed -i "s|  # NovaSchedulerDefaultFilters|  ' +
                    'NovaSchedulerDefaultFilters|" ' + file_path]
            cmds.append(
                'sed -i "s|dellnfv::hugepages::enable:.*'
                '|dellnfv::hugepages::enable: ' +
                str(enable_hugepage) +
                '|" ' +
                file_path)
            cmds.append(
                'sed -i "s|dellnfv::numa::enable:.*|dellnfv::numa::enable: ' +
                str(enable_numa) +
                '|" ' +
                file_path)

            cmds.append(
                'sed -i "s|DellComputeCount:.*|DellComputeCount: ' +
                str(dell_compute_count) +
                '|" ' +
                file_path)

            if enable_hugepage:
                hugepage_number = ConfigOvercloud.calculate_hugepage_count(
                    hugepage_size)
                cmds.append('sed -i "s|dellnfv::hugepages::hugepagesize:.*'
                            '|dellnfv::hugepages::hugepagesize: ' +
                            hugepage_size[0:-1] + '|" ' + file_path)
                cmds.append(
                    'sed -i "s|dellnfv::hugepages::hugepagecount:.*'
                    '|dellnfv::hugepages::hugepagecount: ' +
                    str(hugepage_number) +
                    '|" ' +
                    file_path)
            if enable_numa:
                vcpu_pin_set = ConfigOvercloud.calculate_hostos_cpus(
                    hostos_cpu_count)
                cmds.append(
                    "sed -i 's|dellnfv::numa::vcpu_pin_set:.*"
                    "|dellnfv::numa::vcpu_pin_set: \"" +
                    vcpu_pin_set +
                    "\"|' " +
                    file_path)
                cmds.append(
                    'sed -i "s|  # NovaVcpuPinSet|  ' +
                    'NovaVcpuPinSet|" ' +
                    file_path)
                cmds.append(
                    "sed -i 's|NovaVcpuPinSet:.*|NovaVcpuPinSet: \"" +
                    vcpu_pin_set +
                    "\"|' " +
                    file_path)
            # Performance and Optimization
            if innodb_buffer_pool_size != "dynamic":
                BufferPoolSize = int(innodb_buffer_pool_size.replace(
                    "G", ""))*1024
                memory_mb = ConfigOvercloud.get_minimum_memory_size("control")
                if memory_mb < BufferPoolSize:
                    raise Exception("innodb_buffer_pool_size is greater than"
                                    " available memory size")
            cmds.append(
                'sed -i "s|MysqlMaxConnections.*|MysqlMaxConnections: ' +
                mariadb_max_connections +
                '|" ' +
                file_path)
            if ovs_dpdk:
                f_path = dpdk_file
            else:
                f_path = file_path
            cmds.append(
                'sed -i "s|BufferPoolSize.*|BufferPoolSize: ' +
                innodb_buffer_pool_size +
                '|" ' +
                f_path)
            cmds.append(
                'sed -i "s|BufferPoolInstances.*|BufferPoolInstances: ' +
                innodb_buffer_pool_instances +
                '|" ' +
                f_path)
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
            # Create host object
            host_obj = hosts.HostManager(nova)

            # Get list of dell nfv nodes
            dell_hosts = []

            for host in host_obj.list():
                if "dell-compute" in host.host_name:
                    hostname = str(host.host_name)
                    dell_hosts.append(hostname)
            return dell_hosts
        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            logger.error(message)
            raise Exception("Failed to get the Dell Compute nodes.")

    def edit_aggregate_environment_file(
            self, hostname_list):
        logger.info("Editing create aggregate environment file")
        file_path = home_dir \
            + '/pilot/templates/create_aggregate_environment.yaml'
        if not os.path.isfile(file_path):
            raise Exception(
                "The create_aggregate_environment.yaml file does not exist")
        cmd = (
            'sed -i "s|hosts:.*|hosts: ' +
            str(hostname_list) +
            '|" ' +
            file_path)

        status = os.system(cmd)
        logger.info("cmd: {}".format(cmd))
        if status != 0:
            raise Exception(
                "Failed to execute the command {}"
                " with error code {}".format(
                    cmd, status))

    def create_aggregate(self):
        UC_AUTH_URL, UC_PROJECT_ID, UC_USERNAME, UC_PASSWORD = \
            CredentialHelper.get_overcloud_creds()
        # Create nova client object
        nova = nvclient.Client(
            2,
            UC_USERNAME,
            UC_PASSWORD,
            UC_PROJECT_ID,
            UC_AUTH_URL)
        hostname_list = self.get_dell_compute_nodes_hostnames(nova)
        self.edit_aggregate_environment_file(
            hostname_list)
        env_opts = \
            " -e ~/pilot/templates/create_aggregate_environment.yaml"

        cmd = self.overcloudrc + "openstack stack create " \
            " Dell_Aggregate" \
            " --template" \
            " ~/pilot/templates/overcloud/puppet/" \
            "services/dellnfv/createaggregate.yaml" \
            " {}" \
            "".format(env_opts)
        aggregate_create_status = os.system(cmd)
        if aggregate_create_status == 0:
            logger.info("Dell_Aggregate created")
        else:
            raise Exception(
                "Aggregate {} could not be created..."
                " Exiting post deployment tasks")

    def post_deployment_tasks(self):
        try:
            # Reboot all the Dell NFV compute nodes
            self.reboot_compute_nodes()

            logger.info("Initiating post deployment tasks")

            # create aggregate
            self.create_aggregate()

        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            raise Exception(message)
