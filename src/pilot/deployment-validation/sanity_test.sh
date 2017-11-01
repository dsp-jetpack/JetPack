#!/bin/bash

# Copyright (c) 2015-2017 Dell Inc. or its subsidiaries.
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

FLOATING_IP_NETWORK=$(get_value floating_ip_network)
FLOATING_IP_NETWORK_START_IP=$(get_value floating_ip_network_start_ip)
FLOATING_IP_NETWORK_END=$(get_value floating_ip_network_end_ip)
FLOATING_IP_NETWORK_GATEWAY=$(get_value floating_ip_network_gateway)
FLOATING_IP_NETWORK_VLAN=$(get_value floating_ip_network_vlan)
SANITY_TENANT_NETWORK=$(get_value sanity_tenant_network)
SANITY_USER_PASSWORD=$(get_value sanity_user_password)
SANITY_USER_EMAIL=$(get_value sanity_user_email)
SANITY_KEY_NAME=$(get_value sanity_key_name)
SANITY_NUMBER_INSTANCES=$(get_value sanity_number_instances)
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
BASE_PROJECT_NAME=$(get_value base_project_name)
BASE_USER_NAME=$(get_value base_user_name)
BASE_CONTAINER_NAME=$(get_value base_container_name)

IMAGE_FILE_NAME=$(basename $SANITY_IMAGE_URL)
SECURITY_GROUP_NAME="$BASE_SECURITY_GROUP_NAME"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o KbdInteractiveDevices=no"

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
  set_admin_scope
  net_exists=$(openstack network list -c Name -f value | grep "$TENANT_NETWORK_NAME")
  if [ "$net_exists" != "$TENANT_NETWORK_NAME" ]
  then
    execute_command "openstack network create --share $TENANT_NETWORK_NAME"
  else
    info "#----- Tenant network '$TENANT_NETWORK_NAME' exists. Skipping"
  fi

  subnet_exists=$(openstack subnet list -c Name -f value | grep "$VLAN_NAME")
  if [ "$subnet_exists" != "$VLAN_NAME" ]
  then
    execute_command "neutron subnet-create $TENANT_NETWORK_NAME $SANITY_TENANT_NETWORK --name $VLAN_NAME"
  else
    info "#-----VLAN Network subnet '$SANITY_TENANT_NETWORK' exists. Skipping"
  fi

  router_exists=$(openstack router list -c Name -f value | grep "$TENANT_ROUTER_NAME")
  if [ "$router_exists" != "$TENANT_ROUTER_NAME" ]
  then
    execute_command "neutron router-create $TENANT_ROUTER_NAME"

    subnet_id=$(neutron net-list | grep $TENANT_NETWORK_NAME | head -n 1 | awk '{print $6}')

    execute_command "neutron router-interface-add $TENANT_ROUTER_NAME $subnet_id"
  else
    info "#----- $TENANT_ROUTER_NAME exists. Skipping"
  fi

  execute_command "ssh ${SSH_OPTS} heat-admin@$CONTROLLER sudo grep network_vlan_ranges /etc/neutron/plugin.ini"

  ext_net_exists=$(openstack network list -c Name -f value | grep "$FLOATING_IP_NETWORK_NAME")
  if [ "$ext_net_exists" != "$FLOATING_IP_NETWORK_NAME" ]
  then
    execute_command "neutron net-create $FLOATING_IP_NETWORK_NAME --router:external --provider:network_type vlan --provider:physical_network physext --provider:segmentation_id $FLOATING_IP_NETWORK_VLAN"
    execute_command "neutron subnet-create --name $FLOATING_IP_SUBNET_NAME --allocation-pool start=$FLOATING_IP_NETWORK_START_IP,end=$FLOATING_IP_NETWORK_END --gateway $FLOATING_IP_NETWORK_GATEWAY --disable-dhcp $FLOATING_IP_NETWORK_NAME $FLOATING_IP_NETWORK"
  else
    info "#----- External network '$FLOATING_IP_NETWORK_NAME' exists. Skipping"
  fi


  execute_command "openstack network list"

  execute_command "openstack router list"

  # Use external network name
  execute_command "neutron router-gateway-set $TENANT_ROUTER_NAME $FLOATING_IP_NETWORK_NAME"
  
  # switch to tenant context
  set_tenant_scope
  openstack security group list -c Name -f value | grep -q $SECURITY_GROUP_NAME
  if [[ "$?" == 0 ]];
  then
    info "#----- Security group '$SECURITY_GROUP_NAME' exists. Skipping"
  else
    info "### Creating a Security Group ####"
    execute_command "neutron security-group-create $SECURITY_GROUP_NAME"

    # Allow all inbound and outbound ICMP
    execute_command "neutron security-group-rule-create --direction ingress --ethertype IPv4 --protocol icmp --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"
    execute_command "neutron security-group-rule-create --direction egress --ethertype IPv4 --protocol icmp --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"

    # Allow all inbound and outbound TCP
    execute_command "neutron security-group-rule-create --direction ingress --ethertype IPv4 --protocol tcp --port-range-min 1 --port-range-max 65535 --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"
    execute_command "neutron security-group-rule-create --direction egress --ethertype IPv4 --protocol tcp --port-range-min 1 --port-range-max 65535 --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"

    # Allow all inbound and outbound UDP
    execute_command "neutron security-group-rule-create --direction ingress --ethertype IPv4 --protocol udp --port-range-min 1 --port-range-max 65535 --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"
    execute_command "neutron security-group-rule-create --direction egress --ethertype IPv4 --protocol udp --port-range-min 1 --port-range-max 65535 --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"
  fi
}


