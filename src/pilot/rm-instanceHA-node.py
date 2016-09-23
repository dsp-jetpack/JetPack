#!/usr/bin/python

# (c) 2016 Dell
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


def check_ip_validity(ipaddr):
    octet_exp = "(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    ValidIpAddressRegex = ("^" + octet_exp + "\." +
                           octet_exp + "\." +
                           octet_exp + "\." +
                           octet_exp + "$")
    ip_match = re.search(ValidIpAddressRegex, ipaddr)
    return ip_match


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


# Instance HA Specific Methods

# Distribute authkey to all nodes
def distribute_all_authkey(compute_nodes_ip, controller_nodes_ip):
    for compute_node_ip in compute_nodes_ip:
        distribute_node_authkey(compute_node_ip)
    for controller_node_ip in controller_nodes_ip:
        distribute_node_authkey(controller_node_ip)


# Distribute authkey to node
def distribute_node_authkey(node_ip):
    LOG.info("Distribute auth_key to node {}.".format(node_ip))

    cmd = "scp ~/authkey heat-admin@" + node_ip + ":~/authkey"
    os.system(cmd)

    ssh_cmd(node_ip, "heat-admin",
            "sudo mkdir -p /etc/pacemaker")

    ssh_cmd(node_ip, "heat-admin",
            "sudo mv ~heat-admin/authkey /etc/pacemaker/")

    ssh_cmd(node_ip, "heat-admin",
            "sudo chown root:root /etc/pacemaker/authkey")


# Enable and start pacemaker remote on all compute nodes
def enable_start_pacemaker(compute_nodes_ip):
    for compute_node_ip in compute_nodes_ip:
        enable_start_compute_pacemaker(compute_node_ip)


# Enable and start pacemaker remote on a compute node
def enable_start_compute_pacemaker(compute_node_ip):
    LOG.info("Enable and start pacemaker_remote service on compute node {}."
             .format(compute_node_ip))

    ssh_cmd(compute_node_ip, "heat-admin",
            "sudo sudo systemctl enable pacemaker_remote")

    ssh_cmd(compute_node_ip, "heat-admin",
            "sudo systemctl start pacemaker_remote")


# Disable all OpenStack resources across the control plane.
def disable_all_openstack_resource(first_controller_node_ip):
    LOG.info("Disable all OpenStack resources across the control plane.")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource disable openstack-keystone --wait=1000s")


# Create a list of the current controllers using cibadmin data.
# Use this list to tag these nodes as controllers with the
# osprole=controller property.
def tag_controllers_with_osprole(first_controller_node_ip):
    LOG.info("Get a list of current controllers & tag them with"
             " the osprole=controller property.")

    out, err = ssh_cmd(first_controller_node_ip, "heat-admin",
                       "sudo cibadmin -Q -o nodes | grep uname")
    out_list = out.split()

    controllers = [entry for entry in out_list if entry.startswith('uname')]

    for controller in controllers:
        controller = re.findall(r'"([^"]*)"', controller)
        ssh_cmd(first_controller_node_ip, "heat-admin",
                "sudo pcs property set --node " + controller[0] +
                " osprole=controller")


# Add stonith devices for all compute nodes. Replace the ipaddr, login and
# passwd values to suit your IPMI device. Run ~/pilot/identify_nodes.sh to see
# which idrac is associated with the host and crm_node -n to get the hostname.
def add_compute_nodes_stonith_devices(compute_nodes_ip,
                                      undercloud_config,
                                      first_controller_node_ip,
                                      instack_file):
    for compute_node_ip in compute_nodes_ip:
        add_compute_node_stonith_devices(compute_node_ip,
                                         undercloud_config,
                                         first_controller_node_ip,
                                         instack_file)


