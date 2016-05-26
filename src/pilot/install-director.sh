#!/bin/bash

# (c) 2016 Dell
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

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <dns_ip> <subscription_manager_user> <subscription_manager_pass> <subcription_manager_poolid>"
  exit 1
fi

flavors="control compute ceph-storage"
subnet_name="ctlplane"

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

echo
echo "## Installing probe-idrac utility..."
~/pilot/install_probe_idrac.sh
echo "## Done."

cd

echo
echo "## Configuring paths..."
ESCAPED_HOME=${HOME//\//\\/}
sed -i "s/HOME/$ESCAPED_HOME/g" $HOME/pilot/undercloud.conf
cp $HOME/pilot/undercloud.conf $HOME
echo "## Done."

echo "# Fetching the puppet-ironic with the iPXE fix"
sudo yum install -y openstack-puppet-modules instack-undercloud git
# NOTE(Gonéri): to remove as soon as the new openstack-puppet-modules is available
sudo rm -rf /usr/share/openstack-puppet/modules/ironic
sudo git clone https://github.com/openstack/puppet-ironic -b stable/liberty /usr/share/openstack-puppet/modules/ironic

sudo sed -i "s,\('pxe/http_root':                value => '/httpboot';\),\1\n  'pxe/ipxe_timeout':             value => '60';," /usr/share/instack-undercloud/puppet-stack-config/puppet-stack-config.pp
sudo bash -c "echo 'ironic::inspector::ipxe_timeout: 60' >> /usr/share/instack-undercloud/puppet-stack-config/puppet-stack-config.yaml.template"

echo
echo "## Installing Director"
openstack undercloud install
echo "## Done."

source stackrc

echo
if [ ! -d $HOME/pilot/images ];
then
  echo "## Downloading images..."
  sudo yum install rhosp-director-images -y
  mkdir $HOME/pilot/images
  ln -sf /usr/share/rhosp-director-images/overcloud-full-latest-8.0.tar $HOME/pilot/images/overcloud-full.tar
  ln -sf /usr/share/rhosp-director-images/ironic-python-agent-latest-8.0.tar $HOME/pilot/images/ironic-python-agent.tar
fi

echo "## Extracting images..."
cd $HOME/pilot/images
for image in ./*.tar; do tar xvf $image; done
echo "## Done."

echo
echo "## Customizing the overcloud image & upload images"
~/pilot/customize_image.sh $subscription_manager_user $subscription_manager_pass $subcription_manager_poolid
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

echo
echo "## Apply pxe freeze patches"

LOCKFILE=/etc/yum/pluginconf.d/versionlock.list
if [ $LOCKFILE ]
then
    sudo sed -i 's/openstack-ironic-conductor-.*/openstack-ironic-conductor-4.2.3-2.el7ost.*/' $LOCKFILE
    sudo sed -i 's/openstack-ironic-api-.*/openstack-ironic-api-4.2.3-2.el7ost.*/' $LOCKFILE
    sudo sed -i 's/openstack-ironic-common-.*/openstack-ironic-common-4.2.3-2.el7ost.*/' $LOCKFILE
fi

cd $HOME/pilot/ipxe
sudo yum install -y openstack-ironic-api-4.2.3-2.el7ost.noarch.rpm openstack-ironic-common-4.2.3-2.el7ost.noarch.rpm openstack-ironic-conductor-4.2.3-2.el7ost.noarch.rpm
sudo sed -i '/\[pxe\]/a \\nipxe_timeout = 60' /etc/ironic/ironic.conf
sudo service openstack-ironic-api restart
sudo service openstack-ironic-conductor restart

echo
echo "## Configuration complete!"
