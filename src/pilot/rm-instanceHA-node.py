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


# Delete a controller node resource
def delete_controller_node_resources(controller_node_ip,
                                     first_controller_node_ip):
    out, err = ssh_cmd(controller_node_ip, "heat-admin",
                       "hostname")
    node_name = out.strip()
    controller_node_name = awk_it(node_name, 1, ".")

    LOG.info("Delete controller node resource {}"
             .format(controller_node_name))

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs cluster node remove " + controller_node_name)


# Delete a compute node resource
def delete_compute_node_resources(compute_node_ip, first_controller_node_ip):

    out, err = ssh_cmd(compute_node_ip, "heat-admin", "sudo crm_node -n")
    crm_node_name = out.strip()
    nova_compute_name = awk_it(crm_node_name, 1, ".")

    LOG.info("Delete compute node resources {}."
             .format(compute_node_ip))

    ssh_cmd(compute_node_ip, "heat-admin",
            "sudo systemctl stop pacemaker_remote")

    ssh_cmd(compute_node_ip, "heat-admin",
            "sudo systemctl disable pacemaker_remote")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource delete " + crm_node_name)

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs stonith delete ipmilan-" + nova_compute_name)

    LOG.info("Compute node resources {}."
             .format(nova_compute_name))

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource clean " + crm_node_name)


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
                        default=Constants.INSTACKENV_FILENAME)
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
    instack_file = os.path.expanduser(args.file)

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

    # Get CONTROLLER_NODE_NAMES
    p1 = subprocess.Popen(['nova', 'list'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('awk \'/controller/ {print $4}\''),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    controller_node_names = p2.communicate()[0].split()

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

    # Get first_controller_node_ip
    p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('grep -A1 "cntl0"'),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    p3 = subprocess.Popen(shlex.split('awk \'/Hostname/ {print $2}\''),
                          stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    first_controller_node_ip = p3.communicate()[0].rstrip()

    oc_auth_url, oc_tenant_name, oc_username, oc_password = \
        CredentialHelper.get_overcloud_creds()

    LOG.setLevel(args.logging_level)

    LOG.debug("home_dir: {}".format(home_dir))
    LOG.debug("oc_stack_name: {}".format(oc_stack_name))
    LOG.debug("oc_auth_url: {}".format(oc_auth_url))
    LOG.debug("oc_username: {}".format(oc_username))
    LOG.debug("oc_password: {}".format(oc_password))
    LOG.debug("oc_tenant_name: {}".format(oc_tenant_name))
    LOG.debug("controller_nodes_ip: {}".format(controller_nodes_ip))
    LOG.debug("controller_nodes_names: {}".format(controller_nodes_ip))
    LOG.debug("compute_nodes_ip: {}".format(compute_nodes_ip))
    LOG.debug("compute_nova_names: {}".format(compute_nodes_ip))

    # Execute Compute node deletion
    if args.compute_node_ip != '':
        compute_node_ip = args.compute_node_ip.rstrip()
        if check_ip_validity(compute_node_ip):
            LOG.info("***  Removing a compute node {} to InstanceHA"
                     " configuration.".format(compute_node_ip))
            delete_compute_node_resources(compute_node_ip,
                                          first_controller_node_ip)
        else:
            LOG.critical("!!! - Fatal Error: Invalid IP address: {}"
                         .format(compute_node_ip))
            exit(-1)

    # Execute Controller node deletion
    if args.controller_node_ip != '':
        controller_node_ip = args.controller_node_ip.rstrip()
        if check_ip_validity(controller_node_ip):
            LOG.info("***  Removing a controller node {} to InstanceHA"
                     " configuration.".format(controller_node_ip))
            LOG.debug("controller_node_ip: {}".format(controller_node_ip))
            delete_controller_node_resources(controller_node_ip,
                                             first_controller_node_ip)
        else:
            LOG.critical("!!! - Fatal Error: Invalid IP address: {}"
                         .format(controller_node_ip))
            exit(-1)


if __name__ == "__main__":
    main()
