#!/bin/bash

# Copyright (c) 2015-2019 Dell Inc. or its subsidiaries.
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

#exit on failure
#set -e
#Variables


INI_FILE=sanity.ini

while getopts :s: option
do
    case "${option}"
    in
    s) INI_FILE=$OPTARG;;
    esac
done

get_value() {
    echo $(grep "$1=" $INI_FILE  | awk -F= '{print $2}')
}

get_value_lower() { 
    echo $(grep "$1=" $INI_FILE  | awk -F= '{print $2}'| tr '[:upper:]' '[:lower:]' )
}


FLOATING_IP_NETWORK=$(get_value floating_ip_network)
FLOATING_IP_NETWORK_START_IP=$(get_value floating_ip_network_start_ip)
FLOATING_IP_NETWORK_END=$(get_value floating_ip_network_end_ip)
FLOATING_IP_NETWORK_GATEWAY=$(get_value floating_ip_network_gateway)
FLOATING_IP_NETWORK_VLAN=$(get_value floating_ip_network_vlan)
OVS_DPDK_ENABLED=$(get_value_lower ovs_dpdk_enabled)
DVR_ENABLED=$(get_value_lower dvr_enabled)
SANITY_TENANT_NETWORK=$(get_value sanity_tenant_network)
SANITY_VLANTEST_NETWORK=$(get_value sanity_vlantest_network)
SANITY_USER_PASSWORD=$(get_value sanity_user_password)
SANITY_USER_EMAIL=$(get_value sanity_user_email)
SANITY_KEY_NAME=$(get_value sanity_key_name)
SANITY_NUMBER_INSTANCES=$(get_value sanity_number_instances)
VLAN_AWARE_SANITY=$(get_value_lower vlan_aware_sanity)
SANITY_IMAGE_URL=$(get_value image_url)
FLOATING_IP_NETWORK_NAME=$(get_value floating_ip_network_name)
FLOATING_IP_SUBNET_NAME=$(get_value floating_ip_subnet_name)
IMAGE_NAME=$(get_value image_name)
FLAVOR_NAME=$(get_value flavor_name)
BASE_SECURITY_GROUP_NAME=$(get_value base_security_group_name)
BASE_TENANT_NETWORK_NAME=$(get_value base_tenant_network_name)
BASE_TENANT_ROUTER_NAME=$(get_value base_tenant_router_name)
BASE_VLAN_NAME=$(get_value base_vlan_name)
BASE_NOVA_INSTANCE_NAME=$(get_value base_nova_instance_name)
BASE_VOLUME_NAME=$(get_value base_volume_name)
BASE_SHARE_NAME=$(get_value base_share_name)
BASE_PROJECT_NAME=$(get_value base_project_name)
BASE_USER_NAME=$(get_value base_user_name)
BASE_CONTAINER_NAME=$(get_value base_container_name)
SRIOV_ENABLED=$(get_value_lower sriov_enabled)
HPG_ENABLED=$(get_value_lower hugepages_enabled)
NUMA_ENABLED=$(get_value_lower numa_enabled)

IMAGE_FILE_NAME=$(basename $SANITY_IMAGE_URL)
SECURITY_GROUP_NAME="$BASE_SECURITY_GROUP_NAME"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o KbdInteractiveDevices=no"

#vlan specific environmental variables
PARENT_PORT1="tenant_pp1"
TRUNK_PORT1="tenant_trunk1"
VLAN_NETWORK_NAME="tenant_vlan_net"

shopt -s nullglob

LOG_FILE=./sanity_test.log
exec > >(tee -a ${LOG_FILE} )
exec 2> >(tee -a ${LOG_FILE} >&2)

# Logging levels
FATAL=0
ERROR=1
WARN=2
INFO=3
DEBUG=4

# Default logging level
LOG_LEVEL=$INFO

# Logging functions
log() { echo -e "$(date '+%F %T'): $@" >&2; }
fatal() { log "FATAL: $@" >&2; exit 1; }
error() { [[ $ERROR -le $LOG_LEVEL ]] && log "ERROR: $@"; }
warn() { [[ $WARN -le $LOG_LEVEL ]] && log "WARN: $@"; }
info() { [[ $INFO -le $LOG_LEVEL ]] && log "INFO: $@"; }
debug() { [[ $DEBUG -le $LOG_LEVEL ]] && log "DEBUG: $@"; }

######## Functions ############
set_admin_scope(){
  info "setting admin scope with: ~/${STACK_NAME}rc."
  source ~/${STACK_NAME}rc
  [ -n "$OS_TENANT_NAME" ] && export OS_PROJECT_NAME=$OS_TENANT_NAME
  info "### sourcing ~/${STACK_NAME}rc"
}

set_tenant_scope(){
  info "Setting tenant scope."
  export OS_USERNAME=$USER_NAME
  export OS_PASSWORD=$SANITY_USER_PASSWORD
  export OS_TENANT_NAME=$PROJECT_NAME
  export OS_PROJECT_NAME=$PROJECT_NAME
}

generate_sanity_rc(){
  info "Generating sanityrc file."
  cp ~/${STACK_NAME}rc ${SANITYRC}
  USERNAMEREPL=`grep OS_USERNAME ~/${STACK_NAME}rc`
  PASSWORDREPL=`grep OS_PASSWORD ~/${STACK_NAME}rc`
  PROJECTNAMEREPL=`grep OS_PROJECT_NAME ~/${STACK_NAME}rc`
  TENANTNAMEREPL=`grep OS_TENANT_NAME ~/${STACK_NAME}rc`
  sed -i "s/${USERNAMEREPL}/export OS_USERNAME=${USER_NAME}/g" ${SANITYRC}
  sed -i "s/${PASSWORDREPL}/export OS_PASSWORD=${SANITY_USER_PASSWORD}/g" ${SANITYRC}
  sed -i "s/${PROJECTNAMEREPL}/export OS_PROJECT_NAME=${PROJECT_NAME}/g" ${SANITYRC}
  grep OS_TENANT_NAME $SANITYRC >/dev/null 2>&1
  if [ $? -eq 0 ]
  then
    sed -i "s/${TENANTNAMEREPL}/export OS_TENANT_NAME=${PROJECT_NAME}/g" ${SANITYRC}
  else
    sed -i "\$ a export OS_TENANT_NAME=${PROJECT_NAME}" ${SANITYRC}
  fi
  sed -i "s/export OS_CLOUDNAME=.*/export OS_CLOUDNAME=${PROJECT_NAME}/g" ${SANITYRC}
}

