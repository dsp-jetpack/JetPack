#!/usr/bin/python

# Copyright (c) 2016-2017 Dell Inc. or its subsidiaries.
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
from constants import Constants
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


def get_domainname(first_compute_node_ip):
    out, err = ssh_cmd(first_compute_node_ip, "heat-admin",
                       "sudo crm_node -n")
    crm_node_name = out.strip()
    domainname = crm_node_name.partition('.')[2]
    return domainname


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


def verify_fencing(first_controller_node_ip):
    out, err = ssh_cmd(first_controller_node_ip, "heat-admin",
                       "sudo pcs property show | grep stonith-enable")
    stonith_property = out.strip()
    LOG.debug("stonith_property: {}".format(stonith_property))
    stonith_enabled = stonith_property.partition(': ')[2]
    LOG.debug("stonith_enabled: {}".format(stonith_enabled))
    return stonith_enabled


# Instance HA Specific Methods

# 1) Stop and disable openstack services Compute nodes
def stop_disable_openstack_services(compute_nodes_ip):
    LOG.info("Disable compute node libvirtd and openstack services.")
    services = ['openstack-nova-compute',
                'neutron-openvswitch-agent',
                'libvirtd']

    for compute_node_ip in compute_nodes_ip:
        for service in services:
            ssh_cmd(compute_node_ip, "heat-admin",
                    "sudo systemctl stop " + service)

            ssh_cmd(compute_node_ip, "heat-admin",
                    "sudo systemctl disable " + service)

        ssh_cmd(compute_node_ip, "heat-admin",
                "sudo iptables -I INPUT -p tcp --dport 3121 -j ACCEPT")

        ssh_cmd(compute_node_ip, "heat-admin",
                "sudo service iptables save")


# 2) Create auth_key on first compute node and cp authkey back to local node
def create_authkey(first_compute_node_ip):
    LOG.info("Create auth_key on node: {}".format(first_compute_node_ip))

    ssh_cmd(first_compute_node_ip, "heat-admin",
            "sudo mkdir -p /etc/pacemaker")

    ssh_cmd(first_compute_node_ip, "heat-admin",
            "sudo dd if=/dev/urandom of=/etc/pacemaker/authkey" +
            " bs=4096 count=1")

    ssh_cmd(first_compute_node_ip, "heat-admin",
            "sudo cp /etc/pacemaker/authkey ~/")

    ssh_cmd(first_compute_node_ip, "heat-admin",
            "sudo chown heat-admin:heat-admin ~/authkey")

    cmd = "scp heat-admin@" + first_compute_node_ip + ":~/authkey ~/authkey"
    os.system(cmd)


# 3a) Distribute authkey to all nodes
def distribute_all_authkey(compute_nodes_ip, controller_nodes_ip):
    for compute_node_ip in compute_nodes_ip:
        distribute_node_authkey(compute_node_ip)
    for controller_node_ip in controller_nodes_ip:
        distribute_node_authkey(controller_node_ip)


# 3b) Distribute authkey to node
def distribute_node_authkey(node_ip):
    LOG.info("Distribute auth_key to node {}.".format(node_ip))

    cmd = "scp ~/authkey heat-admin@" + node_ip + ":~/authkey"
    os.system(cmd)

    ssh_cmd(node_ip, "heat-admin",
            "sudo mkdir -p --mode=0755 /etc/pacemaker")

    ssh_cmd(node_ip, "heat-admin",
            "sudo mv ~heat-admin/authkey /etc/pacemaker")

    ssh_cmd(node_ip, "heat-admin",
            "sudo chown root:haclient /etc/pacemaker/authkey")


# 4a) Enable and start pacemaker remote on all compute nodes
def enable_start_pacemaker(compute_nodes_ip):
    for compute_node_ip in compute_nodes_ip:
        enable_start_compute_pacemaker(compute_node_ip)


# 4b) Enable and start pacemaker remote on a compute node
def enable_start_compute_pacemaker(compute_node_ip):
    LOG.info("Enable and start pacemaker_remote service on compute node {}."
             .format(compute_node_ip))

    ssh_cmd(compute_node_ip, "heat-admin",
            "sudo systemctl enable pacemaker_remote")

    ssh_cmd(compute_node_ip, "heat-admin",
            "sudo systemctl start pacemaker_remote")


