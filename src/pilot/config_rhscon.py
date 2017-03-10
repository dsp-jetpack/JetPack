#!/usr/bin/env python

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

import argparse
import logging
import novaclient.client as nova_client
import os
import sys
import time

from command_helper import Scp, Ssh
from credential_helper import CredentialHelper
from logging_helper import LoggingHelper
from netaddr import IPNetwork
from network_helper import NetworkHelper

logging.basicConfig()
LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


class RhsconException(BaseException):
    pass


class Node:
    """
    This is essentially a helper class that makes it easy to run commands
    and transfer files on a remote system. In addition, it provides a simple
    framework for storing and updating the node's machine ID, which is
    required for the code that configures the Overcloud nodes to work with
    the Storage Console.
    """

    etc_hosts = "/etc/hosts"

    storage_network = NetworkHelper.get_storage_network()

    def __init__(self, address, username, password=None):
        self.address = address
        self.username = username
        self.password = password
        self.fqdn = address  # Initial value that will be updated later

    def _read_machine_id(self):
        self.machine_id = self.run("cat /etc/machine-id")

    def initialize(self):
        self.fqdn = self.run("hostname")
        self._read_machine_id()

        # Find the node's IP address on the storage network
        addrs = self.run("sudo ip -4 addr | awk '$1 == \"inet\" {print $2}'")
        for addr in addrs.split("\n"):
            ip_network = IPNetwork(addr)
            if ip_network == Node.storage_network:
                self.storage_ip = str(ip_network.ip)
                break

        if not getattr(self, "storage_ip", None):
            msg = "Node at {} does not have an IP address on the storage" \
                  " network".format(self.address)
            LOG.error(msg)
            raise RhsconException(msg)

    def update_machine_id(self):
        LOG.warn("Generating a new /etc/machine-id on {}".format(self.fqdn))
        self.run("sudo rm -f /etc/machine-id")
        self.run("sudo systemd-machine-id-setup")
        self._read_machine_id()

    def execute(self, command):
        status, stdout, stderr = Ssh.execute_command(self.address,
                                                     command,
                                                     user=self.username,
                                                     password=self.password)

        # For our purposes, any leading or trailing '\n' just gets in the way
        stdout = stdout.strip("\n")
        stderr = stderr.strip("\n")

        LOG.debug("Executed command on {}: \n"
                  "  command : {}\n"
                  "  status  : {}\n"
                  "  stdout  : {}\n"
                  "  stderr  : {}".format(
                      self.fqdn, command, status, stdout, stderr))

        return status, stdout, stderr

    def run(self, command, check_status=True):
        status, stdout, stderr = self.execute(command)
        if int(status) != 0 and check_status:
            raise RhsconException("Command execution failed on {} ({})".format(
                self.fqdn, self.address))
        return stdout

    def put(self, localfile, remotefile):
        LOG.debug("Copying {} to {}@{}:{}".format(
            localfile, self.username, self.fqdn, remotefile))
        Scp.put_file(self.address,
                     localfile,
                     remotefile,
                     user=self.username,
                     password=self.password)

    def get(self, localfile, remotefile):
        LOG.debug("Copying {}@{}:{} to {}".format(
            self.username, self.fqdn, remotefile, localfile))
        Scp.get_file(self.address,
                     localfile,
                     remotefile,
                     user=self.username,
                     password=self.password)


def parse_arguments(rhscon_user):
    """ Parses the input argments
    """

    parser = argparse.ArgumentParser(
        description="Configures the Storage Console and overcloud Ceph nodes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("rhscon_addr",
                        help="The IP address of the Storage Console on the"
                        " external network",
                        metavar="ADDR")
    parser.add_argument("rhscon_pass",
                        help="The {} password of the Storage Console".format(
                            rhscon_user),
                        metavar="PASSWORD")

    LoggingHelper.add_argument(parser)

    return parser.parse_args()


