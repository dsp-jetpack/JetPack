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
# Version: 1.1
#

. ./osp_config.sh

PILOT_DIR=/root/pilot

MEDIUM_NAME="Dell OSP Pilot"
P_NAME="dell-pilot"
P730_NAME="dell-pilot-730xd"
OS_NAME="RedHat 7.1"
SN_NAME="OpenStack"
DOKT_NAME="Dell OpenStack Kickstart Template"
DOPT_NAME="Dell OpenStack PXE Template"
BIT_NAME="bond_interfaces"
ICT_NAME="interface_config"
ENV_NAME="production"
DOMAIN_NAME=$(dnsdomainname)
PROXY_NAME=$(hostname)
ARCH_NAME="x86_64"


die()
{
  echo "Exiting - $1"
  exit 1
}

execute()
{
  if [[ $1 == *"username"* || $1 == *"password"* ]]
  then
    censored=$(echo $1 | sed "s/\".*\"/\"******\"/")
    echo "# $censored"
  else
    echo "# $1"
  fi

  eval $1 || die
  echo
}


create_host () {
  hostname="$1"
  mac="$2"
  ip="$3"
  root_password="$4"
  pool_id="$5"
  repos="$6"

  host_id=$(echo "${existing_hosts}"|grep "${hostname}"|awk '{print $1}')
  if [ -z "${host_id}" ]
  then
    echo "Creating host: ${hostname}"
    if [ -z "${MEDIUM_ID}" ]
    then
      . ./hammer-get-ids.sh
    fi
    ./provision.sh "${hostname}" "${mac}" "${ip}" "${root_password}" "${pool_id}" "${repos}"
  else
    echo "${hostname} already exists.  Skipping creation."
  fi
}


delete_host () {
  hostname=$1

  host_id=$(echo "${existing_hosts}"|grep "${hostname}"|awk '{print $1}')
  if [ -z "${host_id}" ]
  then
    echo "${hostname} does not exist.  Skipping deletion."
  else
    echo "Deleting host: ${hostname} (${host_id})"
    hammer host delete --id ${host_id}
  fi
}


existing_hosts=$(hammer host list)

