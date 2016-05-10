#!/usr/bin/env bash

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

subscription_manager_user="$1"
subscription_manager_pass="$2"
subcription_manager_poolid="$3"

declare -a install_packages=("ceph-radosgw-0.94.5-9.el7cp.x86_64" "diamond-3.4.67-4.el7cp.noarch" "salt-minion-2014.1.5-3.el7cp.noarch --selinux-relabel")
declare -a enable_repos=("rhel-7-server-rhceph-1.3-mon-rpms" "rhel-7-server-rhceph-1.3-tools-rpms")

if [ "$#" -ne 3 ]; then
  echo "Usage: $0  <subscription manager user> <subscription manager password> <subscription pool id>"
  exit 1
fi

echo "## install libguestfs-tools"
cd ~/pilot/images
sudo yum install libguestfs-tools -y

export LIBGUESTFS_BACKEND=direct

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

# upload the image to the overcloud
openstack overcloud image upload --update-existing --image-path $HOME/pilot/images


echo "## Done updating the overcloud image"

