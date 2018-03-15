#!/bin/bash

# Copyright (c) 2016-2018 Dell Inc. or its subsidiaries.
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

exec > >(tee $HOME/pilot/install-director.log)
exec 2>&1

USAGE="$0 --dns <dns_ip> --sm_user <subscription_manager_user> --sm_pwd <subscription_manager_pass> [-- sm_pool <subcription_manager_poolid>] [--proxy <proxy> --nodes_pwd <overcloud_nodes_password>]"



TEMP=`getopt -o h --long dns:,sm_user:,sm_pwd:,sm_pool:,proxy:,nodes_pwd: -n 'install-director.sh' -- "$@"`
eval set -- "$TEMP"

# extract options and their arguments into variables.
while true ; do
    case "$1" in
        -h|help)
            echo "$USAGE "
            exit 1
            ;;
        --dns)
            dns_ip=$2 ; shift 2 ;;
        --sm_user)
                subscription_manager_user=$2 ; shift 2 ;;
        --sm_pwd)
                subscription_manager_pass=$2 ; shift 2 ;;
        --sm_pool)
                subcription_manager_poolid=$2; shift 2 ;; 
        --proxy)
                proxy=$2; shift 2 ;;
        --nodes_pwd)
                overcloud_nodes_pwd=$2; shift 2 ;;
        --) shift ; break ;;
        *) echo "$USAGE" ; exit 1 ;;
    esac
done

if [ -z "${dns_ip}" ] || [ -z "${subscription_manager_user}" ] || [ -z "${subscription_manager_pass}" ]; then
    echo $USAGE
    exit 1
fi


flavors="control compute ceph-storage"
subnet_name="ctlplane"

# Configure a cleaning network so that the Bare Metal service, ironic, can use
# node cleaning.
configure_cleaning_network()
{
  network_name="$1"
  network_uuid=$(neutron net-list | grep "${network_name}" | awk '{print $2}')
  sudo sed -i.bak "s/^.*cleaning_network_uuid.*$/cleaning_network_uuid\ =\ $network_uuid/" /etc/ironic/ironic.conf
  sudo systemctl restart openstack-ironic-conductor.service
}

# Create the requested flavor if it does not exist.
# Set the properties of the flavor regardless.
create_flavor()
{
  flavor_name="$1"

  set_properties="true"
  if [ -n "$2" ];
  then
    set_properties="$2"
  fi

  echo "## Creating flavor: ${flavor_name}"

  flavor_uuid=$(openstack flavor list | grep "${flavor_name}" | awk '{print $2}')
  if [ -z "${flavor_uuid}" ];
  then
    openstack flavor create --id auto --ram 6144 --disk 40 --vcpus 4 "${flavor_name}"

    if [ "$set_properties" = "true" ];
    then
      echo "setting properties"
      openstack flavor set --property "cpu_arch"="x86_64" --property "capabilities:boot_option"="local" --property "capabilities:profile"="${flavor_name}" "${flavor_name}"
    fi
  else
    echo "Warning: Flavor ${flavor_name} already exists.  Skipping creation."
  fi
}

apply_patch(){
  cmd="$1"

  echo "Executing: $cmd"

  $cmd
  if [ $? -ne 0 ]; then
    echo "patch failed"
    exit 1
  fi
}

cd

if [ ! -z $proxy ];
then
  echo
  echo "## Configuring proxy"
  ip_addresses=$(ip addr | grep -Po 'inet \K[\d.]+')
  no_proxy_list=$(echo $ip_addresses | tr ' ' ',')
  export no_proxy=$no_proxy_list
  export http_proxy=$proxy
  export https_proxy=$proxy
  export -p 
  echo "## Done."
fi

