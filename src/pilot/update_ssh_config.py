#!/usr/bin/python

import os
import re
import subprocess


def get_nodes():
    """
    Generator that returns a node name / IP addr tuple for every node returned
    by running "nova list"
    """

    # A dictionary that maps nova node names to something shorter and easier
    # to type.
    node_names = {
        'overcloud-controller': 'cntl',
        'overcloud-novacompute': 'nova',
        'overcloud-cephstorage': 'stor'
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


def main():
    """
    (Re)writes your ~/.ssh/config file with data that makes it easy to
    access each node by a simple name, such as "cntl0" instead of
    "overcloud-controller-0"

    This script is intended to be run only on the Director node, where it's
    OK to rewrite the "stack" user's ~/.ssh/config.
    """

    ssh_config = os.path.join(os.path.expanduser('~'), '.ssh', 'config')
    with open(ssh_config, 'w') as f:
        for node, addr in get_nodes():
            f.write("Host {}\n".format(node))
            f.write("  Hostname {}\n".format(addr))
            f.write("  User heat-admin\n\n")
    os.chmod(ssh_config, 0600)


if __name__ == "__main__":
    main()
