#!/usr/bin/env bash

subscription_manager_user="$1"
subscription_manager_pass="$2"
subcription_manager_poolid="$3"

declare -a install_packages=("ceph-radosgw" "diamond" "salt-minion --selinux-relabel")
declare -a enable_repos=("rhel-7-server-rhceph-1.3-mon-rpms" "rhel-7-server-rhceph-1.3-tools-rpms")

if [ "$#" -ne 3 ]; then
  echo "Usage: $0  <subscription manager user> <subscription manager password> <subscription pool id>"
  exit 1
fi

echo "## install libguestfs-tools"
cd ~/pilot/images
sudo yum install libguestfs-tools -y

echo "## Register the image with subscription manager & enable repos"
virt-customize -a overcloud-full.qcow2 --run-command "subscription-manager register --username=${subscription_manager_user} --password=${subscription_manager_pass}"
virt-customize -a overcloud-full.qcow2 --run-command "subscription-manager attach --pool=${subcription_manager_poolid}"

for repo in "${enable_repos[@]}"
do
        virt-customize -a overcloud-full.qcow2 --run-command "yum-config-manager --enable ${repo}"
done

echo "## Add required packages"
for package in "${install_packages[@]}"
do
        virt-customize -a overcloud-full.qcow2 --install ${package}
done

echo "## Unregister from subscription manager"
virt-customize -a overcloud-full.qcow2 --run-command 'subscription-manager remove --all'
virt-customize -a overcloud-full.qcow2 --run-command 'subscription-manager unregister'



# upload the updated image to the overcloud < no .. move all this in install director script before uploading images& let it upload
openstack overcloud image upload --update-existing --image-path $HOME/pilot/images



echo "## Done updating the overcloud image"

