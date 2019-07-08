#!/usr/bin/env python

# Copyright (c) 2017-2019 Dell Inc. or its subsidiaries.
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
import re
import shutil
import tempfile

from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client

from command_helper import Scp, Ssh
from credential_helper import CredentialHelper
from os.path import expanduser

from logging_helper import LoggingHelper
from netaddr import IPNetwork
from network_helper import NetworkHelper
from socket import getaddrinfo

logging.basicConfig()
LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])


class DashboardException(BaseException):
    pass


class Node:
    """
    This is essentially a helper class that makes it easy to run commands
    and transfer files on a remote system. In addition, it provides a simple
    framework for storing and updating the node's machine ID, which is
    required for the code that configures the Overcloud nodes to work with
    the Ceph Storage Dashboard.
    """

    etc_hosts = "/etc/hosts"
    ansible_hosts = "/etc/ansible/hosts"
    ceph_conf = "/etc/ceph/ceph.conf"
    prometheus_yml = "/var/lib/cephmetrics/prometheus.yml"
    subscription_json = "~/pilot/subscription.json"
    root_home = expanduser("~root")
    heat_admin_home = expanduser("~heat-admin")

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
            raise DashboardException(msg)

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
            raise DashboardException("Command execution failed on {} ({})"
                                     .format(self.fqdn, self.address))
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


def sed_inplace(filename, pattern, repl):
    pattern_compiled = re.compile(pattern)

    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        with open(filename) as src_file:
            for line in src_file:
                tmp_file.write(pattern_compiled.sub(repl, line))

    shutil.copystat(filename, tmp_file.name)
    shutil.move(tmp_file.name, filename)


def parse_arguments(dashboard_user):
    """ Parses the input argments
    """

    parser = argparse.ArgumentParser(
        description="Configures the Ceph Storage Dashboard and Ceph nodes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-dashboard_addr", "--dashboard_addr",
                        help="The IP address of the Ceph Storage Dashboard "
                        "on the external network", required=True)
    parser.add_argument("-dashboard_pass", "--dashboard_pass",
                        help="The password of the Ceph Storage Dashboard "
                        "node ", required=True)
    parser.add_argument("-subUser", "--sbUser",
                        help="The username for Red Hat Subscription Access",
                        action='store', required=False)
    parser.add_argument("-subPass", "--subPass",
                        help="The password for Red Hat Subscription Access",
                        action='store', required=False)
    parser.add_argument("-satOrg", "--satOrg",
                        help="The Red Hat Satellite Organization",
                        action='store', required=False)
    parser.add_argument("-satKey", "--satKey",
                        help="The Red Hat Satellite Activation Key",
                        action='store', required=False)
    parser.add_argument("-physId", "--physId",
                        help="The subscription poolid for Physical Nodes",
                        required=True)
    parser.add_argument("-cephId", "--cephId",
                        help="The subscription poolid for Ceph Nodes",
                        required=True)

    LoggingHelper.add_argument(parser)

    return parser.parse_args()


def get_ceph_nodes(username):
    """ Returns a list of Ceph nodes (Monitors and OSD nodes)

    Scans the list of servers in the overcloud, and determines whether a
    server is a "Ceph node" by searching for the presence of specific Ceph
    process names.
    """

    LOG.info("Identifying Ceph nodes (Monitor and OSD nodes)")

    os_auth_url, os_tenant_name, os_username, os_password, \
        os_user_domain_name, os_project_domain_name = \
        CredentialHelper.get_undercloud_creds()
    auth_url = os_auth_url + "v3"

    auth = v3.Password(
        auth_url=auth_url,
        username=os_username,
        password=os_password,
        project_name=os_tenant_name,
        user_domain_name=os_user_domain_name,
        project_domain_name=os_project_domain_name
    )

    sess = session.Session(auth=auth)
    nova = nova_client.Client(2, session=sess)

    ceph_nodes = []
    for server in nova.servers.list():
        # Use the first "ctlplane" (provisioning network) address
        address = server.addresses["ctlplane"][0]["addr"]
        node = Node(address, username)
        node.initialize()

        # Identify Ceph nodes by looking for Ceph monitor or OSD processes.
        # If there are none then it's not a Ceph node.
        ceph_procs = node.run("pgrep -l 'ceph-[mon\|osd]'",  # noqa: W605
                              check_status=False)
        if ceph_procs:
            # A small cheat below strips domain name from node name
            # as it is not ever used to coonfigure the dashboard
            node.fqdn = node.fqdn + ".mydomain"
            # if (node.fqdn.find(".")):
            if ('.' in node.fqdn):
                node.fqdn, domain_name = node.fqdn.split('.', 1)
            else:
                node.fqdn = node.fqdn
            LOG.info("{} ({}) is a Ceph node".format(node.fqdn,
                                                     node.storage_ip))
            ceph_nodes.append(node)
        else:
            LOG.debug("{} ({}) is not a Ceph node".format(node.fqdn,
                                                          node.storage_ip))

    return sorted(ceph_nodes, key=lambda node: node.fqdn)