def get_ceph_nodes(username):
    """ Returns a list of Ceph nodes (Monitors and OSD nodes)

    Scans the list of servers in the overcloud, and determines whether a
    server is a "Ceph node" by searching for the presence of specific Ceph
    process names.
    """

    LOG.info("Identifying Ceph nodes (Monitor and OSD nodes)")

    os_auth_url, os_tenant_name, os_username, os_password = \
        CredentialHelper.get_undercloud_creds()

    nova = nova_client.Client(2, os_username, os_password,
                              os_tenant_name, os_auth_url)

    ceph_nodes = []
    for server in nova.servers.list():
        # Use the first "ctlplane" (provisioning network) address
        address = server.addresses["ctlplane"][0]["addr"]
        node = Node(address, username)
        node.initialize()

        # Identify Ceph nodes by looking for Ceph monitor or OSD processes.
        # If there are none then it's not a Ceph node.
        ceph_procs = node.run("pgrep -l 'ceph-[mon\|osd]'",
                              check_status=False)
        if ceph_procs:
            LOG.info("{} ({}) is a Ceph node".format(node.fqdn,
                                                     node.storage_ip))

            # Note whether it's a Ceph monitor
            node.is_monitor = ("ceph-mon" in ceph_procs)

            ceph_nodes.append(node)
        else:
            LOG.debug("{} ({}) is not a Ceph node".format(node.fqdn,
                                                          node.storage_ip))

    return sorted(ceph_nodes, key=lambda node: node.fqdn)


def get_calamari_node(ceph_nodes):
    """ Chooses the Calamari server from the list of Ceph nodes

    The Storage Console installation guide states the Calamari server needs
    to run on one, and only one, Monitor node. This function chooses
    controller-0 from the list of overcloud Ceph nodes.
    """

    calamari_node = [n for n in ceph_nodes if "controller-0" in n.fqdn][0]

    if not calamari_node:
        LOG.error("Unable to locate controller-0 (for Calamari server)"
                  " in Ceph nodes")
        raise RhsconException("Error identifying Calamari server")

    LOG.info("Calamari server node is {}".format(calamari_node.fqdn))
    return calamari_node


def prep_machine_ids(nodes):
    """ Ensures the /etc/machine-id is unique on all Ceph nodes

    See https://bugzilla.redhat.com/show_bug.cgi?id=1270860 for what this
    is all about. Apparently the Storage Console uses the machine IDs in
    its database of Ceph nodes, but they may not be unique because the
    overcloud nodes were deployed from a common overcloud image (so they
    all end up with the same machine ID).

    This function will need to exist even after RH fixes the BZ. This is
    because the overcloud may have been deployed prior to the BZ fix.
    """

    LOG.info("Ensuring /etc/machine-id is unique on all Ceph nodes")
    for node in nodes:
        # If there are other nodes with the same machine ID then generate
        # a new ID for this node.
        if len([n for n in nodes if n.machine_id == node.machine_id]) > 1:
            node.update_machine_id()


def prep_host_files(rhscon_node, ceph_nodes, calamari_node):
    """ Prepares the /etc/hosts files on all systems

    The Storage Console prefers using domain names over IP addresses, and
    assumes the names will resolve. The function ensures the necessary
    names are added to the /etc/hosts file on all relevant systems.
    """

    prep_rhscon_hosts(rhscon_node, ceph_nodes)
    prep_ceph_hosts(rhscon_node, ceph_nodes)
    prep_calamari_hosts(calamari_node, ceph_nodes)

