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
# Author:  John Williams
# Version: 1.0
#
shopt -s nullglob

. ./osp_config.sh

HOST_ID=$1

HOST_IP=$(hammer host list | grep "^${HOST_ID} "|awk -F\| '{print $5}'|tr -d '[[:space:]]')
FOURTH=`echo $HOST_IP | cut -d. -f4`

API_IP=192.168.140.${FOURTH}
API_NM=255.255.255.0

STORAGE_IP=192.168.170.${FOURTH}
STORAGE_NM=255.255.255.0

echo "hammer host set-parameter --host-id  $HOST_ID --name bonds --value '( [bond0]=\"onboot none promisc\" [bond0.140]=\"onboot static vlan ${API_IP}/${API_NM}\" [bond1]=\"onboot static ${STORAGE_IP}/${STORAGE_NM}\" )'"
hammer host set-parameter --host-id  $HOST_ID --name bonds --value "( [bond0]=\"onboot none promisc\" [bond0.140]=\"onboot static vlan ${API_IP}/${API_NM}\" [bond1]=\"onboot static ${STORAGE_IP}/${STORAGE_NM}\" )"

echo "hammer host set-parameter --host-id  $HOST_ID --name bond_opts --value '( [bond0]="mode=802.3ad miimon=100" [bond1]="mode=802.3ad miimon=100" )'"
hammer host set-parameter --host-id  $HOST_ID --name bond_opts --value "( [bond0]=\"mode=802.3ad miimon=100\" [bond1]=\"mode=802.3ad miimon=100\" )"
echo "hammer host set-parameter --host-id  $HOST_ID --name bond_ifaces --value \"${COMPUTE_BONDS}\""
hammer host set-parameter --host-id  $HOST_ID --name bond_ifaces --value "${COMPUTE_BONDS}"