def prep_host_files(dashboard_node, ceph_nodes):
    """ Prepares the /etc/hosts files on all systems

    The Ceph Storage Dashboard prefers using domain names
    over IP addresses, and assumes the names will resolve. The function
    ensures the necessary names are added to the /etc/hosts file on all
    relevant systems.
    """

    prep_dashboard_hosts(dashboard_node, ceph_nodes)
    prep_ceph_hosts(dashboard_node, ceph_nodes)


def prep_dashboard_hosts(dashboard_node, ceph_nodes):
    """ Prepares the hosts file on the Ceph Storage Dashboard

    Adds entries for every Ceph node so the Ceph Storage Dashboard
    can access the nodes using their FQDN.
    """

    LOG.info("Preparing hosts file on Ceph Storage Dashboard.")

    tmp_hosts = os.path.join("/tmp", "hosts-{}".format(dashboard_node.fqdn))
    dashboard_node.get(tmp_hosts, Node.etc_hosts)

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
    except:  # noqa: E722
        pass

    # Create a new hosts file with the Ceph nodes at the end
    with open(tmp_hosts, "w") as f:
        f.writelines(host_entries)
        f.write(beg_banner)
        for node in ceph_nodes:
            LOG.debug("Adding '{}\t{}'"
                      .format(node.storage_ip, node.fqdn))
            f.write("{}\t{}\n"
                    .format(node.storage_ip,
                            node.fqdn))
        f.write(end_banner)

    # Upload the new file to the Ceph Storage Dashboard
    dashboard_node.put(tmp_hosts, tmp_hosts)
    dashboard_node.run("sudo cp {} {}.bak"
                       .format(Node.etc_hosts, Node.etc_hosts))
    dashboard_node.run("sudo mv {} {}".format(tmp_hosts, Node.etc_hosts))
    dashboard_node.run("sudo restorecon {}".format(Node.etc_hosts))
    os.unlink(tmp_hosts)


def prep_ceph_hosts(dashboard_node, ceph_nodes):
    """ Prepares the hosts file on the Ceph nodes

    Adds an entry to every Ceph node's host file for the
    Ceph Storage Dashboard's FQDN and the Ceph
    Storage Dashboard's IP address on the storage network.
    """

    LOG.info("Preparing hosts file on Ceph nodes.")
    LOG.debug("Adding '{}\t{}'".format(
        dashboard_node.storage_ip, dashboard_node.fqdn))

    beg_banner = "# Entries added for Ceph Storage Dashboard - Start\n"
    end_banner = "# Entries added for Ceph Storage Dashboard - End\n"

    for node in ceph_nodes:
        # Fetch a copy of the node's hosts file
        tmp_hosts = os.path.join("/tmp", "hosts-{}".format(node.fqdn))
        node.get(tmp_hosts, Node.etc_hosts)

        host_entries = []
        with open(tmp_hosts, "r") as f:
            host_entries = f.readlines()

        # Delete any prior Ceph Storage Dashboard entries
        try:
            beg = host_entries.index(beg_banner)
            end = host_entries.index(end_banner)
            del(host_entries[beg:end+1])
        except:  # noqa: E722
            pass

        # Create a new hosts file with the Ceph Storage Dashboard
        with open(tmp_hosts, "w") as f:
            f.writelines(host_entries)
            f.write("{}{}\t{}\n{}".format(
                beg_banner, dashboard_node.storage_ip,
                dashboard_node.fqdn, end_banner))

        # Upload the new file to the node
        node.put(tmp_hosts, tmp_hosts)
        node.run("sudo cp {} {}.bak".format(Node.etc_hosts, Node.etc_hosts))
        node.run("sudo mv {} {}".format(tmp_hosts, Node.etc_hosts))
        node.run("sudo restorecon {}".format(Node.etc_hosts))
        os.unlink(tmp_hosts)