def prep_rhscon_hosts(rhscon_node, ceph_nodes):
    """ Prepares the /etc/hosts file on the Storage Console

    Adds entries for every Ceph node so the Storage Console can access
    the nodes using their FQDN.
    """

    LOG.info("Preparing /etc/hosts file on Storage Console ({})".format(
        rhscon_node.fqdn))

    tmp_hosts = os.path.join("/tmp", "hosts-{}".format(rhscon_node.fqdn))
    rhscon_node.get(tmp_hosts, Node.etc_hosts)

    host_entries = []
    with open(tmp_hosts, "r") as f:
        host_entries = f.readlines()

    # Delete any prior Ceph node entries
    beg_banner = "# Entries added for Ceph nodes - Start\n"
    end_banner = "# Entries added for Ceph nodes - End\n"
    try:
        beg = host_entries.index(beg_banner)
        end = host_entries.index(end_banner)
        del(host_entries[beg:end+1])
    except:
        pass

    # Create a new hosts file with the Ceph nodes at the end
    with open(tmp_hosts, "w") as f:
        f.writelines(host_entries)
        f.write(beg_banner)
        for node in ceph_nodes:
            LOG.debug("Adding '{}\t{}'".format(node.storage_ip, node.fqdn))
            f.write("{}\t{}\n".format(node.storage_ip, node.fqdn))
        f.write(end_banner)

    # Upload the new file to the Storage Console
    rhscon_node.put(tmp_hosts, tmp_hosts)
    rhscon_node.run("sudo cp {} {}.bak".format(Node.etc_hosts, Node.etc_hosts))
    rhscon_node.run("sudo mv {} {}".format(tmp_hosts, Node.etc_hosts))
    rhscon_node.run("sudo restorecon {}".format(Node.etc_hosts))
    os.unlink(tmp_hosts)

def configure_access(ceph_nodes):
    """For Ceph 2.0 Monitor nodes use port 6789 for communication 
    within the Ceph cluster. The monitor where the calamari-lite is 
    running uses port 8002 for access to the Calamari REST-based API.
    """
    for node in ceph_nodes:
        node.run("sudo iptables -I INPUT -p tcp -s 0.0.0.0/0 --dport 4505 -j ACCEPT")
        node.run("sudo iptables -I INPUT -p tcp -s 0.0.0.0/0 --dport 4506 -j ACCEPT")
        node.run("sudo iptables -I INPUT -p tcp -s 0.0.0.0/0 --dport 6789 -j ACCEPT")
        node.run("sudo iptables -I INPUT -p tcp -s 0.0.0.0/0 --dport 8002 -j ACCEPT")
        node.run("sudo service iptables save")

def prep_ceph_hosts(rhscon_node, ceph_nodes):
    """ Prepares the /etc/hosts file on the Ceph nodes

    Adds an entry to every Ceph node's host file for the Storage Console's
    FQDN and the Storage Console's IP address on the storage network.
    """

    LOG.info("Preparing /etc/hosts file on Ceph nodes")
    LOG.debug("Adding '{}\t{}'".format(
        rhscon_node.storage_ip, rhscon_node.fqdn))

    beg_banner = "# Entries added for Storage Console - Start\n"
    end_banner = "# Entries added for Storage Console - End\n"

    for node in ceph_nodes:
        # Fetch a copy of the node's hosts file
        tmp_hosts = os.path.join("/tmp", "hosts-{}".format(node.fqdn))
        node.get(tmp_hosts, Node.etc_hosts)

        host_entries = []
        with open(tmp_hosts, "r") as f:
            host_entries = f.readlines()

        # Delete any prior Storage Console entries
        try:
            beg = host_entries.index(beg_banner)
            end = host_entries.index(end_banner)
            del(host_entries[beg:end+1])
        except:
            pass

        # Create a new hosts file with the Storage Console entry at the end
        with open(tmp_hosts, "w") as f:
            f.writelines(host_entries)
            f.write("{}{}\t{}\n{}".format(
                beg_banner, rhscon_node.storage_ip,
                rhscon_node.fqdn, end_banner))

        # Upload the new file to the node
        node.put(tmp_hosts, tmp_hosts)
        node.run("sudo cp {} {}.bak".format(Node.etc_hosts, Node.etc_hosts))
        node.run("sudo mv {} {}".format(tmp_hosts, Node.etc_hosts))
        node.run("sudo restorecon {}".format(Node.etc_hosts))
        os.unlink(tmp_hosts)

    #configure access now 
    configure_access(ceph_nodes)


