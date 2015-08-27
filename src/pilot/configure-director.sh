#!/bin/bash

dns_ip="$1"
if [ -z "${dns_ip}" ];
then
  echo "Usage: configure-director.sh <dns_ip>"
  exit 1
fi

controller_flavor_name="controller"
compute_flavor_name="compute"
storage_flavor_name="storage"
subnet_name="ctlplane"

# Create the requested flavor if it does not exist.
# Set the properties of the flavor regardless.
create_flavor()
{
  flavor_name="$1"
  echo "## Creating flavor: ${flavor_name}"

  flavor_uuid=$(openstack flavor list | grep "${flavor_name}" | awk '{print $2}')
  if [ -z "${flavor_uuid}" ];
  then
    openstack flavor create --id auto --ram 6144 --disk 40 --vcpus 4 "${flavor_name}"
  else
    echo "Warning: Flavor ${flavor_name} already exists.  Skipping creation."
  fi
  openstack flavor set --property "cpu_arch"="x86_64" --property "capabilities:boot_option"="local" --property "capabilities:profile"="${flavor_name}" "${flavor_name}"
}


cd ~
source stackrc

echo
echo "## Extracting images..."
if [ ! -d pilot/images ];
then
  echo "Error: A directory named $(pwd)/pilot/images must exist and contain the cloud images."
  exit 1
fi

for image in pilot/images/*.tar; do tar xvf $image; done

echo
echo
echo "## Uploading images..."
glance image-list | grep -q overcloud-full
if [ "$?" -ne 0 ];
then
  openstack overcloud image upload
else
  echo "Warning: Images have already been uploaded.  Skipping upload."
fi

echo
echo
echo "## Creating flavors..."
create_flavor $controller_flavor_name
create_flavor $compute_flavor_name
create_flavor $storage_flavor_name

echo
echo
echo "## Setting DNS in Neutron ${subnet_name} subnet..."
subnet_uuid=$(neutron net-list | grep "${subnet_name}" | awk '{print $6}')
neutron subnet-update "${subnet_uuid}" --dns-nameserver "${dns_ip}"

echo
echo
echo "## Setting up ahc-tools..."
sudo bash -c "sed 's/\[discoverd/\[ironic/' /etc/ironic-discoverd/discoverd.conf > /etc/ahc-tools/ahc-tools.conf"
sudo chmod 0600 /etc/ahc-tools/ahc-tools.conf
sudo cp pilot/ahc-tools/* /etc/ahc-tools/edeploy
echo
echo "## Configuration complete!"
