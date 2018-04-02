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

import argparse
import distutils.dir_util
import os
import re
import sys
import subprocess
import paramiko
import logging
import string
import novaclient.client as nova_client
import time
from command_helper import Ssh
from novaclient.v2 import aggregates
from novaclient.v2 import hosts
from novaclient.v2 import servers
from ironic_helper import IronicHelper
from logging_helper import LoggingHelper

from credential_helper import CredentialHelper

# Dell utilities
from identify_nodes import main as identify_nodes
from update_ssh_config import main as update_ssh_config

logging.basicConfig()
logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])

home_dir = os.path.expanduser('~')

BAREMETAL_FLAVOR = "baremetal"

# Maximum possible value of cpu cores at present.
# It can be updated as per node configuration.
compute_cpu = "47"
vcpu_pin_set = "8-" + compute_cpu


class ConfigOvercloud(object):
    """
    Description: Class responsible for overcloud configurations.
    """

    def __init__(self, nova):
        self.nova = nova
        self.aggregate_obj = aggregates.AggregateManager(self.nova)

    def create_aggregate(self, aggregate_name, availability_zone=None):
        try:
            logger.info("Creating aggregate")
            aggregate = self.aggregate_obj.create(aggregate_name,
                                                  availability_zone)
            return aggregate
        except Exception as error:
            message = "Exception {}: {}".\
                      format(type(error).__name__, str(error))
            logger.error("{}".format(message))
            raise Exception("Failed to create \
                  aggregate {}".format(aggregate_name))

    def set_aggregate_metadata(self, aggregate_id, aggregate_metadata):
        try:
            logger.info("Setting aggregate metadata")
            for metadata in aggregate_metadata:
                self.aggregate_obj.set_metadata(aggregate_id, metadata)
        except Exception as error:
            message = "Exception {}: {}".\
                      format(type(error).__name__, str(error))
            logger.error("{}".format(message))
            raise Exception("Failed to set aggregate metadata \
                  for aggregate with ID {}".format(aggregate_id))

    def add_hosts_to_aggregate(self, aggregate_id, host_name_list):
        try:
            logger.info("Adding host to aggregate")
            for host in host_name_list:
                self.aggregate_obj.add_host(aggregate_id, host)
        except Exception as error:
            message = "Exception {}: {}".\
                      format(type(error).__name__, str(error))
            logger.error("{}".format(message))
            raise Exception("Failed to add hosts {} to aggregate \
                  with ID {}".format(host_name_list, aggregate_id))

    def get_dell_compute_nodes_hostnames(self):
        try:
            logger.info("Getting compute node hostnames")

            # Create host object
            host_obj = hosts.HostManager(self.nova)

            # Get list of dell nfv nodes
            dell_hosts = []
            for host in host_obj.list():
                if "dell-compute" in host.host_name:
                    dell_hosts.append(host.host_name)
            return dell_hosts
        except Exception as error:
            message = "Exception {}: {}".\
                      format(type(error).__name__, str(error))
            logger.error("{}".format(message))
            raise Exception("Failed to get the Dell Compute nodes.")

    def configure_dell_aggregate(self,
                                 aggregate_name,
                                 aggregate_metadata,
                                 host_name_list=None):
        try:
            logger.info("Configuring dell aggregate")

            # Create aggregate
            aggregate_id = self.create_aggregate(aggregate_name)

            # Set aggregate metadata
            self.set_aggregate_metadata(aggregate_id, aggregate_metadata)

            if host_name_list:
                # Add hosts to aggregate
                self.add_hosts_to_aggregate(aggregate_id, host_name_list)
        except Exception as error:
            message = "Exception {}: {}".\
                      format(type(error).__name__, str(error))
            logger.error("{}".format(message))
            raise Exception("Failed to configure \
                            dell aggregate {}.".format(aggregate_name))

    def get_controller_nodes(self):
        try:
            logger.info("Getting controller nodes")

            # Create servers object
            server_obj = servers.ServerManager(self.nova)

            # Get list of all controller nodes
            controller_nodes = []
            for server in server_obj.list():
                if "control" in server.name:
                    controller_nodes.append(str(server_obj.ips(server)
                                            ['ctlplane'][0]['addr']))
            return controller_nodes
        except Exception as error:
            message = "Exception {}: {}".\
                      format(type(error).__name__, str(error))
            logger.error("{}".format(message))
            raise Exception("Failed to get the list of controller nodes.")

    def get_dell_compute_nodes(self):
        try:
            logger.info("Getting dell compute nodes")

            # Create servers object
            server_obj = servers.ServerManager(self.nova)

            # Get list of all dell compute nodes
            dell_compute_nodes = []
            for server in server_obj.list():
                if "dell-compute" in server.name:
                    dell_compute_nodes.append(((str(server_obj.ips(server)
                                                ['ctlplane'][0]['addr']),
                                                server.id)))

            return dell_compute_nodes
        except Exception as error:
            message = "Exception {}: {}".\
                      format(type(error).__name__, str(error))
            logger.error("{}".format(message))
            raise Exception("Failed to get the list of dell_compute nodes.")

    def get_dell_compute_nodes_uuid(self):
        try:
            logger.info("Getting dell compute nodes uuid")
            server_obj = servers.ServerManager(self.nova)
            logger.info("Getting list of all dell compute nodes")
            dell_compute_nodes_uuid = []
            for server in server_obj.list():
                if "dell-compute" in server.name:
                    dell_compute_nodes_uuid.append(server.id)

            return dell_compute_nodes_uuid
        except Exception as error:
            message = "Exception {}: {}".\
                      format(type(error).__name__, str(error))
            logger.error("{}".format(message))
            raise Exception("Failed to get " +
                            "the list of dell_compute nodes uuid.")