init(){

  info "### Random init stuff "
  cd ~

  source ~/stackrc
  [ -n "$OS_TENANT_NAME" ] && export OS_PROJECT_NAME=$OS_TENANT_NAME

  # Collect the SSH keys from all of the overcloud nodes
  info "### Collecting SSH keys... ###"

  local update_ssh_config="${HOME}/pilot/update_ssh_config.py"
  [ -x "${update_ssh_config}" ] || \
      fatal "### '${update_ssh_config}' is required but missing!  Aborting sanity test"
  execute_command "${update_ssh_config}"

  # Get a list of the IPs of all the controller nodes for later use, as well as
  # the IP for a single controller
  CONTROLLERS=$(openstack server list -c Name -c Networks -f value | grep controller | awk '{print $2}' | tr -d 'cntlplane=')
  CONTROLLER=($CONTROLLERS)

  # Now switch to point the OpenStack commands at the overcloud
  STACK_NAME=$(openstack stack list -c 'Stack Name' -f value)
  [ "${STACK_NAME}" ] ||  \
      fatal "### ${STACK_NAME} is required and could not be found!  Aborting sanity test"

  set_admin_scope

  info "### PCS Status "
  ssh ${SSH_OPTS} heat-admin@$CONTROLLER 'sudo /usr/sbin/pcs status'
  ssh ${SSH_OPTS} heat-admin@$CONTROLLER 'sudo /usr/sbin/pcs status|grep -i stopped'

  info "###Ensure db and rabbit services are in the active state"
  ssh ${SSH_OPTS} heat-admin@$CONTROLLER 'sudo ps aux | grep rabbit'
  ssh ${SSH_OPTS} heat-admin@$CONTROLLER 'ps -ef | grep mysqld'
  ssh ${SSH_OPTS} heat-admin@$CONTROLLER 'ps -ef | grep mariadb'
}


execute_command(){
  cmd="$1"

  info "Executing: $cmd"

  $cmd
  if [ $? -ne 0 ]; then
    echo "command failed"
    exit 1
  fi
}


set_unique_names(){
  suffix=$1

  PROJECT_NAME=${BASE_PROJECT_NAME}${suffix}
  SANITYRC=~/${PROJECT_NAME}rc
  TENANT_NETWORK_NAME="${BASE_TENANT_NETWORK_NAME}${suffix}"
  VLAN1_NETWORK_NAME="${VLAN_NETWORK_NAME}${suffix}"
  TENANT_ROUTER_NAME="${BASE_TENANT_ROUTER_NAME}${suffix}"
  VLAN_NAME="${BASE_VLAN_NAME}${suffix}"
  USER_NAME="${BASE_USER_NAME}${suffix}"
  SWIFT_CONTAINER_NAME=${BASE_CONTAINER_NAME}_${suffix}
}


get_unique_names(){
  info "### Getting unique names"
  set_admin_scope

  index=1
  openstack project show ${BASE_PROJECT_NAME}${index} >/dev/null 2>&1
  while [ $? -eq 0 ]
  do
    index=$((index+1))
    openstack project show ${BASE_PROJECT_NAME}${index} >/dev/null 2>&1
  done

  set_unique_names $index
}


