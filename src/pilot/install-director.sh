#!/bin/bash

# Copyright (c) 2016-2020 Dell Inc. or its subsidiaries.
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

USAGE="\nUsing RedHat CDN:$0 --director_ip <director public ip> --dns <dns_ip> [--proxy <proxy> --nodes_pwd <overcloud_nodes_password>] \nUsing Satellite:$0 --dns <dns_ip> --satellite_hostname <satellite_host_name> --satellite_org <satellite_organization> --satellite_key <satellite_activation_key> [--containers_prefix <containers_satellite_prefix>] [--proxy <proxy> --nodes_pwd <overcloud_nodes_password>]"


TEMP=`getopt -o h --long director_ip:,dns:,proxy:,nodes_pwd:,satellite_hostname:,satellite_org:,satellite_key:,containers_prefix: -n 'install-director.sh' -- "$@"`
eval set -- "$TEMP"


# extract options and their arguments into variables.
while true ; do
    case "$1" in
        -h|help)
            echo -e "$USAGE "
            exit 1
            ;;
        --director_ip)
                director_public_ip=$2 ; shift 2 ;;
        --dns)
                dns_ip=$2 ; shift 2 ;;
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

    if [ -z "${satellite_hostname}" ] || [ -z "${dns_ip}" ] || [ -z "${satellite_org}" ] || [ -z ${satellite_key} ] ; then
        echo -e "$USAGE"
        exit 1
    fi

fi


flavors="control compute ceph-storage computehci"
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

run_on_container(){
  container_name="$1"
  command="$2"

  echo "Executing: ${command} on ${container_name} "

  cmd="sudo podman exec --user 0 -ti ${container_name} ${command}"
  $cmd

  if [ $? -ne 0 ]; then
    echo "command failed"
    exit 1
  fi
}