setup_glance(){
  info "### Setting up glance"""
  set_admin_scope

  if [ ! -f ./$IMAGE_FILE_NAME ]; then
    sleep 5 #HACK: a timing issue exists on some stamps -- 5 seconds seems sufficient to fix it
    execute_command "wget $SANITY_IMAGE_URL"
  else
    info "#----- Cirros image exists. Skipping"
  fi

  image_exists=$(openstack image list -c Name -f value | grep -x $IMAGE_NAME)
  if [ "$image_exists" != "$IMAGE_NAME" ]
  then
    execute_command "openstack image create --disk-format qcow2 --container-format bare --file $IMAGE_FILE_NAME $IMAGE_NAME --public"
  else
    info "#----- Image '$IMAGE_NAME' exists. Skipping"
  fi

  execute_command "openstack image list"
}


spin_up_instances(){
  tenant_net_id=$(openstack network list -f value | grep " $TENANT_NETWORK_NAME " | awk '{print $1}')

  image_id=$(openstack image list -f value | grep "$IMAGE_NAME" | awk '{print $1}')

  info "### Initiating build of instances..."
  declare -a instance_names
  index=1
  while [ $index -le $SANITY_NUMBER_INSTANCES ]; do
    instance_name="${BASE_NOVA_INSTANCE_NAME}_$index"

    execute_command "nova boot --security-groups $SECURITY_GROUP_NAME --flavor $FLAVOR_NAME --key-name $SANITY_KEY_NAME --image $image_id --nic net-id=$tenant_net_id $instance_name"

    instance_names[((index-1))]=$instance_name
    index=$((index+1))
  done

  info "### Waiting for the instances to be built..."

  for instance_name in ${instance_names[*]}; do
    instance_status=$(nova show $instance_name | grep status | awk '{print $4}')
    while [ "$instance_status" != "ACTIVE" ]; do
      if [ "$instance_status" != "BUILD" ]; then
        fatal "### Instance status is: ${instance_status}!  Aborting sanity test"
      else
        info "### Instance status is: ${instance_status}.  Sleeping..."
        sleep 10
        instance_status=$(nova show $instance_name | grep status | awk '{print $4}')
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
  execute_command "ssh ${SSH_OPTS} heat-admin@$controller sudo ip netns exec ${name_space} ping -c 1 -w 5 ${ip}"
  if [[ "$?" == 0 ]]
  then
      info "### Successfully pinged $ip from netns $name_space on controller $controller"
  else
      fatal "### Unable to ping $ip from netns $name_space on controller $controller!  Aborting sanity test"
  fi
}