def edit_dell_environment_file(enable_hugepages,
                               enable_numa,
                               hugepages_size,
                               vcpu_pin_set,
                               dell_compute_count):
    try:
        logger.info("Editing dell environment file")
        file_path = home_dir + '/pilot/templates/dell-environment.yaml'
        if not os.path.isfile(file_path):
            raise Exception("The dell-environment.yaml file does not exist")

        # Updating the filters including NUMATopologyFilter
        # and NovaAggregateInstanceFilter
        cmds = ['sed -i "s|  # NovaSchedulerDefaultFilters|  ' +
                'NovaSchedulerDefaultFilters|" ' +
                file_path]

        cmds.append('sed -i "s|dellnfv::hugepages::enable:.*|' +
                    'dellnfv::hugepages::enable: ' +
                    str(enable_hugepages) +
                    '|" ' +
                    file_path)

        cmds.append('sed -i "s|dellnfv::numa::enable:.*|' +
                    'dellnfv::numa::enable: ' +
                    str(enable_numa) +
                    '|" ' +
                    file_path)

        cmds.append('sed -i "s|DellComputeCount:.*|' +
                    'DellComputeCount: ' +
                    str(dell_compute_count) +
                    '|" ' +
                    file_path)

        if hugepages_size == "2MB":
            hugepages_number = 49152
        elif hugepages_size == "1GB":
            hugepages_number = 96

        if enable_hugepages:
            cmds.append('sed -i "s|dellnfv::hugepages::hugepagesize:.*|' +
                        'dellnfv::hugepages::hugepagesize: ' +
                        hugepages_size[0:-1] +
                        '|" ' +
                        file_path)
            cmds.append('sed -i "s|dellnfv::hugepages::hugepagecount:.*|' +
                        'dellnfv::hugepages::hugepagecount: ' +
                        str(hugepages_number) +
                        '|" ' +
                        file_path)
        if enable_numa:
            cmds.append('sed -i "s|  # NovaVcpuPinSet|  ' +
                        'NovaVcpuPinSet|" ' +
                        file_path)

        for cmd in cmds:
            status = os.system(cmd)
            logger.debug("cmd: {}".format(cmd))
            if status != 0:
                raise Exception("Failed to execute the command {} "
                                "with error code {}".format(cmd, status))
    except Exception as error:
        message = "Exception {}: {}".format(type(error).__name__, str(error))
        logger.error("{}".format(message))
        raise Exception("Failed to modify the dell-environment.yaml "
                        "at location {}".format(file_path))