upload_file_to_container(){
  container_name="$1"
  origin_file="$2"
  destination_file="$3"
  echo "uploading: ${origin_file} to ${destination_file} on ${container_name} "

  cmd="sudo podman cp ${origin_file} ${container_name}:${destination_file}"
  $cmd
  if [ $? -ne 0 ]; then
    echo "upload failed"
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
cp $HOME/pilot/containers-prepare-parameter.yaml $HOME
echo "## Done."

echo
echo "## Installing Director"
run_command "sudo dnf install -y python3-tripleoclient"
run_command "sudo dnf install -y ceph-ansible"
run_command "openstack undercloud install"
echo "## Install Tempest plugin dependencies"
run_command "sudo dnf install -y openstack-tempest"
run_command "sudo dnf install -y python3-neutron-tests-tempest python3-cinder-tests-tempest python3-telemetry-tests-tempest python3-keystone-tests-tempest python3-horizon-tests-tempest python3-octavia-tests-tempest python3-manila-tests-tempest python3-barbican-tests-tempest"
run_command "sudo dnf install -y gcc"
run_command "sudo dnf install -y openstack-ironic-api openstack-ironic-conductor python3-ironicclient"
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
  sudo dnf install -y rhosp-director-images rhosp-director-images-ipa octavia-amphora-image

  # It's not uncommon to get connection reset errors when installing this 1.2G
  # RPM.  Keep retrying to complete the download
  echo "Downloading and installing rhosp-director-image"
  while :
  do
    dnf_out=$(sudo dnf install -y rhosp-director-images rhosp-director-images-ipa 2>&1)
    dnf_rc=$?
    echo $dnf_out
    if [ $dnf_rc -eq 1 ]
    then
        if [[ $dnf_out == *"TCP connection reset by peer"* ]];
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

for i in /usr/share/rhosp-director-images/overcloud-full-latest-16.1.tar /usr/share/rhosp-director-images/ironic-python-agent-latest-16.1.tar;
do
  tar -xvf $i;
done
echo "## Done."

echo
echo "## Customizing the overcloud image & uploading images"

if [ ! -z "${satellite_hostname}" ]; then
    run_command "~/pilot/customize_image.sh --director_ip ${director_public_ip} \
                --satellite_hostname ${satellite_hostname} \
                --proxy ${proxy}"

elif [ ! -z "${proxy}" ]; then
    run_command "~/pilot/customize_image.sh --director_ip ${director_public_ip} \
                --proxy ${proxy}"
fi

echo
if [ -n "${overcloud_nodes_pwd}" ]; then
    echo "# Setting overcloud nodes password"
    run_command "sudo dnf install -y libguestfs-tools"
    run_command "sudo service libvirtd start"
    run_command "export LIBGUESTFS_BACKEND=direct"
    run_command "virt-customize -a overcloud-full.qcow2 --root-password password:${overcloud_nodes_pwd} --selinux-relabel"
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
sudo sed -i 's/$(get_python)/python3/' /usr/share/openstack-tripleo-heat-templates/puppet/extraconfig/pre_deploy/per_node.yaml
echo "## Done."

# Patch a fix for https://bugzilla.redhat.com/show_bug.cgi?id=1846020
echo "### Patching tripleo-heat-templates part II"
apply_patch "sudo patch -b -s /usr/share/openstack-tripleo-heat-templates/deployment/swift/swift-proxy-container-puppet.yaml ${HOME}/pilot/swift-proxy-container.patch"
apply_patch "sudo patch -b -s /usr/share/openstack-tripleo-heat-templates/deployment/nova/nova-scheduler-container-puppet.yaml ${HOME}/pilot/nova-scheduler-container.patch"
apply_patch "sudo patch -b -s /usr/share/openstack-tripleo-heat-templates/deployment/database/redis-container-puppet.yaml ${HOME}/pilot/redis-container.patch"
echo "## Done"

echo
echo "## Copying heat templates..."
cp -r /usr/share/openstack-tripleo-heat-templates $HOME/pilot/templates/overcloud
# TODO:dpaterson, why do we copy roles_data to ~/pilot/templates/overcloud/ ?
cp $HOME/pilot/templates/roles_data.yaml $HOME/pilot/templates/overcloud/roles_data.yaml
cp $HOME/pilot/templates/network-isolation.yaml $HOME/pilot/templates/overcloud/environments/network-isolation.yaml
echo "## Done."

echo
echo "## Updating .bash_profile..."
echo "source ~/stackrc" >> ~/.bash_profile
echo "## Done."

# Install patch on all containers to be patched
for container in "ironic_pxe_http" "ironic_pxe_tftp" "ironic_conductor" "ironic_api";
  do
    run_on_container  "${container}" "dnf install -y patch"
  done

# Update ironic patches
for container in "ironic_pxe_http" "ironic_pxe_tftp" "ironic_conductor" "ironic_api" ;
  do
    # This hacks in a patch to make conductor wait while completion of configuration job
    echo
    echo "## Patching Ironic iDRAC driver job.py on ${container}..."
    upload_file_to_container "${container}" "${HOME}/pilot/ironic_job.patch" "/tmp/ironic_job.patch"
    run_on_container "${container}" "patch -b -s /usr/lib/python3.6/site-packages/ironic/drivers/modules/drac/job.py /tmp/ironic_job.patch"
    run_on_container "${container}" "rm -f /usr/lib/python3.6/site-packages/ironic/drivers/modules/drac/job.pyc"
    run_on_container "${container}" "rm -f /usr/lib/python3.6/site-packages/ironic/drivers/modules/drac/job.pyo"
    echo "## Done"

    # This hacks in a patch to create a virtual disk using realtime mode.
    # Note that this code must be here because we use this code prior to deploying
    # the director.
    echo
    echo "## Patching Ironic iDRAC driver raid.py..."
    upload_file_to_container "${container}" "${HOME}/pilot/raid.patch" "/tmp/raid.patch"
    run_on_container "${container}" "patch -b -s /usr/lib/python3.6/site-packages/ironic/drivers/modules/drac/raid.py /tmp/raid.patch"
    run_on_container "${container}" "rm -f /usr/lib/python3.6/site-packages/ironic/drivers/modules/drac/raid.pyc"
    run_on_container "${container}" "rm -f /usr/lib/python3.6/site-packages/ironic/drivers/modules/drac/raid.pyo"
    echo "## Done"

    # This hacks in a patch to define maximum number of retries for the conductor
    # to wait during any configuration job completion.
    echo
    echo "## Patching Ironic iDRAC driver drac.py on ${container} ..."
    upload_file_to_container "${container}" "${HOME}/pilot/drac.patch" "/tmp/drac.patch"
    run_on_container "${container}" "patch -b -s /usr/lib/python3.6/site-packages/ironic/conf/drac.py /tmp/drac.patch"
    run_on_container "${container}" "rm -f /usr/lib/python2.7/site-packages/ironic/conf/drac.pyc"
    run_on_container "${container}" "rm -f /usr/lib/python2.7/site-packages/ironic/conf/drac.pyo"
    echo "## Done"
  done

# Update Drac patches
for container in "ironic_pxe_tftp"  "ironic_conductor" "ironic_api" ;
  do

    # This hacks in a patch to handle various types of settings.
    echo
    echo "## Patching Ironic iDRAC driver utils.py on ${container}.."
    upload_file_to_container "${container}" "${HOME}/pilot/utils.patch" "/tmp/utils.patch"
    run_on_container "${container}" "patch -b -s /usr/lib/python3.6/site-packages/dracclient/utils.py /tmp/utils.patch"
    run_on_container "${container}" "rm -f /usr/lib/python3.6/site-packages/dracclient/utils.pyc"
    run_on_container "${container}" "rm -f /usr/lib/python3.6/site-packages/dracclient/utils.pyo"
    echo "## Done"

    # This hacks in a patch to filter out all non-printable characters during WSMAN
    # enumeration.
    # Note that this code must be here because we use this code prior to deploying
    # the director.
    echo
    echo "## Patching Ironic iDRAC driver wsman.py on ${container}..."
    upload_file_to_container "${container}" "${HOME}/pilot/wsman.patch" "/tmp/wsman.patch"
    run_on_container "${container}" "patch -b -s /usr/lib/python3.6/site-packages/dracclient/wsman.py /tmp/wsman.patch"
    run_on_container "${container}" "rm -f /usr/lib/python3.6/site-packages/dracclient/wsman.pyc"
    run_on_container "${container}" "rm -f /usr/lib/python3.6/site-packages/dracclient/wsman.pyo"
    echo "## Done"

  done

# This patches workarounds for two issues into ironic.conf.
# 1. node_locked_retry_attempts is increased to work around an issue where
#    lock contention on the nodes in ironic can occur during RAID cleaning.
# 2. sync_power_state_interval is increased to work around an issue where
#    servers go into maintenance mode in ironic if polled for power state too
#    aggressively.
# echo
# echo "## Patching ironic.conf..."
# apply_patch "sudo patch -b -s /var/lib/config-data/puppet-generated//ironic/etc/ironic/ironic.conf ${HOME}/pilot/ironic.patch"
# echo "## Done."

# This patches an issue where the  Ironic api service returns http 500 errors
# https://bugzilla.redhat.com/show_bug.cgi?id=1613995
# echo
# echo "## Patching 10-ironic_wsgi.conf"
# apply_patch "sudo patch -b -s /var/lib/config-data/puppet-generated/ironic_api/etc/httpd/conf.d/10-ironic_wsgi.conf ${HOME}/pilot/wsgi.patch"
# echo "## Done"

# Restart containers/services

for service in "tripleo_ironic_api.service" "tripleo_ironic_conductor.service" "tripleo_ironic_inspector.service" "tripleo_ironic_pxe_http.service" "tripleo_ironic_pxe_tftp.service" ;
  do
    echo "restarting ${service}"
    sudo systemctl stop ${service}
    sudo systemctl start ${service}
  done



echo
echo "## Restarting httpd"
sudo systemctl restart httpd
echo "## Done"


# Satellite , if using
if [ ! -z "${containers_prefix}" ]; then
    container_yaml=$HOME/containers-prepare-parameter.yaml
    sed -i "s/namespace:.*/namespace: ${satellite_hostname}:5000/" ${container_yaml}
    sed -i "s/rhceph-4-dashboard-rhel8/${containers_prefix}rhceph_rhceph-4-dashboard-rhel8/" ${container_yaml}
    sed -i "s/ose-prometheus-alertmanager/${containers_prefix}openshift4_ose-prometheus-alertmanager/" ${container_yaml}
    sed -i "s/rhceph-4-rhel8/${containers_prefix}rhceph_rhceph-4-rhel8/" ${container_yaml}
    sed -i "s/ose-prometheus-node-exporter/${containers_prefix}openshift4_ose-prometheus-node-exporter/" ${container_yaml}
    sed -i "s/ose-prometheus$/${containers_prefix}openshift4_ose-prometheus/" ${container_yaml}
    sed -i "s/openstack-/${containers_prefix}rhosp-rhel8_openstack-/" ${container_yaml}
    sed -i "s/tag_from_label:.*/tag_from_label: '16.1'/" ${container_yaml}
fi


# If deployment is unlocked, generate the overcloud container list from the latest.
#if [ -e $HOME/overcloud_images.yaml ];
#then
#    echo "using locked containers versions"
#
#    if [ ! -z "${containers_prefix}" ]; then
#        sed -i "s/registry.access.redhat.com\/rhosp15\/openstack-/${satellite_hostname}:5000\/${containers_prefix}/" $HOME/overcloud_images.yaml
#        sed -i "s/registry.access.redhat.com\/rhceph\//${satellite_hostname}:5000\/${containers_prefix}/" $HOME/overcloud_images.yaml
#
#    fi
#
#else
#    echo "using latest available containers versions"
#    touch $HOME//overcloud_images.yaml
#
#    if [ ! -z "${containers_prefix}" ]; then
#
#        openstack overcloud container image prepare   --namespace=${satellite_hostname}:5000\
#        --prefix=${containers_prefix}   \
#        -e /usr/share/openstack-tripleo-heat-templates/environments/ceph-ansible/ceph-ansible.yaml \
#        -e /usr/share/openstack-tripleo-heat-templates/environments/services-docker/ironic.yaml \
#        -e /usr/share/openstack-tripleo-heat-templates/environments/services/barbican.yaml \
#        -e /usr/share/openstack-tripleo-heat-templates/environments/services-docker/octavia.yaml \
#        --tag-from-label {version}-{release}   \
#        --set ceph_namespace=${satellite_hostname}:5000 \
#        --set ceph_image=${containers_prefix}rhceph-3-rhel7 \
#        --output-env-file=$HOME/overcloud_images.yaml
#
#    else
#        openstack overcloud container image prepare --output-env-file $HOME/overcloud_images.yaml \
#        --namespace=registry.access.redhat.com/rhosp15 \
#        -e /usr/share/openstack-tripleo-heat-templates/environments/ceph-ansible/ceph-ansible.yaml \
#        -e /usr/share/openstack-tripleo-heat-templates/environments/services-docker/ironic.yaml \
#        -e /usr/share/openstack-tripleo-heat-templates/environments/services/barbican.yaml \
#        -e /usr/share/openstack-tripleo-heat-templates/environments/services-docker/octavia.yaml \
#        --set ceph_namespace=registry.access.redhat.com/rhceph \
#        --set ceph_image=rhceph-3-rhel7 \
#        --tag-from-label {version}-{release}
#    fi
#fi


echo
echo "## Configuration complete!"