create_the_networks(){
  info "### Creating the Networks ####"
  set_tenant_scope
  net_exists=$(openstack network list -c Name -f value | grep "$TENANT_NETWORK_NAME")
  if [ "$net_exists" != "$TENANT_NETWORK_NAME" ]
  then
    execute_command "openstack network create $TENANT_NETWORK_NAME "
  else
    info "#----- Tenant network '$TENANT_NETWORK_NAME' exists. Skipping"
  fi

  subnet_exists=$(openstack subnet list -c Name -f value | grep "$VLAN_NAME")
  if [ "$subnet_exists" != "$VLAN_NAME" ]
  then
    set_tenant_scope
    execute_command "openstack subnet create $VLAN_NAME --network $TENANT_NETWORK_NAME --subnet-range $SANITY_TENANT_NETWORK"
  else
    info "#-----VLAN Network subnet '$SANITY_TENANT_NETWORK' exists. Skipping"
  fi
  if [ "$VLAN_AWARE_SANITY" != false ];then
    vlan1_exists=$(openstack network list -c Name -f value | grep "$VLAN1_NETWORK_NAME")
    if [ "$vlan1_exists" != "$VLAN1_NETWORK_NAME" ]
    then
        set_tenant_scope
        execute_command "openstack network create $VLAN1_NETWORK_NAME"
    else
        info "#-------vlan network '$VLAN1_NETWORK_NAME' already exists. Skipping "
    fi

    set_admin_scope
    VLANID_1=$(openstack network show $VLAN1_NETWORK_NAME -c provider:segmentation_id -f value | awk '{print $1}')

    set_tenant_scope
    subnet1_exists=$(openstack subnet list -c Name -f value | grep "vlan${VLANID_1}_sub")
    if [ "$subnet1_exists" != "vlan${VLANID_1}_sub" ]
    then
        execute_command "openstack subnet create vlan${VLANID_1}_sub --network $VLAN1_NETWORK_NAME --subnet-range $SANITY_VLANTEST_NETWORK "
    else
        info "#------- Subnet of VLAN $VLAN1ID already exists. Skipping"
    fi
  else
    info "VLAN AWARE CHECK = false"
  fi

  set_tenant_scope
  router_exists=$(openstack router list -c Name -f value | grep "$TENANT_ROUTER_NAME")
  if [ "$router_exists" != "$TENANT_ROUTER_NAME" ]
  then
    execute_command "openstack router create $TENANT_ROUTER_NAME"

    subnet_id=$(openstack network list | grep $TENANT_NETWORK_NAME | head -n 1 | awk '{print $6}')
    execute_command "openstack router add subnet $TENANT_ROUTER_NAME $subnet_id"
    if [ "$VLAN_AWARE_SANITY" != false ];then
      subnet_id_vlan=$(openstack network list | grep $VLAN1_NETWORK_NAME | head -n 1 | awk '{print $6}')
      execute_command "openstack router add subnet $TENANT_ROUTER_NAME $subnet_id_vlan"
    else
      info "VLAN AWARE CHECK = false"
    fi
    

  else
    info "#----- $TENANT_ROUTER_NAME exists. Skipping"
  fi

  # execute_command "ssh ${SSH_OPTS} heat-admin@$CONTROLLER sudo grep network_vlan_ranges /etc/neutron/plugin.ini"

  set_admin_scope
  ext_net_exists=$(openstack network list -c Name -f value | grep "$FLOATING_IP_NETWORK_NAME")
  if [ "$ext_net_exists" != "$FLOATING_IP_NETWORK_NAME" ]
  then
    execute_command "openstack network create $FLOATING_IP_NETWORK_NAME --external --provider-network-type vlan --provider-physical-network physext --provider-segment $FLOATING_IP_NETWORK_VLAN"
    execute_command "openstack subnet create $FLOATING_IP_SUBNET_NAME --network $FLOATING_IP_NETWORK_NAME --subnet-range $FLOATING_IP_NETWORK --allocation-pool start=$FLOATING_IP_NETWORK_START_IP,end=$FLOATING_IP_NETWORK_END --gateway $FLOATING_IP_NETWORK_GATEWAY --no-dhcp"
  else
    info "#----- External network '$FLOATING_IP_NETWORK_NAME' exists. Skipping"
  fi

  set_tenant_scope
  execute_command "openstack network list"

  execute_command "openstack router list"

  # Use external network name
  execute_command "openstack router set --external-gateway $FLOATING_IP_NETWORK_NAME $TENANT_ROUTER_NAME"
  
  # switch to tenant context
  set_tenant_scope
  openstack security group list -c Name -f value | grep -q $SECURITY_GROUP_NAME
  if [[ "$?" == 0 ]];
  then
    info "#----- Security group '$SECURITY_GROUP_NAME' exists. Skipping"
  else
    info "### Creating a Security Group ####"
    execute_command "openstack security group create $SECURITY_GROUP_NAME"

    # Allow all inbound and outbound ICMP
    execute_command "openstack security group rule create --ingress --ethertype IPv4 --protocol icmp --remote-ip 0.0.0.0/0 $SECURITY_GROUP_NAME"
    execute_command "openstack security group rule create --egress --ethertype IPv4 --protocol icmp --remote-ip 0.0.0.0/0 $SECURITY_GROUP_NAME"

    # Allow all inbound and outbound TCP
    execute_command "openstack security group rule create --ingress --ethertype IPv4 --protocol tcp --dst-port 1:65535 --remote-ip 0.0.0.0/0 $SECURITY_GROUP_NAME"
    execute_command "openstack security group rule create --egress --ethertype IPv4 --protocol tcp --dst-port 1:65535 --remote-ip 0.0.0.0/0 $SECURITY_GROUP_NAME"

    # Allow all inbound and outbound UDP
    execute_command "openstack security group rule create --ingress --ethertype IPv4 --protocol udp --dst-port 1:65535 --remote-ip 0.0.0.0/0 $SECURITY_GROUP_NAME"
    execute_command "openstack security group rule create --egress --ethertype IPv4 --protocol udp --dst-port 1:65535 --remote-ip 0.0.0.0/0 $SECURITY_GROUP_NAME"
  fi
}

port_creation() {
  #Creating ports in the tenant scope
  set_tenant_scope
  pp1_exists=$(openstack port list -c Name -f value | grep "$PARENT_PORT1")
  if [ "$pp1_exists" != "$PARENT_PORT1" ];then
    info "### Creating parent port and setting its security group----------"
    execute_command "openstack port create --network $TENANT_NETWORK_NAME $PARENT_PORT1"
    #Srtting port level security for pinging in the later stage
    execute_command "openstack port set --security-group $SECURITY_GROUP_NAME $PARENT_PORT1"
  else
    info "#-----Parent port 1 already exists. Commencing further----------"
  fi
if [ "$VLAN_AWARE_SANITY" != false ];then
    trunk1_exists=$(openstack trunk list -c Name -f value | grep "$TRUNK_PORT1")
    if [ "$trunk1_exists" != "$TRUNK_PORT1" ]
    then
      execute_command "openstack network trunk create --parent-port $PARENT_PORT1 $TRUNK_PORT1"
    else
      info "#-----Trunk Port 1 already exists. Commencing further----------"
    fi


    MACADDR_PP1=$(openstack port show -c mac_address -f value $PARENT_PORT1)

  # Creating subports
    info "### Creating subports and setting its security group----------"
    subport1_exists=$(openstack port list -c Name -f value | grep "subport1_$VLANID_1")
    if [ "$subport1_exists" != "subport1_$VLANID_1" ]
    then
      set_tenant_scope
      execute_command "openstack port create --mac-address $MACADDR_PP1 --network $VLAN1_NETWORK_NAME subport1_$VLANID_1"
      execute_command "openstack port set --security-group $SECURITY_GROUP_NAME subport1_$VLANID_1"

      info "Attaching subport to the TRUNK_PORT1."
      execute_command "openstack network trunk set --subport port=subport1_$VLANID_1,segmentation-type=vlan,segmentation-id=${VLANID_1} ${TRUNK_PORT1}"
    else
      info "#-----Subport subport1_$VLANID_1 exists.Commencing further----------"
    fi
  else
    info "VLAN AWARE CHECK = false"
  fi
}