echo
echo "## Configuring paths..."
ESCAPED_HOME=${HOME//\//\\/}
sed -i "s/HOME/$ESCAPED_HOME/g" $HOME/pilot/undercloud.conf
cp $HOME/pilot/undercloud.conf $HOME
echo "## Done."

echo
echo "## Installing Director"
sudo yum -y install python-tripleoclient
openstack undercloud install
echo "## Install Tempest plugin dependencies"
sudo yum -y install python-*-tests
echo "## Done."

echo
echo "## Installing probe-idrac utility..."
~/pilot/install_probe_idrac.sh
echo "## Done."

source $HOME/stackrc

echo
images_tar_path='.'
if [ ! -d $HOME/pilot/images ];
then
  sudo yum install rhosp-director-images-ipa -y

  # It's not uncommon to get connection reset errors when installing this 1.2G
  # RPM.  Keep retrying to complete the download
  echo "Downloading and installing rhosp-director-image"
  while :
  do
    yum_out=$(sudo yum install rhosp-director-images -y 2>&1)
    yum_rc=$?
    echo $yum_out
    if [ $yum_rc -eq 1 ]
    then
        if [[ $yum_out == *"TCP connection reset by peer"* ]];
        then
          echo "Got a TCP connection reset.  Retrying..."
          continue
        else
          echo "Failed to download and install rhosp-director-image"
          exit 1
        fi
    else
      echo "Successfully downloaded and installed rhosp-director-image"
      break
    fi
  done

  mkdir $HOME/pilot/images
  images_tar_path='/usr/share/rhosp-director-images'
fi
cd $HOME/pilot/images

for i in /usr/share/rhosp-director-images/overcloud-full-latest-10.0.tar /usr/share/rhosp-director-images/ironic-python-agent-latest-10.0.tar;
do
  tar -xvf $i;
done
echo "## Done."

echo 
echo "## Customizing the overcloud image & uploading images"
~/pilot/customize_image.sh $subscription_manager_user $subscription_manager_pass $subcription_manager_poolid $proxy
echo
if [ -n "${overcloud_nodes_pwd}" ]; then
    echo "# Setting overcloud nodes password"
    virt-customize -a overcloud-full.qcow2 --root-password password:$overcloud_nodes_pwd
    if [ $? -ne 0 ]; then
        echo "Customization of overcloud image FAILED!"
        echo "Overcloud image will not be uploaded, aborting installation"
        exit -1
    fi
fi

openstack overcloud image upload --update-existing --image-path $HOME/pilot/images
echo "## Done"



echo
echo "## Creating flavors..."
for flavor in $flavors;
do
  create_flavor $flavor
done
create_flavor baremetal false
echo "## Done."

echo
echo "## Setting DNS in Neutron ${subnet_name} subnet..."
subnet_uuid=$(neutron net-list | grep "${subnet_name}" | awk '{print $6}')
neutron subnet-update "${subnet_uuid}" --dns-nameserver "${dns_ip}"
echo "## Done."

echo
echo "## Copying heat templates..."
cp -r /usr/share/openstack-tripleo-heat-templates $HOME/pilot/templates/overcloud
cp -r $HOME/pilot/templates/dellnfv $HOME/pilot/templates/overcloud/puppet/services/dellnfv
cp $HOME/pilot/templates/roles_data.yaml $HOME/pilot/templates/overcloud/roles_data.yaml
cp $HOME/pilot/templates/network-isolation.yaml $HOME/pilot/templates/overcloud/environments/network-isolation.yaml
echo "## Done."

echo
echo "## Updating .bash_profile..."
echo "source ~/stackrc" >> ~/.bash_profile
echo "## Done."

# This hacks in a patch to work around a known issue where RAID configuration
# fails because the iDRAC is busy running an export to XML job and is not
# ready. Note that this patch must be here because we use this code prior to
# deploying the director.
echo
echo "## Patching Ironic iDRAC driver is_ready check..."
apply_patch "sudo patch -b -s /usr/lib/python2.7/site-packages/dracclient/client.py ${HOME}/pilot/client.patch"
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/client.pyc
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/client.pyo
echo "## Done."

echo
echo "## Patching Ironic iDRAC driver uris.py..."
apply_patch "sudo patch -b -s /usr/lib/python2.7/site-packages/dracclient/resources/uris.py ${HOME}/pilot/uris.patch"
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/uris.pyc
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/uris.pyo
echo "## Done."

# This hacks in a patch to work around a known issue where a RAID-10 virtual
# disk cannot be created from more than 16 backing physical disks.  This also
# patches in support for NVMe drives.  Note that this code must be here because
# we use this code prior to deploying the director.
echo
echo "## Patching Ironic iDRAC driver RAID library..."
apply_patch "sudo patch -b -s /usr/lib/python2.7/site-packages/dracclient/resources/raid.py ${HOME}/pilot/dracclient_raid.patch"
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/raid.pyc
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/raid.pyo
echo "## Done."

# This patches workarounds for two issues into ironic.conf.
# 1. node_locked_retry_attempts is increased to work around an issue where
#    lock contention on the nodes in ironic can occur during RAID cleaning.
# 2. sync_power_state_interval is increased to work around an issue where
#    servers go into maintenance mode in ironic if polled for power state too
#    aggressively.
echo
echo "## Patching ironic.conf..."
apply_patch "sudo patch -b -s /etc/ironic/ironic.conf ${HOME}/pilot/ironic.patch"
echo "## Done."

echo
echo "## Restarting openstack-ironic-conductor.service..."
sudo systemctl restart openstack-ironic-conductor.service
echo "## Done."

network="ctlplane"
echo
echo "## Configuring neutron network ${network} as a cleaning network"
configure_cleaning_network $network
echo "## Done."

echo
echo "## Configuration complete!"
