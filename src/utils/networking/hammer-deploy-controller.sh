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
HOST_IP=$2
HEARTBEAT_IP=$3

FOURTH=`echo $HOST_IP | cut -d. -f4`

HEARTBEAT_NM=255.255.255.0

PUBLIC_IP=192.168.190.${FOURTH}
PUBLIC_NM=255.255.255.0

API_IP=192.168.140.${FOURTH}
API_NM=255.255.255.0

STORAGE_IP=192.168.170.${FOURTH}
STORAGE_NM=255.255.255.0

echo "hammer host set-parameter --host-id  $HOST_ID --name bonds --value '( [bond0]=\"onboot none\" [bond0.170]=\"onboot static vlan ${STORAGE_IP}/${STORAGE_NM}\" [bond0.140]=\"onboot static vlan ${API_IP}/${API_NM}\" [bond1]=\"onboot static ${PUBLIC_IP}/${PUBLIC_NM}\" )'"
hammer host set-parameter --host-id  $HOST_ID --name bonds --value "( [bond0]=\"onboot none\" [bond0.170]=\"onboot static vlan ${STORAGE_IP}/${STORAGE_NM}\" [bond0.140]=\"onboot static vlan ${API_IP}/${API_NM}\" [bond1]=\"onboot static ${PUBLIC_IP}/${PUBLIC_NM}\" )"

echo "hammer host set-parameter --host-id $HOST_ID --name nics --value \'( [${IDRAC_NIC}]=\"onboot static ${HEARTBEAT_IP}/${HEARTBEAT_NM}\")\'"
hammer host set-parameter --host-id $HOST_ID --name nics --value "( [${IDRAC_NIC}]=\"onboot static ${HEARTBEAT_IP}/${HEARTBEAT_NM}\")"

echo "hammer host set-parameter --host-id  $HOST_ID --name bond_opts --value '( [bond0]=\"mode=balance-xor miimon=100\" [bond1]="\mode=balance-xor miimon=100"\ )'"
hammer host set-parameter --host-id  $HOST_ID --name bond_opts --value "( [bond0]=\"mode=balance-xor miimon=100\" [bond1]=\"mode=balance-xor miimon=100\" )"

echo "hammer host set-parameter --host-id  $HOST_ID --name bond_ifaces --value \"${CONTROLLER_BONDS}\""
hammer host set-parameter --host-id $HOST_ID --name bond_ifaces --value "${CONTROLLER_BONDS}"
