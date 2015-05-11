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
EXTERNAL_SUBNET_NAME="external_sub"
STARTIP="192.168.190.2"
ENDIP="192.168.190.30"
EXTERNAL_VLAN_NETWORK="192.168.190.0/24"
KEY_NAME="key_name"
NOVA_INSTANCE_NAME="cirros_test"
VOLUME_NAME="volume_test"

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

execute_command(){
        cmd="$1"

        info "Executing: $cmd"

        $cmd
        if [ $? -ne 0 ]; then
            echo "command failed"
	    exit 1
	fi
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
  
  execute_command "neutron net-create $TENANT_NETWORK_NAME"
  
  execute_command "neutron subnet-create $TENANT_NETWORK_NAME $VLAN_NETWORK --name $VLAN_NAME"
  
  execute_command "neutron router-create $TENANT_ROUTER_NAME"
  
  execute_command "neutron net-list"
  
  #get the subnet_id 

  subnet_id=$(neutron net-list | grep tenant_net | awk '{print $6}')

  execute_command "neutron router-interface-add $TENANT_ROUTER_NAME $subnet_id"
  
  execute_command "grep network_vlan_ranges /etc/neutron/plugin.ini"

  execute_command "neutron net-create $EXTERNAL_NETWORK_NAME --router:external True"
  
  execute_command "neutron subnet-create --name $EXTERNAL_SUBNET_NAME --allocation-pool start=$STARTIP,end=$ENDIP --disable-dhcp $EXTERNAL_NETWORK_NAME $EXTERNAL_VLAN_NETWORK"
  

   execute_command "neutron net-list"
 
   execute_command "neutron router-list"

   ext_net_id=$(neutron net-list | grep $EXTERNAL_NETWORK_NAME | awk '{print $2}')

  #replace the external_net_id
   execute_command "neutron router-gateway-set $TENANT_ROUTER_NAME $ext_net_id"
 
}

setup_glance(){

 info "### Setting up glance"""

 execute_command "wget http://download.cirros-cloud.net/0.3.3/cirros-0.3.3-x86_64-disk.img"

 execute_command "glance image-create --name "cirros image" --is-public true --disk-format qcow2 --container-format bare --file cirros-0.3.3-x86_64-disk.img"

 execute_command "glance image-list"

 execute_command "nova flavor-list"

 execute_command "nova image-list"
}

setup_nova (){
 info "### Setup Nova"""

 $file = "MY_KEY.pem"
 echo "nova keypair-add $KEY_NAME " > $file 

 tenant_net_id=$(neutron net-list | grep $TENANT_NETWORK_NAME | awk '{print $2}')

 image_id=$(glance image-list | grep cirros| awk '{print $2}')

 execute_command "nova boot --flavor 2 --key_name $KEY_NAME --image $image_id --nic net-id=$tenant_net_id $NOVA_INSTANCE_NAME"

 execute_command "nova list"

}

setup_cinder(){
 info "### Cinder test"""
 
 execute_command "cinder list"

 execute_command "cinder create --display-name $VOLUME_NAME 1"
 
 execute_command "cinder list"

 server_id=$(nova list | grep $NOVA_INSTANCE_NAME| awk '{print $2}')
 volume_id=$(cinder list | grep $VOLUME_NAME| awk '{print $2}')

 execute_command "nova volume-attach $server_id $volume_id \\\\dev\\vdb"

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

#setup_glance

#setup_nova

setup_cinder


info "##### Done #####"

exit
