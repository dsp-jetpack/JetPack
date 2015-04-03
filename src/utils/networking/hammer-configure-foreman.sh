#!/bin/bash
# Copyright 2015, Dell
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
# Version: 1.0
#

. ./common.sh

echo
echo "Configuring Foreman:"
echo

MEDIUM_NAME="Dell OSP Pilot"
MEDIUM_ID=$(hammer medium list|grep "${MEDIUM_NAME}" |awk '{print $1}')
if [ -z "${MEDIUM_ID}" ]
then
  execute "hammer medium create --name \"${MEDIUM_NAME}\" --os-family Redhat --path \"${MEDIUM_URL}\""
  MEDIUM_ID=$(hammer medium list|grep "${MEDIUM_NAME}" |awk '{print $1}')
else
  echo "Medium ${MEDIUM_NAME} already exists"
  echo
fi

P_NAME="dell-pilot"
P_ID=$(hammer partition-table list|grep " ${P_NAME} "|awk '{print $1}')
if [ -z "$P_ID" ]
then
  execute "hammer partition-table create --name \"${P_NAME}\" --os-family Redhat --file ${PILOT_DIR}/dell-pilot.partition"
  P_ID=$(hammer partition-table list|grep " ${P_NAME} "|awk '{print $1}')
else
  echo "Partition table ${P_NAME} already exists"
  echo
fi

P730_NAME="dell-pilot-730xd"
P730_ID=$(hammer partition-table list|grep "${P730_NAME}"|awk '{print $1}')
if [ -z "$P730_ID" ]
then
  execute "hammer partition-table create --name \"${P730_NAME}\" --os-family Redhat --file ${PILOT_DIR}/dell-pilot-730xd.partition"
  P730_ID=$(hammer partition-table list|grep "${P730_NAME}"|awk '{print $1}')
else
  echo "Partition table ${P739_NAME} already exists"
  echo
fi

OS_NAME="RedHat 7.0"
OS_ID=$(hammer os list|grep "${OS_NAME}"|awk '{print $1}')
if [ -z "$OS_ID" ]
then
  execute "hammer os create --name \"RedHat\" --major 7 --minor 0 --family Redhat"
  OS_ID=$(hammer os list|grep "${OS_NAME}"|awk '{print $1}')
else
  echo "OS ${OS_NAME} already exists"
  echo
fi

execute "hammer os add-architecture --architecture x86_64 --id ${OS_ID}"

execute "hammer os add-ptable --ptable-id ${P_ID} --id ${OS_ID}"
execute "hammer os add-ptable --ptable-id ${P730_ID} --id ${OS_ID}"

SN_NAME="OpenStack"
SN_ID=$(hammer subnet list|grep "${SN_NAME}"|awk '{print $1}')

execute "hammer subnet update --id ${SN_ID} --from ${START_IP_RANGE} --to ${END_IP_RANGE} --gateway ${GATEWAY_IP}"

DOKT_NAME="Dell OpenStack Kickstart Template"
DOKT_ID=$(hammer template list|grep "${DOKT_NAME}"|awk '{print $1}')
if [ -z "$DOKT_ID" ]
then
  execute "hammer template create --name \"${DOKT_NAME}\" --type provision --operatingsystem-ids \"${OS_ID}\" --file ${PILOT_DIR}/dell-osp-ks.template"
  DOKT_ID=$(hammer template list|grep "${DOKT_NAME}"|awk '{print $1}')
else
  echo "Provisioning template ${DOKT_NAME} already exists"
  echo
fi

DOPT_NAME="Dell OpenStack PXE Template"
DOPT_ID=$(hammer template list|grep "${DOPT_NAME}"|awk '{print $1}')
if [ -z "$DOPT_ID" ]
then
  execute "hammer template create --name \"${DOPT_NAME}\" --type PXELinux --operatingsystem-ids \"${OS_ID}\" --file ${PILOT_DIR}/dell-osp-pxe.template"
  DOPT_ID=$(hammer template list|grep "${DOPT_NAME}"|awk '{print $1}')
else
  echo "Provisioning template ${DOPT_NAME} already exists"
  echo
fi

BIT_NAME="bond_interfaces"
BIT_ID=$(hammer template list|grep "${BIT_NAME}"|awk '{print $1}')
if [ -z "$BIT_ID" ]
then
  execute "hammer template create --name \"${BIT_NAME}\" --type snippet --file ${PILOT_DIR}/bonding_snippet.template"
  BIT_ID=$(hammer template list|grep "${BIT_NAME}"|awk '{print $1}')
else
  echo "Provisioning template snippet ${BIT_NAME} already exists"
  echo
fi

ICT_NAME="interface_config"
ICT_ID=$(hammer template list|grep "${ICT_NAME}"|awk '{print $1}')
if [ -z "$ICT_ID" ]
then
  execute "hammer template create --name \"${ICT_NAME}\" --type snippet --file ${PILOT_DIR}/interface_config.template"
  ICT_ID=$(hammer template list|grep "${ICT_NAME}"|awk '{print $1}')
else
  echo "Provisioning template snippet ${ICT_NAME} already exists"
  echo
fi

execute "hammer os update --config-template-ids \"${DOKT_ID}, ${DOPT_ID}\" --medium-ids ${MEDIUM_ID} --id ${OS_ID}"

execute "hammer os set-default-template --config-template-id ${DOKT_ID} --id ${OS_ID}"
execute "hammer os set-default-template --config-template-id ${DOPT_ID} --id ${OS_ID}"

ENV_ID=$(hammer environment list|grep production|awk '{print $1}')
DOMAIN_ID=$(hammer domain list|grep "$(dnsdomainname)"|awk '{print $1}')
PROXY_ID=$(hammer proxy list|grep "$(hostname)"|awk '{print $1}')
ARCH_ID=$(hammer architecture list|grep x86_64|awk '{print $1}')

execute "hammer os set-parameter --operatingsystem-id ${OS_ID} --name subscription_manager --value true"

execute "hammer os set-parameter --operatingsystem-id ${OS_ID} --name subscription_manager_username --value \"${SUBSCRIPTION_MANAGER_USERNAME}\""
echo

execute "hammer os set-parameter --operatingsystem-id ${OS_ID} --name subscription_manager_password --value \"${SUBSCRIPTION_MANAGER_PASSWORD}\""

echo
echo IDs:
echo
echo Medium ID: ${MEDIUM_ID}
echo OS ID: ${OS_ID}
echo ${P_NAME} partition table ID: ${P_ID}
echo ${P730_NAME} partition table ID: ${P730_ID}
echo "${DOKT_NAME} ID: ${DOKT_ID}"
echo "${DOPT_NAME} ID: ${DOPT_ID}"
echo "${BIT_NAME} template ID: ${BIT_ID}"
echo "${ICT_NAME} template ID: ${ICT_ID}"
echo Environment ID: ${ENV_ID}
echo Domain ID: ${DOMAIN_ID}
echo Proxy ID: ${PROXY_ID}
echo Architecture ID: ${PROXY_ID}
