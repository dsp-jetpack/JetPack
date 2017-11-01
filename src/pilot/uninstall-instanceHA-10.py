#!/usr/bin/python

# Copyright (c) 2017 Dell Inc. or its subsidiaries.
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

###############################################################################
# Run this script run from the director node as the director's admin user.
# This script assumes the update_ssh_config.py is present.
###############################################################################

# IMPORTS
import argparse
import os
import sys
import subprocess
import shlex
import re
import paramiko
import logging

# Dell utilities
from identify_nodes import main as identify_nodes
from credential_helper import CredentialHelper
from update_ssh_config import main as update_ssh_config

FORMAT = '%(levelname)s: %(message)s'
logging.basicConfig(format=FORMAT)
LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


# Global method definition
def ssh_cmd(address, user, command):
    try:
        cmd = "ssh " + user + "@" + address + " \"" + command + "\""
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(address, username=user)
        stdin, ss_stdout, ss_stderr = client.exec_command(command)
        r_out, r_err = ss_stdout.read(), ss_stderr.read()
        client.close()
    except IOError:
        LOG.error(".. host " + address + " is not up")
        return "host not up"
    return r_out, r_err


def awk_it(instring, index, delimiter=" "):
    try:
        return [instring,
                instring.split(delimiter)[index-1]][max(0, min(1, index))]
    except:
        return ""


def logging_level(string):
    string_level = string

    try:
        # Convert to upper case to allow the user to specify
        # --logging-level=DEBUG or --logging-level=debug.
        numeric_level = getattr(logging, string_level.upper())
    except AttributeError:
        raise argparse.ArgumentTypeError(
            "Unknown logging level: {}".format(string_level))

    if not isinstance(numeric_level, (int, long)) or int(numeric_level) < 0:
        raise argparse.ArgumentTypeError(
            "Logging level not a nonnegative integer: {!r}".format(
                numeric_level))

    return numeric_level


def enable_openstack_services(compute_nodes_ip):
    LOG.info("Disable compute node libvirtd and openstack services.")
    services = ['openstack-nova-compute', 'neutron-openvswitch-agent',
                'libvirtd']

    for compute_node_ip in compute_nodes_ip:
        for service in services:
            ssh_cmd(compute_node_ip, "heat-admin",
                    "sudo systemctl start " + service)

            ssh_cmd(compute_node_ip, "heat-admin",
                    "sudo systemctl enable " + service)


def disable_remote_pacemaker(compute_nodes_ip):
    for compute_node_ip in compute_nodes_ip:
        LOG.info("Disable pacemaker_remote service on compute node {}."
                 .format(compute_node_ip))

        ssh_cmd(compute_node_ip, "heat-admin",
                "sudo sudo systemctl disable pacemaker_remote")

        ssh_cmd(compute_node_ip, "heat-admin",
                "sudo systemctl stop pacemaker_remote")


def delete_compute_nodes_stonith_devices(compute_nodes_ip,
                                         first_controller_node_ip):

    for compute_node_ip in compute_nodes_ip:
        LOG.info("Delete stonith devices for the compute node {}."
                 .format(compute_node_ip))

        out, err = ssh_cmd(compute_node_ip, "heat-admin",
                           "sudo crm_node -n")
        crm_node_name = out.strip()
        nova_compute_name = awk_it(crm_node_name, 1, ".")

        ssh_cmd(first_controller_node_ip, "heat-admin",
                "sudo pcs stonith delete ipmilan-" + nova_compute_name +
                " --force")


def delete_nova_evacuate_resource(first_controller_node_ip):
    LOG.info("Delete the nova-evacuate resource.")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource delete nova-evacuate --force")


def delete_compute_nodes_resources(first_controller_node_ip):
    LOG.info("Delete the compute node resources within pacemaker.")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource delete neutron-openvswitch-agent-compute \
            --force")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs stonith delete fence-nova --force")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource delete libvirtd-compute --force")

# Then the nova-compute resource:

    oc_auth_url, oc_tenant_name, oc_username, oc_password = \
        CredentialHelper.get_overcloud_creds()

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource delete nova-compute-checkevacuate --force")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource delete nova-compute --force")


def delete_compute_nodeName_resource(compute_nodes_ip,
                                     first_controller_node_ip):
    for compute_node_ip in compute_nodes_ip:
        LOG.info("Delete Compute node:{} resources and set the \
                 stonith level 1.".format(compute_node_ip))

        out, err = ssh_cmd(compute_node_ip, "heat-admin",
                           "sudo crm_node -n")
        crm_node_name = out.strip()
        crm_node_sname = crm_node_name.partition('.')[0]
        domainname = crm_node_name.partition('.')[2]

        ssh_cmd(first_controller_node_ip, "heat-admin",
                "sudo pcs resource delete " + crm_node_sname + " --force")


def disable_control_plane_services(first_controller_node_ip):
    LOG.info("Disable the control and Compute plane services.")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource disable nova-compute")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource disable nova-compute-checkevacuate")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource disable libvirtd-compute")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource disable neutron-openvswitch-agent-compute")