setup_glance(){
  info "### Setting up glance"""
  set_tenant_scope

  if [ ! -f ./$IMAGE_FILE_NAME ]; then
    sleep 5 #HACK: a timing issue exists on some stamps -- 5 seconds seems sufficient to fix it
    info "### Downloading CentOS image file. Please wait..."
    wget --progress=bar:force $SANITY_IMAGE_URL
    if [ $? -ne 0 ]; then
      echo "command failed"
      exit 1
    fi
    info "### Download complete."
  else
    info "#----- CentOS image exists. Skipping"
  fi

  image_exists=$(openstack image list -c Name -f value | grep -x $IMAGE_NAME)
  if [ "$image_exists" != "$IMAGE_NAME" ]
  then
    execute_command "openstack image create --disk-format qcow2 --container-format bare --file $IMAGE_FILE_NAME $IMAGE_NAME"
  else
    info "#----- Image '$IMAGE_NAME' exists. Skipping"
  fi

  execute_command "openstack image list"
  #reset
  set_admin_scope
}

sriov_port_creation(){
  #Creating ports in the tenant scope
  set_tenant_scope

  execute_command "openstack port create --network $TENANT_NETWORK_NAME --vnic-type direct $sriov_port_name"
}

spin_up_instances(){
  tenant_net_id=$(openstack network list -f value | grep " $TENANT_NETWORK_NAME " | awk '{print $1}')

  image_id=$(openstack image list -f value | grep "$IMAGE_NAME" | awk 'NR==1{print $1}')
  
  pp1_id=$(openstack port show $PARENT_PORT1 -c id -f value | awk '{print $1}')

  info "### Initiating build of instances..."
  
  declare -a instance_names
info "VLAN AWARE CHECK == ${VLAN_AWARE_SANITY}"
  if [ "$VLAN_AWARE_SANITY" != false ];then
    info "SANITY_NUMBER_INSTANCES = ${SANITY_NUMBER_INSTANCES}"
    SANITY_NUMBER_INSTANCES=$((SANITY_NUMBER_INSTANCES+1))
    info "SANITY_NUMBER_INSTANCES WITH Vlan Instance = ${SANITY_NUMBER_INSTANCES}"
  else
    info "SANITY_NUMBER_INSTANCES = ${SANITY_NUMBER_INSTANCES}"
  fi
  index=1

  while [ $index -le $((${SANITY_NUMBER_INSTANCES})) ]; do
  instance_name="${BASE_NOVA_INSTANCE_NAME}_$index"
    if [ $index -le $((${SANITY_NUMBER_INSTANCES})) ] && [ "$VLAN_AWARE_SANITY" == false ]; then
      info "SRIOV_ENABLED == ${SRIOV_ENABLED}"
      if [ "$SRIOV_ENABLED" != false ];then
        info "### SRIOV: Creating SRIOV ports"
        sriov_port_name="sriov_port_$index"
        sriov_port_creation $sriov_port_name
        sleep 50
        info "### SRIOV: Initiating build of SR-IOV enabled instances..."
        execute_command "openstack server create --security-group $SECURITY_GROUP_NAME --flavor $FLAVOR_NAME --key-name $SANITY_KEY_NAME --image $image_id --nic port-id=$sriov_port_name $instance_name"
      else
        execute_command "nova boot --security-groups $SECURITY_GROUP_NAME --flavor $FLAVOR_NAME --key-name $SANITY_KEY_NAME --image $image_id --nic net-id=$tenant_net_id $instance_name"
      fi
    elif [ $index -le $((${SANITY_NUMBER_INSTANCES})) ] && [ "$VLAN_AWARE_SANITY" != false ]; then
      if [ $index -lt $((${SANITY_NUMBER_INSTANCES})) ]; then
        if [ "$SRIOV_ENABLED" != false ];then
          info "### SRIOV: Creating SRIOV ports"
          sriov_port_name="sriov_port_$index"
          sriov_port_creation $sriov_port_name
          sleep 50
          info "### SRIOV: Initiating build of SR-IOV enabled instances..."
          execute_command "openstack server create --security-group $SECURITY_GROUP_NAME --flavor $FLAVOR_NAME --key-name $SANITY_KEY_NAME --image $image_id --nic port-id=$sriov_port_name $instance_name"
        else
          execute_command "nova boot --security-groups $SECURITY_GROUP_NAME --flavor $FLAVOR_NAME --key-name $SANITY_KEY_NAME --image $image_id --nic net-id=$tenant_net_id $instance_name"
        fi
      else
        info "### Initiating build of Vlan-Aware-Instance..."
        execute_command "nova boot --security-groups $SECURITY_GROUP_NAME --flavor $FLAVOR_NAME --key-name $SANITY_KEY_NAME --image $image_id --nic port-id=${pp1_id} --user-data ${HOME}/interfacescript $instance_name"
      fi
    else
        info "VLAN AWARE CHECK == ${VLAN_AWARE_SANITY}"
    fi
  instance_names[((index-1))]=$instance_name
  index=$((index+1))
  done

  info "### Waiting for the instances to be built..."
  set_tenant_scope


  for instance_name in ${instance_names[*]}; do
    instance_status=$(nova list | grep -w $instance_name | awk '{print $6}')
    info "### Instance status is: ${instance_name} : ${instance_status}"
    while [ "$instance_status" != "ACTIVE" ]; do
      if [ "$instance_status" == "ERROR" ]; then
        fatal "### Instance status is: ${instance_name} : ${instance_status}!  Aborting sanity test"
      elif [ "$instance_status" == "ACTIVE" ]; then
        break
      else
        info "### Instance status is: ${instance_name} : ${instance_status}.  Sleeping..."
        sleep 30 
        instance_status=$(nova list | grep -w $instance_name | awk '{print $6}')
      fi
    done
  done

  info "### Instances are successfully built"
  execute_command "nova list"
}