def create_aggregates(enable_hugepages, enable_numa, overcloud_name):
    host_name_list = []
    try:
        if enable_hugepages or enable_numa:
            logger.info("Creating aggregates")

            # Get overcloud details
            os_auth_url, os_tenant_name, os_username, os_password = \
                CredentialHelper.get_overcloud_creds()

            kwargs = {'username': os_username,
                      'password': os_password,
                      'auth_url': os_auth_url,
                      'project_id': os_tenant_name}

            # Create nova client object
            nova = nova_client.Client(2, **kwargs)

            # Create the ConfigOvercloud object
            config_oc_obj = ConfigOvercloud(nova)
            host_name_list = config_oc_obj.get_dell_compute_nodes_hostnames()
            # Create aggregate for numa configuration
            try:
                if enable_numa:
                    aggregate_name = "Numa_Aggr"
                    aggregate_meta = [{'pinned': 'True'}]
                    config_oc_obj.configure_dell_aggregate(aggregate_name,
                                                           aggregate_meta,
                                                           host_name_list)
            except Exception as error:
                message = "Exception {}: {}".format(type(error).__name__,
                                                    str(error))
                logger.error("{}".format(message))

            # Create aggregate for hugepages configuration
            try:
                if enable_hugepages:
                    aggregate_name = "HugePage_Aggr"
                    aggregate_meta = [{'hugepages': 'True'}]
                    config_oc_obj.configure_dell_aggregate(aggregate_name,
                                                           aggregate_meta,
                                                           host_name_list)
            except Exception as error:
                message = "Exception {}: {}".format(type(error).__name__,
                                                    str(error))
                logger.error("{}".format(message))

            # Create normal aggregate
            aggregate_name = "Normal_Aggr"
            aggregate_meta = [{'pinned': 'False'}, {'hugepages': 'False'}]
            config_oc_obj.configure_dell_aggregate(aggregate_name,
                                                   aggregate_meta)
    except Exception as error:
        message = "Exception {}: {}".format(type(error).__name__, str(error))
        logger.error("{}".format(message))


def get_dell_compute_nodes_uuids():
    logger.info("Getting dell compute node uuids")
    # Get the undercloud details
    os_auth_url, os_tenant_name, os_username, os_password = \
        CredentialHelper.get_undercloud_creds()

    kwargs = {'username': os_username,
              'password': os_password,
              'auth_url': os_auth_url,
              'project_id': os_tenant_name}

    # Create nova client object
    nova = nova_client.Client(2, **kwargs)

    # Create the ConfigOvercloud object
    config_oc_obj = ConfigOvercloud(nova)
    dell_compute_nodes_uuid = config_oc_obj.get_dell_compute_nodes_uuid()
    logger.debug("dell_compute_nodes_uuid: {}".format(dell_compute_nodes_uuid))
    return dell_compute_nodes_uuid


def reboot_compute_nodes():
    logger.info("Rebooting dell compute nodes")
    # Get the undercloud details
    os_auth_url, os_tenant_name, os_username, os_password = \
        CredentialHelper.get_undercloud_creds()

    kwargs = {'username': os_username,
              'password': os_password,
              'auth_url': os_auth_url,
              'project_id': os_tenant_name}

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
                logger.info("Server with IP: {} is not responsive".format(ip))
            else:
                logger.info("Server with IP: {} is responsive".format(ip))
                ssh_success_count += 1
                break

            # Waiting 10s before the next attempt
            time.sleep(10)

    if ssh_success_count == len(dell_compute):
        logger.info("All compute nodes are now responsive. Continuing...")
    else:
        logger.error("Failed to reboot the nodes or at least one node failed "
                     "to get back up")
        raise Exception("At least one compute node failed to reboot")


