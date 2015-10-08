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
  partition_id="$7"

  host_id=$(echo "${existing_hosts}"|grep "${hostname}"|awk '{print $1}')

  if [ -z "${host_id}" ]
  then
    echo "Creating host: ${hostname}"
    if [ -z "${MEDIUM_ID}" ]
    then
      . ./hammer-get-ids.sh
    fi
    ./provision.sh "${hostname}" "${mac}" "${ip}" "${root_password}" "${pool_id}" "${repos}" "${partition_id}"
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