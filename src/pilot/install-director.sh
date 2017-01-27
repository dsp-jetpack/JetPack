#!/bin/bash

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

exec > >(tee $HOME/pilot/install-director.log)
exec 2>&1

dns_ip="$1"
subscription_manager_user="$2"
subscription_manager_pass="$3"
subcription_manager_poolid="$4"
proxy="$5"

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <dns_ip> <subscription_manager_user> <subscription_manager_pass> [<subcription_manager_poolid>] [<proxy>]"
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
  sudo yum install rhosp-director-images rhosp-director-images-ipa -y
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
echo "## Done."

echo
echo "## Updating .bash_profile..."
echo "source ~/stackrc" >> ~/.bash_profile
echo "## Done."

# This hacks in a patch that has been merged to upstream already, but is not
# currently present in OSP10.  We will need to remove this after the fix
# appears in OSP10.  Note that this patch must be here because we use this
# code prior to deploying the director.
echo
echo "## Patching Ironic vendor passthru..."
OUT=$(sudo patch -b -s /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/vendor_passthru.py ~/pilot/vendor_passthru.patch)
sudo rm -f /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/vendor_passthru.pyc
sudo rm -f /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/vendor_passthru.pyo
sudo systemctl restart openstack-ironic-conductor.service
echo "## Done."

# This hacks in a patch to fix correct querying WSMAN Enumerations that have
# more than 100 entries.  We will need to remove this after the fix appears
# in OSP10.  Note that this patch must be here because we use this code prior
# to deploying the director.
echo
echo "## Patching Ironic iDRAC driver WSMAN library..."
OUT=$(sudo patch -b -s /usr/lib/python2.7/site-packages/dracclient/wsman.py ~/pilot/wsman.patch)
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/wsman.pyc
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/wsman.pyo
sudo systemctl restart openstack-ironic-conductor.service
echo "## Done."

# This hacks in a workaround to fix in-band introspection.  A fix has been
# made to NetworkManager upstream, but is not currently present in OSP10.
# We will need to remove this after the fix appears in OSP10.
echo
echo "## Patching Ironic in-band introspection..."
sudo sed -i 's/initrd=agent.ramdisk /initrd=agent.ramdisk net.ifnames=0 biosdevname=0 /' /httpboot/inspector.ipxe
echo "## Done."

network="ctlplane"
echo
echo "## Configuring neutron network ${network} as a cleaning network"
configure_cleaning_network $network
echo "## Done."

echo
echo "## Configuration complete!"