setup_nova (){
  info "### Setup Nova"""
  openstack flavor show $FLAVOR_NAME > /dev/null 2>&1
  if [ $? -ne 0 ]
  then
    execute_command "openstack flavor create --ram 2048 --vcpus 1 --disk 20 $FLAVOR_NAME"
  else
    info "#----- Flavor '$FLAVOR_NAME' exists. Skipping"
  fi
  if [ "$NUMA_ENABLED" != "false" ]; then
    info "### NUMA: Adding metadata properties to flavor"
    execute_command "openstack flavor set --property hw:cpu_policy=dedicated --property hw:cpu_thread_policy=require --property hw:numa_nodes=1 $FLAVOR_NAME"
  fi
  if [ "$HPG_ENABLED" != "false" ]; then
    info "### HUGEPAGES: Adding metadata properties to flavor"
    execute_command "openstack flavor set --property hw:mem_page_size=large $FLAVOR_NAME"
  fi
  if [ "$OVS_DPDK_ENABLED" != "false" ]; then
    info "### OVS DPDK: Adding metadata properties to flavor"
    execute_command "openstack flavor set --property hw:emulator_threads_policy=isolate $FLAVOR_NAME"
  fi
  set_tenant_scope
  if [ ! -f ~/$SANITY_KEY_NAME ]; then
    info "creating keypair $SANITY_KEY_NAME"
    ssh-keygen -f ~/$SANITY_KEY_NAME -t rsa -N ""
  else
    info "using existing keypair $SANITY_KEY_NAME"
  fi

  nova keypair-show $SANITY_KEY_NAME 1>/dev/null 2>&1
  if [ $? -ne 0 ]
  then
    info "loading $SANITY_KEY_NAME keypair into nova"
    nova keypair-add --pub-key ~/${SANITY_KEY_NAME}.pub $SANITY_KEY_NAME
  else
    info "skipping loading $SANITY_KEY_NAME keypair into nova"
  fi
}

ping_from_netns(){

  ip=$1
  name_space=$2

  # Find the controller that has the IP set to an interface in the netns
  for controller in $CONTROLLERS
  do
      ssh ${SSH_OPTS} heat-admin@$controller "sudo /sbin/ip netns exec ${name_space} ip a" | grep -q $ip
    if [[ "$?" == 0 ]]
    then
      break
    fi
  done

  info "### Pinging $ip from netns $name_space on controller $controller"
  sleep 50
  execute_command "ssh ${SSH_OPTS} heat-admin@$controller sudo ip netns exec ${name_space} ping -c 1 -w 5 ${ip}"
  if [[ "$?" == 0 ]]
  then
      info "### Successfully pinged $ip from netns $name_space on controller $controller"
  else
      fatal "### Unable to ping $ip from netns $name_space on controller $controller!  Aborting sanity test"
  fi
}

ping_from_snat_netns(){

  ip=$1
  name_space=$2

  # Find the controller that has the IP set to an interface in the netns
  for controller in $CONTROLLERS
  do
      ssh ${SSH_OPTS} heat-admin@$controller "sudo /sbin/ip netns list" | grep -q $name_space
    if [[ "$?" == 0 ]]
    then
      break
    fi
  done
  sleep 50
  info "### Pinging $ip from netns $name_space on controller $controller"
  execute_command "ssh ${SSH_OPTS} heat-admin@$controller sudo ip netns exec ${name_space} ping -c 1 -w 5 ${ip}"
  if [[ "$?" == 0 ]]
  then
      info "### Successfully pinged $ip from netns $name_space on controller $controller"
  else
      fatal "### Unable to ping $ip from netns $name_space on controller $controller!  Aborting sanity test"
  fi
}

test_neutron_networking (){
  set_tenant_scope
  router_id=$(openstack router list | grep $TENANT_ROUTER_NAME | awk '{ print $2} ')

  net_ids=$(openstack network list | grep $TENANT_NETWORK_NAME | awk '{ print $2 " " $6 }')
  net_id=$(echo $net_ids | awk '{print $1}')
  subnet_id=$(echo $net_ids | awk '{print $2}')

  floating_ips=()
  for private_ip in $(openstack server list -c Networks -f value | awk -F= '{print $2}')
  do
      # Test pinging the private IP of the instance from the network namespace
      ping_from_netns $private_ip "qdhcp-${net_id}"

      # Allocate a floating IP
      info "Allocating floating IP"
      floating_ip_id=$(openstack floating ip create $FLOATING_IP_NETWORK_NAME | grep " id " | awk '{print $4}')
      floating_ip=$(openstack floating ip show $floating_ip_id | grep floating_ip_address | awk '{print $4}')
      floating_ips+=($floating_ip)

      # Find the port to associate it with
      set_tenant_scope
      port_id=$(openstack port list | grep $subnet_id | grep $private_ip | awk '{print $2}')

      # And finally associate the floating IP with the instance
      execute_command "openstack floating ip set $floating_ip_id --port $port_id"
  done

  sleep 3

  for floating_ip in ${floating_ips[@]}
  do
    if [ "$DVR_ENABLED" == "True" ]; then
      # Test pinging the floating IP of the instance from the snat
      # network namespace
      ping_from_snat_netns $floating_ip "snat-${router_id}"
    else
      # Test pinging the floating IP of the instance from the virtual router
      # network namespace
      ping_from_netns $floating_ip "qrouter-${router_id}"
    fi
  done
}