def prep_calamari_hosts(calamari_node, ceph_nodes):
    """Prepares the /etc/hosts file on the Calamari server

    NOTE: See https://bugzilla.redhat.com/show_bug.cgi?id=1414918
          This function implements a workaround to the BZ.

    The Storage Console likes to identify nodes by their FQDN, which is
    typically what you see when running "hostname --fqdn" on each
    node. However, when the Storage Console imports an external Ceph cluster,
    it uses the Calamari server (running on a Ceph monitor node, such as
    controller-0) to acquire the FQDNs of every MON and OSD node in the
    cluster.

    The Calamari server uses the contents of its own /etc/hosts file to map
    the IP address of each node to the FQDN that it reports to the Storage
    Console, and the hosts file is created by the OSP Director. Unfortunately,
    the Director adds an extra ".storage" subdomain to all Controllers'
    storage network address. This causes the Calamari server to report an
    FQDN for all monitors that don't match their actual FQDN, and that ends
    up confusing the Storage Console.

    The workaround involves patching the Calamari server's /etc/hosts file.
    Each entry for Ceph node that's a Ceph Monitor (that would be the
    controllers), the patch ensures the first host name matches the host's
    real FQDN, and not the name that includes the extra ".storage" subdomain.

    Only the controller entries need to be patched. For the OSD nodes, the
    FQDN for their storage network address happens to match the actual FQDN
    (no patching necessary).
    """

    LOG.info("Preparing /etc/hosts file on Calamari server ({})".format(
        calamari_node.fqdn))

    tmp_hosts = os.path.join("/tmp", "hosts-{}".format(calamari_node.fqdn))
    calamari_node.get(tmp_hosts, Node.etc_hosts)

    host_entries = []
    with open(tmp_hosts, "r") as f:
        host_entries = f.readlines()

    # We only need to worry about patching the Ceph Monitor entries
    for node in [n for n in ceph_nodes if n.is_monitor]:
        # Scan all lines in host_entries by index so that, if necessary, we
        # can replace an entry using its index.
        for index in range(len(host_entries)):
            entry = host_entries[index]
            tokens = entry.split()
            if len(tokens) < 2:
                continue
            if tokens[0] == node.storage_ip and tokens[1] != node.fqdn:
                new_entry = entry.replace(node.storage_ip, "{} {}".format(
                    node.storage_ip, node.fqdn))
                LOG.info("Patching host entry:\n"
                         "  was : {}"
                         "  now : {}".format(entry, new_entry.strip("\n")))
                host_entries[index] = new_entry
                break

    with open(tmp_hosts, "w") as f:
        f.writelines(host_entries)

    # Upload the file to the Calamari node, but this time do not create
    # another backup file.
    calamari_node.put(tmp_hosts, tmp_hosts)
    calamari_node.run("sudo mv {} {}".format(tmp_hosts, Node.etc_hosts))
    calamari_node.run("sudo restorecon {}".format(Node.etc_hosts))
    os.unlink(tmp_hosts)