def prep_root_user(dashboard_node, ceph_nodes):
    """ Prepares root user on the Ceph Storage Dashboard
    Modifies the Ceph Storage Nodes so that Ceph Storage Dashboard
    can access so that root can install dashboard.
    """

    home = expanduser("~")
    root_key = Node.root_home + "/.ssh/authorized_keys"
    tmp_key = "/tmp/authorized_keys"
    repl_str = ".*sleep 10\" "
    bak_date = dashboard_node.run('date +"%Y%m%d%H%M"')

    status, stdout, stderr = dashboard_node.execute("[ -f {} ] \
                                                    && echo true \
                                                    || echo false "
                                                    .format(root_key))
    if "true" in stdout:
        return

    LOG.info("Preparing remote access on the Ceph Storage Dashboard.")

    ssh_files = ('.ssh/authorized_keys',
                 '.ssh/id_rsa',
                 '.ssh/id_rsa.pub')

    for file in ssh_files:
        tmp_ssh_file = os.path.join("/tmp", "tmp_ssh_file-{}"
                                    .format(dashboard_node.fqdn))
        node_ssh_dir = Node.root_home + "/.ssh"
        node_file = os.path.join(Node.root_home, file)
        local_file = os.path.join(os.sep, home, file)

        dashboard_node.put(local_file, tmp_ssh_file)
        dashboard_node.run("sudo /bin/bash -c 'if [ ! -d {} ]; \
                           then mkdir {}; fi'"
                           .format(node_ssh_dir, node_ssh_dir))
        dashboard_node.run("sudo chown root.root {}".format(node_ssh_dir))
        dashboard_node.run("sudo chmod 0700 {}".format(node_ssh_dir))
        dashboard_node.run("sudo mv {} {}".format(tmp_ssh_file, node_file))
        dashboard_node.run("sudo chown root.root {}".format(node_file))
        dashboard_node.run("sudo chmod 0600 {}".format(node_file))
        dashboard_node.run("sudo restorecon {}".format(node_file))
    dashboard_node.run("sudo cat ~root/.ssh/id_rsa.pub \
                       >> ~root/.ssh/authorized_keys")

    for node in ceph_nodes:
        dashboard_node.run("sudo ssh-keyscan -t ecdsa-sha2-nistp256 {} \
                           >> ~root/.ssh/known_hosts".format(node.fqdn))
    dashboard_node.run("sudo ssh-keyscan -t ecdsa-sha2-nistp256 {} \
                       >> ~root/.ssh/known_hosts"
                       .format(dashboard_node.fqdn))

    for node in ceph_nodes:
        tmp_keys = os.path.join("/tmp", "key-{}".format(node.fqdn))
        node.run("sudo cp {} {}-{}.bak".format(root_key, root_key, bak_date))
        node.run("sudo cp {} {}".format(root_key, tmp_key))
        node.run("sudo chmod 0644 {}".format(tmp_key))
        node.run("sudo sed -i 's/{}//' {}".format(repl_str, tmp_key))
        node.get(tmp_keys, tmp_key)
        node.run("sudo mv {} {}".format(tmp_key, root_key))
        node.run("sudo chmod 0400 {}".format(root_key))


