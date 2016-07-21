#!/bin/bash

# (c) 2015-2016 Dell
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
VLAN_NETWORK="192.168.201.0/24"
EXTERNAL_NETWORK_NAME="public"
EXTERNAL_SUBNET_NAME="external_sub"
STARTIP="192.168.191.2"
ENDIP="192.168.191.30"
EXTERNAL_VLAN="191"
EXTERNAL_VLAN_NETWORK="192.168.191.0/24"
GATEWAY_IP=192.168.191.1
KEY_NAME="key_name"
KEY_FILE="$KEY_NAME.pem"
IMAGE_NAME="cirros"
PASSWORD="cr0wBar!"
EMAIL="ce-cloud@dell.com"

BASE_SECURITY_GROUP_NAME="sanity_security_group"
BASE_TENANT_NETWORK_NAME="tenant_net"
BASE_TENANT_ROUTER_NAME="tenant_201_router"
BASE_VLAN_NAME="tenant_201"
BASE_NOVA_INSTANCE_NAME="cirros_test"
BASE_VOLUME_NAME="volume_test"
BASE_PROJECT_NAME="sanity"
BASE_USER_NAME="sanity"

SECURITY_GROUP_NAME="$BASE_SECURITY_GROUP_NAME"
TENANT_NETWORK_NAME="$BASE_TENANT_NETWORK_NAME"
TENANT_ROUTER_NAME="$BASE_TENANT_ROUTER_NAME"
VLAN_NAME="$BASE_VLAN_NAME"
NOVA_INSTANCE_NAME="$BASE_NOVA_INSTANCE_NAME"
VOLUME_NAME="$BASE_VOLUME_NAME"
PROJECT_NAME="$BASE_PROJECT_NAME"
USER_NAME="$BASE_USER_NAME"

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

# global var
NAME=''

# Logging functions
log() { echo -e "$(date '+%F %T'): $@" >&2; }
fatal() { log "FATAL: $@" >&2; exit 1; }
error() { [[ $ERROR -le $LOG_LEVEL ]] && log "ERROR: $@"; }
warn() { [[ $WARN -le $LOG_LEVEL ]] && log "WARN: $@"; }
info() { [[ $INFO -le $LOG_LEVEL ]] && log "INFO: $@"; }
debug() { [[ $DEBUG -le $LOG_LEVEL ]] && log "DEBUG: $@"; }


######## Functions ############