def start_rhscon_skyring(rhscon_node):
    """ Starts the Skyring service on the Storage Console

    Skyring is the name of the service that implements the Storage Console's
    UI, and it needs to be set up. The "skyring-setup" command prompts the
    user for a small amount of input, which is scripted below.
    """

    LOG.info("Starting 'skyring' on Storage Console ({})".format(
        rhscon_node.fqdn))

    # NOTE: "skyring-setup is a short Python script, and one of the first
    # things it does is initialize the Django database that is used to store
    # metrics collected from the Ceph nodes. Unfortunately, early tests
    # revealed that command wants to prompt for user input, and will basically
    # swallow *ALL* input we try to pipe into the "skyring-setup" script.
    #
    # Fortunately, this can be avoided by running the same Django command with
    # an additional "--noinput" argument. So, first we run the Django command
    # with --noinput," and this makes Django happy enough so that it doesn't
    # prompt for input when the command is run again by "skyring-setup." The
    # nature of the Django command is such that it's OK to run it twice.
    #
    # Find the exact command that will run Django's "syncdb". Then run the
    # command with an additional "--noinput" argument.
    syncdb_cmd = rhscon_node.run("grep syncdb $(which skyring-setup)")
    rhscon_node.run("{} --noinput".format(syncdb_cmd))

    # Now run the "skyring-setup" and specify answers for the two questions
    # it will ask:
    #    1) The public FQDN or IP of the Storage Console
    #    2) Whether we want to create a self-signed SSL certificate
    rhscon_node.run("skyring-setup <<EOF\n"
                    "{}\n"
                    "y\n"
                    "EOF".format(rhscon_node.address))

    # Restart the service so it picks up the new configuration
    rhscon_node.run("systemctl restart skyring")

    # Pause for a bit to give the service time to come up. That way it's
    # ready before we try to install the console agent on the Ceph nodes.
    time.sleep(5)


def install_console_agent(rhscon_node, ceph_nodes):
    """ Installs the Storage Console agent on all Ceph nodes

    The console agent installation is pretty clever. Each node tickles a
    RESTful API on the Storage Console and pipes the output to bash. The
    script is quite small, and basically it just creates a special
    "ceph-installer" user, and sets things up so the Storage Console has
    SSH access and sudo privilege (basically the same as the "heat-admin"
    account used by the Director). The last line of the bash script causes
    the node to tickle another Storage Console RESTful API, which triggers
    the Storage Console to finish the storage console installation.

    To monitor the installation process, you can tickle yet another RESTful
    API, and the output reveals the Storage Console is running an Ansible
    playbook. This function manages the overall installation by parsing
    the Ansible output.
    """

    LOG.info("Installing Storage Console agent on Ceph nodes")

    # This hot mess is the curl command to execute the RESTful API for
    # checking the console agent installation process, followed by a sed
    # script that converts "\n" (two characters) into a single '\n' newline.
    # Note that each '\' has to be escaped for Python.
    check_task_cmd = "curl -sS http://{}:8181/api/tasks/ |" \
                     " sed -e 's/\\\\n/\\n/g'".format(rhscon_node.storage_ip)

    for node in ceph_nodes:
        LOG.debug("Installing the agent on {} ({})".format(
            node.fqdn, node.storage_ip))

        # Tickle the RESTful API to trigger the console agent installation
        node.run("curl -sS http://{}:8181/setup/agent/ | sudo bash".format(
            rhscon_node.storage_ip))

        # Poll a while until the installation task completes
        result = ""
        for i in range(1, 30):
            time.sleep(5)

            # Here we run the command that dumps the output of the Ansible
            # playbook that drives the console agent installation.
            # Unfortunately you get the output for *all* runs of the playbook
            # (one per Ceph node), so we filter on this particular node's
            # IP address. Ansible always finishes with summary lines that
            # begin with the IP address of the remote systems, so we look
            # for the IP address at the beginning of the line.

            result = node.run("{} | grep ^{} | tail -1".format(
                check_task_cmd, node.storage_ip), check_status=False)
            if result:
                break

            LOG.debug("Waiting for the installation to complete ({})...".
                      format(i))

        # The final summary provided by Ansible will indicate the number
        # of commands that failed, and we need to be sure none of them did.
        if "failed=0" not in result:
            LOG.error("An error or timeout occured when installing the Storage"
                      " Console agent on {} ({})".format(
                          node.fqdn, node.storage_ip))
            LOG.error("Run this command for hints on what may have happened:")
            LOG.error("  ssh {}@{} {}".format(
                      node.username, node.address, check_task_cmd))
            raise RhsconException(
                "Error or timeout installing the Storage Console agent")

    # End of install_console_agent