# Add stonith devices for a compute nodes.
def add_compute_node_stonith_devices(compute_node_ip,
                                     undercloud_config,
                                     first_controller_node_ip,
                                     instack_file):
    LOG.info("Add stonith devices for the compute node {}."
             .format(compute_node_ip))

    out, err = ssh_cmd(compute_node_ip, "heat-admin",
                       "sudo crm_node -n")
    crm_node_name = out.strip()
    nova_compute_name = awk_it(crm_node_name, 1, ".")

    # Get first_compute_node_ip
    p1 = subprocess.Popen(['grep', nova_compute_name, undercloud_config],
                          stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('cut -d" " -f2'),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    compute_node_drac_ip = p2.communicate()[0].rstrip()

    # Get drac_user
    p1 = subprocess.Popen(['cat', instack_file], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('grep -A3 ' + compute_node_drac_ip),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    p3 = subprocess.Popen(shlex.split('awk -F\'"\' \'/pm_user/ {print $4}\''),
                          stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    drac_user = p3.communicate()[0].rstrip()

    # Get drac_password
    p1 = subprocess.Popen(['cat', instack_file], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('grep -A3 ' + compute_node_drac_ip),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    p3 = subprocess.Popen(shlex.split('awk -F\'"\' \'/pm_pass/ {print $4}\''),
                          stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    drac_password = p3.communicate()[0].rstrip()

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs stonith create ipmilan-" + nova_compute_name +
            " fence_ipmilan pcmk_host_list=" + crm_node_name +
            " ipaddr=" + compute_node_drac_ip + " login=" + drac_user +
            " passwd=" + drac_password +
            " lanplus=1 cipher=1 op monitor interval=60s")


# Create all compute node resources and set the stonith level 1 to include
# both the nodes's physical fence device and fence-nova.
def create_compute_nodes_resources(compute_nodes_ip, first_controller_node_ip):
    for compute_node_ip in compute_nodes_ip:
        create_compute_node_resources(compute_node_ip,
                                      first_controller_node_ip)


# Create a compute node resources and set the stonith level 1 to include
# both the nodes's physical fence device and fence-nova.
def create_compute_node_resources(compute_node_ip, first_controller_node_ip):
    LOG.info("Create Compute node:{} resources and set the stonith level 1."
             .format(compute_node_ip))

    out, err = ssh_cmd(compute_node_ip, "heat-admin",
                       "sudo crm_node -n")
    crm_node_name = out.strip()
    crm_node_sname = awk_it(crm_node_name, 1, ".")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource create " + crm_node_name +
            " ocf:pacemaker:remote reconnect_interval=60 op" +
            " monitor interval=20")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs property set --node " + crm_node_name +
            " osprole=compute")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs stonith level add 1 " + crm_node_name +
            " ipmilan-" + crm_node_sname + ",fence-nova")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs stonith")


# Allow some time for the environment to settle before cleaning up any
# failed resources.
def final_resource_cleanup(first_controller_node_ip):
    LOG.info("Clean up any failed resources.")

    os.system("sleep 60")
    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource cleanup")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs status")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs property set stonith-enabled=true")


# Main Routine
def main():

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-compute",
                       "--compute",
                       dest="compute_node_ip",
                       action="store",
                       default='')
    group.add_argument("-controller",
                       "--controller",
                       dest="controller_node_ip",
                       action="store",
                       default='')
    parser.add_argument('-f',
                        '--file',
                        help='name of json file containing the node being set',
                        default='instackenv.json')
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
    instack_file = os.path.join(home_dir, args.file)

    # Run ~/pilot/update_ssh_config.py
    cmd = os.path.join(home_dir, 'pilot/update_ssh_config.py')
    os.system(cmd)

    # Run ~/pilot/identify_nodes.py > ~/undercloud_nodes.txt
    cmd = os.path.join(home_dir,
                       'pilot/identify_nodes.py > ~/undercloud_nodes.txt')
    os.system(cmd)

    # Get CONTROLLER_NODES_IP
    p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('grep -A1 "cntl"'),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    p3 = subprocess.Popen(shlex.split('awk \'/Hostname/ {print $2}\''),
                          stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    controller_nodes_ip = p3.communicate()[0].split()


    # Get COMPUTE_NODES_IP
    p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('egrep -A1 -h "nova|compute"'),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    p3 = subprocess.Popen(shlex.split('awk \'/Hostname/ {print $2}\''),
                          stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    compute_nodes_ip = p3.communicate()[0].split()

    oc_auth_url, oc_tenant_name, oc_username, oc_password = \
        CredentialHelper.get_overcloud_creds()

    LOG.setLevel(args.logging_level)

    # Install RA instanceHA Configuration
    if args.compute_node_ip == '' and args.controller_node_ip == '':
        LOG.info("***  Configuring Instance HA for stack {}  ***"
                 .format(oc_stack_name))

        LOG.debug("home_dir: {}".format(home_dir))
        LOG.debug("oc_stack_name: {}".format(oc_stack_name))
        LOG.debug("oc_auth_url: {}".format(oc_auth_url))
        LOG.debug("oc_username: {}".format(oc_username))
        LOG.debug("oc_password: {}".format(oc_password))
        LOG.debug("oc_tenant_name: {}".format(oc_tenant_name))
        LOG.debug("controller_nodes_ip: {}".format(controller_nodes_ip))
        LOG.debug("compute_nodes_ip: {}".format(compute_nodes_ip))

    # Execute Compute node addition
    if args.compute_node_ip != '':
        compute_node_ip = args.compute_node_ip.rstrip()
        if check_ip_validity(compute_node_ip):
            LOG.info("***  Removing a compute node {} to InstanceHA"
                     " configuration.".format(compute_node_ip))

            LOG.debug("compute_node_ip: {}".format(compute_node_ip))
            LOG.debug("undercloud_config: {}".format(undercloud_config))
            LOG.debug("instack_file: {}".format(instack_file))

        else:
            LOG.critical("!!! - Fatal Error: Invalid IP address: {}"
                         .format(compute_node_ip))
            exit(-1)

    # Execute Controller node addition
    if args.controller_node_ip != '':
        controller_node_ip = args.controller_node_ip.rstrip()
        if check_ip_validity(controller_node_ip):
            LOG.info("***  Removing a controller node {} to InstanceHA"
                     " configuration.".format(controller_node_ip))

            LOG.debug("controller_node_ip: {}".format(controller_node_ip))

        else:
            LOG.critical("!!! - Fatal Error: Invalid IP address: {}"
                         .format(controller_node_ip))
            sys.exit(-1)

if __name__ == "__main__":
    main()
