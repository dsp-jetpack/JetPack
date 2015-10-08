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
shopt -s nullglob

HOSTNAME="$1"
MAC="$2"
HOST_IP="$3"
SERVER_MODEL="$4"

. ./osp_config.sh
. ./common.sh

PARTITION_ID=$(hammer partition-table list|grep " ${COMPUTE_PARTITION_NAME} "|awk '{print $1}')

create_host "${HOSTNAME}" "${MAC}" "${HOST_IP}" "${ROOT_PASSWORD}" "${POOL_ID}" "${COMPUTE_NODE_REPOS}" "${PARTITION_ID}"
HOST_ID=$(hammer host list|grep "${HOSTNAME}"|awk '{print $1}')
[[ $HOST_ID ]] || die "could not create host!"

FOURTH=`echo $HOST_IP | cut -d. -f4`

API_IP=192.168.140.${FOURTH}
API_NM=255.255.255.0

STORAGE_IP=192.168.170.${FOURTH}
STORAGE_NM=255.255.255.0

echo "hammer host set-parameter --host-id  $HOST_ID --name bonds --value '( [bond0]=\"onboot none promisc\" [bond0.140]=\"onboot static vlan ${API_IP}/${API_NM}\" [bond1]=\"onboot static ${STORAGE_IP}/${STORAGE_NM}\" )'"
hammer host set-parameter --host-id  $HOST_ID --name bonds --value "( [bond0]=\"onboot none promisc\" [bond0.140]=\"onboot static vlan ${API_IP}/${API_NM}\" [bond1]=\"onboot static ${STORAGE_IP}/${STORAGE_NM}\" )"

echo "hammer host set-parameter --host-id  $HOST_ID --name bond_opts --value \'( [bond0]=\"$COMPUTE_BOND_OPTS\" [bond1]=\"$COMPUTE_BOND_OPTS\" )\'"
hammer host set-parameter --host-id  $HOST_ID --name bond_opts --value "( [bond0]=\"$COMPUTE_BOND_OPTS\" [bond1]=\"$COMPUTE_BOND_OPTS\" )"
echo "hammer host set-parameter --host-id  $HOST_ID --name bond_ifaces --value \"${SERVER_BONDS}\""
hammer host set-parameter --host-id  $HOST_ID --name bond_ifaces --value "${SERVER_BONDS}"