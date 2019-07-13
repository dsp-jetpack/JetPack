#!/usr/bin/python

# Copyright (c) 2016-2019 Dell Inc. or its subsidiaries.
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
from ironic_helper import IronicHelper
from logging_helper import LoggingHelper
from credential_helper import CredentialHelper
from dell_nfv import ConfigOvercloud
# Dell utilities
from identify_nodes import main as identify_nodes
from update_ssh_config import main as update_ssh_config
logging.basicConfig()
logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])

home_dir = os.path.expanduser('~')

BAREMETAL_FLAVOR = "baremetal"


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

    os_auth_url, os_tenant_name, os_username, os_password, \
        os_user_domain_name, os_project_domain_name = \
        CredentialHelper.get_overcloud_creds()

    kwargs = {'username': os_username,
              'password': os_password,
              'auth_url': os_auth_url,
              'project_name': os_tenant_name,
              'user_domain_name': os_user_domain_name,
              'project_domain_name': os_project_domain_name}
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
        types.append(["dellsc_backend", "dellsc"])

    if args.enable_unity:
        types.append(["unity_backend", "tripleo_dellemc_unity"])

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


def create_share_types():
    logger.info("Creating manila share types...")
    types = []

    if args.enable_unity_manila:
        types.append(["unity_share", "tripleo_manila_unity"])

    overcloudrc_name = CredentialHelper.get_overcloudrc_name()

    for type in types:
        type_name = type[0]
        cmd = "source {} && manila type-list | grep ' {} ' | " \
              "awk '{{print $4}}'".format(overcloudrc_name, type_name)
        proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
        return_output = proc.communicate()[0].strip()

        if type_name == return_output:
            logger.warning("Manila type exists, skipping {}".format(type[0]))
            continue
        else:
            logger.info("Creating manila share type {}".format(type[0]))
            cmd = "source {} && " \
                  "manila type-create --is_public True {} true && " \
                  "manila type-key {} set share_backend_name={}" \
                  "".format(overcloudrc_name, type[0], type[0], type[1])
            os.system(cmd)

    os.system("source {} && "
              "manila extra-specs-list".format(overcloudrc_name))


def run_deploy_command(cmd):
    status = os.system(cmd)

    if status == 0:
        stack_status = CredentialHelper.get_overcloud_stack_status()
        if not stack_status or 'FAILED' in stack_status:
            logger.info("\nDeployment failed even "
                        "though command returned success.")
            status = 1

    return status


