#!/bin/bash

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

exec > >(tee $HOME/pilot/install-director.log)
exec 2>&1

USAGE="\nUsing RedHat CDN:$0 --dns <dns_ip> --sm_user <subscription_manager_user> --sm_pwd <subscription_manager_pass> [--sm_pool <subcription_manager_poolid>] [--proxy <proxy> --nodes_pwd <overcloud_nodes_password>] \nUsing Satellite:$0 --dns <dns_ip> --satellite_hostname <satellite_host_name> --satellite_org <satellite_organization> --satellite_key <satellite_activation_key> [--containers_prefix <containers_satellite_prefix>] [--proxy <proxy> --nodes_pwd <overcloud_nodes_password>]"


TEMP=`getopt -o h --long dns:,sm_user:,sm_pwd:,sm_pool:,proxy:,nodes_pwd:,satellite_hostname:,satellite_org:,satellite_key:,containers_prefix: -n 'install-director.sh' -- "$@"`
eval set -- "$TEMP"


# extract options and their arguments into variables.
while true ; do
    case "$1" in
        -h|help)
            echo -e "$USAGE "
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
        --satellite_hostname)
                satellite_hostname=$2; shift 2;;
        --satellite_org)
                satellite_org=$2; shift 2;;
        --satellite_key)
                satellite_key=$2; shift 2;;
        --containers_prefix)
                containers_prefix=$2; shift 2;;
        --proxy)
                proxy=$2; shift 2 ;;
        --nodes_pwd)
                overcloud_nodes_pwd=$2; shift 2 ;;
        --) shift ; break ;;
        *) echo -e "$USAGE" ; exit 1 ;;
    esac
done


if [ ! -z "${satellite_hostname}" ]; then
   
    if [ -z "${dns_ip}" ] || [ -z "${satellite_hostname}" ] || [ -z "${satellite_org}" ] || [ -z ${satellite_key} ] ; then
        echo -e "$USAGE"
        exit 1
    fi

elif [ ! -z "${subscription_manager_user}" ];then

    if [ -z "${dns_ip}" ] || [ -z "${subscription_manager_user}" ] || [ -z "${subscription_manager_pass}" ]; then
        echo -e "$USAGE"
        exit 1
    fi
else
    echo -e "$USAGE"
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

apply_patch(){
  cmd=$*

  echo "Executing: $cmd"

  $cmd
  if [ $? -ne 0 ]; then
    echo "patch failed"
    exit 1
  fi
}

