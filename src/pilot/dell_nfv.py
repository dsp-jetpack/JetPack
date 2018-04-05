#!/usr/bin/python

# Copyright (c) 2016-2018 Dell Inc. or its subsidiaries.
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
logging.basicConfig()
logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

home_dir = os.path.expanduser('~')
# Dell nfv configuration global values
undercloudrc_file_name = "stackrc"
UC_USERNAME = UC_PASSWORD = UC_PROJECT_ID = UC_AUTH_URL = ''


class ConfigOvercloud(object):
    """
    Description: Class responsible for overcloud configurations.
    """
    ironic = IronicHelper()
    ironic_client = ironic.get_ironic_client()
    nodes = ironic_client.node.list()
    get_drac_credentail = CredentialHelper()

    def __init__(self, overcloud_name):
        self.overcloud_name = overcloud_name
        self.source_stackrc = "source ~/stackrc;"
        self.overcloudrc = "source " + home_dir + "/"\
            + self.overcloud_name + "rc;"

    @classmethod
    def get_undercloud_details(cls):
        try:
            global UC_USERNAME, UC_PASSWORD, UC_PROJECT_ID, UC_AUTH_URL
            file_path = home_dir + '/' + undercloudrc_file_name
            if not os.path.isfile(file_path):
                raise Exception(
                    "The Undercloud rc file does"
                    " not exist {}".format(file_path))

            with open(file_path) as rc_file:
                for line in rc_file:
                    if 'OS_USERNAME=' in line:
                        UC_USERNAME = line.split('OS_USERNAME=')[
                            1].strip("\n").strip("'")
                    elif 'OS_PASSWORD=' in line:
                        cmd = 'sudo hiera admin_password'
                        proc = subprocess.Popen(
                            cmd,
                            shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
                        output = proc.communicate()
                        output = output[0]
                        UC_PASSWORD = output[:-1]
                    elif 'OS_TENANT_NAME=' in line:
                        UC_PROJECT_ID = line.split('OS_TENANT_NAME=')[
                            1].strip("\n").strip("'")
                    elif 'OS_AUTH_URL=' in line:
                        UC_AUTH_URL = line.split('OS_AUTH_URL=')[
                            1].strip("\n").strip("'")
        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            logger.error("{}".format(message))
            raise Exception(
                "Failed to get undercloud details from"
                " the undercloud rc file {}".format(file_path))

    @classmethod
    def get_overcloud_details(cls, overcloud_name):
        try:
            global UC_USERNAME, UC_PASSWORD, UC_PROJECT_ID, UC_AUTH_URL
            file_path = home_dir + '/' + overcloud_name + "rc"
            if not os.path.isfile(file_path):
                raise Exception(
                    "The Overcloud rc file does"
                    " not exist {}".format(file_path))

            with open(file_path) as rc_file:
                for line in rc_file:
                    if 'OS_USERNAME' in line:
                        UC_USERNAME = line.split('OS_USERNAME=')[
                            1].strip("\n").strip("'")
                    elif 'OS_PASSWORD' in line:
                        UC_PASSWORD = line.split('OS_PASSWORD=')[
                            1].strip("\n").strip("'")
                    elif 'OS_PROJECT_NAME' in line:
                        UC_PROJECT_ID = line.split('OS_PROJECT_NAME=')[
                            1].strip("\n").strip("'")
                    elif 'OS_AUTH_URL' in line:
                        UC_AUTH_URL = line.split('OS_AUTH_URL=')[
                            1].strip("\n").strip("'")
        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            logger.error("{}".format(message))
            raise Exception(
                "Failed to get overcloud details from"
                " the overcloud rc file {}".format(file_path))

    def reboot_dell_nfv_nodes(self):
        try:
            logger.info("Rebooting dellnfv nodes")
            ConfigOvercloud.get_undercloud_details()
            # Create servers object
            nova = nvclient.Client(
                2,
                UC_USERNAME,
                UC_PASSWORD,
                UC_PROJECT_ID,
                UC_AUTH_URL)
            server_obj = servers.ServerManager(nova)
            for server in server_obj.list():
                if "dell-compute" in str(server):
                    server_obj.reboot(server)
        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            raise Exception("Failed to reboot dell nfv nodes with error {}".format(
                message))

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
                    ConfigOvercloud.get_drac_credentail.get_drac_creds(
                        ConfigOvercloud.ironic_client, node_uuid)
                stor = client.DRACClient(drac_ip, drac_user, drac_password)
                # cpu socket information for every compute node
                sockets = stor.list_cpus()
                cpu_count = 0
                for socket in sockets:
                    if socket.ht_enabled:
                        cpu_count += socket.cores * 2
                    else:
			            raise Exception("Hyperthreading is not enabled in " + \
                            str(node_uuid) + ". So exiting the code execution.")
                        sys.exit(0)
                cpu_count_list.append(cpu_count)

            min_cpu_count = min(cpu_count_list)
            if min_cpu_count not in [40, 48, 64, 72, 128]:
			    raise Exception("CPU count should be one of these" \
                    " values : [40,48,64,72,128]. But number of cpu is " + str(
                        min_cpu_count))
                sys.exit(0)
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
            raise Exception("Failed to calculate Numa Vcpu list {}".format(message))

    @classmethod
    def calculate_hugepage_count(self, hugepage_size):
        try:

            pages = []

            for node in ConfigOvercloud.nodes:
                node_uuid = node.uuid  # uuid of a node
                node_details = ConfigOvercloud.ironic_client.node.get(
                    node_uuid)  # details of a node
                memory_count = node_details.properties['memory_mb']
                node_properties_capabilities = \
                    node_details.properties['capabilities'].split(',')[
                        0].split(':')[1]
                if 'compute' in node_properties_capabilities:
                    # Subtracting
                    # 16384MB = (Host Memory 12GB + Kernel Memory 4GB)
                    memory_count = (memory_count - 16384)
                    if hugepage_size == "2MB":
                        pages.append((memory_count / 2))
                    if hugepage_size == "1GB":
                        pages.append((memory_count / 1024))
            logger.info("hugepage_count {}".format(min(pages)))
            return min(pages)
        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            raise Exception("Failed to calculate hugepage count {}".format(message))

    def edit_dell_environment_file(
            self,
            enable_hugepage,
            enable_numa,
            hugepage_size,
            hostos_cpu_count,
            dell_compute_count=0):
        try:
            logger.info("Editing dell environment file")
            file_path = home_dir + '/pilot/templates/dell-environment.yaml'
            if not os.path.isfile(file_path):
                raise Exception(
                    "The dell-environment.yaml file does not exist")
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

            for cmd in cmds:
                status = os.system(cmd)
                logger.debug("cmd: {}".format(cmd))
            if status != 0:
                raise Exception(
                    "Failed to execute the command {}"
                    " with error code {}".format(
                        cmd, status))

        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            logger.error("{}".format(message))
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
            logger.error("{}".format(message))
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
        print "cmd: {}".format(cmd)
        if status != 0:
            raise Exception(
                "Failed to execute the command {}"
                " with error code {}".format(
                    cmd, status))

    def create_aggregates(self, aggr_name):
        env_opts = \
            " -e ~/pilot/templates/create_aggregate_environment.yaml"

        cmd = self.overcloudrc + "openstack stack create " \
            " {}" \
            " --template" \
            " ~/pilot/templates/overcloud/puppet/" \
            "services/dellnfv/createaggregate.yaml" \
            " {}" \
            "".format(aggr_name,
                      env_opts)
        aggregate_create_status = os.system(cmd)
        if aggregate_create_status == 0:
            logger.info("Aggregate {} created".format(aggr_name))
        else:
            raise Exception(
                "Aggregate {} could not be created..."
                " Exiting post deployment tasks".format(aggr_name))
            sys.exit(0)

    def set_aggregate_metadata(self):
        try:
            # Get the overcloud details
			aggregate_name = "Dell_Aggr"
            ConfigOvercloud.get_overcloud_details(self.overcloud_name)

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
            self.create_aggregates(aggregate_name)
        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            logger.error("{}".format(message))
            raise Exception(
                "Unable to set aggregate metadata."
                " Exiting post deployment task...")
            sys.exit(0)

    def post_deployment_tasks(self, enable_hugepages, enable_numa, hpg_size):
        try:
            # Reboot all the Dell NFV compute nodes
            self.reboot_dell_nfv_nodes()

            # Wait for 5 mins to let dll nfv nodes boot up
            time.sleep(300)

            logger.info("Initiating post deployment tasks")

            # create aggregate
            self.set_aggregate_metadata()

        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            raise Exception("{}".format(message))