def finalize_overcloud():
    # from keystone.v3 import client

    # os_auth_url, os_tenant_name, os_username, os_password = \
    #     CredentialHelper.get_overcloud_creds()

    # try:
    #     keystone_client = client.get_keystone_client(os_username,
    #                                                 os_password,
    #                                                 os_tenant_name,
    #                                                 os_auth_url)
    # except:
    #     return None

    create_flavors()
    create_volume_types()
    create_share_types()

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
                            dest="num_dell_computes",
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
                            default="1GB",
                            help="HugePages size")
        parser.add_argument("--hostos_cpu_count",
                            dest="hostos_cpu_count",
                            required=False,
                            default="4",
                            help="HostOs Cpus to be configured")
        parser.add_argument("--mariadb_max_connections",
                            dest="mariadb_max_connections",
                            required=False,
                            default="15360",
                            help="Maximum number of connections for MariaDB")
        parser.add_argument("--innodb_buffer_pool_size",
                            dest="innodb_buffer_pool_size",
                            required=False,
                            default="dynamic",
                            help="InnoDB buffer pool size")
        parser.add_argument("--innodb_buffer_pool_instances",
                            dest="innodb_buffer_pool_instances",
                            required=False,
                            default="16",
                            help="InnoDB buffer pool instances.")
        parser.add_argument('--enable_dellsc',
                            action='store_true',
                            default=False,
                            help="Enable cinder Dell Storage Center backend")
        parser.add_argument('--enable_unity',
                            action='store_true',
                            default=False,
                            help="Enable Dell EMC Unity backend")
        parser.add_argument('--enable_unity_manila',
                            action='store_true',
                            default=False,
                            help="Enable Dell EMC Unity Manila backend")
        parser.add_argument('--disable_rbd',
                            action='store_true',
                            default=False,
                            help="Disable cinder Ceph and rbd backend")
        parser.add_argument('--octavia_enable',
                            action='store_true',
                            default=False,
                            help="Enables Octavia Load Balancer")
        parser.add_argument('--octavia_user_certs_keys',
                            action='store_true',
                            default=False,
                            help="Enables Octavia Load Balancer with "
                                 "user provided certs and keys")
        parser.add_argument('--dvr_enable',
                            action='store_true',
                            default=False,
                            help="Enables Distributed Virtual Routing")
        parser.add_argument('--barbican_enable',
                            action='store_true',
                            default=False,
                            help="Enables Barbican key manager")
        parser.add_argument('--static_ips',
                            action='store_true',
                            default=False,
                            help="Specify the IPs on the overcloud nodes")
        parser.add_argument('--static_vips',
                            action='store_true',
                            default=False,
                            help="Specify the VIPs for the networks")
        parser.add_argument('--ovs_dpdk',
                            action='store_true',
                            default=False,
                            help="Enable OVS+DPDK")
        parser.add_argument('--sriov',
                            action='store_true',
                            default=False,
                            help="Enable SR-IOV")
        parser.add_argument('--hw_offload',
                            action='store_true',
                            default=False,
                            help="Enable SR-IOV Offload")
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
        parser.add_argument("--mtu",
                            dest="mtu",
                            type=int,
                            required=True,
                            default=1500,
                            help="Tenant Network MTU")
        LoggingHelper.add_argument(parser)
        args = parser.parse_args()
        LoggingHelper.configure_logging(args.logging_level)
        p = re.compile('\d+:\d+')  # noqa: W605
        if not p.match(args.vlan_range):
            raise ValueError("Error: The VLAN range must be a number followed "
                             "by a colon, followed by another number")
        os_auth_url, os_tenant_name, os_username, os_password, \
            os_user_domain_name, os_project_domain_name = \
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
        # logger.info("Applying patches to director...")
        # cmd = os.path.join(home_dir, 'pilot', 'patch-director.sh')
        # status = os.system(cmd)
        # if status != 0:
        #    raise ValueError("\nError: {} failed, unable to continue.  See "
        #                     "the comments in that file for additional "
        #                     "information".format(cmd))
        # Pass the parameters required by puppet which will be used
        # to enable/disable dell nfv features
        # Edit the dellnfv_environment.yaml
        # If disabled, default values will be set and
        # they won't be used for configuration
        # Create ConfigOvercloud object
        config = ConfigOvercloud(args.overcloud_name)
        # Remove this when Numa siblings added
        # Edit the dellnfv_environment.yaml
        config.edit_environment_files(
            args.mtu,
            args.enable_hugepages,
            args.enable_numa,
            args.hugepages_size,
            args.hostos_cpu_count,
            args.ovs_dpdk,
            args.sriov,
            nic_env_file,
            args.mariadb_max_connections,
            args.innodb_buffer_pool_size,
            args.innodb_buffer_pool_instances,
            args.num_controllers,
            args.num_storage,
            control_flavor,
            ceph_storage_flavor,
            swift_storage_flavor,
            block_storage_flavor,
            args.vlan_range,
            args.num_dell_computes
            )

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

        # The neutron-ovs-dvr.yaml.yaml must be included after the
        # network-environment.yaml
        if args.dvr_enable:
            env_opts += " -e ~/pilot/templates/neutron-ovs-dvr.yaml"

        # The configure-barbican.yaml must be included after the
        # network-environment.yaml
        if args.barbican_enable:
            env_opts += " -e ~/pilot/templates/configure-barbican.yaml"

        # The octavia.yaml must be included after the
        # network-environment.yaml
        if args.octavia_enable:
            env_opts += " -e ~/pilot/templates/octavia.yaml"
            if args.octavia_user_certs_keys is True:
                env_opts += " -e ~/pilot/templates/cert_keys.yaml"

        if args.node_placement:
            env_opts += " -e ~/pilot/templates/node-placement.yaml"

        # The dell-environment.yaml must be included after the
        # storage-environment.yaml and ceph-radosgw.yaml
        env_opts += " -e ~/pilot/templates/overcloud/environments/" \
                    "storage-environment.yaml" \
                    " -e ~/overcloud_images.yaml" \
                    " -e ~/pilot/templates/dell-environment.yaml" \
                    " -e ~/pilot/templates/overcloud/environments/" \
                    "puppet-pacemaker.yaml"
        host_config = False
        if args.enable_hugepages or args.enable_numa:
            env_opts += " -e ~/pilot/templates/overcloud/environments/" \
                        "host-config-and-reboot.yaml"
            host_config = True
        if args.ovs_dpdk:
            if not args.enable_hugepages or not args.enable_numa:
                raise ValueError("Both hugepages and numa must be" +
                                 "enabled in order to use OVS-DPDK")
            else:
                env_opts += " -e ~/pilot/templates/neutron-ovs-dpdk.yaml"

        if args.sriov:
            env_opts += " -e ~/pilot/templates/neutron-sriov.yaml"
            if args.hw_offload:
                env_opts += " -e ~/pilot/templates/ovs-hw-offload.yaml"
            if not host_config:
                env_opts += " -e ~/pilot/templates/overcloud/environments/" \
                            "host-config-and-reboot.yaml"

        if args.enable_dellsc:
            env_opts += " -e ~/pilot/templates/dell-cinder-backends.yaml"

        if args.enable_unity:
            env_opts += " -e ~/pilot/templates/dellemc-unity-cinder-" \
                        "backend.yaml"
        if args.enable_unity_manila:
            env_opts += " -e ~/pilot/templates/unity-manila-config.yaml"

        cmd = "cd ;source ~/stackrc; openstack overcloud deploy" \
              " {}" \
              " --log-file ~/pilot/overcloud_deployment.log" \
              " -t {}" \
              " {}" \
              " --templates ~/pilot/templates/overcloud" \
              " -e /usr/share/openstack-tripleo-heat-templates/" \
              "environments/ceph-ansible/ceph-ansible.yaml" \
              " -e /usr/share/openstack-tripleo-heat-templates/" \
              "environments/ceph-ansible/ceph-rgw.yaml" \
              " {}" \
              " --libvirt-type kvm" \
              " --ntp-server {}" \
              "".format(debug,
                        args.timeout,
                        overcloud_name_opt,
                        env_opts,
                        args.ntp_server_fqdn,
                        )

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
        logger.info('Fetching SSH keys...')

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
