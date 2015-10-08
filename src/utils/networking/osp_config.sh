#!/bin/bash
#
# OpenStack - A set of software tools for building and managing cloud
# computing platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.
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
#   "mode=802.3ad miimon=100"        Mode 4 (compute, storage, controller)
#   "mode=balance-xor miimon=100"    Mode 2 (compute, storage, controller)
#   "mode=active-backup miimon=100"  Mode 1 (compute, storage, controller)
CONTROLLER_BOND_OPTS="CHANGEME_BOND_OPTS"
COMPUTE_BOND_OPTS="CHANGEME_BOND_OPTS"
STORAGE_BOND_OPTS="CHANGEME_BOND_OPTS"

# set this to your external tenant vlan for controller nodes (e.g. "bond1.191")
EXTERNAL_TENANT_VLAN=CHANGEME_VLAN

# CHANGEME: Specify your Red Hat Subscription Manager Repository pool id
# (It's a very long apha-numeric string: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
POOL_ID="CHANGEME_POOL_ID"
STORAGE_POOL_ID="CHANGEME_STORAGE_POOL_ID"

# Cluster root password
ROOT_PASSWORD='CHANGEME_PASSWORD'


CONTROLLER_NODE_REPOS="\
rhel-7-server-rpms, \
rhel-server-rhscl-7-rpms, \
rhel-7-server-openstack-7.0-rpms, \
rhel-ha-for-rhel-7-server-rpms, \
rhel-7-server-rhceph-1.3-tools-rpms, \
rhel-7-server-rhceph-1.3-mon-rpms"

COMPUTE_NODE_REPOS="\
rhel-7-server-rpms, \
rhel-server-rhscl-7-rpms, \
rhel-7-server-openstack-7.0-rpms"

STORAGE_NODE_REPOS="\
rhel-7-server-rpms, \
rhel-7-server-rhceph-1.3-osd-rpms"

CONTROLLER_PARTITION_NAME="CHANGEME_PARTITION_NAME e.g. dell-pilot"

COMPUTE_PARTITION_NAME="CHANGEME_PARTITION_NAME e.g. dell-pilot"

# CHANGEME - if using xd model as storage, likely one of
# 12G 720xd - "dell-pilot"
# 13G 730xd - "dell-pilot-730xd"
STORAGE_PARTITION_NAME="CHANGEME_PARTITION_NAME"
