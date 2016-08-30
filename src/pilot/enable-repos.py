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
