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
import heatclient
from heatclient import client as heat_client
from heatclient import exc
from keystoneauth1.identity import v2
from keystoneauth1 import session
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
    get_drac_credentail = CredentialHelper()

    def __init__(self, overcloud_name):
        self.overcloud_name = overcloud_name

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
                        raise Exception("Hyperthreading is not enabled in "
                                        + str(node_uuid))
                        sys.exit(0)
                cpu_count_list.append(cpu_count)

            min_cpu_count = min(cpu_count_list)
            if min_cpu_count not in [40, 48, 56, 64, 72, 128]:
                raise Exception("CPU count should be one of these"
                                " values : [40,48,56,64,72,128]"
                                " But number of cpu is " + str(
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
            raise Exception("Failed to calculate "
                            "Numa Vcpu list {}".format(message))

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
            raise Exception("Failed to calculate"
                            " hugepage count {}".format(message))

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
        logger.info("cmd: {}".format(cmd))
        if status != 0:
            raise Exception(
                "Failed to execute the command {}"
                " with error code {}".format(
                    cmd, status))

    def create_aggregate(self):
        try:
            logger.info("Creating Aggregate..")
            stack_name = "Dell_Aggregate"
            OC_AUTH_URL, OC_PROJECT_ID, OC_USERNAME, OC_PASSWORD = \
                CredentialHelper.get_overcloud_creds()
            keystone_auth = v2.Password(username=OC_USERNAME,
                                        password=OC_PASSWORD,
                                        tenant_name=OC_PROJECT_ID,
                                        auth_url=OC_AUTH_URL)
            keystone_session = session.Session(auth=keystone_auth)
            kwargs = {'auth_url': OC_AUTH_URL,
                      'session': keystone_session,
                      'auth': keystone_auth,
                      'service_type': 'orchestration'}
            ht_client = heat_client.Client('1', **kwargs)
            try:
                file_path = home_dir \
                    + '/pilot/templates/overcloud/puppet/'\
                    "services/dellnfv/createaggregate.yaml"
                template = open(file_path)
            except Exception as error:
                message = "Exception {}: {}".format(
                    type(error).__name__, str(error))
                logger.error("{}".format(message))
                raise Exception("The createaggregate.yaml file does not exist")
            try:
                file_path = home_dir \
                    + '/pilot/templates/create_aggregate_environment.yaml'
                environment = open(file_path)
            except Exception as error:
                message = "Exception {}: {}".format(
                    type(error).__name__, str(error))
                logger.error("{}".format(message))
                raise Exception("The create_aggregate_environment.yaml"
                                "file does not exist")
            try:
                stack = ht_client.stacks.create(stack_name=stack_name,
                                                template=template.read(),
                                                environment=environment.read())
            except heatclient.exc.HTTPConflict as e:
                error_state = e.error
                raise Exception("Stack already exists : ",
                                error_state, stack_name)
            template.close()
            environment.close()
        except Exception as error:
            message = "Exception {}: {}".format(
                type(error).__name__, str(error))
            raise Exception("Aggregate could not be"
                            " created due to {}".format(message))

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
            raise Exception("{}".format(message))