run_command(){
  cmd="$1"

  echo "Executing: $cmd"

  eval $cmd
  if [ $? -ne 0 ]; then
    echo "$cmd execution failed"
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
# Clean the nodes disks befor redeploying
#sed -i "s/clean_nodes = false/clean_nodes = true/" $HOME/pilot/undercloud.conf
cp $HOME/pilot/undercloud.conf $HOME
echo "## Done."

echo
echo "## Installing Director"
run_command "sudo yum -y install python-tripleoclient"
run_command "sudo yum install -y ceph-ansible"
run_command "openstack undercloud install"
echo "## Install Tempest plugin dependencies"
run_command "sudo yum -y install openstack-tempest"
run_command "sudo yum install -y python-neutron-tests-tempest python-cinder-tests-tempest python-telemetry-tests-tempest python-keystone-tests-tempest python-horizon-tests-tempest python2-octavia-tests-tempest python2-manila-tests-tempest python2-barbican-tests-tempest"
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
  sudo yum install rhosp-director-images rhosp-director-images-ipa octavia-amphora-image -y

  # It's not uncommon to get connection reset errors when installing this 1.2G
  # RPM.  Keep retrying to complete the download
  echo "Downloading and installing rhosp-director-image"
  while :
  do
    yum_out=$(sudo yum install rhosp-director-images rhosp-director-images-ipa -y 2>&1)
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

for i in /usr/share/rhosp-director-images/overcloud-full-latest-13.0.tar /usr/share/rhosp-director-images/ironic-python-agent-latest-13.0.tar;
do
  tar -xvf $i;
done
echo "## Done."

echo 
echo "## Customizing the overcloud image & uploading images"
if [ ! -z "${satellite_hostname}" ]; then
    run_command "~/pilot/customize_image.sh --satellite_hostname ${satellite_hostname} \
                --satellite_org ${satellite_org} \
                --satellite_key ${satellite_key} \
                --proxy ${proxy}"
                  
elif [ ! -z "${subscription_manager_user}" ];then
    run_command "~/pilot/customize_image.sh --sm_user ${subscription_manager_user} \
                --sm_pwd ${subscription_manager_pass} \
                --sm_pool ${subcription_manager_poolid} --proxy ${proxy}"
fi

echo
if [ -n "${overcloud_nodes_pwd}" ]; then
    echo "# Setting overcloud nodes password"
    run_command "sudo yum install libguestfs-tools -y"
    run_command "virt-customize -a overcloud-full.qcow2 --root-password password:${overcloud_nodes_pwd}"
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
subnet_uuid=$(openstack network list | grep "${subnet_name}" | awk '{print $6}')
openstack subnet set "${subnet_uuid}" --dns-nameserver "${dns_ip}"
echo "## Done."

# This patch fixes an issue in tripleo-heat-templates
echo
echo "### Patching tripleo-heat-templates"
sudo sed -i 's/$(get_python)/python/' /usr/share/openstack-tripleo-heat-templates/puppet/extraconfig/pre_deploy/per_node.yaml
echo "## Done."

echo
echo "## Copying heat templates..."
cp -r /usr/share/openstack-tripleo-heat-templates $HOME/pilot/templates/overcloud
cp $HOME/pilot/templates/roles_data.yaml $HOME/pilot/templates/overcloud/roles_data.yaml
cp $HOME/pilot/templates/network-isolation.yaml $HOME/pilot/templates/overcloud/environments/network-isolation.yaml
echo "## Done."

echo
echo "## Updating .bash_profile..."
echo "source ~/stackrc" >> ~/.bash_profile
echo "## Done."

# This hacks in a patch to validate and retrieve raid and boss controller and physical disk status.
echo
echo "## Patching Ironic iDRAC driver raid.py..."
apply_patch "sudo patch -b -s /usr/lib/python2.7/site-packages/dracclient/resources/raid.py ${HOME}/pilot/dracclient_raid.patch"
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/raid.pyc
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/raid.pyo

# This hacks in a patch to out-of-band inspection to set boot_mode on the node
# being inspected.
echo
echo "## Patching Ironic iDRAC driver inspect.py.."
apply_patch "sudo patch -b -s /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/inspect.py ${HOME}/pilot/inspect.patch"
sudo rm -f /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/inspect.pyc
sudo rm -f /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/inspect.pyo

# This hacks in a patch to create a virtual disk using realtime mode.
# Note that this code must be here because we use this code prior to deploying
# the director.
echo
echo "## Patching Ironic iDRAC driver raid.py..."
apply_patch "sudo patch -b -s /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/raid.py ${HOME}/pilot/raid.patch"
sudo rm -f /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/raid.pyc
sudo rm -f /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/raid.pyo
echo "## Done."

# This hacks in a patch to filter out all non-printable characters during WSMAN
# enumeration.
# Note that this code must be here because we use this code prior to deploying
# the director.
echo
echo "## Patching Ironic iDRAC driver wsman.py..."
apply_patch "sudo patch -b -s /usr/lib/python2.7/site-packages/dracclient/wsman.py ${HOME}/pilot/wsman.patch"
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/wsman.pyc
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/wsman.pyo
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

# This patches an issue where the  Ironic api service returns http 500 errors
# https://bugzilla.redhat.com/show_bug.cgi?id=1613995
echo
echo "## Patching 10-ironic_wsgi.conf"
apply_patch "sudo patch -b -s /etc/httpd/conf.d/10-ironic_wsgi.conf ${HOME}/pilot/wsgi.patch"
echo "## Done"

echo
echo "## Restarting httpd"
sudo systemctl restart httpd
echo "## Done"

echo
echo "## Restarting openstack-ironic-conductor.service..."
sudo systemctl restart openstack-ironic-conductor.service
echo "## Done."

# If deployment is unlocked, generate the overcloud container list from the latest.
if [ -e $HOME/overcloud_images.yaml ];
then
    echo "using locked containers versions"
else
    echo "using latest available containers versions"
    touch $HOME//overcloud_images.yaml
    
    if [ ! -z "${containers_prefix}" ]; then

       echo "openstack overcloud container image prepare   --namespace=${satellite_hostname}:5000\
        --prefix=${containers_prefix}   \
        -e /usr/share/openstack-tripleo-heat-templates/environments/ceph-ansible/ceph-ansible.yaml \
        -e /usr/share/openstack-tripleo-heat-templates/environments/services-docker/ironic.yaml \
        -e /usr/share/openstack-tripleo-heat-templates/environments/services/barbican.yaml \
        -e /usr/share/openstack-tripleo-heat-templates/environments/services-docker/octavia.yaml \
        --tag-from-label {version}-{release}   \
        --set ceph_namespace=${satellite_hostname}:5000 \
        --set ceph_image=${containers_prefix}rhceph-3-rhel7 \
        --output-env-file=$HOME/overcloud_images.yaml"

        openstack overcloud container image prepare   --namespace=${satellite_hostname}:5000\
        --prefix=${containers_prefix}   \
        -e /usr/share/openstack-tripleo-heat-templates/environments/ceph-ansible/ceph-ansible.yaml \
        -e /usr/share/openstack-tripleo-heat-templates/environments/services-docker/ironic.yaml \
        -e /usr/share/openstack-tripleo-heat-templates/environments/services/barbican.yaml \
        -e /usr/share/openstack-tripleo-heat-templates/environments/services-docker/octavia.yaml \
        --tag-from-label {version}-{release}   \
        --set ceph_namespace=${satellite_hostname}:5000 \
        --set ceph_image=${containers_prefix}rhceph-3-rhel7 \
        --output-env-file=$HOME/overcloud_images.yaml
     
    else
        openstack overcloud container image prepare --output-env-file $HOME/overcloud_images.yaml \
        --namespace=registry.access.redhat.com/rhosp13 \
        -e /usr/share/openstack-tripleo-heat-templates/environments/ceph-ansible/ceph-ansible.yaml \
        -e /usr/share/openstack-tripleo-heat-templates/environments/services-docker/ironic.yaml \
        -e /usr/share/openstack-tripleo-heat-templates/environments/services/barbican.yaml \
        -e /usr/share/openstack-tripleo-heat-templates/environments/services-docker/octavia.yaml \
        --set ceph_namespace=registry.access.redhat.com/rhceph \
        --set ceph_image=rhceph-3-rhel7 \
        --tag-from-label {version}-{release}
    fi
fi

sudo yum install -y os-cloud-config
sudo yum install -y ceph-ansible


echo
echo "## Configuration complete!"
