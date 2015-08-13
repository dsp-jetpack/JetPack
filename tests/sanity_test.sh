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
EXTERNAL_NETWORK_NAME="external_net"
EXTERNAL_SUBNET_NAME="external_sub"
STARTIP="192.168.190.2"
ENDIP="192.168.190.30"
EXTERNAL_VLAN_NETWORK="192.168.190.0/24"
KEY_NAME="key_name"
NOVA_INSTANCE_NAME="cirros_test"
VOLUME_NAME="volume_test"
IMAGE_NAME="cirros"

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

  execute_command "neutron net-create $EXTERNAL_NETWORK_NAME --router:external --shared"
  
  execute_command "neutron subnet-create --name $EXTERNAL_SUBNET_NAME --allocation-pool start=$STARTIP,end=$ENDIP --disable-dhcp $EXTERNAL_NETWORK_NAME $EXTERNAL_VLAN_NETWORK"
  

   execute_command "neutron net-list"
 
   execute_command "neutron router-list"

   ext_net_id=$(neutron net-list | grep $EXTERNAL_NETWORK_NAME | awk '{print $2}')

  #replace the external_net_id
   execute_command "neutron router-gateway-set $TENANT_ROUTER_NAME $ext_net_id"
 
}

setup_glance(){

 info "### Setting up glance"""

 if [ ! -f ./cirros-0.3.3-x86_64-disk.img ]; then
     execute_command "wget http://download.cirros-cloud.net/0.3.3/cirros-0.3.3-x86_64-disk.img"
 fi

 execute_command "glance image-create --name  $IMAGE_NAME --is-public true --disk-format qcow2 --container-format bare --file cirros-0.3.3-x86_64-disk.img"

 execute_command "glance image-list"

 execute_command "nova flavor-list"

 execute_command "nova image-list"
}

setup_nova (){
 info "### Setup Nova"""

 info "creating keypair $KEY_NAME"

 file=MY_KEY.pem
 nova keypair-add $KEY_NAME  > $file 

 tenant_net_id=$(neutron net-list | grep $TENANT_NETWORK_NAME | awk '{print $2}')

 image_id=$(glance image-list | grep $IMAGE_NAME | awk '{print $2}')

 execute_command "nova boot --flavor 2 --key_name $KEY_NAME --image $image_id --nic net-id=$tenant_net_id $NOVA_INSTANCE_NAME"
 
 info "Waiting a min for instance to be built"
 sleep 1m

 execute_command "nova list"

}

setup_cinder(){
 info "### Cinder test"""
 
 execute_command "cinder list"

 execute_command "cinder create --display-name $VOLUME_NAME 1"
 
 execute_command "cinder list"

 server_id=$(nova list | grep $NOVA_INSTANCE_NAME| awk '{print $2}')
 volume_id=$(cinder list | grep $VOLUME_NAME| awk '{print $2}')

 execute_command "nova volume-attach $server_id $volume_id /dev/vdd"

 info "Volume attached, ssh into instance $NOVA_INSTANCE_NAME and verify"

}

end(){
 

   info "#####VALIDATION SUCCESS#####" 
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

end 

info "##### Done #####"

exit