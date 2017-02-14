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

import os
import re
import subprocess
import tempfile

from credential_helper import CredentialHelper


def get_nodes():
    """
    Generator that returns a node name / IP addr tuple for every node returned
    by running "nova list"
    """

    stack_name = CredentialHelper.get_overcloud_name()

    # A dictionary that maps nova node names to something shorter and easier
    # to type.
    node_names = {
        stack_name + '-controller': 'cntl',
        stack_name + '-novacompute': 'nova',
        stack_name + '-compute': 'nova',
        stack_name + '-cephstorage': 'stor'
    }

    # Ensure 'nova list' is performed on the undercloud!
    undercloudrc = CredentialHelper.get_undercloudrc_name()
    nova_list_cmd = 'source {} && nova list'.format(undercloudrc)

    for line in subprocess.check_output(nova_list_cmd, shell=True).split('\n'):
        # Create a match object that chops up the "nova list" output so we
        # can extract the pieces we need.
        m = re.search('(.+ \| )(\S+)(-)(\d+)( .+ctlplane=)(\S+)( .+)', line)
        if not m:
            # No match (probably banner text)
            continue
        try:
            node_type = m.group(2)
            node_num = m.group(4)
            addr = m.group(6)
            if node_type in node_names:
                node = node_names[node_type] + node_num
                full_name = node_type + "-" + node_num
            else:
                node = node_type + node_num
                full_name = node_type + "-" + node_num
        except IndexError:
            pass
        yield node, addr, full_name


def update_known_hosts(host_addrs):
    """
    Updates your ~/.ssh/known_hosts file the ssh keys for each of the
    host_addrs. First it removes old (stale) entries for each address,
    then it uses ssh-keyscan to fetch fresh keys.
    """

    known_hosts = os.path.join(os.path.expanduser('~'), '.ssh', 'known_hosts')
    try:
        with open(known_hosts, 'r') as f:
            hosts = list(f)
    except:
        hosts = []

    # Remove stale references to all host_addrs
    for addr in host_addrs:
        for h in [h for h in hosts if h.startswith(addr + ' ')]:
            hosts.remove(h)

    # Write remaining entries to a new file
    known_hosts_new = known_hosts + '.new'
    with open(known_hosts_new, 'w') as f:
        f.writelines(hosts)

    # Fetch and append the keys for the host_addrs
    try:
        cmd = 'ssh-keyscan -t ecdsa-sha2-nistp256'.split()
        cmd.extend(host_addrs)
        # ssh-keyscan produces "chatty" output on stderr when things work, so
        # just suppress it. If there are error messages, the user will
        # eventually see them when they try to access the host that triggered
        # the error.
        subprocess.call(cmd,
                        stdout=open(known_hosts_new, 'a'),
                        stderr=open('/dev/null', 'w'))
    except:
        pass

    if os.path.isfile(known_hosts):
        os.rename(known_hosts, known_hosts + '.old')
    os.rename(known_hosts_new, known_hosts)
    os.chmod(known_hosts, 0600)


def update_etc_hosts(overcloud):
    """
    Rewrites /etc/hosts, adding fresh entries for each overcloud node.
    """
    etc_hosts = '/etc/hosts'
    etc_file = open(etc_hosts, 'r')

    new_fd, new_hosts = tempfile.mkstemp()
    new_file = os.fdopen(new_fd, 'w')

    marker = '# Overcloud entries generated by update_ssh_config.py\n'

    # Generate a clean hosts file with old entries removed
    for line in etc_file.readlines():
        words = line.split()
        if ((line == marker) or
            (len(words) == 3 and words[2] in overcloud.keys())):

            continue
        new_file.write(line)

    etc_file.close()

    # Add new entries for the overcloud nodes
    new_file.write(marker)
    for node in sorted(overcloud.keys()):
        new_file.write('{} {}\n'.format(overcloud[node], node))

    new_file.close()
    os.chmod(new_hosts, 0644)
    os.system('sudo mv {} {}'.format(new_hosts, etc_hosts))
    os.system('sudo chown root:root {}'.format(etc_hosts))


def main():
    """
    (Re)writes your ~/.ssh/config file with data that makes it easy to
    access each node by a simple name, such as "cntl0" instead of
    "overcloud-controller-0".  Adds similar entries to /etc/hosts.

    This script is intended to be run only on the Director node, where it's
    OK to rewrite the "stack" user's ~/.ssh/config.
    """

    overcloud = {}

    ssh_config = os.path.join(os.path.expanduser('~'), '.ssh', 'config')
    with open(ssh_config, 'w') as f:
        for node, addr, full_name in get_nodes():
            overcloud[node] = addr + " " + full_name
            f.write("Host {} {}\n".format(node, full_name))
            f.write("  Hostname {}\n".format(addr))
            f.write("  User heat-admin\n\n")
    os.chmod(ssh_config, 0600)
    
    update_known_hosts(overcloud.values())
    update_etc_hosts(overcloud)


if __name__ == "__main__":
    main()