def prep_heat_admin_user(dashboard_node, ceph_nodes):
    """ Prepares heat_admin user on the Ceph Storage Dashboard
    Modifies the Ceph Storage Nodes so that Ceph Storage Dashboard
    can access so that root can install dashboard.
    """

    home = expanduser("~")
    heat_admin_key = Node.heat_admin_home + "/.ssh/authorized_keys"
    tmp_key = "/tmp/heat_authorized_keys"
    repl_str = ".*sleep 10\" "
    bak_date = dashboard_node.run('date +"%Y%m%d%H%M"')

    status, stdout, stderr = dashboard_node.execute("[ -f {} ] \
                                                    && echo true \
                                                    || echo false "
                                                    .format(heat_admin_key))
    if "true" in stdout:
        return

    LOG.info("Preparing remote access on the Ceph Storage Dashboard.")

    ssh_files = ('.ssh/authorized_keys',
                 '.ssh/id_rsa',
                 '.ssh/id_rsa.pub')

    for file in ssh_files:
        tmp_ssh_file = os.path.join("/tmp", "tmp_ssh_file-{}"
                                    .format(dashboard_node.fqdn))
        node_ssh_dir = Node.heat_admin_home + "/.ssh"
        node_file = os.path.join(Node.heat_admin_home, file)
        local_file = os.path.join(os.sep, home, file)

        dashboard_node.put(local_file, tmp_ssh_file)
        dashboard_node.run("sudo /bin/bash -c 'if [ ! -d {} ]; \
                           then mkdir {}; fi'"
                           .format(node_ssh_dir, node_ssh_dir))
        dashboard_node.run("sudo chown heat-admin.heat-admin {}"
                           .format(node_ssh_dir))
        dashboard_node.run("sudo chmod 0700 {}".format(node_ssh_dir))
        dashboard_node.run("sudo mv {} {}".format(tmp_ssh_file, node_file))
        dashboard_node.run("sudo chown heat-admin.heat-admin {}"
                           .format(node_file))
        dashboard_node.run("sudo chmod 0600 {}".format(node_file))
        dashboard_node.run("sudo restorecon {}".format(node_file))
    dashboard_node.run("sudo cat ~heat-admin/.ssh/id_rsa.pub \
                       >> ~heat-admin/.ssh/authorized_keys")

    for node in ceph_nodes:
        tmp_keys = os.path.join("/tmp", "key-{}".format(node.fqdn))
        node.run("sudo cp {} {}-{}.bak"
                 .format(heat_admin_key, heat_admin_key, bak_date))
        node.run("sudo cp {} {}".format(heat_admin_key, tmp_key))
        node.run("sudo chmod 0644 {}".format(tmp_key))
        node.run("sudo sed -i 's/{}//' {}".format(repl_str, tmp_key))
        node.get(tmp_keys, tmp_key)
        node.run("sudo mv {} {}".format(tmp_key, heat_admin_key))
        node.run("sudo chown heat-admin.heat-admin {}".format(heat_admin_key))
        node.run("sudo chmod 0400 {}".format(heat_admin_key))
        node.run("sudo restorecon {}".format(heat_admin_key))


