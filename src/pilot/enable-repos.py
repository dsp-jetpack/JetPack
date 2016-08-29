#!/usr/bin/python

import os
import sys


repos = [
    "rhel-7-server-openstack-9-rpms",
    "rhel-7-server-openstack-9-director-rpms"]


def execute(cmd):
    print cmd
    return_code = os.system(cmd)
    if return_code != 0:
        sys.exit(return_code)


for repo in repos:
    execute("subscription-manager repos --enable=%s" % repo)
    execute("yum-config-manager --enable %s --setopt=%s.priority=1" %
            (repo, repo))