test_neutron_networking (){
  set_admin_scope
  router_id=$(neutron router-show -F id $TENANT_ROUTER_NAME | grep "id" | awk '{print $4}')

  set_tenant_scope
  net_ids=$(neutron net-show -F id -F subnets $TENANT_NETWORK_NAME | grep -E 'id|subnets' | awk '{print $4}')
  net_id=$(echo $net_ids | awk '{print $1}')
  subnet_id=$(echo $net_ids | awk '{print $2}')

  floating_ips=()
  for private_ip in $(openstack server list -c Networks -f value | awk -F= '{print $2}')
  do
      # Test pinging the private IP of the instance from the network namespace
      ping_from_netns $private_ip "qdhcp-${net_id}"

      # Allocate a floating IP
      info "Allocating floating IP"
      floating_ip_id=$(neutron floatingip-create $FLOATING_IP_NETWORK_NAME | grep " id " | awk '{print $4}')
      floating_ip=$(neutron floatingip-show $floating_ip_id | grep floating_ip_address | awk '{print $4}')
      floating_ips+=($floating_ip)

      # Find the port to associate it with
      set_admin_scope
      port_id=$(neutron port-list | grep $subnet_id | grep $private_ip | awk '{print $2}')

      # And finally associate the floating IP with the instance
      set_tenant_scope
      execute_command "neutron floatingip-associate $floating_ip_id $port_id"
  done

  sleep 3

  for floating_ip in ${floating_ips[@]}
  do
    # Test pinging the floating IP of the instance from the virtual router
    # network namespace
    ping_from_netns $floating_ip "qrouter-${router_id}"
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
      execute_command "cinder type-list"
      execute_command "cinder create --display-name $volume_name 1 --volume-type=rbd_backend"
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


radosgw_test(){
  info "### RadosGW test"
  set_tenant_scope

  execute_command "swift post $SWIFT_CONTAINER_NAME"

  execute_command "swift list"

  touch test_file
  execute_command "swift upload $SWIFT_CONTAINER_NAME test_file"

  execute_command "swift list $SWIFT_CONTAINER_NAME"
}


radosgw_cleanup(){
  info "### RadosGW cleanup"
  rm -f test_file
  swift delete $SWIFT_CONTAINER_NAME
  execute_command "swift list"
}


setup_project(){
  info "### Setting up new project $PROJECT_NAME"
  set_admin_scope

  pro_exists=$(openstack project show -c name -f value $PROJECT_NAME)
  if [ "$pro_exists" != "$PROJECT_NAME" ]
  then
    execute_command "openstack project create $PROJECT_NAME"
    execute_command "openstack user create --project $PROJECT_NAME --password $SANITY_USER_PASSWORD --email $SANITY_USER_EMAIL $USER_NAME"
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
    keypair_id=$(nova keypair-list | grep $SANITY_KEY_NAME | awk '{print $2}')
    info   "keypair id: $keypair_id"
    [[ $keypair_ids ]] && echo $keypair_ids | xargs -n1 nova keypair-delete

    info "### Deleting the floating ips"
    private_ips=$(nova list | grep "$BASE_NOVA_INSTANCE_NAME" | awk '{print $12}' | awk -F= '{print $2}')
    for private_ip in $private_ips
    do
      private_ip=${private_ip%,}
      public_ip_id=$(neutron floatingip-list | grep $private_ip | awk '{print $2}')

      [[ $public_ip_id ]] && neutron floatingip-disassociate $public_ip_id
      [[ $public_ip_id ]] && neutron floatingip-delete $public_ip_id
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

    radosgw_cleanup

    set_admin_scope
    info "#### Disconnecting the router"
    neutron router-interface-delete $TENANT_ROUTER_NAME $VLAN_NAME

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
  info   "#### Deleting the security groups"
  security_group_ids=$(neutron security-group-list | grep $BASE_SECURITY_GROUP_NAME | awk '{print $2}')
  [[ $security_group_ids ]] && echo $security_group_ids | xargs -n1 neutron security-group-delete

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
  
  info "### Deleting routers"
  router_ids=$(neutron router-list | grep $BASE_TENANT_ROUTER_NAME | awk '{print $2}')
  for router_id in $router_ids
  do
    neutron router-gateway-clear $router_id
    neutron router-delete $router_id
  done

  info "### Deleting networks"
  network_ids=$(neutron net-list | grep -E "$BASE_TENANT_NETWORK_NAME|$FLOATING_IP_NETWORK_NAME" | awk '{print $2}')
  for network_id in $network_ids
  do
    neutron net-delete $network_id
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

  setup_glance

  setup_nova

  spin_up_instances

  test_neutron_networking

  setup_cinder

  radosgw_test

  end

  info "##### Done #####"

  exit
fi