def prep_ansible_hosts(dashboard_node, ceph_nodes):
    """ Prepares the /etc/ansible/hosts file on the
    Ceph Storage Dashboard. Adds entries for the
    Ceph nodes to the roles sections of the ansible hosts file.
    """

    LOG.info("Preparing ansible host file on Ceph Storage " +
             "Dashboard.")

    tmp_hosts = os.path.join("/tmp", "ansiblehosts-{}"
                             .format(dashboard_node.fqdn))
    dashboard_node.get(tmp_hosts, Node.ansible_hosts)

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
    except:  # noqa: E722
        pass

    # Update the ansible hosts file with the Ceph nodes at the end
    with open(tmp_hosts, "w") as f:
        f.writelines(host_entries)
        f.write("\n")
        f.write(beg_banner)
        mon_nodes = []
        rgw_nodes = []
        osd_nodes = []
        for node in ceph_nodes:
            if "controller" in node.fqdn:
                mon_nodes.append(node)
                rgw_nodes.append(node)
            if "storage" in node.fqdn:
                osd_nodes.append(node)

        LOG.info("Adding Monitors Stanza to Ansible hosts file")
        f.write("[mons]\n")
        for node in mon_nodes:
            f.write("{}\n".format(node.fqdn))

        LOG.info("Adding RadosGW Stanza to Ansible hosts file")
        f.write("\n")
        f.write("[rgws]\n")
        for node in rgw_nodes:
            f.write("{}\n".format(node.fqdn))

        LOG.info("Adding OSD Stanza to Ansible hosts file")
        f.write("\n")
        f.write("[osds]\n")
        for node in osd_nodes:
            f.write("{}\n".format(node.fqdn))

        LOG.info("Adding MGR Stanza to Ansible hosts file")
        f.write("\n")
        f.write("[mgrs]\n")
        for node in mon_nodes:
            f.write("{}\n".format(node.fqdn))

        LOG.info("Adding Graphana Stanza to Ansible hosts file")
        f.write("\n")
        f.write("[ceph-grafana]\n")
        f.write("{}\n".format(dashboard_node.fqdn))
        f.write(end_banner)

    # Upload the new file to the Ceph Storage Dashboard
    dashboard_node.put(tmp_hosts, tmp_hosts)
    dashboard_node.run("sudo cp {} {}.bak"
                       .format(Node.ansible_hosts, Node.ansible_hosts))
    dashboard_node.run("sudo mv {} {}"
                       .format(tmp_hosts, Node.ansible_hosts))
    dashboard_node.run("sudo restorecon {}".format(Node.ansible_hosts))
    os.unlink(tmp_hosts)


def prep_ceph_conf(dashboard_node, ceph_nodes):
    """ Prepares the /etc/ceph/ceph.conf file on the Ceph Storage Nodes
    Adds the string "mon_health_preluminous_compat=true" to the
    mon section of the storage node "ceph.conf" file.
    """
    LOG.info("Preparing /etc/ceph/ceph.conf file on Ceph nodes.")

    beg_banner = "# Preluminous_compat entry added - Start\n"
    end_banner = "# Preluminous_compat entry added - End\n"

    for node in ceph_nodes:
        if "controller" in node.fqdn:
            # Fetch a copy of the node's ceph_conf file
            tmp_hosts = os.path.join("/tmp", "ceph_conf-{}"
                                     .format(node.fqdn))
            node.get(tmp_hosts, Node.ceph_conf)

            host_entries = []
            with open(tmp_hosts, "r") as f:
                host_entries = f.readlines()

            # Delete any prior ceph conf file entries
            try:
                beg = host_entries.index(beg_banner)
                end = host_entries.index(end_banner)
                del(host_entries[beg:end+1])
            except:  # noqa: E722
                pass

            # Create ceph_conf with the preluminous entry
            with open(tmp_hosts, "w") as f:
                f.writelines(host_entries)
                f.write("{}{}\n{}".format(
                    beg_banner,
                    "mon_health_preluminous_compat=true",
                    end_banner))

            # Upload the new file to the node
            node.put(tmp_hosts, tmp_hosts)
            node.run("sudo cp {} {}.bak"
                     .format(Node.ceph_conf, Node.ceph_conf))
            node.run("sudo mv {} {}".format(tmp_hosts, Node.ceph_conf))
            node.run("sudo restorecon {}".format(Node.ceph_conf))
            os.unlink(tmp_hosts)


def restart_prometheus(dashboard_node, ceph_nodes):
    # Prepares the /var/lib/cephmetrics/prometheus.yml file
    LOG.info("Preparing the Ceph Storage Cluster prometheus service.")

    tmp_yml = os.path.join("/tmp", "prometheus.yml-{}"
                           .format(dashboard_node.fqdn))
    dashboard_node.get(tmp_yml, Node.prometheus_yml)

    for node in ceph_nodes:
        if "controller" in node.fqdn or "storage" in node.fqdn:
            orig_str = "'" + node.fqdn + ":"
            repl_str = "'" + node.storage_ip + ":"
            sed_inplace(tmp_yml, orig_str, repl_str)
    dashboard_str = "'" + dashboard_node.fqdn + ":"
    sed_inplace(tmp_yml, dashboard_node.fqdn, "localhost")

    # Upload the new file to the node
    dashboard_node.put(tmp_yml, tmp_yml)
    dashboard_node.run("sudo cp {} {}.bak"
                       .format(Node.prometheus_yml, Node.prometheus_yml))
    dashboard_node.run("sudo mv {} {}".format(tmp_yml, Node.prometheus_yml))
    dashboard_node.run("sudo restorecon {}".format(Node.prometheus_yml))
    os.unlink(tmp_yml)

    LOG.info("Restarting prometheus service on node ({})"
             .format(dashboard_node.fqdn))
    dashboard_node.run("sudo systemctl restart prometheus.service")


