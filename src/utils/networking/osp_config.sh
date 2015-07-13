#!/bin/bash
# Copyright 2014, Dell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author:  Chris Dearborn
# Version: 1.1
#
MEDIUM_URL="http://CHANGEME_IP/CHANGEME_PATH"
START_IP_RANGE="CHANGEME_SUBNET_START_IP"
END_IP_RANGE="CHANGEME_SUBNET_END_IP"
GATEWAY_IP="CHANGEME_FOREMAN_PROVISIONING_IP"
SUBSCRIPTION_MANAGER_USERNAME="CHANGEME_USERNAME"
SUBSCRIPTION_MANAGER_PASSWORD="CHANGEME_PASSWORD"

# CHANGEME: Customize the interface for the IDRAC NIC below as needed
IDRAC_NIC="CHANGEME_IDRAC_NIC"

# CHANGEME: Customize the interfaces for the bonds for each needed server 
# model below as needed
# e.g. CHANGEME_BOND1 => "p5p2 p7p2"
# the entire line would look like:
# R720_BONDS="( [bond0]=\"p5p1 p7p1\" [bond1]=\"p5p2 p7p2\" )"

R430_BONDS="( [bond0]=\"CHANGEME_BOND0\" [bond1]=\"CHANGEME_BOND1\" )"
R630_BONDS="( [bond0]=\"CHANGEME_BOND0\" [bond1]=\"CHANGEME_BOND1\" )"
R730_BONDS="( [bond0]=\"CHANGEME_BOND0\" [bond1]=\"CHANGEME_BOND1\" )"
R630XD_BONDS="( [bond0]=\"CHANGEME_BOND0\" [bond1]=\"CHANGEME_BOND1\" )"
R730XD_BONDS="( [bond0]=\"CHANGEME_BOND0\" [bond1]=\"CHANGEME_BOND1\" )"
R720_BONDS="( [bond0]=\"CHANGEME_BOND0\" [bond1]=\"CHANGEME_BOND1\" )"
R720XD_BONDS="( [bond0]=\"CHANGEME_BOND0\" [bond1]=\"CHANGEME_BOND1\" )"

# assign bonds for one of the supported server models, where SERVER_MODEL 
# (such as "R720") is passed as parameter to the parent script 
eval "SERVER_BONDS=\${${SERVER_MODEL}_BONDS}"

# set the bonding options for each type of node. Supported bond mode types:
#   "mode=802.3ad miimon=100"  (compute, storage)
#   "balance-xor miimon=100"   (controller)
CONTROLLER_BOND_OPTS="CHANGEME_BOND_OPTS"
COMPUTE_BOND_OPTS="CHANGEME_BOND_OPTS"
STORAGE_BOND_OPTS="CHANGEME_BOND_OPTS"

# CHANGEME: Specify your Red Hat Subscription Manager Repository pool id
# (It's a very long apha-numeric string: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
POOL_ID="CHANGEME_POOL_ID"

# Cluster root password
ROOT_PASSWORD='CHANGEME_PASSWORD'

CONTROLLER_NODE_REPOS="\
rhel-7-server-rpms, \
rhel-server-rhscl-7-rpms, \
rhel-7-server-openstack-6.0-rpms, \
rhel-ha-for-rhel-7-server-rpms"

COMPUTE_NODE_REPOS="\
rhel-7-server-rpms, \
rhel-server-rhscl-7-rpms, \
rhel-7-server-openstack-6.0-rpms"

STORAGE_NODE_REPOS="\
rhel-7-server-rpms"

CONTROLLER_PARTITION_NAME="CHANGEME_PARTITION_NAME e.g. dell-pilot"

COMPUTE_PARTITION_NAME="CHANGEME_PARTITION_NAME e.g. dell-pilot"

# CHANGEME - if using xd model as storage, likely one of
# 12G 720xd - "dell-pilot"
# 13G 730xd - "dell-pilot-730xd"
STORAGE_PARTITION_NAME="CHANGEME_PARTITION_NAME"
