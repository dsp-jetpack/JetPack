#!/usr/bin/python

import os
import re
import subprocess

from misc_helper import MiscHelper


def get_nodes():
    """
    Generator that returns a node name / IP addr tuple for every node returned
    by running "nova list"
    """

    stack_name = MiscHelper.get_stack_name()

    # A dictionary that maps nova node names to something shorter and easier
    # to type.
    node_names = {
        stack_name + '-controller': 'cntl',
        stack_name + '-novacompute': 'nova',
        stack_name + '-cephstorage': 'stor'
    }

    for line in subprocess.check_output(['nova', 'list']).split('\n'):
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
            else:
                node = node_type + node_num
        except IndexError:
            pass
        yield node, addr


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
        # just suppress it. If there are error messages, the user will eventually
        # see them when they try to access the host that triggered the error.
        subprocess.call(cmd,
                        stdout=open(known_hosts_new, 'a'),
                        stderr=open('/dev/null', 'w'))
    except:
        pass

    if os.path.isfile(known_hosts):
        os.rename(known_hosts, known_hosts + '.old')
    os.rename(known_hosts_new, known_hosts)
    os.chmod(known_hosts, 0600)


def main():
    """
    (Re)writes your ~/.ssh/config file with data that makes it easy to
    access each node by a simple name, such as "cntl0" instead of
    "overcloud-controller-0"

    This script is intended to be run only on the Director node, where it's
    OK to rewrite the "stack" user's ~/.ssh/config.
    """

    overcloud_addrs = []

    ssh_config = os.path.join(os.path.expanduser('~'), '.ssh', 'config')
    with open(ssh_config, 'w') as f:
        for node, addr in get_nodes():
            overcloud_addrs.append(addr)
            f.write("Host {}\n".format(node))
            f.write("  Hostname {}\n".format(addr))
            f.write("  User heat-admin\n\n")
    os.chmod(ssh_config, 0600)

    update_known_hosts(overcloud_addrs)


if __name__ == "__main__":
    main()