def prep_cluster_for_collection(dashboard_node, ceph_nodes, dashboard_addr):
    """ Take over an existing Ceph Storage Cluster
    """

    fsid_repl_str = '#fsid: "{{ cluster_uuid.stdout }}"'
    gen_repl_str = '#generate_fsid: true'
    sym_link = "/etc/ansible/group_vars"
    ceph_ansible_dir = "/usr/share/ceph-ansible"
    toc_yml = "take-over-existing-cluster.yml"
    cephmetrics_ansible_dir = "/usr/share/cephmetrics-ansible"

    # Get ceph fsid information from a storage node
    for node in ceph_nodes:
        if "controller" in node.fqdn:
            ceph_fsid = node.run("sudo ceph fsid", check_status=False)

    status, stdout, stderr = dashboard_node.execute("[ -L {} ] \
                                                    && echo true \
                                                    || echo false"
                                                    .format(sym_link))

    if "true" in stdout:
        return

    LOG.info("Preparing the Ceph Storage Cluster for data collection.")
    dashboard_node.run("sudo ln -s /usr/share/ceph-ansible/group_vars {}"
                       .format(sym_link))
    dashboard_node.run("cd {}; sudo cp all.yml.sample all.yml"
                       .format(sym_link))
    dashboard_node.run("cd {}; sudo echo 'ceph_stable_release: luminous' \
                       >> all.yml" .format(sym_link))
    dashboard_node.run("sudo sed -i 's/{}/fsid: {}/' \
                       /etc/ansible/group_vars/all.yml"
                       .format(fsid_repl_str, ceph_fsid))
    dashboard_node.run("sudo sed -i 's/{}/generate_fsid: false/' \
                       /etc/ansible/group_vars/all.yml"
                       .format(gen_repl_str))
    dashboard_node.run("cd {}; sudo cp infrastructure-playbooks/{} ."
                       .format(ceph_ansible_dir, toc_yml))
    dashboard_node.run("cd {}; sudo echo '      tags:' >> {}"
                       .format(ceph_ansible_dir, toc_yml))
    dashboard_node.run("cd {}; sudo echo '        gen_conf_file' >> {}"
                       .format(ceph_ansible_dir, toc_yml))
    dashboard_node.run("cd {}; ansible-playbook {} -u root --skip-tags \
                       'gen_conf_file'".format(ceph_ansible_dir, toc_yml))
    dashboard_node.run("setsebool -P httpd_can_network_connect 1")

    LOG.info("Installing the Ceph Storage Dashboard.")
    dashboard_node.run("cd {}; sudo ansible-playbook -s -v --skip-tags \
                       cephmetrics-collectors playbook.yml"
                       .format(cephmetrics_ansible_dir))

    for node in ceph_nodes:
        if "controller" in node.fqdn:
            node.run("sudo chmod 644 /etc/ceph/ceph.client.openstack.keyring")

    for node in ceph_nodes:
        if "controller-0" in node.fqdn:
            node.run("sudo pcs resource restart openstack-cinder-volume")

    LOG.info("Ceph Storage Dashboard configuration is complete")
    LOG.info("You may access the Ceph Storage Dashboard at:")
    LOG.info("      http://{}:3000,".format(dashboard_addr))
    LOG.info("with user 'admin' and password 'admin'.")