# Check to see if the sequence contains numbers that increase by 1
def is_coherent(seq):
    return seq == range(seq[0], seq[-1]+1)


def validate_node_placement():
    logger.info("Validating node placement...")

    # For each role/flavor, node indices must start at 0 and increase by 1
    ironic = IronicHelper.get_ironic_client()

    flavor_to_indices = {}
    for node in ironic.node.list(detail=True):
        # Skip nodes that are in maintenance mode
        if node.maintenance:
            continue

        # Get the value of the "node" capability
        node_capability = None
        capabilities = node.properties["capabilities"]
        for capability in capabilities.split(","):
            (key, val) = capability.split(":")
            if key == "node":
                node_capability = val

        # If the node capability was not set then error out
        if not node_capability:
            ip, _ = CredentialHelper.get_drac_ip_and_user(node)

            raise ValueError("Error: Node {} has not been assigned a node "
                             "placement index.  Run assign_role for this "
                             "node and specify a role with the "
                             "<role>-<index> format".format(ip))

        hyphen = node_capability.rfind("-")
        flavor = node_capability[0:hyphen]
        index = node_capability[hyphen + 1:]

        # Build up a dict that maps a flavor name to a sequence of placment
        # indices
        if flavor not in flavor_to_indices:
            flavor_to_indices[flavor] = []

        flavor_to_indices[flavor].append(int(index))

    # Validate that the sequence starts at zero and is coherent
    error_msg = ''
    for flavor in flavor_to_indices.keys():
        flavor_to_indices[flavor].sort()
        seq = flavor_to_indices[flavor]
        if seq[0] != 0:
            error_msg += "Error: There must be a node with flavor \"{}\" " \
                "that has node placement index 0.  Current nodes placement " \
                "indices are {}\n".format(flavor, str(seq))

        if not is_coherent(seq):
            error_msg += "Error: Nodes that have been assigned the \"{}\" " \
                "flavor do not have node placement indices that increase by " \
                "1.  Current node indices are {}\n".format(flavor, str(seq))

    # If any errors were detected then bail
    if error_msg:
        raise ValueError(error_msg)


def create_flavors():
    logger.info("Creating overcloud flavors...")

    flavors = [
        {"id": "1", "name": "m1.tiny",   "memory": 512,   "disk": 1,
         "cpus": 1},
        {"id": "2", "name": "m1.small",  "memory": 2048,  "disk": 20,
         "cpus": 1},
        {"id": "3", "name": "m1.medium", "memory": 4096,  "disk": 40,
         "cpus": 2},
        {"id": "4", "name": "m1.large",  "memory": 8192,  "disk": 80,
         "cpus": 4},
        {"id": "5", "name": "m1.xlarge", "memory": 16384, "disk": 160,
         "cpus": 8}]

    os_auth_url, os_tenant_name, os_username, os_password = \
        CredentialHelper.get_overcloud_creds()

    kwargs = {'username': os_username,
              'password': os_password,
              'auth_url': os_auth_url,
              'project_id': os_tenant_name}
    n_client = nova_client.Client(2, **kwargs)

    existing_flavor_ids = []
    for existing_flavor in n_client.flavors.list(detailed=False):
        existing_flavor_ids.append(existing_flavor.id)

    for flavor in flavors:
        if flavor["id"] not in existing_flavor_ids:
            print '    Creating ' + flavor["name"]
            n_client.flavors.create(flavor["name"], flavor["memory"],
                                    flavor["cpus"], flavor["disk"],
                                    flavorid=flavor["id"])
        else:
            print '    Flavor ' + flavor["name"] + " already exists"


