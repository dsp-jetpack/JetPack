#!/bin/bash

dns_ip="$1"
if [ -z "${dns_ip}" ];
then
  echo "Usage: configure-director.sh <dns_ip>"
  exit 1
fi

flavor_name="baremetal"
subnet_name="ctlplane"

cd ~
source stackrc

echo
echo "## Extracting images..."
if [ ! -d images ];
then
  echo "Error: A directory named $(pwd)/images must exist and contain the cloud images."
  exit 1
fi

for image in images/*.tar; do tar xvf $image; done

echo
echo
echo "## Uploading images..."
openstack overcloud image upload

echo
echo
echo "## Creating flavors..."

flavor_uuid=$(openstack flavor list | grep "${flavor_name}" | awk '{print $2}')
if [ -z "${flavor_uuid}" ];
then
  openstack flavor create --id auto --ram 4096 --disk 40 --vcpus 1 "${flavor_name}"
else
  echo "Flavor ${flavor_name} already exists!"
fi
openstack flavor set --property "cpu_arch"="x86_64" --property "capabilities:boot_option"="local" "${flavor_name}"

echo
echo
echo "## Setting DNS in Neutron ${subnet_name} subnet..."
subnet_uuid=$(neutron net-list | grep "${subnet_name}" | awk '{print $6}')
neutron subnet-update "${subnet_uuid}" --dns-nameserver "${dns_ip}"