def prep_subscription_json(subUser, subPass, physId, cephId):
    # Prepares the subscription.json file
    LOG.info("Preparing the subscription json file.")

    tmp_file = os.path.join("/tmp", "subscription.json-mod")
    os.system('cp ' + Node.subscription_json + ' ' + tmp_file)
    sed_inplace(tmp_file, "CHANGEME_username", subUser)
    sed_inplace(tmp_file, "CHANGEME_password", subPass)
    sed_inplace(tmp_file, "CHANGEME_openstack_pool_id", physId)
    sed_inplace(tmp_file, "CHANGEME_ceph_pool_id", cephId)
    os.system('cp ' + tmp_file + ' ' + Node.subscription_json)
    os.unlink(tmp_file)


def prep_subscription_json_satellite(satOrg, satKey, physId, cephId):
    # Prepares the subscription.json file
    LOG.info("Preparing the subscription json file.")

    tmp_file = os.path.join("/tmp", "subscription.json-mod")
    os.system('cp ' + Node.subscription_json + ' ' + tmp_file)
    sed_inplace(tmp_file, "_satellite_credentials", "satellite_credentials")
    sed_inplace(tmp_file, "CHANGEME_organiaztion", satOrg)
    sed_inplace(tmp_file, "CHANGEME_organiaztion", satOrg)
    sed_inplace(tmp_file, "CHANGEME_activationkey", satKey)
    sed_inplace(tmp_file, "CHANGEME_openstack_pool_id", physId)
    sed_inplace(tmp_file, "CHANGEME_ceph_pool_id", cephId)
    os.system('cp ' + tmp_file + ' ' + Node.subscription_json)
    os.unlink(tmp_file)


def register_overcloud_nodes():
    LOG.info("Register the overcloud nodes.")
    os.system("python register_overcloud.py")


def unregister_overcloud_nodes():
    LOG.info("Unregister the overcloud nodes.")
    os.system("python unregister_overcloud.py")


def add_iptables_ports(ceph_nodes):
    LOG.info("Add new ports to iptables ceph nodes")
    for node in ceph_nodes:
        node.run("sudo iptables -I INPUT 1 -m state --state NEW \
                 -m tcp -p tcp --dport 9100 -j ACCEPT")
        node.run("sudo iptables -I INPUT 1 -m state --state NEW \
                 -m tcp -p tcp --dport 9283 -j ACCEPT")
        node.run("sudo iptables-save > /tmp/iptables.new")
        node.run("sudo systemctl stop iptables")
        node.run("sudo mv /tmp/iptables.new /etc/sysconfig/iptables")
        node.run("sudo systemctl start iptables")


def main():
    """ Configures the Ceph Storage Dashboard and Ceph nodes
    """

    dashboard_user = "root"
    args = parse_arguments(dashboard_user)
    LOG.setLevel(args.logging_level)

    dashboard_node = Node(args.dashboard_addr,
                          dashboard_user,
                          args.dashboard_pass)
    dashboard_node.initialize()

    LOG.info("Configuring Ceph Storage Dashboard on {} ({})".format(
        dashboard_node.address, dashboard_node.fqdn))

    ceph_nodes = get_ceph_nodes(username="heat-admin")
    if len(args.satOrg) > 1:
        prep_subscription_json_satellite(args.satOrg, args.satKey,
                                         args.physId, args.cephId)
    else:
        prep_subscription_json(args.subUser, args.subPass,
                               args.physId, args.cephId)
    register_overcloud_nodes()
    prep_host_files(dashboard_node, ceph_nodes)
    prep_root_user(dashboard_node, ceph_nodes)
    prep_heat_admin_user(dashboard_node, ceph_nodes)
    prep_ansible_hosts(dashboard_node, ceph_nodes)
    prep_ceph_conf(dashboard_node, ceph_nodes)
    prep_cluster_for_collection(dashboard_node,
                                ceph_nodes,
                                args.dashboard_addr)
    add_iptables_ports(ceph_nodes)
    unregister_overcloud_nodes()
    restart_prometheus(dashboard_node, ceph_nodes)


if __name__ == "__main__":
    sys.exit(main())
