#!/bin/bash

# Copyright (c) 2016-2021 Dell Inc. or its subsidiaries.
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

USAGE="\nUsing RedHat CDN:$0 --director_ip <director public ip> --dns <dns_ip> [--proxy <proxy> --nodes_pwd <overcloud_nodes_password>] \nUsing Satellite:$0 --dns <dns_ip> --satellite_hostname <satellite_host_name> --satellite_org <satellite_organization> --satellite_key <satellite_activation_key> [--containers_prefix <containers_satellite_prefix>] [--proxy <proxy> --nodes_pwd <overcloud_nodes_password>] [--enable_powerflex]" 


TEMP=`getopt -o h --long director_ip:,dns:,proxy:,nodes_pwd:,enable_powerflex,satellite_hostname:,satellite_org:,satellite_key:,containers_prefix: -n 'install-director.sh' -- "$@"`
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
        --enable_powerflex)
                enable_powerflex=1; shift 1;;
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


flavors="control compute ceph-storage computehci powerflex-storage"
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
sudo sed -i "s/HOME/$ESCAPED_HOME/g" $HOME/pilot/undercloud.conf
# Clean the nodes disks befor redeploying
sudo cp $HOME/pilot/undercloud.conf $HOME
sudo cp $HOME/pilot/containers-prepare-parameter.yaml $HOME
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

if [ -n "${overcloud_nodes_pwd}" ] || [ ${enable_powerflex} == 1 ]; then
    echo "# Overcloud customizatin required, Installing libguestfs-tools"
    run_command "sudo dnf install -y libguestfs-tools"
    run_command "sudo service libvirtd start"
    run_command "export LIBGUESTFS_BACKEND=direct"
fi
    
#if [ -n "${overcloud_nodes_pwd}" ]; then
#    echo "# Setting overcloud nodes password"
#    run_command "virt-customize -a overcloud-full.qcow2 --root-password password:${overcloud_nodes_pwd} --selinux-relabel"
#fi

#if [ ${enable_powerflex} == 1 ]; then
#    echo "# PowerFlex backend enabled, injecting rpms"
#    run_command "virt-customize -a overcloud-full.qcow2 --mkdir /opt/dellemc/powerflex"
#    run_command "virt-customize -a overcloud-full.qcow2 --copy-in $HOME/pilot/powerflex/rpms:/opt/dellemc/powerflex/ --selinux-relabel"
#    echo "# Cloning Dell EMC TripleO PowerFlex repository"
#    run_command "sudo dnf install -y ansible-tripleo-powerflex"
#fi

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

# This hacks in a patch for XE2420 where if GroupID returned by wsman is null
# config_idrac.py fails.  This patch allows GroupID to be returned as null and the deployment to continue
echo "### Patching idrac_card.py"
apply_patch "sudo patch -b -s /usr/lib/python3.6/site-packages/dracclient/resources/idrac_card.py ${HOME}/pilot/idrac_card_groupid.patch"
echo "## Done"

if [ ${enable_powerflex} == 1 ]; then
    # This patch fixes an issue when updating a stack on which PowerFlex is already installed
    # Waiting for the mod we did into the tripleo-powerflex avaiable into the RDO package
    echo
    echo "### Patching powerflex-ansible site.yaml"
    apply_patch "sudo patch -b -s /usr/share/powerflex-ansible/site.yaml ${HOME}/pilot/powerflex_ansible_site.patch"
    echo "### Patching powerflex-ansible roles/powerflex-facts/task/facts.yaml"
    apply_patch "sudo patch -b -s /usr/share/powerflex-ansible/roles/powerflex-facts/tasks/facts.yaml ${HOME}/pilot/powerflex_ansible_facts.patch"
    echo "### Done."
fi

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



echo
echo "## Configuration complete!"