def start_calamari_server(rhscon_node, calamari_node):
    """Starts the Calamari server

    Runs the command that initialzes and starts the Calamari server (one
    of the Ceph Monitor nodes)

    Under the old Calamari UI (prior to the Storage Console), the Calamari
    server ran on the Ceph admin VM, and was configured with the username
    and password used to log into the UI.

    With the Storage Console, the Calamari server runs on one of the Ceph
    Monitor nodes, and it communicates with the Storage Console UI running
    on a VM. In fact, the Storage Console is the one that logs into the
    Calarmari server.

    NOTE:

    The Storage Console installation instructions mention it uses hard-coded
    credentials when logging into the Calamari server !!!  It's important the
    Calamari server be initialed to use the same credentials or else the
    Storage Console won't be able to connect to it. The hard-coded credentials
    are... (wait for it!) admin/admin.
    """

    LOG.info("Starting Calamari sever on {}".format(calamari_node.fqdn))

    # NOTE: This is where the Calamari server credentials are hard-coded
    calamari_node.run("sudo calamari-ctl initialize --admin-username admin"
                      " --admin-password admin --admin-email admin@{}".format(
                          rhscon_node.fqdn))


def check_bz_1403576(rhscon_node, ceph_node):
    """ Checks whether BZ 1403576 will prevent installing the console agent

    Check the ceph-ansible version on the Storage Console. If it's old
    (pre-2.0) then there will be a problem installing the Storage Console agent
    on the Ceph nodes unless the Overcloud nodes are registered.
    """

    ceph_ansible_version = rhscon_node.run(
        "yum list ceph-ansible | awk '$1 ~ /ceph-ansible/ {print $2}'")

    LOG.info("Storage Console has ceph-ansible-{}".format(
        ceph_ansible_version))
    if ceph_ansible_version.startswith("2."):
        return

    _, stdout, _ = rhscon_node.execute("sudo grep ignore_errors " +
                                       "/usr/share/ceph-ansible/" +
                                       "roles/ceph-agent/tasks/" +
                                       "pre_requisite.yml")

    if "ignore_errors" not in stdout:
        LOG.warn("Patching /usr/share/ceph-ansible on {}".format(
            rhscon_node.fqdn))
        LOG.warn("See https://bugzilla.redhat.com/show_bug.cgi?id=1403576"
                 " for details")
        rhscon_node.run("yum -y install patch")
        rhscon_node.run("""
cat << EOF | patch -b -d /usr/share/ceph-ansible/roles/ceph-agent/tasks
--- pre_requisite.yml.orig
+++ pre_requisite.yml
@@ -2,6 +2,7 @@
 - name: determine if node is registered with subscription-manager.
   command: subscription-manager identity
   register: subscription
+  ignore_errors: true
   changed_when: false
   when:
     ansible_os_family == 'RedHat'
EOF
""")


def main():
    """ Configures the Storage Console and Ceph nodes
    """

    rhscon_user = "root"
    args = parse_arguments(rhscon_user)
    LOG.setLevel(args.logging_level)

    rhscon_node = Node(args.rhscon_addr, rhscon_user, args.rhscon_pass)
    rhscon_node.initialize()

    LOG.info("Configuring Storage Console on {} ({})".format(
        rhscon_node.address, rhscon_node.fqdn))

    ceph_nodes = get_ceph_nodes(username="heat-admin")
    calamari_node = get_calamari_node(ceph_nodes)

    # Make sure BZ 1403576 won't bite us. This check can be removed once
    # an upstream fix reaches CDN, and that should happen before JS-7
    # is released.
    check_bz_1403576(rhscon_node, calamari_node)

    prep_machine_ids(ceph_nodes)
    prep_host_files(rhscon_node, ceph_nodes, calamari_node)

    start_rhscon_skyring(rhscon_node)
    install_console_agent(rhscon_node, ceph_nodes)
    start_calamari_server(rhscon_node, calamari_node)

    LOG.info("Storage Console configuration is complete")

if __name__ == "__main__":
    sys.exit(main())
