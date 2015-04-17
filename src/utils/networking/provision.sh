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
. ./osp_config.sh

HOSTNAME="$1"
MAC="$2"
IP="$3"
ROOT_PASSWORD="$4"
POOL_ID="$5"
SUBSCRIPTION_MANAGER_REPOS="$6"

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
  --partition-table-id "${P_ID}" \
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