# 7) Create a NovaEvacuate active/passive resource using the overcloudrc file
# to provide the auth_url, username, tenant and password values
def create_nova_evacuate_resource(first_controller_node_ip, domainname):
    LOG.info("Create the nova-evacuate active/passive resource.")

    oc_auth_url, oc_tenant_name, oc_username, oc_password = \
        CredentialHelper.get_overcloud_creds()

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource create nova-evacuate" +
            " ocf:openstack:NovaEvacuate auth_url=" + oc_auth_url +
            " username=" + oc_username +
            " password=" + oc_password +
            " tenant_name=" + oc_tenant_name +
            " domain=" + domainname +
            " op monitor interval=60s timeout=240s --force")


# 8) Confirm that nova-evacuate is started after the floating IP resources,
# and the Image Service (glance), OpenStack Networking (neutron),
# Compute (nova) services
def confirm_nova_evacuate_resource(first_controller_node_ip):
    LOG.info("Confirm nova-evacuate is started after haproxy-clone,"
             " galera-master and rabbitmq-clone services.")

    resource_list = ['haproxy-clone',
                     'galera-master',
                     'rabbitmq-clone']

    for res in resource_list:
        ssh_cmd(first_controller_node_ip, "heat-admin",
                "sudo pcs constraint order start " + res +
                " then nova-evacuate")


# 10) Create a list of the current controllers using cibadmin data.
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


# 13) Build a list of stonith devices already present in the environment.
# Tag the control plane services to make sure they only run on
# the controllers identified above, skipping any stonith devices listed.
def tag_the_control_plane(first_controller_node_ip):
    LOG.info("Get a list of stonith devices & tag the control plane services.")
    # Build stonithdevs list
    stonithdevs = []
    out, err = ssh_cmd(first_controller_node_ip, "heat-admin",
                       "sudo pcs stonith")
    list = out.split('\n')
    for line in list:
        if len(line.strip()) != 0:
            x = ''.join(line).lstrip(" ")
            y = awk_it(x, 1, "\t")
            stonithdevs.append(y)

    if not stonithdevs:
        LOG.error("There were no Stonith devices found,"
                  " please ensure fencing is enabled.")
        exit(-1)

    # Build resources list
    resources = []
    out, err = ssh_cmd(first_controller_node_ip, "heat-admin",
                       "sudo cibadmin -Q --xpath //primitive --node-path")
    list = out.split('\n')
    for line in list:
        if len(line.strip()) != 0:
            x = ''.join(line)
            y = awk_it(x, 2, "id='")
            z = awk_it(y, 1, "']")
            resources.append(z)

    # Process stonithdevs and resources lists -- setting constraints
    for res in resources:
        found = 0
        for stdev in stonithdevs:
            if stdev == res:
                found = 1
        if found == 0:
            LOG.debug("INSIDE found == 0: {} ".format(res))
            ssh_cmd(first_controller_node_ip, "heat-admin",
                    "sudo pcs constraint location " + res +
                    " rule resource-discovery=exclusive score=0" +
                    " osprole eq controller")


# 14) Populate the Compute node resources within pacemaker, starting with
# neutron-openvswitch-agent:
def populate_compute_nodes_resources(first_controller_node_ip, domainname):
    LOG.info("Populate the compute node resources within pacemaker.")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource create neutron-openvswitch-agent-compute" +
            " systemd:neutron-openvswitch-agent op start timeout=200s op" +
            " stop timeout=200s --clone interleave=true" +
            " --disabled --force")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs constraint location" +
            " neutron-openvswitch-agent-compute-clone rule" +
            " resource-discovery=exclusive score=0 osprole eq compute")

#  Then the Compute libvirtd resource:

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource create libvirtd-compute systemd:libvirtd" +
            " op start timeout=200s op stop timeout=200s" +
            " --clone interleave=true --disabled --force")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs constraint location libvirtd-compute-clone rule" +
            " resource-discovery=exclusive score=0 osprole eq compute")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs constraint order start" +
            " neutron-openvswitch-agent-compute-clone" +
            " then libvirtd-compute-clone")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs constraint colocation add libvirtd-compute-clone" +
            " with neutron-openvswitch-agent-compute-clone")