init(){
  info "### Random init stuff "
  cd ~

  source ~/stackrc

  # Collect the SSH keys from all of the overcloud nodes
  info "### Collecting SSH keys... ###"

  local update_ssh_config="${HOME}/pilot/update_ssh_config.py"
  [ -x "${update_ssh_config}" ] || \
      fatal "### '${update_ssh_config}' is required but missing!  Aborting sanity test"
  execute_command "${update_ssh_config}"

  # Find the IP for controller0 from the undercloud
  CONTROLLER_0_NAME=$(nova list | grep '\-controller-0' | awk -F\| '{print $3}'| tr -d ' ')
  CONTROLLER=$(nova show ${CONTROLLER_0_NAME} |grep "ctlplane network"| awk -F\| '{print $3}'| tr -d ' ')

  # Get a list of the IPs of all the controller nodes for later use
  CONTROLLERS=$(nova list | grep '\-controller-' | awk -F\| '{print $7}' | awk -F= '{print $2}')

  # Now switch to point the OpenStack commands at the overcloud
  STACK_NAME=$(heat stack-list | grep CREATE_ | awk -F\| '{print $3}' | tr -d ' ')
  [ "${STACK_NAME}" ] ||  \
      STACK_NAME=$(heat stack-list | grep UPDATE_ | awk -F\| '{print $3}' | tr -d ' ')
  [ "${STACK_NAME}" ] ||  \
      fatal "### '${STACK_NAME}' is required and could not be found!  Aborting sanity test"
    
  source ~/${STACK_NAME}rc

  info "### PCS Status "
  ssh heat-admin@$CONTROLLER 'sudo /usr/sbin/pcs status'
  ssh heat-admin@$CONTROLLER 'sudo /usr/sbin/pcs status|grep -i stopped'

  info "###Ensure db and rabbit services are in the active state"
  execute_command "openstack-service status"
  ssh heat-admin@$CONTROLLER 'sudo ps aux | grep rabbit'
  ssh heat-admin@$CONTROLLER 'ps -ef | grep mysqld'
  ssh heat-admin@$CONTROLLER 'ps -ef | grep mariadb'

  info "### Verify OpenStack services are running."
  execute_command "ssh heat-admin@$CONTROLLER sudo nova-manage service list"
  execute_command "ssh heat-admin@$CONTROLLER sudo cinder-manage service list"
  execute_command "ssh heat-admin@$CONTROLLER systemctl status openstack-keystone"
  execute_command "ssh heat-admin@$CONTROLLER systemctl status openstack-glance-api"
  execute_command "ssh heat-admin@$CONTROLLER systemctl status openstack-glance-registry"
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


#Generates a unique name
get_unique_name (){
  cmd=$1
  name=$2
  tmp=$name

  for i in {1..25}
  do
    name="$tmp$i"    
    name_exists=$($cmd | grep $name | head -n 1 | awk '{print $4}')
    echo $name_exists , $cmd , $tmp, $name
    if [ "$name_exists" != "$name"  ]
    then
       NAME=$i
       return
    fi
  done
}


set_unique_names(){
  info "###get_unique-name"
  inst_exists=$(nova list | grep $NOVA_INSTANCE_NAME |  head -n 1  | awk '{print $4}')
  if [ "$inst_exists" == "$NOVA_INSTANCE_NAME" ]
  then
     info "$NOVA_INSTANCE_NAME instance exists, creating new set"
     get_unique_name "nova list" "$NOVA_INSTANCE_NAME"

     TENANT_NETWORK_NAME="$TENANT_NETWORK_NAME$NAME"
     TENANT_ROUTER_NAME="$TENANT_ROUTER_NAME$NAME"
     VLAN_NAME="$VLAN_NAME$NAME"
     NOVA_INSTANCE_NAME="$NOVA_INSTANCE_NAME$NAME"
     VOLUME_NAME="$VOLUME_NAME$NAME"
     PROJECT_NAME="$PROJECT_NAME$NAME"
     USER_NAME="$USER_NAME$NAME"
  fi
}


create_the_networks(){
  info "### Creating the Networks ####"
 
  net_exists=$(neutron net-list | grep $TENANT_NETWORK_NAME |  head -n 1  | awk '{print $4}')
  if [ "$net_exists" != "$TENANT_NETWORK_NAME" ]
  then 
    execute_command "neutron net-create $TENANT_NETWORK_NAME --shared"
  else
    info "#----- Tenant network '$TENANT_NETWORK_NAME' exists. Skipping"
  fi
  
  subnet_exists=$(neutron subnet-list | grep $VLAN_NAME |  head -n 1  | awk '{print $4}')
  if [ "$subnet_exists" != "$VLAN_NAME" ]
  then
    execute_command "neutron subnet-create $TENANT_NETWORK_NAME $VLAN_NETWORK --name $VLAN_NAME"
  else
    info "#-----VLAN Network subnet '$VLAN_NETWORK' exists. Skipping"
  fi

  router_exists=$(neutron router-list | grep $TENANT_ROUTER_NAME | head -n 1  |  awk '{print $4}')
  if [ "$router_exists" != "$TENANT_ROUTER_NAME" ]
  then
    execute_command "neutron router-create $TENANT_ROUTER_NAME"
    
    subnet_id=$(neutron net-list | grep $TENANT_NETWORK_NAME | head -n 1 | awk '{print $6}')

    execute_command "neutron router-interface-add $TENANT_ROUTER_NAME $subnet_id"
  else
    info "#----- $TENANT_ROUTER_NAME exists. Skipping"
  fi

  execute_command "ssh heat-admin@$CONTROLLER sudo grep network_vlan_ranges /etc/neutron/plugin.ini"

  ext_net_exists=$(neutron net-list | grep $EXTERNAL_NETWORK_NAME |  head -n 1  | awk '{print $4}')
  if [ "$ext_net_exists" != "$EXTERNAL_NETWORK_NAME" ]
  then
    execute_command "neutron net-create $EXTERNAL_NETWORK_NAME --router:external --provider:network_type vlan --provider:physical_network physext --provider:segmentation_id $EXTERNAL_VLAN"
    execute_command "neutron subnet-create --name $EXTERNAL_SUBNET_NAME --allocation-pool start=$STARTIP,end=$ENDIP --gateway $GATEWAY_IP --disable-dhcp $EXTERNAL_NETWORK_NAME $EXTERNAL_VLAN_NETWORK"  
  else
    info "#----- External network '$EXTERNAL_NETWORK_NAME' exists. Skipping"
  fi


  execute_command "neutron net-list"

  execute_command "neutron router-list"

  # Use external network name
  execute_command "neutron router-gateway-set $TENANT_ROUTER_NAME $EXTERNAL_NETWORK_NAME"

  neutron security-group-list | grep -q $SECURITY_GROUP_NAME
  if [[ "$?" == 0 ]];
  then 
    info "#----- Security group '$SECURITY_GROUP_NAME' exists. Skipping"
  else
    info "### Creating a Security Group ####"
    execute_command "neutron security-group-create $SECURITY_GROUP_NAME"

    # Allow all inbound and outbound ICMP
    execute_command "neutron security-group-rule-create --tenant-id sanity --direction ingress --ethertype IPv4 --protocol icmp --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"
    execute_command "neutron security-group-rule-create --tenant-id sanity --direction egress --ethertype IPv4 --protocol icmp --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"

    # Allow all inbound and outbound TCP
    execute_command "neutron security-group-rule-create --tenant-id sanity --direction ingress --ethertype IPv4 --protocol tcp --port-range-min 1 --port-range-max 65535 --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"
    execute_command "neutron security-group-rule-create --tenant-id sanity --direction egress --ethertype IPv4 --protocol tcp --port-range-min 1 --port-range-max 65535 --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"

    # Allow all inbound and outbound UDP
    execute_command "neutron security-group-rule-create --tenant-id sanity --direction ingress --ethertype IPv4 --protocol udp --port-range-min 1 --port-range-max 65535 --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"
    execute_command "neutron security-group-rule-create --tenant-id sanity --direction egress --ethertype IPv4 --protocol udp --port-range-min 1 --port-range-max 65535 --remote-ip-prefix 0.0.0.0/0 $SECURITY_GROUP_NAME"
  fi
}


setup_glance(){

  info "### Setting up glance"""

  if [ ! -f ./cirros-0.3.3-x86_64-disk.img ]; then
    sleep 5 #HACK: a timing issue exists on some stamps -- 5 seconds seems sufficient to fix it
    execute_command "wget http://download.cirros-cloud.net/0.3.3/cirros-0.3.3-x86_64-disk.img"
  else
    info "#----- Cirros image exists. Skipping"
  fi

  image_exists=$(glance image-list | grep $IMAGE_NAME |  head -n 1  | awk '{print $4}')
  if [ "$image_exists" != "$IMAGE_NAME" ]
  then
     execute_command "glance image-create --name  $IMAGE_NAME --disk-format qcow2 --container-format bare --file cirros-0.3.3-x86_64-disk.img"
  else
    info "#----- Image '$IMAGE_NAME' exists. Skipping"
  fi

  execute_command "glance image-list"
 
  execute_command "nova flavor-list"

  execute_command "nova image-list"
}


setup_nova (){
  info "### Setup Nova"""

  info "creating keypair $KEY_NAME"
  if [ ! -f "$KEY_FILE" ]; then
    nova keypair-add $KEY_NAME  > "$KEY_FILE" 
  else
    info "#----- Key '$KEY_NAME' exists. Skipping"
  fi

  tenant_net_id=$(neutron net-list | grep $TENANT_NETWORK_NAME | head  -n 1  | awk '{print $2}')

  image_id=$(glance image-list | grep $IMAGE_NAME | head -n 1  | awk '{print $2}')

  execute_command "nova boot --security-groups $SECURITY_GROUP_NAME --flavor 2 --key_name $KEY_NAME --image $image_id --nic net-id=$tenant_net_id $NOVA_INSTANCE_NAME"

  info "### Waiting for the instance to be built..."
  instance_status=$(nova list | grep "$NOVA_INSTANCE_NAME" | awk '{print $6}')
  while [ "$instance_status" != "ACTIVE" ]; do
    if [ "$instance_status" != "BUILD" ]; then
      fatal "### Instance status is: ${instance_status}!  Aborting sanity test"
    else
      info "### Instance status is: ${instance_status}.  Sleeping..."
      sleep 10
      instance_status=$(nova list | grep "$NOVA_INSTANCE_NAME" | awk '{print $6}')
    fi
  done
  info "### Instance is built, status is ${instance_status}"

  execute_command "nova list"
}


ping_from_netns(){

  ip=$1
  name_space=$2

  # Find the controller that has the IP set to an interface in the netns
  for controller in $CONTROLLERS
  do
    ssh heat-admin@$controller "sudo /sbin/ip netns exec ${name_space} ip a" | grep -q $ip
    if [[ "$?" == 0 ]]
    then
      break
    fi
  done

  info "### Pinging $ip from netns $name_space on controller $controller"
  execute_command "ssh heat-admin@$controller sudo ip netns exec ${name_space} ping -c 1 -w 5 ${ip}"
  if [[ "$?" == 0 ]]
  then
      info "### Successfully pinged $ip from netns $name_space on controller $controller"
  else
      fatal "### Unable to ping $ip from netns $name_space on controller $controller!  Aborting sanity test"
  fi
}


test_neutron_networking (){

  private_ip=$(nova show $NOVA_INSTANCE_NAME | grep "$TENANT_NETWORK_NAME network" | awk -F\| '{print $3}' | tr -d " ")

  net_ids=$(neutron net-show -F id -F subnets $TENANT_NETWORK_NAME | grep -E 'id|subnets' | awk '{print $4}')
  net_id=$(echo $net_ids | awk '{print $1}')
  subnet_id=$(echo $net_ids | awk '{print $2}')

  # Test pinging the private IP of the instance from the network namespace
  ping_from_netns $private_ip "qdhcp-${net_id}"

  # Allocate a floating IP
  info "Allocating floating IP"
  floating_ip_id=$(neutron floatingip-create $EXTERNAL_NETWORK_NAME | grep " id " | awk '{print $4}')
  floating_ip=$(neutron floatingip-show $floating_ip_id | grep floating_ip_address | awk '{print $4}')

  # Find the port to associate it with
  port_id=$(neutron port-list | grep $subnet_id | grep $private_ip | awk '{print $2}')
  router_id=$(neutron router-show -F id $TENANT_ROUTER_NAME | grep "id" | awk '{print $4}')

  # And finally associate the floating IP with the instance
  execute_command "neutron floatingip-associate $floating_ip_id $port_id"

  sleep 3

  # Test pinging the floating IP of the instance from the virtual router
  # network namespace
  ping_from_netns $floating_ip "qrouter-${router_id}"
}


setup_cinder(){
  info "### Cinder test"""

  execute_command "cinder list"

  vol_exists=$(cinder list | grep $VOLUME_NAME |  head -n 1  | awk '{print $6}')
  if [ "$vol_exists" != "$VOLUME_NAME" ]
  then
    execute_command "cinder create --display-name $VOLUME_NAME 1"
    execute_command "cinder list"

    info "### Waiting for volume status to change to available..."
    volume_status=$(cinder list | grep "$VOLUME_NAME" | awk '{print $4}')
    while [ "$volume_status" != "available" ]; do
      if [ "$volume_status" != "creating" ]; then
        fatal "### Volume status is: ${volume_status}!  Aborting sanity test"
      else
        info "### Volume status is: ${volume_status}.  Sleeping..."
        sleep 5
        volume_status=$(cinder list | grep "$VOLUME_NAME" | awk '{print $4}')
      fi
    done
    info "### Volume is ready, status is ${volume_status}"
  fi

  server_id=$(nova list | grep $NOVA_INSTANCE_NAME| head -n 1 | awk '{print $2}')
  volume_id=$(cinder list | grep $VOLUME_NAME| head -n 1 | awk '{print $2}')

  execute_command "nova volume-attach $server_id $volume_id /dev/vdb"

  info "Volume attached, ssh into instance $NOVA_INSTANCE_NAME and verify"
}


radosgw_test(){
  info "### RadosGW test"""

  execute_command "swift post container"

  execute_command "swift list"

  execute_command "swift upload container keystonerc_admin"

  execute_command "swift list container"
}


radosgw_cleanup(){
  info "### RadosGW test"""

  execute_command "swift delete container keystonerc_admin"

  execute_command "swift list container"

  execute_command "swift delete container"

  execute_command "swift list"
}


setup_project(){
  info "### Setting up new project"

  pro_exists=$(keystone tenant-list | grep $PROJECT_NAME |  head -n 1  | awk '{print $4}')
  if [ "$pro_exists" != "$PROJECT_NAME" ]
  then
    execute_command "keystone tenant-create --name $PROJECT_NAME"
    execute_command "keystone user-create --name $USER_NAME --tenant $PROJECT_NAME --pass $PASSWORD --email $EMAIL"
  else
    info "#Project $PROJECT_NAME exists ---- Skipping"
  fi
}


end(){
  info "#####VALIDATION SUCCESS#####" 
}


info "###Appendix-C Openstack Operations Functional Test ###"

init

if [[ $# > 0 ]]
then
  ### CLEANUP
  arg="$1"
  if [[ "$arg" == "clean" ]]
  then
    info "### CLEANING MODE"  

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
    instance_ids=$(nova list | grep $NOVA_INSTANCE_NAME | awk '{print $2}')
    [[ $instance_ids ]] && echo $instance_ids | xargs -n1 nova delete

    info "### Waiting for the instance to be deleted..."
    num_instances=$(nova list | grep $NOVA_INSTANCE_NAME | wc -l)
    while [ "$num_instances" -gt 0 ]; do
      info "#### ${num_instances} remain.  Sleeping..."
      sleep 3
      num_instances=$(nova list | grep $NOVA_INSTANCE_NAME | wc -l)
    done

    info   "#### Deleting the volumes"
    volume_ids=$(cinder list | grep $VOLUME_NAME | awk '{print $2}')
    [[ $volume_ids ]] && echo $volume_ids | xargs -n1 cinder delete

    info "### Waiting for the volumes to be deleted..."
    num_volumes=$(cinder list | grep $VOLUME_NAME | wc -l)
    while [ "$num_volumes" -gt 0 ]; do
      info "#### ${num_volumes} remain.  Sleeping..."
      sleep 3
      num_volumes=$(cinder list | grep $VOLUME_NAME | wc -l)
    done

    info   "#### Deleting the images"
    image_ids=$(glance image-list | grep $IMAGE_NAME | awk '{print $2}')
    [[ $image_ids ]] && echo $image_ids | xargs -n1 glance image-delete

    info   "#### Deleting the security groups and key_file"
    security_group_ids=$(neutron security-group-list | grep $BASE_SECURITY_GROUP_NAME | awk '{print $2}')
    [[ $security_group_ids ]] && echo $security_group_ids | xargs -n1 neutron security-group-delete

    rm -f $KEY_FILE

    info "### Deleting networks"

    # Pick up all of the subnets in the tenants and the external subnet
    subnet_ids=$(neutron subnet-list | grep -E "$BASE_VLAN_NAME|$EXTERNAL_SUBNET_NAME" | awk '{print $2}')
    for subnet_id in $subnet_ids
    do
      # Pick up all of the tenant routers
      router_ids=$(neutron router-list | grep $BASE_TENANT_ROUTER_NAME | awk '{print $2}')
      for router_id in $router_ids
      do
        neutron router-gateway-clear $router_id
        neutron router-interface-delete $router_id $subnet_id
        neutron router-delete $router_id
      done
    done

    # Now delete the networks
    network_ids=$(neutron net-list | grep -E "$BASE_TENANT_NETWORK_NAME|$EXTERNAL_NETWORK_NAME" | awk '{print $2}')
    for network_id in $network_ids
    do
      neutron net-delete $network_id
    done
  fi
  exit 1
else
  #### EXECUTE

  info "### CREATION MODE"

  set_unique_names
  echo $NAME is the new set

  ###
  setup_project

  ### Setting up Networks

  create_the_networks

  setup_glance

  setup_nova

  test_neutron_networking

  setup_cinder

  #radosgw_test
  #radosgw_cleanup
 
  end

  info "##### Done #####"

  exit
fi
