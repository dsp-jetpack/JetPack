#!/bin/bash

exec > >(tee $HOME/pilot/install-director.log)
exec 2>&1

dns_ip="$1"
if [ -z "${dns_ip}" ];
then
  echo "Usage: install-director.sh <dns_ip>"
  exit 1
fi

flavors="controller compute storage"
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


cd

echo
echo "## Configuring paths..."
ESCAPED_HOME=${HOME//\//\\/}
sed -i "s/HOME/$ESCAPED_HOME/g" $HOME/pilot/templates/network-environment.yaml
sed -i "s/HOME/$ESCAPED_HOME/g" $HOME/pilot/undercloud.conf
cp $HOME/pilot/undercloud.conf $HOME
echo "## Done."

echo
echo "## Installing Director"
openstack undercloud install
echo "## Done."

source stackrc

echo
echo "## Extracting images..."
if [ ! -d $HOME/pilot/images ];
then
  echo "Error: A directory named $HOME/pilot/images must exist and contain the cloud images."
  exit 1
fi

cd $HOME/pilot/images
for image in ./*.tar; do tar xvf $image; done
echo "## Done."

echo
echo "## Uploading images..."
glance image-list | grep -q overcloud-full
if [ "$?" -ne 0 ];
then
  openstack overcloud image upload
else
  echo "Warning: Images have already been uploaded.  Skipping upload."
fi
echo "## Done."

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
echo "## Configuration complete!"
