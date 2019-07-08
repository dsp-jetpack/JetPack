#!/usr/bin/env bash

# Copyright (c) 2016-2019 Dell Inc. or its subsidiaries.
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



USAGE="\nUsing RedHat CDN :$0 --sm_user <subscription_manager_user> --sm_pwd <subscription_manager_pass> - sm_pool [<subcription_manager_poolid>] [--proxy <proxy>]   \nUsing Satellite : $0 --satellite_hostname <satellite_host_name> --satellite_org <satellite_organization> --satellite_key <satellite_activation_key> ]  [--proxy <proxy> ]"

TEMP=`getopt -o h --long sm_user:,sm_pwd:,sm_pool:,proxy:,satellite_hostname:,satellite_org:,satellite_key: -n 'customize_image.sh' -- "$@"`
eval set -- "$TEMP"

# extract options and their arguments into variables.
while true ; do
    case "$1" in
        -h|help)
            echo -e "$USAGE "
            exit 1
            ;;
        --sm_user)
                subscription_manager_user=$2 ; shift 2 ;;
        --sm_pwd)
                subscription_manager_pass=$2 ; shift 2 ;;
        --sm_pool)
                subscription_manager_poolid=$2; shift 2 ;;
        --satellite_hostname)
                satellite_hostname=$2; shift 2;;
        --satellite_org)
                satellite_org=$2; shift 2;;
        --satellite_key)
                satellite_key=$2; shift 2;;
        --proxy)
                proxy=$2; shift 2 ;;
        --) shift ; break ;;
        *) echo -e "-$USAGE" ; exit 1 ;;
    esac
done

if [ -z "${satellite_hostname}" ] && [ -z "${subscription_manager_user}" ];then
     echo -e " . $USAGE"
     exit 1
elif [ ! -z "${satellite_hostname}" ]; then
    if [ -z "${satellite_hostname}" ] || [ -z "${satellite_org}" ] || [ -z "${satellite_key}" ] ; then
        echo -e ".. $USAGE"
        exit 1
    fi
elif [ ! -z "${subscription_manager_user}" ];then
    if [ -z "${subscription_manager_user}" ] || [ -z "${subscription_manager_pass}" ]; then
        echo -e "... $USAGE"
        exit 1
    fi
fi

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
    rhel-7-server-rhceph-3-tools-rpms
)

packages=(
    cephmetrics-ansible
)

del_packages=(
    collectd-ipmi,collectd-ping
)

function join { local IFS="$1"; shift; echo "$*"; }

echo "## Updating the overcloud image"
cd ~/pilot
director_ip=`grep 'network_gateway = ' undercloud.conf | awk -F" = " '{print $2}'`
director_short=`hostname -s`
director_long=`hostname`
cd ~/pilot/images

echo ".....1 "

if [ ! -z "${satellite_hostname}" ]; then
    satelliteip=`grep "${satellite_hostname}" /etc/hosts | awk '{print $1}'`
    run_command "virt-customize \
        --memsize 2000 \
        --add overcloud-full.qcow2 \
        --run-command \"echo '${satelliteip}   ${satellite_hostname}' >> /etc/hosts;hostname tempname \" \
        --run-command \"rpm -Uvh http://${satellite_hostname}/pub/katello-ca-consumer-latest.noarch.rpm\" \
        --run-command \"subscription-manager register --org=${satellite_org} --activationkey=${satellite_key}\" \
        --run-command \"subscription-manager repos --disable='*' ${repos[*]/#/--enable=}\" \
        --install $(join \",\" ${packages[*]}) \
        --uninstall $(join \",\" ${del_packages[*]}) \
        --sm-remove \
        --sm-unregister \
        --selinux-relabel -v"
else
   run_command "virt-customize -a overcloud-full.qcow2 --run-command \"echo '${director_ip} ${director_short} ${director_long}' >> /etc/hosts\""

    run_command "virt-customize \
        --memsize 2000 \
        --add overcloud-full.qcow2 \
        --sm-credentials "${subscription_manager_user}:password:${subscription_manager_pass}" \
        --sm-register \
        --sm-attach \"pool:${subscription_manager_poolid}\" \
        --run-command \"subscription-manager repos --disable='*' ${repos[*]/#/--enable=}\" \
        --install $(join \",\" ${packages[*]}) \
        --uninstall $(join \",\" ${del_packages[*]}) \
        --sm-remove \
        --sm-unregister \
        --selinux-relabel"
fi

run_command "virt-customize \
    --add overcloud-full.qcow2"

echo "## Done updating the overcloud image"