def create_volume_types():
    logger.info("Creating cinder volume types...")
    types = []
    if not args.disable_rbd:
        types.append(["rbd_backend", "tripleo_ceph"])

    if args.enable_dellsc:
        cinder_file = open(home_dir +
                           '/pilot/templates/dell-cinder-backends.yaml', 'r')
        for line in cinder_file:
            line = line.strip()
            try:
                found = re.search('cinder_user_enabled_backends: \[(.+?)\]',
                                  line).group(1)
                backends = found.split(",")
                for backend in backends:
                    types.append([backend + "_backend", backend])
            except AttributeError:
                found = ''

    overcloudrc_name = CredentialHelper.get_overcloudrc_name()

    for type in types:
        type_name = type[0]
        cmd = "source {} && cinder type-list | grep ' {} ' | " \
              "awk '{{print $4}}'".format(overcloudrc_name, type_name)
        proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
        return_output = proc.communicate()[0].strip()

        if type_name == return_output:
            logger.warning("Cinder type exists, skipping {}".format(type[0]))
            continue
        else:
            logger.info("Creating cinder type {}".format(type[0]))
            cmd = "source {} && " \
                  "cinder type-create {} && " \
                  "cinder type-key {} set volume_backend_name={}" \
                  "".format(overcloudrc_name, type[0], type[0], type[1])
            os.system(cmd)

    os.system("source {} && "
              "cinder extra-specs-list".format(overcloudrc_name))


def run_deploy_command(cmd):
    status = os.system(cmd)

    if status == 0:
        stack = CredentialHelper.get_overcloud_stack()
        if not stack or 'FAILED' in stack.stack_status:
            logger.info("\nDeployment failed even "
                        "though command returned success.")
            status = 1

    return status


def finalize_overcloud():
    from os_cloud_config.utils import clients

    os_auth_url, os_tenant_name, os_username, os_password = \
        CredentialHelper.get_overcloud_creds()

    try:
        keystone_client = clients.get_keystone_client(os_username,
                                                      os_password,
                                                      os_tenant_name,
                                                      os_auth_url)
    except:
        return None

    create_flavors()
    create_volume_types()
    create_aggregates(args.enable_hugepages, args.enable_numa,
                      args.overcloud_name)
    reboot_compute_nodes()

    # horizon_service = keystone_client.services.find(**{'name': 'horizon'})
    # horizon_endpoint = keystone_client.endpoints.find(
    #     **{'service_id': horizon_service.id})
    # return horizon_endpoint.publicurl
    return None


