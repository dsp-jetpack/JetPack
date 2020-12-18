#!/usr/bin/env bash

# Copyright (c) 2016-2021 Dell Inc. or its subsidiaries.
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



USAGE="\nUsing RedHat CDN :$0 [--director_ip <director_public_ip>] [--proxy <proxy>]  \nUsing Satellite : $0 [--director_ip <director_public_ip>] --satellite_hostname <satellite_host_name>   [--proxy <proxy> ]"

TEMP=`getopt -o h --long proxy:,satellite_hostname:,satellite_org:,satellite_key:,director_ip: -n 'customize_image.sh' -- "$@"`
eval set -- "$TEMP"

# extract options and their arguments into variables.
while true ; do
    case "$1" in
        -h|help)
            echo -e "$USAGE "
            exit 1
            ;;
        --director_ip)
                director_public_ip=$2; shift 2 ;;
        --satellite_hostname)
                satellite_hostname=$2; shift 2;;
        --proxy)
                proxy=$2; shift 2 ;;
        --) shift ; break ;;
        *) echo -e "-$USAGE" ; exit 1 ;;
    esac
done


if [ ! -z "${proxy}" ];
then
  echo "## Configuring proxy"
  ip_addresses=$(ip addr | grep -Po 'inet \K[\d.]+')
  no_proxy_list=$(echo $ip_addresses | tr ' ' ',')

  export no_proxy=$no_proxy_list
  export http_proxy=$proxy
  export https_proxy=$proxy
fi


run_command(){

  cmd=$*
  echo "Executing: $cmd"

  eval $cmd
  if [ $? -ne 0 ]; then
    echo "$cmd execution failed"
    exit 1
  fi
}


echo "## install libguestfs-tools"
cd ~/pilot/images
run_command  "sudo yum install libguestfs-tools -y"
run_command "sudo service libvirtd start"

export LIBGUESTFS_BACKEND=direct


function join { local IFS="$1"; shift; echo "$*"; }

echo "## Updating the overcloud image"
cd ~/pilot
# director_ip=`grep 'network_gateway = ' undercloud.conf | awk -F" = " '{print $2}'`
director_short=`hostname -s`
director_long=`hostname`
cd ~/pilot/images


if [ ! -z "${satellite_hostname}" ]; then
    satelliteip=`grep "${satellite_hostname}" /etc/hosts | awk '{print $1}'`
    run_command "virt-customize \
        --memsize 2000 \
        --add overcloud-full.qcow2 \
        --run-command \"echo '${satelliteip}   ${satellite_hostname}' >> /etc/hosts;hostname tempname \" \
        --selinux-relabel -v"
else
    run_command "virt-customize -a overcloud-full.qcow2 --run-command \"echo '${director_public_ip} ${director_short} ${director_long}' >> /etc/hosts\""

fi

run_command "virt-customize \
    --add overcloud-full.qcow2"

echo "## Done updating the overcloud image"