# Main Routine
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-l",
                        "--logging-level",
                        default="INFO",
                        type=logging_level,
                        help="""logging level defined by the logging module;
                                choices include CRITICAL, ERROR, WARNING,
                                INFO, and DEBUG""", metavar="LEVEL")
    args = parser.parse_args()

    home_dir = os.path.expanduser('~')
    undercloudrc_name = os.path.join(home_dir, 'stackrc')
    oc_stack_name = CredentialHelper.get_overcloud_name()
    ssh_config = os.path.join(home_dir, '.ssh/config')
    undercloud_config = os.path.join(home_dir, 'undercloud_nodes.txt')

    # Run update_ssh_config.py
    cmd = os.path.join(os.getcwd(), 'update_ssh_config.py')
    os.system(cmd)

    # Run identify_nodes.py > ~/undercloud_nodes.txt
    cmd = os.path.join(os.getcwd(),
                       'identify_nodes.py > ~/undercloud_nodes.txt')
    os.system(cmd)

    # Get first_controller_node
    p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('awk \'/cntl0/ {print $2}\''),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    first_controller_node = p2.communicate()[0].rstrip()

    # Get first_controller_node_ip
    p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('grep -A1 "cntl0"'),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    p3 = subprocess.Popen(shlex.split('awk \'/Hostname/ {print $2}\''),
                          stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    first_controller_node_ip = p3.communicate()[0].rstrip()

    # Get COMPUTE_NODES_IP
    p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('grep -A1 "cntl"'),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    p3 = subprocess.Popen(shlex.split('awk \'/Hostname/ {print $2}\''),
                          stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    controller_nodes_ip = p3.communicate()[0].split()

    # Get first_compute_node
    p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split
                          ('awk \'/nova0/ || /compute0/ {print $2}\''),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    first_compute_node = p2.communicate()[0].rstrip()

    # Get first_compute_node_ip
    p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('egrep -A1 -h "nova0|compute0"'),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    p3 = subprocess.Popen(shlex.split('awk \'/Hostname/ {print $2}\''),
                          stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    first_compute_node_ip = p3.communicate()[0].rstrip()

    # Get COMPUTE_NODES_IP
    p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('egrep -A1 -h "nova|compute"'),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    p3 = subprocess.Popen(shlex.split('awk \'/Hostname/ {print $2}\''),
                          stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    compute_nodes_ip = p3.communicate()[0].split()

    # Get COMPUTE_NOVA_NAMES
    p1 = subprocess.Popen(['nova', 'list'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('awk \'/compute/ {print $4}\''),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    compute_nova_names = p2.communicate()[0].split()
    first_compute_nova_name = compute_nova_names[0]

    # Get CONTROLLER_NOVA_NAMES
    p1 = subprocess.Popen(['nova', 'list'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('awk \'/controller/ {print $4}\''),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    controller_nova_names = p2.communicate()[0].split()
    first_controller_nova_name = controller_nova_names[0]

    oc_auth_url, oc_tenant_name, oc_username, oc_password = \
        CredentialHelper.get_overcloud_creds()

    LOG.setLevel(args.logging_level)

    # Install RA instanceHA Configuration
    LOG.info("***  Removing Instance HA for stack {}  ***"
             .format(oc_stack_name))

    LOG.debug("home_dir: {}".format(home_dir))
    LOG.debug("oc_stack_name: {}".format(oc_stack_name))
    LOG.debug("oc_auth_url: {}".format(oc_auth_url))
    LOG.debug("oc_username: {}".format(oc_username))
    LOG.debug("oc_password: {}".format(oc_password))
    LOG.debug("oc_tenant_name: {}".format(oc_tenant_name))
    LOG.debug("first_controller_node: {}".format(first_controller_node))
    LOG.debug("first_controller_node_ip: {}"
              .format(first_controller_node_ip))
    LOG.debug("controller_nodes_ip: {}".format(controller_nodes_ip))
    LOG.debug("first_compute_node: {}".format(first_compute_node))
    LOG.debug("first_compute_node_ip: {}".format(first_compute_node_ip))
    LOG.debug("compute_nodes_ip: {}".format(compute_nodes_ip))
    LOG.debug("compute_nova_names: {}".format(compute_nova_names))
    LOG.debug("first_compute_nova_name: {}".format(first_compute_nova_name))
    LOG.debug("controller_nova_names: {}".format(controller_nova_names))
    LOG.debug("first_controller_nova_name: {}"
              .format(first_controller_nova_name))

    cmd = "source {} ".format(undercloudrc_name)
    os.system(cmd)

    out = ssh_cmd(first_controller_node_ip, "heat-admin",
                  "sudo pcs property show stonith-enabled \
                  | awk '/stonith/ {print $2}'")
    result = out[0].rstrip()
    LOG.debug("result: {}".format(result))

    if result == 'true':
        ssh_cmd(first_controller_node_ip, "heat-admin",
                "sudo pcs property set stonith-enabled=false")
        ssh_cmd(first_controller_node_ip, "heat-admin",
                "sudo pcs property set maintenance-mode=true")

    disable_control_plane_services(first_controller_node_ip)
    delete_compute_nodeName_resource(compute_nodes_ip,
                                     first_controller_node_ip)
    delete_compute_nodes_resources(first_controller_node_ip)
    delete_compute_nodes_stonith_devices(compute_nodes_ip,
                                         first_controller_node_ip)
    delete_nova_evacuate_resource(first_controller_node_ip)
    disable_remote_pacemaker(compute_nodes_ip)
    enable_openstack_services(compute_nodes_ip)

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs property set maintenance-mode=false")
    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs property set stonith-enabled=true")


if __name__ == "__main__":
    main()
