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

. ./common.sh

echo
echo "Configuring Foreman:"
echo

. ./hammer-get-ids.sh
echo

if [ -z "${MEDIUM_ID}" ]
then
  execute "hammer medium create --name \"${MEDIUM_NAME}\" --os-family Redhat --path \"${MEDIUM_URL}\""
  MEDIUM_ID=$(hammer medium list|grep "${MEDIUM_NAME}" |awk '{print $1}')
else
  echo "Medium ${MEDIUM_NAME} already exists"
  echo
fi

if [ -z "$P_ID" ]
then
  execute "hammer partition-table create --name \"${P_NAME}\" --os-family Redhat --file ${PILOT_DIR}/dell-pilot.partition"
  P_ID=$(hammer partition-table list|grep " ${P_NAME} "|awk '{print $1}')
else
  echo "Partition table ${P_NAME} already exists"
  echo
fi

if [ -z "$P730_ID" ]
then
  execute "hammer partition-table create --name \"${P730_NAME}\" --os-family Redhat --file ${PILOT_DIR}/dell-pilot-730xd.partition"
  P730_ID=$(hammer partition-table list|grep "${P730_NAME}"|awk '{print $1}')
else
  echo "Partition table ${P730_NAME} already exists"
  echo
fi

if [ -z "$OS_ID" ]
then
  OS_PREFIX=$(echo "${OS_NAME}"|awk '{print $1}')
  OS_SUFFIX=$(echo "${OS_NAME}"|awk '{print $2}')
  OS_MAJOR=$(echo "${OS_SUFFIX}"|awk -F . '{print $1}')
  OS_MINOR=$(echo "${OS_SUFFIX}"|awk -F . '{print $2}')

  execute "hammer os create --name \"$OS_PREFIX\" --major ${OS_MAJOR} --minor ${OS_MINOR} --family Redhat"
  OS_ID=$(hammer os list|grep "${OS_NAME}"|awk '{print $1}')
else
  echo "OS ${OS_NAME} already exists"
  echo
fi

execute "hammer os add-architecture --architecture x86_64 --id ${OS_ID}"

execute "hammer os add-ptable --ptable-id ${P_ID} --id ${OS_ID}"
execute "hammer os add-ptable --ptable-id ${P730_ID} --id ${OS_ID}"

execute "hammer subnet update --id ${SN_ID} --from ${START_IP_RANGE} --to ${END_IP_RANGE} --gateway ${GATEWAY_IP}"

if [ -z "$DOKT_ID" ]
then
  execute "hammer template create --name \"${DOKT_NAME}\" --type provision --operatingsystem-ids \"${OS_ID}\" --file ${PILOT_DIR}/dell-osp-ks.template"
  DOKT_ID=$(hammer template list|grep "${DOKT_NAME}"|awk '{print $1}')
else
  echo "Provisioning template ${DOKT_NAME} already exists"
  echo
fi

if [ -z "$DOPT_ID" ]
then
  execute "hammer template create --name \"${DOPT_NAME}\" --type PXELinux --operatingsystem-ids \"${OS_ID}\" --file ${PILOT_DIR}/dell-osp-pxe.template"
  DOPT_ID=$(hammer template list|grep "${DOPT_NAME}"|awk '{print $1}')
else
  echo "Provisioning template ${DOPT_NAME} already exists"
  echo
fi

if [ -z "$BIT_ID" ]
then
  execute "hammer template create --name \"${BIT_NAME}\" --type snippet --file ${PILOT_DIR}/bonding_snippet.template"
  BIT_ID=$(hammer template list|grep "${BIT_NAME}"|awk '{print $1}')
else
  echo "Provisioning template snippet ${BIT_NAME} already exists"
  echo
fi

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

execute "hammer os set-parameter --operatingsystem-id ${OS_ID} --name subscription_manager --value true"

execute "hammer os set-parameter --operatingsystem-id ${OS_ID} --name subscription_manager_username --value \"${SUBSCRIPTION_MANAGER_USERNAME}\""
echo

execute "hammer os set-parameter --operatingsystem-id ${OS_ID} --name subscription_manager_password --value \"${SUBSCRIPTION_MANAGER_PASSWORD}\""

./hammer-dump-ids.sh

./hammer-ceph-fix.sh

# Workaround for neutron fails to start, BZ1192674
cp /usr/share/openstack-puppet/modules/neutron/manifests/server.pp /usr/share/openstack-puppet/modules/neutron/manifests/server.pp.orig

sed -e "s/require.*=> Neutron_config/subscribe     => Neutron_config/"  /usr/share/openstack-puppet/modules/neutron/manifests/server.pp.orig > /usr/share/openstack-puppet/modules/neutron/manifests/server.pp