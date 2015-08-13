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
. ./osp_config.sh

HOSTNAME="$1"
MAC="$2"
IP="$3"
ROOT_PASSWORD="$4"
POOL_ID="$5"
SUBSCRIPTION_MANAGER_REPOS="$6"
PARTITION_ID="$7"

if [ -z "${MEDIUM_ID}" ]
then
  . ./hammer-get-ids.sh
fi

hammer host create \
  --name "${HOSTNAME}" \
  --root-password "${ROOT_PASSWORD}" \
  --build true \
  --enabled true \
  --managed true \
  --medium-id "${MEDIUM_ID}" \
  --operatingsystem-id "${OS_ID}" \
  --partition-table-id "${PARTITION_ID}" \
  --environment-id "${ENV_ID}" \
  --domain-id "${DOMAIN_ID}" \
  --puppet-proxy-id "${PROXY_ID}" \
  --architecture-id "${ARCH_ID}" \
  --subnet-id "${SN_ID}" \
  --ip "${IP}" \
  --mac "${MAC}"

HOST_ID=$(hammer host list|grep "${HOSTNAME}"|awk '{print $1}')

[[ $HOST_ID ]] || exit 1

hammer host set-parameter --host-id ${HOST_ID} \
  --name subscription_manager_repos \
  --value "${SUBSCRIPTION_MANAGER_REPOS}"

hammer host set-parameter --host-id ${HOST_ID} \
  --name subscription_manager_pool \
  --value "${POOL_ID}"