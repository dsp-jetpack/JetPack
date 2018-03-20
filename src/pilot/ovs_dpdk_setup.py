#!/usr/bin/env python

# Copyright (c) 2015-2017 Dell Inc. or its subsidiaries.
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
import sys
import logging
import argparse
import subprocess
from ironicclient import client

from credential_helper import CredentialHelper
from logging_helper import LoggingHelper

logging.basicConfig()
LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


def get_ironic_client():
    try:
        os_auth_url, os_tenant_name, os_username, os_password = \
            CredentialHelper.get_undercloud_creds()
        kwargs = {
            'os_username': os_username,
            'os_password': os_password,
            'os_auth_url': os_auth_url,
            'os_project_name': os_tenant_name
            }

        ironic = client.get_client(1, **kwargs)
    except:
        raise Exception('ERROR: Error setting up ironic client.')
    LOG.info("Ironic client authnetication successful.")
    return ironic


def get_ironic_nodes(ironic_client):
    try:
        nodes = ironic_client.node.list(detail=True)
    except:
        raise Exception('ERROR: Error retrieving ironic nodes.')
    LOG.info("Retreiving baremetal nodes information from Ironic client.")
    return nodes


def setup_ovs_dpdk_environment(nics, config_file, env_file, mode):
    assert os.path.isfile(
        config_file), config_file + " file does not exist"
    assert os.path.isfile(
        env_file), env_file + " file does not exist"
    if mode == 2:
        interfaces = "'" + ",".join(nics[0:2]) + "'"
    else:
        interfaces = "'" + ",".join(nics) + "'"

    cmds = [
        'sed -i "s|Compute::Net::SoftwareConfig:.*|' +
        'Compute::Net::SoftwareConfig: ' + config_file + '|" ' + env_file,
        'sed -i "s|DpdkInterfaces:.*|DpdkInterfaces: ' +
        interfaces + '|" ' + env_file,
        ]
    LOG.info("Running sed commands to configure environment.")
    for cmd in cmds:
        LOG.info(cmd)
        out = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        LOG.info("output: " + str(out.stdout.read()))


def main():

    R630_NICS = ['p2p1', 'p3p1', 'p2p2', 'p3p2']
    R730_NICS = ['p4p1', 'p5p1', 'p4p2', 'p5p2']
    parser = argparse.ArgumentParser()
    parser.add_argument("--env_file",
                        dest="env_file",
                        required=True,
                        help="OVS DPDK Environment file")
    parser.add_argument("--nic_config_file",
                        dest="config_file",
                        required=True,
                        help="OVS-DPDK Compute NIC configs")
    parser.add_argument("--mode",
                        dest="mode",
                        type=int,
                        required=True,
                        help="OVS-DPDK Mode")
    LoggingHelper.add_argument(parser)
    args = parser.parse_args()

    root_logger = logging.getLogger()
    root_logger.setLevel(args.logging_level)
    urllib3_logger = logging.getLogger("requests.packages.urllib3")
    urllib3_logger.setLevel(logging.WARN)

    ironic_client = get_ironic_client()
    nodes = get_ironic_nodes(ironic_client)

    compute_nodes_model = set()
    for node in nodes:
        node = node.to_dict()
        if 'compute' in node['properties']['capabilities']:
            model = node['properties']['model']
            compute_nodes_model.add(model)
            LOG.info("Node: " + node['uuid'] + " model: " + model)
    if len(compute_nodes_model) == 0:
        raise Exception('ERROR: No server model found for compute nodes.')
    elif len(compute_nodes_model) != 1:
        raise Exception('ERROR: Multiple server models found for compute '
                        'nodes. All compute nodes must have same '
                        'server models.')

    compute_nodes_model = list(compute_nodes_model)
    if compute_nodes_model[0] == 'PowerEdge R630':
        nics = R630_NICS
    else:
        nics = R730_NICS
    mode = args.mode
    if mode == 1 or mode == 2:
        pass
    else:
        raise Exception('ERROR: Mode ' + mode + ' is not supported.'
                        'Only supported values are 1 and 2.')
    setup_ovs_dpdk_environment(nics, args.config_file, args.env_file, mode)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        LOG.error(str(e))
        exit(1)
