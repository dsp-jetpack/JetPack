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
import sys
import argparse

args_parser = argparse.ArgumentParser()
args_parser.add_argument("--proxy", help="proxy address formatted as 'http://<proxy_user>:<proxy_password>@<proxy_address>:<proxy_port>'")

args = args_parser.parse_args()

repos = [
    "rhel-7-server-openstack-10-rpms",
    "rhel-7-server-openstack-10-devtools-rpms"]

def execute(cmd):
    print cmd
    return_code = os.system(cmd)
    if return_code != 0:
        sys.exit(return_code)

if args.proxy:
    proxy = args.proxy
    os.environ["http_proxy"]=proxy
    os.environ["https_proxy"]=proxy

for repo in repos:
    execute("subscription-manager repos --enable=%s" % repo)
    execute("yum-config-manager --enable %s --setopt=%s.priority=1" %
            (repo, repo))