def main():
    try:
        global args
        parser = argparse.ArgumentParser()
        parser.add_argument("--controllers",
                            dest="num_controllers",
                            type=int,
                            default=3,
                            help="The number of controller nodes")
        parser.add_argument("--dell-computes",
                            dest="num_computes",
                            type=int,
                            required=True,
                            help="The number of dell compute nodes")
        parser.add_argument("--storage",
                            dest="num_storage",
                            type=int,
                            required=True,
                            help="The number of storage nodes")
        parser.add_argument("--enable_hugepages",
                            action='store_true',
                            default=False,
                            help="Enable/Disable hugepages feature")
        parser.add_argument("--enable_numa",
                            action='store_true',
                            default=False,
                            help="Enable/Disable numa feature")
        parser.add_argument("--vlans",
                            dest="vlan_range",
                            required=True,
                            help="The VLAN range to use for Neutron in "
                                 " xxx:yyy format")
        parser.add_argument("--nic_env_file",
                            default="5_port/nic_environment.yaml",
                            help="The NIC environment file to use")
        parser.add_argument("--ntp",
                            dest="ntp_server_fqdn",
                            default="0.centos.pool.ntp.org",
                            help="The FQDN of the ntp server to use")
        parser.add_argument("--timeout",
                            default="120",
                            help="The amount of time in minutes to allow the "
                                 "overcloud to deploy")
        parser.add_argument("--overcloud_name",
                            default=None,
                            help="The name of the overcloud")
        parser.add_argument("--hugepages_size",
                            dest="hugepages_size",
                            required=False,
                            help="HugePages size")
        parser.add_argument('--enable_dellsc',
                            action='store_true',
                            default=False,
                            help="Enable cinder Dell Storage Center backend")
        parser.add_argument('--disable_rbd',
                            action='store_true',
                            default=False,
                            help="Disable cinder Ceph and rbd backend")
        parser.add_argument('--static_ips',
                            action='store_true',
                            default=False,
                            help="Specify the IPs on the overcloud nodes")
        parser.add_argument('--static_vips',
                            action='store_true',
                            default=False,
                            help="Specify the VIPs for the networks")
        parser.add_argument('--node_placement',
                            action='store_true',
                            default=False,
                            help="Control which physical server is assigned "
                                 "which instance")
        parser.add_argument("--debug",
                            default=False,
                            action='store_true',
                            help="Indicates if the deploy-overcloud script "
                                 "should be run in debug mode")

        LoggingHelper.add_argument(parser)

        args = parser.parse_args()

        LoggingHelper.configure_logging(args.logging_level)

        p = re.compile('\d+:\d+')
        if not p.match(args.vlan_range):
            raise ValueError("Error: The VLAN range must be a number followed "
                             "by a colon, followed by another number")

        os_auth_url, os_tenant_name, os_username, os_password = \
            CredentialHelper.get_undercloud_creds()

        # Set up the default flavors
        control_flavor = "control"
        ceph_storage_flavor = "ceph-storage"
        swift_storage_flavor = "swift-storage"
        block_storage_flavor = "block-storage"

        if args.node_placement:
            validate_node_placement()

            # If node-placement is specified, then the baremetal flavor must
            # be used
            control_flavor = BAREMETAL_FLAVOR
            ceph_storage_flavor = BAREMETAL_FLAVOR
            swift_storage_flavor = BAREMETAL_FLAVOR
            block_storage_flavor = BAREMETAL_FLAVOR

        # Validate that the NIC envronment file exists
        nic_env_file = os.path.join(home_dir,
                                    "pilot/templates/nic-configs",
                                    args.nic_env_file)
        if not os.path.isfile(nic_env_file):
            raise ValueError("\nError: The nic_env_file {} does not "
                             "exist!".format(nic_env_file))

        # Apply any patches required on the Director itself. This is done each
        # time the overcloud is deployed (instead of once, after the Director
        # is installed) in order to ensure an update to the Director doesn't
        # overwrite the patch.
        logger.info("Applying patches to director...")
        cmd = os.path.join(home_dir, 'pilot', 'patch-director.sh')
        status = os.system(cmd)
        if status != 0:
            raise ValueError("\nError: {} failed, unable to continue.  See "
                             "the comments in that file for additional "
                             "information".format(cmd))
        # Pass the parameters required by puppet which will be used
        # to enable/disable dell nfv features
        # Edit the dellnfv_environment.yaml
        # If disabled, default values will be set and
        # they won't be used for configuration
        edit_dell_environment_file(args.enable_hugepages, args.enable_numa,
                                   args.hugepages_size, vcpu_pin_set,
                                   args.num_computes)

        # Launch the deployment

        overcloud_name_opt = ""
        if args.overcloud_name is not None:
            overcloud_name_opt = "--stack " + args.overcloud_name

        debug = ""
        if args.debug:
            debug = "--debug"

        # The order of the environment files is important as a later inclusion
        # overrides resources defined in prior inclusions.

        # The roles_data.yaml must be included at the beginning.
        # This is needed to enable the custome role Dell Compute.
        # It overrides the default roles_data.yaml
        env_opts = "-r ~/pilot/templates/roles_data.yaml"

        # The network-environment.yaml must be included after the
        # network-isolation.yaml
        env_opts += " -e ~/pilot/templates/overcloud/environments/" \
                    "network-isolation.yaml" \
                    " -e ~/pilot/templates/network-environment.yaml" \
                    " -e {}" \
                    " -e ~/pilot/templates/ceph-osd-config.yaml" \
                    "".format(nic_env_file)

        # The static-ip-environment.yaml must be included after the
        # network-environment.yaml
        if args.static_ips:
            env_opts += " -e ~/pilot/templates/static-ip-environment.yaml"

        # The static-vip-environment.yaml must be included after the
        # network-environment.yaml
        if args.static_vips:
            env_opts += " -e ~/pilot/templates/static-vip-environment.yaml"

        if args.node_placement:
            env_opts += " -e ~/pilot/templates/node-placement.yaml"

        # The dell-environment.yaml must be included after the
        # storage-environment.yaml and ceph-radosgw.yaml
        env_opts += " -e ~/pilot/templates/overcloud/environments/" \
                    "storage-environment.yaml" \
                    " -e ~/pilot/templates/overcloud/environments/" \
                    "ceph-radosgw.yaml" \
                    " -e ~/pilot/templates/dell-environment.yaml" \
                    " -e ~/pilot/templates/overcloud/environments/" \
                    "puppet-pacemaker.yaml"

        if args.enable_dellsc:
            env_opts += " -e ~/pilot/templates/dell-cinder-backends.yaml"

        cmd = "cd ; openstack overcloud deploy" \
              " {}" \
              " --log-file ~/pilot/overcloud_deployment.log" \
              " -t {}" \
              " {}" \
              " --templates ~/pilot/templates/overcloud" \
              " {}" \
              " --control-flavor {}" \
              " --ceph-storage-flavor {}" \
              " --swift-storage-flavor {}" \
              " --block-storage-flavor {}" \
              " --neutron-public-interface bond1" \
              " --neutron-network-type vlan" \
              " --neutron-disable-tunneling" \
              " --libvirt-type kvm" \
              " --os-auth-url {}" \
              " --os-project-name {}" \
              " --os-user-id {}" \
              " --os-password {}" \
              " --control-scale {}" \
              " --ceph-storage-scale {}" \
              " --ntp-server {}" \
              " --neutron-network-vlan-ranges physint:{},physext" \
              " --neutron-bridge-mappings physint:br-tenant,physext:br-ex" \
              "".format(debug,
                        args.timeout,
                        overcloud_name_opt,
                        env_opts,
                        control_flavor,
                        ceph_storage_flavor,
                        swift_storage_flavor,
                        block_storage_flavor,
                        os_auth_url,
                        os_tenant_name,
                        os_username,
                        os_password,
                        args.num_controllers,
                        args.num_storage,
                        args.ntp_server_fqdn,
                        args.vlan_range)

        with open(os.path.join(home_dir, 'pilot', 'overcloud_deploy_cmd.log'),
                  'w') as f:
            f.write(cmd.replace(' -', ' \\\n -'))
            f.write('\n')
        print cmd
        start = time.time()
        status = run_deploy_command(cmd)
        end = time.time()
        logger.info('\nExecution time: {} (hh:mm:ss)'.format(
            time.strftime('%H:%M:%S', time.gmtime(end - start))))
        print 'Fetching SSH keys...'
        update_ssh_config()
        if status == 0:
            horizon_url = finalize_overcloud()
            logger.info("\nDeployment Completed")
        else:
            horizon_url = None
        logger.info('Overcloud nodes:')
        identify_nodes()

        if horizon_url:
            logger.info('\nHorizon Dashboard URL: {}\n'.format(horizon_url))
    except Exception as err:
        print >> sys.stderr, err
        sys.exit(1)

if __name__ == "__main__":
    main()
