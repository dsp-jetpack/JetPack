#!/usr/bin/python

# Copyright (c) 2016 Dell Inc. or its subsidiaries.
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
import time
import novaclient.client as nova_client
from ironic_helper import IronicHelper

from credential_helper import CredentialHelper

# Dell utilities
from identify_nodes import main as identify_nodes
from update_ssh_config import main as update_ssh_config

home_dir = os.path.expanduser('~')

BAREMETAL_FLAVOR = "baremetal"


# Check to see if the sequence contains numbers that increase by 1
def is_coherent(seq):
    return seq == range(seq[0], seq[-1]+1)


def validate_node_placement():
    print 'Validating node placement...'

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
    print 'Creating overcloud flavors...'

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
    print 'Creating cinder volume types...'
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
        type_name= type[0]
        cmd = "source {} && cinder type-list | grep ' {} ' | awk '{{print $4}}'".format(overcloudrc_name, type_name)
        proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
        return_output = proc.communicate()[0].strip()

        if type_name == return_output:
            print "Cinder type exists, skipping {}".format(type[0])
            continue
        else:
            print "Creating cinder type {}".format(type[0])
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
            print '\nDeployment failed even though command returned success.'
            status = 1

    return status


def finalize_overcloud():
    from keystoneclient.v3 import client

    os_auth_url, os_tenant_name, os_username, os_password = \
        CredentialHelper.get_overcloud_creds()

    try:
        keystone_client = client.get_keystone_client(os_username,
                                                      os_password,
                                                      os_tenant_name,
                                                      os_auth_url)
    except:
        return None

    create_flavors()
    create_volume_types()

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
        parser.add_argument("--computes",
                            dest="num_computes",
                            type=int,
                            required=True,
                            help="The number of compute nodes")
        parser.add_argument("--storage",
                            dest="num_storage",
                            type=int,
                            required=True,
                            help="The number of storage nodes")
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
        args = parser.parse_args()
        os_auth_url, os_tenant_name, os_username, os_password = \
            CredentialHelper.get_undercloud_creds()

        # Set up the default flavors
        control_flavor = "control"
        compute_flavor = "compute"
        ceph_storage_flavor = "ceph-storage"
        swift_storage_flavor = "swift-storage"
        block_storage_flavor = "block-storage"

        if args.node_placement:
            validate_node_placement()

            # If node-placement is specified, then the baremetal flavor must
            # be used
            control_flavor = BAREMETAL_FLAVOR
            compute_flavor = BAREMETAL_FLAVOR
            ceph_storage_flavor = BAREMETAL_FLAVOR
            swift_storage_flavor = BAREMETAL_FLAVOR
            block_storage_flavor = BAREMETAL_FLAVOR

        # Apply any patches required on the Director itself. This is done each
        # time the overcloud is deployed (instead of once, after the Director
        # is installed) in order to ensure an update to the Director doesn't
        # overwrite the patch.
        print 'Applying patches to director...'
        cmd = os.path.join(home_dir, 'pilot', 'patch-director.sh')
        status = os.system(cmd)
        if status != 0:
            raise ValueError("\nError: {} failed, unable to continue.  See "
                             "the comments in that file for additional "
                             "information".format(cmd))

        # Launch the deployment

        overcloud_name_opt = ""
        if args.overcloud_name is not None:
            overcloud_name_opt = "--stack " + args.overcloud_name

        debug = ""
        if args.debug:
            debug = "--debug"

        # The order of the environment files is important as a later inclusion
        # overrides resources defined in prior inclusions.

        # The network-environment.yaml must be included after the
        # network-isolation.yaml
        env_opts = "-e ~/pilot/templates/overcloud/environments/" \
                   "network-isolation.yaml" \
                   " -e ~/pilot/templates/network-environment.yaml" \
                   " -e ~/pilot/templates/ceph-osd-config.yaml"

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
              " --compute-flavor {}" \
              " --ceph-storage-flavor {}" \
              " --swift-storage-flavor {}" \
              " --block-storage-flavor {}" \
              " --libvirt-type kvm" \
              " --os-auth-url {}" \
              " --os-project-name {}" \
              " --os-user-id {}" \
              " --os-password {}" \
              " --control-scale {}" \
              " --compute-scale {}" \
              " --ceph-storage-scale {}" \
              " --ntp-server {}" \
              "".format(debug,
                        args.timeout,
                        overcloud_name_opt,
                        env_opts,
                        control_flavor,
                        compute_flavor,
                        ceph_storage_flavor,
                        swift_storage_flavor,
                        block_storage_flavor,
                        os_auth_url,
                        os_tenant_name,
                        os_username,
                        os_password,
                        args.num_controllers,
                        args.num_computes,
                        args.num_storage,
                        args.ntp_server_fqdn)

        with open(os.path.join(home_dir, 'pilot', 'overcloud_deploy_cmd.log'),
                  'w') as f:
            f.write(cmd.replace(' -', ' \\\n -'))
            f.write('\n')
        print cmd
        start = time.time()
        status = run_deploy_command(cmd)
        end = time.time()
        print '\nExecution time: {} (hh:mm:ss)'.format(
            time.strftime('%H:%M:%S', time.gmtime(end - start)))
        print 'Fetching SSH keys...'
        update_ssh_config()
        if status == 0:
            horizon_url = finalize_overcloud()
        else:
            horizon_url = None
        print 'Overcloud nodes:'
        identify_nodes()

        if horizon_url:
            print '\nHorizon Dashboard URL: {}\n'.format(horizon_url)
    except ValueError as err:
        print >> sys.stderr, err
        sys.exit(1)

if __name__ == "__main__":
    main()
