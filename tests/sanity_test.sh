#!/bin/bash
#
# OpenStack - A set of software tools for building and managing cloud
# computing platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.
#
#exit on failure
#set -e 

#Variables
TENANT_NETWORK_NAME="tenant_net"
TENANT_ROUTER_NAME="tenant_201_router"
VLAN_NETWORK="192.168.201.0/24"
VLAN_NAME="tenant_201"
EXTERNAL_NETWORK_NAME="nova"
EXTERNAL_SUBNET_NAME="external_sub"
STARTIP="192.168.190.2"
ENDIP="192.168.190.30"
EXTERNAL_VLAN_NETWORK="192.168.190.0/24"
GATEWAY_IP=192.168.190.254
KEY_NAME="key_name"
NOVA_INSTANCE_NAME="cirros_test"
VOLUME_NAME="volume_test"
IMAGE_NAME="cirros"
PROJECT_NAME="sanity"
USER_NAME="sanity"
PASSWORD="cr0wBar!"
EMAIL="ce-cloud@dell.com"

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
  source overcloudrc
  info "### PCS Status "
  pcs status
  pcs status | grep -i stopped


  info "###Ensure db and rabbit services are in the active state"
  execute_command "openstack-service status"
  ps aux | grep rabbit
  ps -ef | grep mysqld
  ps -ef | grep mariadb

  info "### Verify OpenStack services are running."
  execute_command "nova-manage service list"
  execute_command "cinder-manage service list"
  execute_command "systemctl status openstack-keystone"
  execute_command "systemctl status openstack-glance-api"
  execute_command "systemctl status openstack-glance-registry"
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


check_service(){
  SERVICE="$1"

  if [ "'systemctl is-active $SERVICE'" != "active" ]
  then
    echo "$SERVICE wasnt running so attempting restart"
    systemctl restart $SERVICE
    systemctl status $SERVICE 
    systemctl enable $SERVICE
  fi
  echo "$SERVICE is currently running"
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
     EXTERNAL_NETWORK_NAME="$EXTERNAL_NETWORK_NAME$NAME"
     EXTERNAL_SUBNET_NAME="$EXTERNAL_SUBNET_NAME$NAME"
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
    execute_command "neutron net-create $TENANT_NETWORK_NAME"
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

  execute_command "grep network_vlan_ranges /etc/neutron/plugin.ini"

  ext_net_exists=$(neutron net-list | grep $EXTERNAL_NETWORK_NAME |  head -n 1  | awk '{print $4}')
  if [ "$ext_net_exists" != "$EXTERNAL_NETWORK_NAME" ]
  then
    execute_command "neutron net-create $EXTERNAL_NETWORK_NAME --router:external --shared"
    execute_command "neutron subnet-create --name $EXTERNAL_SUBNET_NAME --allocation-pool start=$STARTIP,end=$ENDIP --gateway $GATEWAY_IP --disable-dhcp $EXTERNAL_NETWORK_NAME $EXTERNAL_VLAN_NETWORK"  
  else
    info "#----- External network '$EXTERNAL_NETWORK_NAME' exists. Skipping"
  fi


  execute_command "neutron net-list"

  execute_command "neutron router-list"

  # Use external network name
  execute_command "neutron router-gateway-set $TENANT_ROUTER_NAME $EXTERNAL_NETWORK_NAME"
}


setup_glance(){

  info "### Setting up glance"""

  if [ ! -f ./cirros-0.3.3-x86_64-disk.img ]; then
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
  if [ ! -f ./MY_KEY.pem ]; then
    file=MY_KEY.pem
    nova keypair-add $KEY_NAME  > $file 
  else
    info "#----- Key '$KEY_NAME' exists. Skipping"
  fi

  tenant_net_id=$(neutron net-list | grep $TENANT_NETWORK_NAME | head  -n 1  | awk '{print $2}')

  image_id=$(glance image-list | grep $IMAGE_NAME | head -n 1  | awk '{print $2}')

  execute_command "nova boot --flavor 2 --key_name $KEY_NAME --image $image_id --nic net-id=$tenant_net_id $NOVA_INSTANCE_NAME"

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


if [[ $# > 0 ]]
then
  ### CLEANUP
  arg="$1"
  if [[ "$arg" == "clean" ]]
  then
    info "### CLEANING MODE"  

    info "### DELETING NETWORKS"
    cmd=$(neutron subnet-list | awk '{print $2}' | grep -v ^ID | grep -v ^$)
    for subnet in $cmd
    do
      if [ "$subnet" != "id" ]
      then
        echo subet_id=$subnet 

        cmd=$(neutron router-list | awk '{print $2}' | grep -v ^ID | grep -v ^$)
        for router in $cmd
        do
          if [ "$router" != "id" ]
          then
            echo router_id=$router 
            neutron router-gateway-clear $router
            neutron router-interface-delete $router $subnet
            neutron router-delete $router
          fi
        done
        neutron subnet-delete $subnet
      fi
    done

    #now delete the networks
    cmd=$(neutron net-list | awk '{print $2}' | grep -v ^ID | grep -v ^$)
    for V in $cmd
    do
      echo $V ;
      neutron net-delete $V ;
    done

    info   "#### Deleting the images"
    glance image-list | awk '$2 && $2 != "ID" {print $2}' | xargs -n1 glance image-delete

    info   "#### Deleting the instances"
    nova list | awk '$2 && $2 != "ID" {print $2}' | xargs -n1 nova delete
 
    info "### Waiting for the instances to be deleted..."
    num_instances=$(nova list | awk '$2 && $2 != "ID" {print $2}'|wc -l)
    while [ "$num_instances" -gt 0 ]; do
      info "#### ${num_instances} remain.  Sleeping..."
      sleep 3
      num_instances=$(nova list | awk '$2 && $2 != "ID" {print $2}'|wc -l)
    done

    info   "#### Deleting the volumes"
    cinder list | awk '$2 && $2 != "ID" {print $2}' | xargs -n1 cinder delete

    info "### Waiting for the volumes to be deleted..."
    num_volumes=$(cinder list | awk '$2 && $2 != "ID" {print $2}'|wc -l)
    while [ "$num_volumes" -gt 0 ]; do
      info "#### ${num_volumes} remain.  Sleeping..."
      sleep 3
      num_volumes=$(cinder list | awk '$2 && $2 != "ID" {print $2}'|wc -l)
    done
  fi
  exit 1
else
  #### EXECUTE

  info "### CREATION MODE"
  init

  set_unique_names
  echo $NAME is the new set

  ###
  setup_project

  ### Setting up Networks

  create_the_networks


  ##

  setup_glance

  setup_nova

  setup_cinder

  #radosgw_test
  #radosgw_cleanup
 
  end

  info "##### Done #####"

  exit
fi
