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
subscription_manager_poolid="$3"

if [ "$#" -lt 2 ]; then
  echo "Usage: $0  <subscription manager user> <subscription manager password> [<subscription pool id>]"
  exit 1
fi

echo "## install libguestfs-tools"
cd ~/pilot/images
sudo yum install libguestfs-tools -y

export LIBGUESTFS_BACKEND=direct

echo "## Register the image with subscription manager & enable repos"
virt-customize -a overcloud-full.qcow2 --run-command "\
    subscription-manager register --username=${subscription_manager_user} --password=${subscription_manager_pass}"

if [ -z "${subscription_manager_poolid}" ]; then
    subscription_manager_poolid=$(sudo subscription-manager list --available --matches='Red Hat Ceph Storage' --pool-only|tail -n1)
    echo "Red Hat Ceph Storage pool: ${subscription_manager_poolid}"
fi

if [ -z "${subscription_manager_poolid}" ]; then
    echo "subscription_manager_poolid is empty."
    exit 1
fi

virt-customize -a overcloud-full.qcow2 \
    --run-command "subscription-manager attach --pool=${subscription_manager_poolid}" \
    --run-command "\
        subscription-manager repos '--disable=*' --enable=rhel-7-server-rpms \
            --enable=rhel-7-server-rhceph-1.3-calamari-rpms --enable=rhel-7-server-rhceph-1.3-installer-rpms \
            --enable=rhel-7-server-rhceph-1.3-mon-rpms --enable=rhel-7-server-rhceph-1.3-osd-rpms \
            --enable=rhel-7-server-rhceph-1.3-tools-rpms"

echo "## Add required packages"
virt-customize -a overcloud-full.qcow2 --upload ../patch_rpms/python-novaclient-3.3.2-1.el7ost.noarch.rpm:/tmp/python-novaclient-3.3.2-1.el7ost.noarch.rpm &> ~/pilot/customize_image.log
virt-customize -a overcloud-full.qcow2 --run-command 'rpm -Uvh /tmp/python-novaclient-3.3.2-1.el7ost.noarch.rpm' --selinux-relabel &>> ~/pilot/customize_image.log
virt-customize -v -x -m 2000 -a overcloud-full.qcow2 --install ceph-radosgw,diamond,salt-minion,ceph-selinux --selinux-relabel &>> ~/pilot/customize_image.log

echo "## Unregister from subscription manager"
virt-customize -a overcloud-full.qcow2 --run-command 'subscription-manager remove --all' --run-command 'subscription-manager unregister'

# upload the image to the overcloud
openstack overcloud image upload --update-existing --image-path $HOME/pilot/images


echo "## Done updating the overcloud image"

