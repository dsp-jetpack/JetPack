#!/bin/bash
# Copyright 2014, Dell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Rajini Ram
# Version: 0.1
#
#exit on failure
#set -e 

#Variables
TENANT_NETWORK_NAME="tenant_net"
TENANT_ROUTER_NAME="tenant_201_router"
VLAN_NETWORK="192.168.201.0/24"
VLAN_NAME="tenant_201"
EXTERNAL_NETWORK_NAME="external_net"
$EXTERNAL_SUBNET_NAME="external_sub"
STARTIP="192.168.190.2"
ENDIP=192.168.190.30
EXTERNAL_VLAN_NETWORK="192.168.190.0/24"

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

init(){
   info "Random init stuff "
   cd ~
   source keystonerc_admin
   pcs status
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

create_the_networks(){
  info "### Creating the Networks ####"
  
  neutron net-create $TENANT_NETWORK_NAME
  
  neutron subnet-create $TENANT_NETWORK_NAME $VLAN_NETWORK --name $VLAN_NAME
  
  neutron router-create $TENANT_ROUTER_NAME
  
  neutron net-list
  
  #get the subnet_id 

  neutron router-interface-add tenant_router $subnet_id
  
  grep network_vlan_ranges /etc/neutron/plugin.ini

  neutron net-create $EXTERNAL_NETWORK_NAME --router:external True --shared --provider:network_type local --provider:physical_network physext
  
  neutron subnet-create --name $EXTERNAL_SUBNET_NAME --allocation-pool start=$START_IP,end=$END_IP --disable-dhcp $EXTERNAL_NETWORK_NAME $EXTERNAL_VLAN_NETWORK
  

  neutron net-list
 
  neutron router-list

  #replace the external_net_id
  neutron router-gateway-set $TENANT_ROUTER_NAME $external_net_id
 
}

setup_glance(){

 info "### Setting up glance"""

 wget http://download.cirros-cloud.net/0.3.3/cirros-0.3.3-x86_64-disk.img

 glance image-create --name "cirros image" --is-public true --disk-format qcow2 --container-format bare --file cirros-0.3.3-x86_64-disk.img

 glance image-list

 nova flavor-list

 nova image-list
}

setup_nova (){
 info "### SEtup Nova"""

 nova keypair-add $KEY_NAME > MY_KEY.pem

 nova boot --flavor 2 --key_name $KEY_NAME --image $image_id --nic net-id=$net_id cirros-test

 nova list

}

setup_cinder(){
 info "### Cinder test"""
 
 cinder list

 cinder create --display-name volume_test 1
 
 cinder list
 
 nova volume-attach $server_id $volume_id  $device

}

end(){
 
   info "#####VALIDATION#####" 
}


info "###Appendix-C Openstack Operations Functional Test ###"

####

init

### Setting up Networks

create_the_networks


##

setup_glance

setup_nova

setup_cinder


info "##### Done #####"

exit