setup_cinder(){
  info "### Cinder test"""
  set_tenant_scope
  execute_command "cinder list"

  info "### Kicking off volume creation..."
  volumes=()
  openstack server list -c ID -c Name -f value | while read line
  do
    server_id=$(echo $line | awk '{print $1}')
    server_name=$(echo $line | awk '{print $2}')
    server_index=$(echo $server_name | awk -F_ '{print $3}')

    volume_name=${BASE_VOLUME_NAME}_${server_index}
    vol_exists=$(cinder list | grep $volume_name |  head -n 1  | awk '{print $6}')
    if [ "$vol_exists" != "$volume_name" ]
    then
      info "### Creating volume ${volume_name}"
      execute_command "cinder create --display-name $volume_name 1"
      volumes+=($volume_name)
    else
      info "### Volume $volume_name already exists.  Skipping creation"
    fi
  done

  execute_command "cinder list"    

  info "### Waiting for volumes status to change to available..."
  for volume_name in ${volumes[@]}
  do
    volume_status=$(cinder list | grep "$volume_name" | awk '{print $4}')
    while [ "$volume_status" != "available" ]; do
      if [ "$volume_status" != "creating" ]; then
        fatal "### Volume status is: ${volume_status}!  Aborting sanity test"
      else
        info "### Volume status is: ${volume_status}.  Sleeping..."
        sleep 5
        volume_status=$(cinder list | grep "$volume_name" | awk '{print $4}')
      fi
    done
    info "### Volume $volume_name is ready, status is $volume_status"
  done

  info "### Attaching volumes to instances..."
  openstack server list -c ID -c Name -f value | while read line
  do
    server_id=$(echo $line | awk '{print $1}')
    server_name=$(echo $line | awk '{print $2}')
    server_index=$(echo $server_name | awk -F_ '{print $3}')
    volume_name=${BASE_VOLUME_NAME}_${server_index}

    volume_id=$(cinder list | grep $volume_name | head -n 1 | awk '{print $2}')

    execute_command "nova volume-attach $server_id $volume_id /dev/vdb"

    info "Volume $volume_name attached to $server_name.  ssh in and verify"
  done
}

setup_manila(){
  info "### Manila test"""
  
  set_admin_scope
  manila_exists=$(manila service-list | grep manila-share |  head -n 1  | awk '{print $4}')
  if [ "$manila_exists" != 'manila-share' ]; then
    info "### Manila is not deployed. Skipping..."
    return 1
  fi

  info "### Create manila share network (unity requires)..."

  set_tenant_scope #Create shares in tenant aka sanity scope

  execute_command "manila share-network-list"  
  manila_share_network_exists=$(manila share-network-list | grep unity_share_net | awk '{print $4}')
  if [ "$manila_share_network_exists" != "unity_share_net" ]; then
    net_id=$(openstack network list | grep " $FLOATING_IP_NETWORK_NAME " | head -n 1 | awk '{print $2}')
    subnet_id=$(openstack network list | grep $FLOATING_IP_NETWORK_NAME | head -n 1 | awk '{print $6}')
    
    execute_command "manila share-network-create --neutron-net-id  $net_id --neutron-subnet-id $subnet_id --name unity_share_net" 
  fi   
  execute_command "manila share-network-list"
  
	  
  execute_command "manila list"

  info "### Kicking off share creation..."

  shares=()
  share_name=$BASE_SHARE_NAME
  share_exists=$(manila list | grep "$share_name" | awk '{print $2}')
  if [ "$share_exists" != "$share_name" ]; then
    info "### Creating share ${share_name}"
    execute_command "manila create --name $share_name --share_type unity_share --share_network unity_share_net nfs 10"
    shares+=($share_name)
  else
    info "### Share $share_name already exists.  Skipping creation"
  fi

  execute_command "manila list"    

  info "### Waiting for shares status to change to available..."
  for share_name in ${shares[@]}
  do
    share_status=$(manila list | grep "$share_name" | awk '{print $10}')
    while [ "$share_status" != "available" ]; do
      if [ "$share_status" != "creating" ]; then
        fatal "### Share status is: ${share_status}!  Aborting sanity test"
      else
        info "### Share status is: ${share_status}.  Sleeping..."
        sleep 30
        share_status=$(manila list | grep "$share_name" | awk '{print $10}')
      fi
    done
    info "### Share $share_name is ready, status is $share_status"
 
  
  info "### Mounting the share to instances..."
  share_path=$(manila share-export-location-list "$share_name" | grep ":/" | awk '{print $4}')
  info "Share path of $share_name is $share_path ..."
  openstack server list -c ID -c Name -c Networks -f value | while read line
  do
    echo "Line = $line"
    server_id=$(echo $line | awk '{print $1}')
    server_name=$(echo $line | awk '{print $2}')
    server_ip=$(echo $line | awk '{print $4}')
    server_index=$(echo $server_name | awk -F_ '{print $3}')

    #allow access to the VM using ip
    info "Share $share_name allows access to $server_name.  ssh in and mount to verify"
    execute_command "manila access-allow $share_name ip $server_ip"
    sleep 30
    ssh ${SSH_OPTS} -i ~/$SANITY_KEY_NAME centos@${server_ip} "sudo mkdir ~/mnt"
    ssh ${SSH_OPTS} -i ~/$SANITY_KEY_NAME centos@${server_ip} "sudo mount -t nfs ${share_path} ~/mnt"
    ssh ${SSH_OPTS} -i ~/$SANITY_KEY_NAME centos@${server_ip} "sudo touch ~/mnt/${server_ip}"
 
  done
   
    set_admin_scope #reset
  done
}