#  Then the nova-compute resource:

    oc_auth_url, oc_tenant_name, oc_username, oc_password = \
        CredentialHelper.get_overcloud_creds()

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource create nova-compute-checkevacuate" +
            " ocf:openstack:nova-compute-wait auth_url=" + oc_auth_url +
            " username=" + oc_username +
            " password=" + oc_password +
            " tenant_name=" + oc_tenant_name +
            " domain=" + domainname +
            " op start timeout=300 --clone interleave=true --disabled --force")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs constraint location nova-compute-checkevacuate-clone" +
            " rule resource-discovery=exclusive score=0 osprole eq compute")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource create nova-compute" +
            " systemd:openstack-nova-compute" +
            " op start timeout=200s op stop timeout=200s" +
            " --clone interleave=true --disabled --force")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs constraint location nova-compute-clone" +
            " rule resource-discovery=exclusive score=0 osprole eq compute")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs constraint order start" +
            " nova-compute-checkevacuate-clone" +
            " then nova-compute-clone require-all=true")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs constraint order start nova-compute-clone" +
            " then nova-evacuate require-all=false")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs constraint order start libvirtd-compute-clone" +
            " then nova-compute-clone")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs constraint colocation add nova-compute-clone" +
            " with libvirtd-compute-clone")


# 15a) Add stonith devices for all compute nodes. Replace the ipaddr, login and
# passwd values to suit your IPMI device. Run identify_nodes.sh to see
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


# 15b) Add stonith devices for a compute nodes.
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
    p1 = subprocess.Popen(['grep', compute_node_ip, undercloud_config],
                          stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('cut -d" " -f2'),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    compute_node_drac_ip = p2.communicate()[0].rstrip()

    # Get drac_user
    p1 = subprocess.Popen(['cat', instack_file], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('grep -n3 ' + compute_node_drac_ip),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    p3 = subprocess.Popen(shlex.split('awk -F\'"\' \'/pm_user/ {print $4}\''),
                          stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    drac_user = p3.communicate()[0].rstrip()

    # Get drac_password
    p1 = subprocess.Popen(['cat', instack_file], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('grep -n2 ' + compute_node_drac_ip),
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE)
    p3 = subprocess.Popen(shlex.split('awk -F\'"\' \'/pm_pass/ {print $4}\''),
                          stdin=p2.stdout,
                          stdout=subprocess.PIPE)
    drac_password = p3.communicate()[0].rstrip()

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs stonith create ipmilan-" + nova_compute_name +
            " fence_ipmilan pcmk_host_list=" + nova_compute_name +
            " ipaddr=" + compute_node_drac_ip + " login=" + drac_user +
            " passwd=" + drac_password +
            " lanplus=1 cipher=1 op monitor interval=60s")


# 16) Create a seperate fence-nova stonith device.
def create_fence_nova_device(first_controller_node_ip, domainname):
    LOG.info("Create a seperate fence-nova stonith device.")

    oc_auth_url, oc_tenant_name, oc_username, oc_password = \
        CredentialHelper.get_overcloud_creds()

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs stonith create fence-nova fence_compute" +
            " auth-url=" + oc_auth_url +
            " login=" + oc_username +
            " passwd=" + oc_password +
            " tenant-name=" + oc_tenant_name +
            " domain=" + domainname +
            " record-only=1 op monitor interval=60s timeout=180s --force")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs constraint location" +
            " fence-nova rule resource-discovery=never score=0" +
            " osprole eq controller")


# 17) Make certain the Compute nodes are able to recover after fencing.
def enable_compute_nodes_recovery(first_controller_node_ip):
    LOG.info("Ensure the Compute nodes are able to recover after fencing.")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs property set cluster-recheck-interval=1min")


# 18) Create all compute node resources and set the stonith level 1 to include
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
            "sudo pcs resource create " + crm_node_sname +
            " ocf:pacemaker:remote reconnect_interval=60 op" +
            " monitor interval=20")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs property set --node " + crm_node_sname +
            " osprole=compute")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs stonith level add 1 " + crm_node_sname +
            " ipmilan-" + crm_node_sname + ",fence-nova")


# 19) Enable the control and Compute plane services.
def enable_control_plane_services(first_controller_node_ip):
    LOG.info("Enable the control and Compute plane services.")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource enable neutron-openvswitch-agent-compute")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource enable libvirtd-compute")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource enable nova-compute-checkevacuate")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource enable nova-compute")


