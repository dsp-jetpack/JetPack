#!/usr/bin/python

import re
import os
import netaddr


class NetworkHelper:
    @staticmethod
    def get_provisioning_network():
        pattern = re.compile("^network_cidr\s*=\s*(.+)$")
        undercloud_conf = open(os.path.join(os.path.expanduser('~'), 'pilot',
                                            'undercloud.conf'), 'r')

        cidr = None
        for line in undercloud_conf:
            match = pattern.match(line)
            if match:
                cidr = netaddr.IPNetwork(match.group(1))
                break

        return cidr