manila_cleanup()
{
    set_tenant_scope

    info "#### Deleting the shares"

    ids=$(manila list | grep $BASE_SHARE_NAME | awk '{print $2}')
    info "share ids: $ids"
    [[ $ids ]] && echo $ids | xargs -n1 manila delete
     
    sleep 5

    ids=$(manila share-network-list | grep unity_share_net | awk '{print $2}')
    info "share network ids: $ids"
    [[ $ids ]] && echo $ids | xargs -n1 manila share-network-delete

}


radosgw_test(){
  info "### RadosGW test"
  set_tenant_scope

  execute_command "swift post $SWIFT_CONTAINER_NAME"

  execute_command "swift list"

  echo "This is a test file for RGW" >  test_file
  execute_command "swift upload $SWIFT_CONTAINER_NAME test_file"

  execute_command "swift list $SWIFT_CONTAINER_NAME"
}


radosgw_cleanup(){
  info "### RadosGW cleanup"
  rm -f test_file
  swift delete $SWIFT_CONTAINER_NAME
  execute_command "swift list"
}

create_vlan_aware_interface_script(){
#Script for the setting up the interfaces of vlan network in vlan aware instance
info "### Creating interfaces script for interface setup-------------"
ip_sbp=$(openstack port list | grep subport1_$VLANID_1 | awk '{print $8}' | awk -F"'" '{print $2}')
gw_vlan_net=${SANITY_VLANTEST_NETWORK%0\/24}1
cat << EOF >~/interfacescript
#!/bin/bash
intfc=\$(ip route | grep default | sed -e "s/^.*dev.//" -e "s/.proto.*//") && intfc=\$(echo \$intfc)
sudo touch /etc/sysconfig/network-scripts/ifcfg-\${intfc}.${VLANID_1} 
sudo tee /etc/sysconfig/network-scripts/ifcfg-\${intfc}.$VLANID_1 <<- End >/dev/null
    DEVICE="\${intfc}.$VLANID_1"
    BOOTPROTO="static"
    ONBOOT="yes"
    NETMASK=255.255.255.0
    IPADDR=${ip_sbp}
    USERCTL="yes"
    DEFROUTE="no"
    PEERDNS="no"
    VLAN=yes
End
sudo touch /etc/sysconfig/network-scripts/route-\${intfc}.$VLANID_1
sudo tee /etc/sysconfig/network-scripts/route-\${intfc}.$VLANID_1 <<- End >/dev/null
    default via ${gw_vlan_net} dev \${intfc}.${VLANID_1} proto static metric 200
End
sudo /etc/sysconfig/network-scripts/ifup ifcfg-\${intfc}.${VLANID_1}
sudo sleep 3  
EOF
}


vlan_aware_test(){

  info "### Commencing vlan-instance interface testing"
  set_tenant_scope

  ip_vlan1=$(openstack port list | grep subport1_$VLANID_1 | awk '{print $8}' | awk -F"'" '{print $2}')

  netid_vlan1=$(openstack network show $VLAN1_NETWORK_NAME | grep " id" | awk '{print $4}')

  ping_from_netns ${ip_vlan1} qdhcp-${netid_vlan1}

  info "### Successfully completed the vlan-instance test"
}


setup_project(){
  info "### Setting up new project $PROJECT_NAME"
  set_admin_scope

  pro_exists=$(openstack project show -c name -f value $PROJECT_NAME)
  if [ "$pro_exists" != "$PROJECT_NAME" ]
  then
    execute_command "openstack project create $PROJECT_NAME"
    execute_command "openstack user create --project $PROJECT_NAME --password $SANITY_USER_PASSWORD --email $SANITY_USER_EMAIL $USER_NAME"
    execute_command "openstack role add --project $PROJECT_NAME --user $USER_NAME member"
  else
    info "#Project $PROJECT_NAME exists ---- Skipping"
  fi
}


end(){
  info "#####VALIDATION SUCCESS#####"
}


info "###Appendix-C Openstack Operations Functional Test ###"

init