# 20) Allow some time for the environment to settle before cleaning up any
# failed resources.
def final_resource_cleanup(first_controller_node_ip):
    LOG.info("Clean up any failed resources.")

    os.system("sleep 60")
    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs resource cleanup")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo pcs status")

    ssh_cmd(first_controller_node_ip, "heat-admin",
            "sudo echo pcs property set stonith-enabled=true")


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
    instack_file = os.path.join(home_dir, args.file)

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

    oc_auth_url, oc_tenant_name, oc_username, oc_password = \
        CredentialHelper.get_overcloud_creds()

    domainname = get_domainname(first_compute_node_ip)

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
        LOG.debug("first_controller_node: {}".format(first_controller_node))
        LOG.debug("first_controller_node_ip: {}"
                  .format(first_controller_node_ip))
        LOG.debug("controller_nodes_ip: {}".format(controller_nodes_ip))
        LOG.debug("first_compute_node: {}".format(first_compute_node))
        LOG.debug("first_compute_node_ip: {}".format(first_compute_node_ip))
        LOG.debug("compute_nodes_ip: {}".format(compute_nodes_ip))
        LOG.debug("compute_nova_names: {}".format(compute_nova_names))
        LOG.debug("domainname: {}".format(domainname))

        if (verify_fencing(first_controller_node_ip) != "false" ):
            LOG.debug("Stonith is enabled.")
        else:
            LOG.critical("!!! - Error: Fencing must be enabled.")
            LOG.info("Use agent_fencing.sh script to enable fencing.")
            sys.exit(-1)

        stop_disable_openstack_services(compute_nodes_ip)
        create_authkey(first_compute_node_ip)
        distribute_all_authkey(compute_nodes_ip, controller_nodes_ip)
        enable_start_pacemaker(compute_nodes_ip)
        create_nova_evacuate_resource(first_controller_node_ip,
                                      domainname)
        confirm_nova_evacuate_resource(first_controller_node_ip)
        tag_controllers_with_osprole(first_controller_node_ip)
        tag_the_control_plane(first_controller_node_ip)
        populate_compute_nodes_resources(first_controller_node_ip,
                                         domainname)
        add_compute_nodes_stonith_devices(compute_nodes_ip,
                                          undercloud_config,
                                          first_controller_node_ip,
                                          instack_file)
        create_fence_nova_device(first_controller_node_ip,
                                 domainname)
        enable_compute_nodes_recovery(first_controller_node_ip)
        create_compute_nodes_resources(compute_nodes_ip,
                                       first_controller_node_ip)
        enable_control_plane_services(first_controller_node_ip)
        final_resource_cleanup(first_controller_node_ip)

    # Execute Compute node addition
    if args.compute_node_ip != '':
        compute_node_ip = args.compute_node_ip.rstrip()
        if check_ip_validity(compute_node_ip):
            LOG.info("***  Adding a compute node {} to InstanceHA"
                     " configuration.".format(compute_node_ip))

            LOG.debug("compute_nodes_ip: {}".format(compute_nodes_ip))
            LOG.debug("compute_node_ip: {}".format(compute_node_ip))
            LOG.debug("first_controller_node_ip: {}"
                      .format(first_controller_node_ip))
            LOG.debug("undercloud_config: {}".format(undercloud_config))
            LOG.debug("instack_file: {}".format(instack_file))

            stop_disable_openstack_services(compute_nodes_ip)
            distribute_node_authkey(compute_node_ip)
            enable_start_compute_pacemaker(compute_node_ip)
            add_compute_node_stonith_devices(compute_node_ip,
                                             undercloud_config,
                                             first_controller_node_ip,
                                             instack_file)
            create_compute_node_resources(compute_node_ip,
                                          first_controller_node_ip)
            enable_control_plane_services(first_controller_node_ip)
            final_resource_cleanup(first_controller_node_ip)

        else:
            LOG.critical("!!! - Fatal Error: Invalid IP address: {}"
                         .format(compute_node_ip))
            exit(-1)

    # Execute Controller node addition
    if args.controller_node_ip != '':
        controller_node_ip = args.controller_node_ip.rstrip()
        if check_ip_validity(controller_node_ip):
            LOG.info("***  Adding a controller node {} to InstanceHA"
                     " configuration.".format(controller_node_ip))

            LOG.debug("controller_node_ip: {}".format(controller_node_ip))
            LOG.debug("first_controller_node_ip: {}"
                      .format(first_controller_node_ip))

            distribute_node_authkey(controller_node_ip)
            tag_controllers_with_osprole(first_controller_node_ip)
            final_resource_cleanup(first_controller_node_ip)

        else:
            LOG.critical("!!! - Fatal Error: Invalid IP address: {}"
                         .format(controller_node_ip))
            sys.exit(-1)

if __name__ == "__main__":
    main()
