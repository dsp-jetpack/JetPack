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