### CLEANUP
if [[ "$1" == "clean" ]]
then
  info "### CLEANING MODE"
  cd ~
  set_admin_scope

  index=1
  openstack project show ${BASE_PROJECT_NAME}${index} >/dev/null 2>&1
  while [ $? -eq 0 ]
  do
    set_unique_names $index

    export OS_TENANT_NAME=$PROJECT_NAME
    export OS_PROJECT_NAME=$PROJECT_NAME
    export OS_PASSWORD=$SANITY_USER_PASSWORD
    export OS_USERNAME=$USER_NAME

    info "### Starting deletion of $PROJECT_NAME"
    info "### Deleting keypair"
    keypair_ids=$(nova keypair-list | grep $SANITY_KEY_NAME | awk '{print $2}')
    info   "keypair id: $keypair_id"
    [[ $keypair_ids ]] && echo $keypair_ids | xargs -n1 nova keypair-delete

    info "### Deleting the floating ips"
    private_ips=$(nova list | grep "$BASE_NOVA_INSTANCE_NAME" | awk '{print $12}' | awk -F= '{print $2}')
    for private_ip in $private_ips
    do
      private_ip=${private_ip%,}
      public_ip_id=$(openstack floating ip list | grep $private_ip | awk '{print $2}')

      [[ $public_ip_id ]] && openstack floating ip unset $public_ip_id
      [[ $public_ip_id ]] && openstack floating ip delete $public_ip_id
    done

    info   "#### Deleting the instances"
    instance_ids=$(nova list | grep $BASE_NOVA_INSTANCE_NAME | awk '{print $2}')
    [[ $instance_ids ]] && echo $instance_ids | xargs -n1 nova delete

    info "### Waiting for the instances to be deleted..."
    num_instances=$(nova list | grep $BASE_NOVA_INSTANCE_NAME | wc -l)
    info "num instance: $num_instances"
    while [ "$num_instances" -gt 0 ]; do
      info "#### ${num_instances} remain.  Sleeping..."
      sleep 3
      num_instances=$(nova list | grep $BASE_NOVA_INSTANCE_NAME | wc -l)
    done

    info "#### Deleting the volumes"
    volume_ids=$(cinder list | grep $BASE_VOLUME_NAME | awk '{print $2}')
    info "volume ids: $volume_ids"
    [[ $volume_ids ]] && echo $volume_ids | xargs -n1 cinder delete

    info "### Waiting for the volumes to be deleted..."
    num_volumes=$(cinder list | grep $BASE_VOLUME_NAME | wc -l)
    while [ "$num_volumes" -gt 0 ]; do
      info "#### ${num_volumes} remain.  Sleeping..."
      sleep 3
      num_volumes=$(cinder list | grep $BASE_VOLUME_NAME | wc -l)
    done

    manila_cleanup

    radosgw_cleanup

    set_admin_scope

    info "#### Deleting the user"
    openstack user show $USER_NAME >/dev/null 2>&1
    if [ $? -eq 0 ]
    then 
      execute_command "openstack user delete $USER_NAME"
    fi

    info "#### Deleting the project"
    openstack project show $PROJECT_NAME >/dev/null 2>&1
    if [ $? -eq 0 ]
    then
      execute_command "openstack project delete $PROJECT_NAME"
    fi

    index=$((index+1))
    openstack project show ${BASE_PROJECT_NAME}${index} >/dev/null 2>&1
  done

  set_admin_scope


  info   "#### Deleting the images"
  image_ids=$(openstack image list | grep $IMAGE_NAME | awk '{print $2}')
  [[ $image_ids ]] && echo $image_ids | xargs -n1 openstack image delete

  info "### Deleting the flavor"
  openstack flavor show $FLAVOR_NAME > /dev/null 2>&1
  if [ $? -eq 0 ]
  then
    openstack flavor delete $FLAVOR_NAME
  fi
  
  if [ -f ./$IMAGE_FILE_NAME ]; then
     rm -f ./$IMAGE_FILE_NAME
  fi

  info "### Deleting the script"
  if [ -f ~/interfacescript ]; then
    rm ~/interfacescript
  fi
  info "### Deleting trunk and its associated ports"
  trunk_ports=$(openstack network trunk list | grep $TRUNK_PORT1 | awk '{print $2}')
  for trunk_port in $trunk_ports
  do 
    openstack network trunk delete $trunk_port
  done
  
  parent_ports=$(openstack port list | grep $PARENT_PORT1 | awk '{print $2}')
  for parent_port in $parent_ports
  do
    openstack port delete $parent_port
  done 

  subports=$(openstack port list | grep subport1_$VLANID_1 | awk '{print $2}')
  for subport in $subports
  do
    openstack port delete $subport
  done

  #Deleting SRIOV ports
  if [ "$SRIOV_ENABLED" != false ]; then
    info "### Deleting SRIOV ports..."
    sriov_ports=$(openstack port list | grep -E "*sriov_port_*" | awk '{print $2}')
    for sriov_port in $sriov_ports
    do
      openstack port delete $sriov_port
    done
  fi

  info   "#### Deleting the security groups"
  security_group_ids=$(openstack security group list | grep $BASE_SECURITY_GROUP_NAME | awk '{print $2}')
  [[ $security_group_ids ]] && echo $security_group_ids | xargs -n1 openstack security group delete



  info "### Deleting router and router interfaces"
  router_ids=$(openstack router list | grep $BASE_VLAN_NAME | awk '{print $2}')
  subnet_network_ids=$(openstack subnet list | grep -E "${BASE_VLAN_NAME}|*vlan[0-9|_]{4}sub*" | awk '{print $2}')
  for router_id in $router_ids
  do
    for subnet_network_id in $subnet_network_ids
    do
      openstack router remove subnet $router_id $subnet_network_id
    done
    openstack router unset --all-tag $router_id
    openstack router delete $router_id
  done

  info "### Deleting network subnets"
  for subnet_network_id in $subnet_network_ids
  do
    openstack subnet delete $subnet_network_id
  done 
  
  info "### Deleting networks"
  network_ids=$(openstack network list | grep -E "$BASE_TENANT_NETWORK_NAME|$VLAN_NETWORK_NAME|$FLOATING_IP_NETWORK_NAME" | awk '{print $2}')
  public_id=$(openstack network list | grep $FLOATING_IP_NETWORK_NAME | head -n 1 | awk '{print $2}')
  for network_id in $network_ids
  do
    if [ "$network_id" != "$public_id" ];then
      openstack network delete $network_id
    else
      info "Public Network Can not be deleted"
    fi
  done

  info "### Deleting key file"
  rm -f ~/${SANITY_KEY_NAME}
  rm -f ~/${SANITY_KEY_NAME}.pub

  info "### Deleting ${BASE_PROJECT_NAME}rc files"
  rm -f ~/${BASE_PROJECT_NAME}*rc

  info "########### CLEANUP SUCCESSFUL ############"
  exit 1
else
  #### EXECUTE

  info "### CREATION MODE"

  get_unique_names

  generate_sanity_rc

  setup_project

  create_the_networks

  port_creation   

  setup_glance

  setup_nova
  
  if [ "$VLAN_AWARE_SANITY" != false ];then
    create_vlan_aware_interface_script
  else
    info "VLAN aware check is false."
  fi

  spin_up_instances

  test_neutron_networking

  setup_cinder

  setup_manila

  if [ "$VLAN_AWARE_SANITY" != false ];then
    vlan_aware_test
  fi

  radosgw_test

  end

  info "##### Done #####"

  exit
fi
