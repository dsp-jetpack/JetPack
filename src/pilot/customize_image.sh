#!/usr/bin/env bash

# Copyright (c) 2016-2017 Dell Inc. or its subsidiaries.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

subscription_manager_user="$1"
subscription_manager_pass="$2"
subscription_manager_poolid="$3"
proxy="$4"

if [ "$#" -lt 2 ]; then
  echo "Usage: $0  <subscription manager user> <subscription manager password> [<subscription pool id>] [<proxy>]"
  exit 1
fi

if [ ! -z "$proxy" ];
then
  echo "## Configuring proxy"
  ip_addresses=$(ip addr | grep -Po 'inet \K[\d.]+')
  no_proxy_list=$(echo $ip_addresses | tr ' ' ',')

  export no_proxy=$no_proxy_list
  export http_proxy=$proxy
  export https_proxy=$proxy
fi

echo "## install libguestfs-tools"
cd ~/pilot/images
sudo yum install libguestfs-tools -y

export LIBGUESTFS_BACKEND=direct

if [ -z "${subscription_manager_poolid}" ]; then
    subscription_manager_poolid=$(sudo subscription-manager list --available --matches='Red Hat Ceph Storage' --pool-only|tail -n1)
    if [ -z "${subscription_manager_poolid}" ]; then
        echo "subscription_manager_poolid is empty."
        exit 1
    fi
    echo "Red Hat Ceph Storage pool: ${subscription_manager_poolid}"
fi


repos=(
    rhel-7-server-rpms
    rhel-7-server-rhscon-2-agent-rpms
    rhel-7-server-rhceph-2-mon-rpms
)

packages=(
    calamari-server
    rhscon-agent
)

function join { local IFS="$1"; shift; echo "$*"; }

echo "## Updating the overcloud image"

virt-customize \
    --memsize 2000 \
    --add overcloud-full.qcow2 \
    --sm-credentials "${subscription_manager_user}:password:${subscription_manager_pass}" \
    --sm-register \
    --sm-attach "pool:${subscription_manager_poolid}" \
    --run-command "subscription-manager repos --disable='*' ${repos[*]/#/--enable=}" \
    --install $(join "," ${packages[*]}) \
    --sm-remove \
    --sm-unregister \
    --selinux-relabel 2>&1 | tee -a ~/pilot/customize_image.log

echo "## Done updating the overcloud image"

