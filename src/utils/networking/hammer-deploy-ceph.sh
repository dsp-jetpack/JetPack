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

HOST_ID=$1
HOST_IP=$2

#POOL_ID=$3
#POOL_ID=8a85f98744091dea0144314ba24c726c

FOURTH=`echo $HOST_IP | cut -d. -f4`
API_IP="192.168.140.${FOURTH}"
API_NM=255.255.255.0
NOVA_PRIVATE_IP="192.168.202.${FOURTH}"
NOVA_PRIVATE_NM=255.255.255.0
STORAGE_IP="192.168.170.${FOURTH}"
STORAGE_NM=255.255.255.0
NOVA_PUBLIC_IP="192.168.190.${FOURTH}"
NOVA_PUBLIC_NM=255.255.255.0
CEPH_PRIVATE_IP=192.168.180.${FOURTH}
CEPH_PRIVATE_NM=255.255.255.0


hammer host set-parameter --host-id  $HOST_ID --name bonds --value '( [bond0]="onboot none" [bond0.170]="onboot static vlan ${STORAGE_IP}/${STORAGE_NM}" [bond1]="onboot none" [bond1.180]="onboot static vlan ${CEPH_PRIVATE_IP}/${CEPH_PRIVATE_NM}" )'

hammer host set-parameter --host-id  $HOST_ID --name bond_opts --value '( [bond0]="mode=balance-tlb miimon=100" [bond1]="mode=balance-tlb miimon=100" )'

hammer host set-parameter --host-id  $HOST_ID --name bond_ifaces --value '([bond0]="em1 p4p1" [bond1]="em2 p4p2" ) '


