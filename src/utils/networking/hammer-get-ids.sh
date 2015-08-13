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

echo -n "Getting IDs"

echo -n "."
export MEDIUM_ID=$(hammer medium list|grep "${MEDIUM_NAME}" |awk '{print $1}')

echo -n "."
export OS_ID=$(hammer os list|grep "${OS_NAME}"|awk '{print $1}')

echo -n "."
export P_ID=$(hammer partition-table list|grep " ${P_NAME} "|awk '{print $1}')

echo -n "."
export P730_ID=$(hammer partition-table list|grep "${P730_NAME}"|awk '{print $1}')

echo -n "."
export SN_ID=$(hammer subnet list|grep "${SN_NAME}"|awk '{print $1}')

echo -n "."
export DOKT_ID=$(hammer template list|grep "${DOKT_NAME}"|awk '{print $1}')

echo -n "."
export DOPT_ID=$(hammer template list|grep "${DOPT_NAME}"|awk '{print $1}')

echo -n "."
export BIT_ID=$(hammer template list|grep "${BIT_NAME}"|awk '{print $1}')

echo -n "."
export ICT_ID=$(hammer template list|grep "${ICT_NAME}"|awk '{print $1}')

echo -n "."
export ENV_ID=$(hammer environment list|grep production|awk '{print $1}')

echo -n "."
export DOMAIN_ID=$(hammer domain list|grep "$(dnsdomainname)"|awk '{print $1}')

echo -n "."
export PROXY_ID=$(hammer proxy list|grep "$(hostname)"|awk '{print $1}')

echo "."
export ARCH_ID=$(hammer architecture list|grep x86_64|awk '{print $1}')