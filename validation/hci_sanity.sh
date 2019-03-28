#!/bin/bash

# Copyright (c) 2015-2018 Dell Inc. or its subsidiaries.
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

# This is a modified version of sanity_test.sh that has been altered
# from sanity_test to:
#   - disable quotas
#   - use CentOS instead of cirros
#   - create more VMs than 1
#   - create 20GB RBD cinder volume per vm
#   - increased resources for cpu, ram, disk of each vm

INI_FILE="hci_sanity.ini"

TestReport="S.No.;Testcases;Status;Error Description\n"


testing_status=0

count_testcases=0

while getopts :s: option
do
    case "${option}"
    in
    s) INI_FILE=$OPTARG;;
    esac
done

get_value() {
    echo $(grep "$1=" ${INI_FILE}  | awk -F= '{print $2}')
}

LETTERS="abcdefghijklmnopqrstuvwxyz"
FLOATING_IP_NETWORK=$(get_value floating_ip_network)
FLOATING_IP_NETWORK_START_IP=$(get_value floating_ip_network_start_ip)
FLOATING_IP_NETWORK_END=$(get_value floating_ip_network_end_ip)
FLOATING_IP_NETWORK_GATEWAY=$(get_value floating_ip_network_gateway)
FLOATING_IP_NETWORK_VLAN=$(get_value floating_ip_network_vlan)
TENANT_NETWORK1=$(get_value tenant_network1)
TENANT_NETWORK2=$(get_value tenant_network2)
TENANT_NETWORK3=$(get_value tenant_network3)
USER_PASSWORD=$(get_value user_password)
USER_EMAIL=$(get_value user_email)
SSH_KEY_NAME=$(get_value ssh_key_name)
NUMBER_INSTANCES=$(get_value number_instances)
NUMBER_VOLUMES_PER_VM=$(get_value number_volumes_per_vm)
VOLUME_SIZE_GB=$(get_value volume_size_gb)
EPHEMERAL_DISK_SIZE_GB=$(get_value ephemeral_disk_size_gb)
INSTANCE_RAM_MB=$(get_value instance_ram_mb)
INSTANCE_VCPUS=$(get_value instance_vcpus)
IMAGE_URL=$(get_value image_url)
TEST_IMAGE_URL=$(get_value test_ceph_img_url)
FLOATING_IP_NETWORK_NAME=$(get_value floating_ip_network_name)
FLOATING_IP_SUBNET_NAME=$(get_value floating_ip_subnet_name)
IMAGE_NAME=$(get_value image_name)
TEST_IMAGE_NAME=$(get_value test_ceph_img_name)
FLAVOR_NAME=$(get_value flavor_name)
BASE_SECURITY_GROUP_NAME=$(get_value base_security_group_name)
BASE_TENANT_NETWORK_NAME=$(get_value base_tenant_network_name)
BASE_TENANT_ROUTER_NAME=$(get_value base_tenant_router_name)
BASE_VLAN_NAME=$(get_value base_vlan_name)
BASE_NOVA_INSTANCE_NAME=$(get_value base_nova_instance_name)
BASE_VOLUME_NAME=$(get_value base_project_name)
BASE_PROJECT_NAME=$(get_value base_project_name)
BASE_USER_NAME=$(get_value base_user_name)
BASE_CONTAINER_NAME=$(get_value base_container_name)
CLEANUP=$(get_value cleanup)

IMAGE_FILE_NAME=$(basename ${IMAGE_URL})
SECURITY_GROUP_NAME="${BASE_SECURITY_GROUP_NAME}"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o KbdInteractiveDevices=no"
tenant_net_index=1
shopt -s nullglob

LOG_FILE=./hcisanity.log
exec > >(sudo tee -a ${LOG_FILE} )
exec 2> >(sudo tee -a ${LOG_FILE} >&2)

# Logging levels
fatal=0
ERROR=1
WARN=2
INFO=3
DEBUG=4

# Default logging level
LOG_LEVEL=${INFO}

# Logging functions
log() { echo -e "$(date '+%F %T'): $@" >&2; }
fatal() { log "fatal: $@" >&2; exit 1; }
error() { [[ ${ERROR} -le ${LOG_LEVEL} ]] && log "ERROR: $@"; }
warn() { [[ ${WARN} -le ${LOG_LEVEL} ]] && log "WARN: $@"; }
info() { [[ ${INFO} -le ${LOG_LEVEL} ]] && log "INFO: $@"; }
debug() { [[ ${DEBUG} -le ${LOG_LEVEL} ]] && log "DEBUG: $@"; }

######## Functions ############
set_admin_scope(){
    info "setting admin scope with: ~/${STACK_NAME}rc."
    source ~/${STACK_NAME}rc
    [[ -n "${OS_TENANT_NAME}" ]] && export OS_PROJECT_NAME=${OS_TENANT_NAME}
    info "### sourcing ~/${STACK_NAME}rc"
}

set_tenant_scope(){
    info "Setting tenant scope."
    export OS_USERNAME=${USER_NAME}
    export OS_PASSWORD=${USER_PASSWORD}
    export OS_TENANT_NAME=${PROJECT_NAME}
    export OS_PROJECT_NAME=${PROJECT_NAME}
}

generate_rc(){
    echo
    echo "+--------------------------------------------------+"
    echo " Generating rc file."
    echo "+--------------------------------------------------+"
    cp ~/${STACK_NAME}rc ${RC_FILE}
    USERNAMEREPL=`grep OS_USERNAME ~/${STACK_NAME}rc`
    PASSWORDREPL=`grep OS_PASSWORD ~/${STACK_NAME}rc`
    PROJECTNAMEREPL=`grep OS_PROJECT_NAME ~/${STACK_NAME}rc`
    TENANTNAMEREPL=`grep OS_TENANT_NAME ~/${STACK_NAME}rc`
    sed -i "s/${USERNAMEREPL}/export OS_USERNAME=${USER_NAME}/g" ${RC_FILE}
    sed -i "s/${PASSWORDREPL}/export OS_PASSWORD=${USER_PASSWORD}/g" ${RC_FILE}
    sed -i "s/${PROJECTNAMEREPL}/export OS_PROJECT_NAME=${PROJECT_NAME}/g" ${RC_FILE}
    grep OS_TENANT_NAME ${RC_FILE} >/dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        sed -i "s/${TENANTNAMEREPL}/export OS_TENANT_NAME=${PROJECT_NAME}/g" ${RC_FILE}
    else
        sed -i "\$ a export OS_TENANT_NAME=${PROJECT_NAME}" ${RC_FILE}
    fi
}

init(){
    info "### Initialization started "
    cd ~
    source ~/stackrc
    [[ -n "${OS_TENANT_NAME}" ]] && export OS_PROJECT_NAME=${OS_TENANT_NAME}
    # Get a list of the IPs of all the controller nodes for later use, as well as
    # the IP for a single controller
    CONTROLLERS=$(openstack server list -c Name -c Networks -f value | grep controller | awk '{print $2}' | tr -d 'cntlplane=')
    CONTROLLER=(${CONTROLLERS})
    # Now switch to point the OpenStack commands at the overcloud
    STACK_NAME=$(openstack stack list -c 'Stack Name' -f value)
    [[ "${STACK_NAME}" ]] ||  \
    fatal "### ${STACK_NAME} is required and could not be found!  Aborting"
    info "### Initialization Done "
}

check_pcs_status(){
    echo
    echo "+--------------------------------------------------+"
    echo " Verifying PCS status and db services."
    echo "+--------------------------------------------------+"
    set_admin_scope
    info "### PCS Status "
    ssh ${SSH_OPTS} heat-admin@${CONTROLLER} 'sudo /usr/sbin/pcs status'
    pcs_status=$(ssh ${SSH_OPTS} heat-admin@${CONTROLLER} 'sudo /usr/sbin/pcs status | grep -i stopped')
    if [[ "${pcs_status}" != "" ]]
    then
        info "### Aborting! due to following failure"
        fatal "$pcs_status"
    fi
    info "###Ensure db and rabbit services are in the active state"
    ssh ${SSH_OPTS} heat-admin@${CONTROLLER} 'sudo ps aux | grep rabbit'
    ssh ${SSH_OPTS} heat-admin@${CONTROLLER} 'ps -ef | grep mysqld'
    ssh ${SSH_OPTS} heat-admin@${CONTROLLER} 'ps -ef | grep mariadb'
}

execute_command(){
    cmd="$1"
    info "Executing: ${cmd}"
    ${cmd}
    if [[ $? -ne 0 ]]; then
    echo "command failed"
    exit 1
    fi
}


set_unique_names(){
    suffix=$1
    PROJECT_NAME=${BASE_PROJECT_NAME}${suffix}
    RC_FILE=~/${PROJECT_NAME}rc
    TENANT_NETWORK_NAME="${BASE_TENANT_NETWORK_NAME}"
    TENANT_ROUTER_NAME="${BASE_TENANT_ROUTER_NAME}${suffix}"
    VLAN_NAME="${BASE_VLAN_NAME}"
    USER_NAME="${BASE_USER_NAME}${suffix}"
    SWIFT_CONTAINER_NAME=${BASE_CONTAINER_NAME}_${suffix}
}


get_unique_names(){
    set_admin_scope
    info "### Getting unique names for creating Resources"
    index=1
    openstack project show ${BASE_PROJECT_NAME}${index} >/dev/null 2>&1
    while [[ $? -eq 0 ]]
    do
        index=$((index+1))
        openstack project show ${BASE_PROJECT_NAME}${index} >/dev/null 2>&1
    done
    set_unique_names ${index}
}


create_tenant_networks(){
    set_tenant_scope
    echo
    echo "+------------------------------------------------------------------------+"
    echo " Creating the Tenant Network ${TENANT_NETWORK_NAME}$2"
    echo "+------------------------------------------------------------------------+"
    net_exists=$(openstack network list -c Name -f value | grep "${TENANT_NETWORK_NAME}$2")
    if [[ "${net_exists}" != "${TENANT_NETWORK_NAME}$2" ]]
    then
        execute_command "openstack network create ${TENANT_NETWORK_NAME}$2"
    else
        info "#----- Tenant network '${TENANT_NETWORK_NAME}$2' exists.-------Skipping"
    fi
    subnet_exists=$(openstack subnet list -c Name -f value | grep "${VLAN_NAME}$2")
    if [[ "${subnet_exists}" != "${VLAN_NAME}$2" ]]
    then
        execute_command "openstack subnet create ${VLAN_NAME}$2 --network ${TENANT_NETWORK_NAME}$2 --subnet-range $1 --dns-nameserver 8.8.8.8"
    else
        info "#-----VLAN Network subnet '$1' exists.--------Skipping"
    fi
}

create_router(){
    set_tenant_scope
    echo
    echo "+--------------------------------------------------+"
    echo " Creating the Router ${TENANT_ROUTER_NAME}"
    echo "+--------------------------------------------------+"
    router_exists=$(openstack router list -c Name -f value | grep "${TENANT_ROUTER_NAME}")
    if [[ "${router_exists}" != "${TENANT_ROUTER_NAME}" ]]
    then
        execute_command "openstack router create ${TENANT_ROUTER_NAME}"
    else
        info "#---- ${TENANT_ROUTER_NAME} exists.------Skipping"
    fi
}

add_router_interface(){
    set_tenant_scope
    echo
    echo "+--------------------------------------------------------------------------------------------+"
    echo " Attaching tenant network interface ${TENANT_NETWORK_NAME}$1 to router ${TENANT_ROUTER_NAME}"
    echo "+--------------------------------------------------------------------------------------------+"
    subnet_id=$(openstack network list | grep ${TENANT_NETWORK_NAME}$1 | head -n 1 | awk '{print $6}')
    execute_command "openstack router add subnet ${TENANT_ROUTER_NAME} ${subnet_id}"
}

create_external_network(){
    set_admin_scope
    echo
    echo "+------------------------------+"
    echo " Creating External network "
    echo "+------------------------------+"
    ext_net_exists=$(openstack network list -c Name -f value | grep "${FLOATING_IP_NETWORK_NAME}")
    if [[ "${ext_net_exists}" != "${FLOATING_IP_NETWORK_NAME}" ]]
    then
        execute_command "openstack network create ${FLOATING_IP_NETWORK_NAME} --external --provider-network-type vlan --provider-physical-network physext --provider-segment ${FLOATING_IP_NETWORK_VLAN}"
        execute_command "openstack subnet create ${FLOATING_IP_SUBNET_NAME} --allocation-pool start=${FLOATING_IP_NETWORK_START_IP},end=${FLOATING_IP_NETWORK_END} --gateway ${FLOATING_IP_NETWORK_GATEWAY} --no-dhcp --network ${FLOATING_IP_NETWORK_NAME} --subnet-range ${FLOATING_IP_NETWORK}"
        info "### Set external gateway interface to tenant router."
        execute_command "openstack router set ${TENANT_ROUTER_NAME} --external-gateway ${FLOATING_IP_NETWORK_NAME}"
    else
        info "#----- External network '${FLOATING_IP_NETWORK_NAME}' exists.--------Skipping"
    fi
}

list_resources(){
    echo
    echo "+-------------------------------+"
    echo " Listing the Created Resources. "
    echo "+-------------------------------+"
    echo
    set_admin_scope
    execute_command "openstack project list"
    echo
    execute_command "openstack user list"
    echo
    set_tenant_scope
    execute_command "openstack router list"
    echo
    execute_command "openstack network list"
    echo
    execute_command "openstack image list"
    echo
    execute_command "openstack server list"
    echo
}  

create_security_group(){
    set_tenant_scope
    echo
    echo "+--------------------------------------------------+"
    echo " Creating Security Group ${SECURITY_GROUP_NAME} "
    echo "+--------------------------------------------------+"
    openstack security group list -c Name -f value | grep -q ${SECURITY_GROUP_NAME}
    if [[ "$?" == 0 ]];
    then
        info "#----- Security group '${SECURITY_GROUP_NAME}' exists.------Skipping"
    else
        info "### Creating a Security Group ####"
        execute_command "openstack security group create ${SECURITY_GROUP_NAME}"
        info "### Adding Rules to Security Group to allow ICMP, TCP and UDP traffic. ####"
        # Allow all inbound and outbound ICMP
        execute_command "openstack security group rule create --ingress --ethertype IPv4 --protocol icmp --remote-ip 0.0.0.0/0 ${SECURITY_GROUP_NAME}"
        execute_command "openstack security group rule create --egress --ethertype IPv4 --protocol icmp --remote-ip 0.0.0.0/0 ${SECURITY_GROUP_NAME}"
        # Allow all inbound and outbound TCP
        execute_command "openstack security group rule create --ingress --ethertype IPv4 --protocol tcp --dst-port 1:65535 --remote-ip 0.0.0.0/0 ${SECURITY_GROUP_NAME}"
        execute_command "openstack security group rule create --egress --ethertype IPv4 --protocol tcp --dst-port 1:65535 --remote-ip 0.0.0.0/0 ${SECURITY_GROUP_NAME}"
        # Allow all inbound and outbound UDP
        execute_command "openstack security group rule create --ingress --ethertype IPv4 --protocol udp --dst-port 1:65535 --remote-ip 0.0.0.0/0 ${SECURITY_GROUP_NAME}"
        execute_command "openstack security group rule create --egress --ethertype IPv4 --protocol udp --dst-port 1:65535 --remote-ip 0.0.0.0/0 ${SECURITY_GROUP_NAME}"
    fi
}


setup_glance(){
    echo
    echo "+--------------------------------------------------+"
    echo " Uploading CentOS image to glance"
    echo "+--------------------------------------------------+"
    set_admin_scope
    if [[ ! -f ./${IMAGE_FILE_NAME} ]]; then
        sleep 5 #HACK: a timing issue exists on some stamps -- 5 seconds seems sufficient to fix it
        execute_command "wget ${IMAGE_URL}"
    else
        info "#----- CentOS image exists.--------Skipping"
    fi
    image_exists=$(openstack image list -c Name -f value | grep -x ${IMAGE_NAME})
    if [[ "${image_exists}" != "${IMAGE_NAME}" ]]
    then
        execute_command "openstack image create --disk-format qcow2 --container-format bare --file ${IMAGE_FILE_NAME} ${IMAGE_NAME} --public"
    else
        info "#----- Image '${IMAGE_NAME}' exists.--------Skipping"
    fi
}

create_instances(){
    echo
    echo "+-------------------------------------------------------------------------------------+"
    echo " Creating Tenant Instances on different networks and hosts to test east-west traffic."
    echo "+-------------------------------------------------------------------------------------+"
    index=1
    image_id=$(openstack image list -f value | grep "${IMAGE_NAME}" | awk 'NR==1{print $1}')
    info "### Initiating build of instances..."
    declare -a instance_names
    set_admin_scope
    hypervisors=$(openstack hypervisor list -c "Hypervisor Hostname" -f value)
    set_tenant_scope
    for hypervisor in ${hypervisors}
    do
        instance_name="${BASE_NOVA_INSTANCE_NAME}_${index}"
        tenant_net_id=$(openstack network list -f value | grep " ${TENANT_NETWORK_NAME}${index} " | awk '{print $1}')
        execute_command "openstack server create --security-group ${SECURITY_GROUP_NAME} --flavor ${FLAVOR_NAME} --key-name ${SSH_KEY_NAME} --image ${image_id} --nic net-id=${tenant_net_id} --availability-zone nova:${hypervisor} ${net1_instance_name} ${instance_name}"
        index=`expr $index + 1`
    done
    sleep 10
    for instance_name in $(openstack server list -c Name -f value); do
        instance_status=$(openstack server show ${instance_name} | grep status | awk '{print $4}')
        while [[ "${instance_status}" != "ACTIVE" ]]; do
        if [[ "${instance_status}" != "BUILD" ]]; then
            error "### Instance status is: ${instance_status}!  Aborting"
        else
            info "### Instance status is: ${instance_status}.  Sleeping..."
            sleep 10
            instance_status=$(openstack server show ${instance_name} | grep status | awk '{print $4}')
        fi
        done
    done
}


setup_nova (){
    echo
    echo "+-------------------------------------------------------------------------------------+"
    echo " Setup Nova (flavor creation, SSH key pair creation and addition)"
    echo "+-------------------------------------------------------------------------------------+"
    openstack flavor show ${FLAVOR_NAME} > /dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        execute_command "openstack flavor create --ram ${INSTANCE_RAM_MB} --vcpus ${INSTANCE_VCPUS} --disk ${EPHEMERAL_DISK_SIZE_GB} ${FLAVOR_NAME}"
    else
        info "#----- Flavor '${FLAVOR_NAME}' exists.-----Skipping"
    fi
    set_tenant_scope
    if [[ ! -f ~/${SSH_KEY_NAME} ]]; then
        info "creating keypair ${SSH_KEY_NAME}"
        ssh-keygen -f ~/${SSH_KEY_NAME} -t rsa -N ""
    else
        info "using existing keypair ${SSH_KEY_NAME}"
    fi
    openstack keypair show ${SSH_KEY_NAME} 1>/dev/null 2>&1
    if [[ $? -ne 0 ]]
    then
        info "loading ${SSH_KEY_NAME} keypair into nova"
        nova keypair-add --pub-key ~/${SSH_KEY_NAME}.pub ${SSH_KEY_NAME}
    else
        info "skipping loading ${SSH_KEY_NAME} keypair into nova"
    fi
}

test_instance_access(){
    ip=$1
    name_space=$2
    ssh_keyname=hcisanity
    info "###Finding the controller that has the IP set to an interface in the netns"
    for controller in $CONTROLLERS
    do
        ssh ${SSH_OPTS} heat-admin@${controller} "sudo /sbin/ip netns exec ${name_space} ip a" | grep -q ${ip}
        if [[ "$?" == 0 ]]
        then
            break
        fi
    done
    execute_command "scp /home/osp_admin/hcisanity heat-admin@${controller}:/home/heat-admin/."
    for instance_ip in $(openstack server list -c Networks -f value | awk -F'=' '{print $2}')
    do
        execute_command "ssh ${SSH_OPTS} heat-admin@${controller} sudo /sbin/ip netns exec ${name_space} ssh -i /home/heat-admin/${ssh_keyname} -o StrictHostKeyChecking=no centos@${ip} 'ping -c 1 -w 5 ${instance_ip}'"
        if [[ "$?" == 0 ]]
        then
            info "### Successfully pinged ${ip}"
        else
            testing_status="Unable to ping ${ip}"
            error "### Unable to ping ${ip}!  "
        fi
    done
}

ping_from_netns(){
    ip=$1
    name_space=$2
    info "### Finding the controller that has the IP set to an interface in the netns"
    for controller in ${CONTROLLERS}
    do
        ssh ${SSH_OPTS} heat-admin@${controller} "sudo /sbin/ip netns exec ${name_space} ip a" | grep -q ${ip}
        if [[ "$?" == 0 ]]
        then
            break
        fi
    done
    info "### Pinging ${ip} from netns ${name_space} on controller ${controller}"
    execute_command "ssh ${SSH_OPTS} heat-admin@${controller} sudo ip netns exec ${name_space} ping -c 1 -w 5 ${ip}"
    if [[ "$?" == 0 ]]
    then
        info "### Successfully pinged ${ip} from netns ${name_space} on controller ${controller}"
    else
        testing_status="Unable to ping ${ip} from netns ${name_space} on controller ${controller}"
        error "### Unable to ping ${ip} from netns ${name_space} on controller ${controller}!  "
    fi
}


ping_floating_ip(){
    ip=$1
    info "### Pinging floating ip ${ip} from director node"
    execute_command "ping -c 1 -w 5 ${ip}"
    if [[ "$?" == 0 ]]
    then
        info "### Successfully pinged floating ip ${ip} from director node"
    else
        testing_status="Unable to ping floating ip ${ip} from director node"
        error "### Unable to ping floating ip ${ip} from director node!  Aborting"
    fi
}

test_internal_connectivity(){
    PRIVATE_NETWORK=$1
    set_tenant_scope
    echo
    echo "+--------------------------------------------------------------------------------------------+"
    echo " Test pinging the private IP of instances from tenant network ${PRIVATE_NETWORK}$2 namespace"
    echo "+--------------------------------------------------------------------------------------------+"
    net_ids=$(openstack network show $1$2 | grep -w -E 'id|subnets' | awk '{print $4}')
    net_id=$(echo ${net_ids} | awk '{print $1}')
    subnet_id=$(echo ${net_ids} | awk '{print $2}')
    testing_status="0"
    for private_ip in $(openstack server list -c Networks -f value | awk -F= '{print $2}')
    do
	    ping_from_netns ${private_ip} "qdhcp-${net_id}"
    done
    count_testcases=`expr ${count_testcases} + 1`
    echo
    if [[ "${testing_status}" == "0" ]]
    then
        TestReport="${TestReport}${count_testcases};Internal Connectivity $1$2;SUCCESS;\n"
        echo "Testing Internal Connectivity $1$2 - SUCCESS"
    else
        TestReport="${TestReport}${count_testcases};Internal Connectivity $1$2;FAIL;${testing_status}\n"
        echo "Testing Internal Connectivity $1$2 - FAIL"
    fi
    echo "-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------"

}

test_east_west_traffic(){
    PRIVATE_NETWORK=$1
    set_tenant_scope
    echo
    echo "+--------------------------------------------------------------------------------------------+"
    echo " East-West traffic between the different tenant Networks."
    echo " Test pinging the private IP of instances from each instance belonging on different networks"
    echo "+--------------------------------------------------------------------------------------------+"
    net_ids=$(openstack network show $1$2 | grep -w -E 'id|subnets' | awk '{print $4}')
    net_id=$(echo ${net_ids} | awk '{print $1}')
    subnet_id=$(echo ${net_ids} | awk '{print $2}')
    testing_status="0"
    for private_ip in $(openstack server list -c Networks -f value | awk -F= '{print $2}')
    do
	    test_instance_access ${private_ip} "qdhcp-${net_id}"
    done
    count_testcases=`expr ${count_testcases} + 1`
    echo
    if [[ "${testing_status}" == "0" ]]
    then
	    TestReport="${TestReport}${count_testcases};East West Traffic;SUCCESS;\n"
	    echo "Testing East West Traffic - SUCCESS"
    else
        TestReport="${TestReport}${count_testcases};East West Traffic;FAIL;${testing_status}\n"
        echo "Testing East West Traffic - FAIL"
    fi
    echo "-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------"

}

test_external_connectivity (){
    set_admin_scope
    echo
    echo "+--------------------------------------------------------------------------------------------+"
    echo " Test External (Floating) Network Connectivity from Director Node."
    echo "+--------------------------------------------------------------------------------------------+"
    router_id=$(openstack router show  tenant_router1 | grep -w "id" | awk '{print $4}')
    set_tenant_scope
    floating_ips=()
    for private_ip in $(openstack server list -c Networks -f value | awk -F= '{print $2}')
    do
        info "### Allocating floating IP"
        floating_ip_id=$(openstack floating ip create public | grep " id " | awk '{print $4}')
        floating_ip=$(openstack floating ip show ${floating_ip_id} | grep floating_ip_address | awk '{print $4}')
        floating_ips+=(${floating_ip})
        # Find the port to associate it with
        set_admin_scope
        port_id=$(openstack port list | grep ${private_ip} | awk -F '|' '{print $2}')
        # And finally associate the floating IP with the instance
        set_tenant_scope
        execute_command "openstack floating ip set --port ${port_id} ${floating_ip}"
    done
    sleep 3
    testing_status="0"
    count_testcases=`expr ${count_testcases} + 1`
    for floating_ip in ${floating_ips[@]}
    do
        ping_floating_ip ${floating_ip}
    done
    echo
    if [[ "${testing_status}" == "0" ]]
    then
        TestReport="${TestReport}${count_testcases};External Connectivity;SUCCESS;\n"
        echo "Testing External Connectivity - SUCCESS"
    else
        TestReport="${TestReport}${count_testcases};External Connectivity;FAIL;${testing_status}\n"
        echo "Testing External Connectivity - FAIL"
    fi
    echo "-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------"
}


setup_project(){
    set_admin_scope
    echo
    echo "+--------------------------------------------------+"
    echo " Setting up new project ${PROJECT_NAME}"
    echo "+--------------------------------------------------+"
    pro_exists=$(openstack project show -c name -f value ${PROJECT_NAME})
    if [[ "${pro_exists}" != "${PROJECT_NAME}" ]]
    then
        execute_command "openstack project create ${PROJECT_NAME}"
        info "### Disabling openstack quotas"
        execute_command "openstack quota set --instances -1 ${PROJECT_NAME}"
        execute_command "openstack quota set --volumes -1 ${PROJECT_NAME}"
        execute_command "openstack quota set --ram -1 ${PROJECT_NAME}"
        execute_command "openstack quota set --gigabytes -1 ${PROJECT_NAME}"
        execute_command "openstack quota set --cores -1 ${PROJECT_NAME}"
    else
        info "### Project ${PROJECT_NAME} exists -----Skipping"
    fi
}

setup_user(){
    set_admin_scope
    echo
    echo "+--------------------------------------------------+"
    echo " Setting up new user ${USER_NAME}"
    echo "+--------------------------------------------------+"
    user_exists=$(openstack user show -c name -f value ${USER_NAME})
    if [[ "${user_exists}" != "${USER_NAME}" ]]
    then
        info "### Creating user ${USER_NAME}"
        execute_command "openstack user create --project ${PROJECT_NAME} --password ${USER_PASSWORD} --email ${USER_EMAIL} ${USER_NAME}"
        info "### Setting user ${USER_NAME} as a member of project ${PROJECT_NAME}"
	    execute_command "openstack role add --project ${PROJECT_NAME} --user ${USER_NAME} _member_"
	    execute_command "openstack role add --project ${PROJECT_NAME} --user ${USER_NAME} admin"
    else
        info "### User ${USER_NAME} exists ---- Skipping"
    fi
}

cleanup(){
    echo "+--------------------------------------------------+"
    echo "|                Starting CLEANUP                  |"
    echo "+--------------------------------------------------+"
    cd ~
    set_admin_scope
    index=1
    openstack project show ${BASE_PROJECT_NAME}${index} >/dev/null 2>&1
    while [ $? -eq 0 ]
    do
        set_unique_names ${index}
        export OS_TENANT_NAME=${PROJECT_NAME}
        export OS_PROJECT_NAME=${PROJECT_NAME}
        export OS_PASSWORD=${USER_PASSWORD}
        export OS_USERNAME=${USER_NAME}
        info "### Starting deletion of ${PROJECT_NAME}"
        info "### Deleting keypair"
        keypair_id=$(openstack keypair list | grep ${SSH_KEY_NAME} | awk '{print $2}')
        info   "keypair id: ${keypair_id}"
        [[ ${keypair_ids} ]] && echo ${keypair_ids} | xargs -n1 openstack keypair delete
        info "### Deleting the floating ips"
        private_ips=$(openstack floating ip list -c "Fixed IP Address" -f value)
        for private_ip in ${private_ips}
        do
            public_ip_id=$(openstack floating ip list | grep ${private_ip} | awk '{print $2}')
	        port_id=$(openstack port list | grep ${private_ip} | awk -F '|' '{print $2}')
	        openstack floating ip unset ${public_ip_id}
            openstack floating ip delete ${public_ip_id}
        done
    info   "### Deleting the instances"
    instance_ids=$(openstack server list -c ID -f value)
    for id in ${instance_ids}
    do
        execute_command "openstack server delete $id"
    done
    info "### Waiting for the instances to be deleted..."
    num_instances=$(openstack server list | grep -v '^$' |wc -l)
    info "num instance: ${num_instances}"
    while [[ "${num_instances}" -gt 0 ]]; do
        info "### ${num_instances} remain.  Sleeping..."
        sleep 3
        num_instances=$(openstack server list | grep -v '^$' |wc -l)
    done
    info "### Deleting the volumes"
    volume_ids=$(openstack volume list -c ID -f value)
    for id in ${volume_ids}
    do
        execute_command "openstack volume delete $id"
    done
    info "### Waiting for the volumes to be deleted..."
    num_volumes=$(openstack volume list | grep -v '^$' |wc -l)
    info "volume ids: ${num_volumes}"
    while [[ "${num_volumes}" -gt 0 ]]; do
        info "### ${num_volumes} remain.  Sleeping..."
        sleep 3
        num_volumes=$(openstack volume list | grep -v '^$' |wc -l)
    done
    set_admin_scope
    info "### Disconnecting the router"
    openstack router remove subnet ${TENANT_ROUTER_NAME} ${VLAN_NAME}${index}
    openstack router remove subnet ${TENANT_ROUTER_NAME} ${VLAN_NAME}$((index+1))
    openstack router remove subnet ${TENANT_ROUTER_NAME} ${VLAN_NAME}$((index+2))
    info "### Deleting the user"
    openstack user show ${USER_NAME} >/dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        execute_command "openstack user delete ${USER_NAME}"
    fi
    info "### Deleting the project"
    openstack project show ${PROJECT_NAME} >/dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        execute_command "openstack project delete ${PROJECT_NAME}"
    fi
    index=$((index+1))
    openstack project show ${BASE_PROJECT_NAME}${index} >/dev/null 2>&1
    done
    set_admin_scope
    info   "### Deleting the security groups"
    security_group_ids=$(openstack security group list | grep ${BASE_SECURITY_GROUP_NAME} | awk '{print $2}')
    [[ ${security_group_ids} ]] && echo ${security_group_ids} | xargs -n1 openstack security group delete
    info   "### Deleting the images"
    image_ids=$(openstack image list -c ID -f value)
    for id in ${image_ids}
    do
        execute_command "openstack image delete $id"
    done
    info "### Deleting the flavor"
    openstack flavor show ${FLAVOR_NAME} > /dev/null 2>&1
    if [[ $? -eq 0 ]]
    then
        execute_command "openstack flavor delete ${FLAVOR_NAME}"
    fi
    info "### Deleting routers"
    router_ids=$(openstack router list | grep ${BASE_TENANT_ROUTER_NAME} | awk '{print $2}')
    for router_id in ${router_ids}
    do
	    execute_command "openstack router unset ${router_id} --external-gateway"
        execute_command "openstack router delete ${router_id}"
    done
    info "### Deleting networks"
    network_ids=$(openstack network list | grep -E "${BASE_TENANT_NETWORK_NAME}|${FLOATING_IP_NETWORK_NAME}" | awk '{print $2}')
    openstack network list | grep ${BASE_TENANT_NETWORK_NAME} | awk -F'|' '{ print $2}' | xargs openstack network delete
    set_admin_scope
    execute_command "openstack network delete ${FLOATING_IP_NETWORK_NAME}"
    info "### Deleting key file"
    rm -f ~/${SSH_KEY_NAME}
    rm -f ~/${SSH_KEY_NAME}.pub
    info "### Deleting ${BASE_PROJECT_NAME}rc files"
    rm -f ~/${BASE_PROJECT_NAME}*rc
    echo
    echo "###########-------------CLEANUP SUCCESSFUL-------------############"
    exit 1
}


test_ceph_status () {
    echo
    echo "+--------------------------------------------------+"
    echo " Testing Ceph status and Health."
    echo "+--------------------------------------------------+"
    CephStatus=$(ssh ${SSH_OPTS} heat-admin@${CONTROLLER} "ceph status")
    testing_status=$(echo "${CephStatus}" | grep "error")
    count_testcases=`expr ${count_testcases} + 1`
    if [[ "${testing_status}" == "" ]]
    then
        ssh ${SSH_OPTS} heat-admin@${CONTROLLER} "ceph status"
        TestReport="${TestReport}${count_testcases};Ceph Status;SUCCESS;\n"
        echo
        echo "Testing Ceph Status - SUCCESS"
    else
        error "### Failed to test ceph status"
        TestReport="${TestReport}${count_testcases};Ceph Status;FAIL;${testing_status}\n"
        echo
        echo "Testing Ceph Status - FAIL"
    fi
    echo "-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------"
}

test_ceph_integration_with_glance(){
    set_admin_scope
    echo
    echo "+--------------------------------------------------+"
    echo " Testing Ceph integration with Glance."
    echo "+--------------------------------------------------+"
    info "### Downloading the test image"
    execute_command "wget ${TEST_IMAGE_URL}"
    info "### Converting test image to RAW format"
    image_name=$(echo ${TEST_IMAGE_URL} | awk -F/ '{print $NF}')
    raw_image_name="${image_name::-4}.raw"
    execute_command "qemu-img convert ${image_name} ${raw_image_name}"
    info "### Uploading test image to Glance"
    image_exists=$(openstack image list -c Name -f value | grep -x ${TEST_IMAGE_NAME})
    if [[ "${image_exists}" != "${TEST_IMAGE_NAME}" ]]
    then
        execute_command "openstack image create --file ${raw_image_name} --container-format bare --disk-format raw --public ${TEST_IMAGE_NAME}"
    fi
    info "### Verifying test image exists in Glance"
    execute_command "openstack image list"
    image_id=$(openstack image list | grep ${TEST_IMAGE_NAME} | awk '{print $2}')
    info "### Verifying test image exists in Ceph"
    Check_in_Ceph=$(ssh ${SSH_OPTS} heat-admin@${CONTROLLER} "rbd -p images ls | grep ${image_id}")
    count_testcases=`expr ${count_testcases} + 1`
    echo
    if [[ "${image_id}" != "" ]]
    then
        if [[ ${Check_in_Ceph}  == ${image_id} ]]
        then
            echo "$Check_in_Ceph"
            info "### Successfully verified that test image exist in Ceph"
            TestReport="${TestReport}${count_testcases};Ceph Integration with Glance;SUCCESS;\n"
            echo
            echo "Testing Ceph Integration with Glance - SUCCESS"
        else
            error "### Failed to verify that test image exist in Ceph"
            testing_status="Image \"${TEST_IMAGE_NAME}\" does not exists in Ceph."
            TestReport="${TestReport}${count_testcases};Ceph Integration with Glance;FAIL;${testing_status}\n"
            echo
            echo "Testing Ceph Integration with Glance - FAIL"
        fi
    fi
    echo "-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------"
}

test_ceph_integration_with_cinder(){
    echo
    echo "+--------------------------------------------------+"
    echo " Testing Ceph integration with Cinder."
    echo "+--------------------------------------------------+"
    info "### Creating test volume"
    set_tenant_scope
    execute_command "openstack volume create --size 10 testvol"
    info "### Verifying test volume exist in Cinder"
    execute_command "openstack volume list"
    vol_id=$(openstack volume list | grep testvol | awk '{print $2}')
    if [[ "${vol_id}" != "" ]]
    then
        info "### Successfully verified that test volume exist in Cinder"
    else
        error "### Failed to verify the test volume in Cinder"
    fi
    info "### Verifying test volume exist in Ceph "
    Check_Vol_in_Ceph=$(ssh ${SSH_OPTS} heat-admin@${CONTROLLER} "rbd -p volumes ls | grep ${vol_id}")
    Check_Vol_in_Ceph=$(echo ${Check_Vol_in_Ceph} | cut -c 8-)
    count_testcases=`expr ${count_testcases} + 1`
    echo
    if [[ "${vol_id}" != "" ]]
    then
        if [[ "${Check_Vol_in_Ceph}" == "${vol_id}" ]]
        then
            info "Executing : rbd -p volumes ls | grep ${vol_id}"
            ssh ${SSH_OPTS} heat-admin@${CONTROLLER} "rbd -p volumes ls | grep ${vol_id}"
            echo
            info "### Successfully verified that test volume exist in Ceph "
            TestReport="${TestReport}${count_testcases};Ceph Integration with Cinder;SUCCESS;\n"
            echo
            echo "Testing Ceph Integration with Cinder - SUCCESS"
        else
            error "### Failed to verify that test volume exists in Ceph "
            testing_status="\"testvol\"-${vol_id} does not exists in Ceph"
            TestReport="${TestReport}${count_testcases};Ceph Integration with Cinder;FAIL;${testing_status}\n"
            echo
            echo "Testing Ceph Integration with Cinder - FAIL"
        fi
    else
        testing_status="\"testvol\" does not exists in Cinder"
        TestReport="${TestReport}${count_testcases};Ceph Integration with Cinder;FAIL;${testing_status}\n"
        echo
        echo "Testing Ceph Integration with Cinder - FAIL"
    fi
    echo "-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------"
}

test_ceph_integration_with_nova_from_image(){
    echo
    echo "+--------------------------------------------------------+"
    echo " Testing Ceph integration with Nova booted from Image."
    echo "+--------------------------------------------------------+"
    set_admin_scope
    tenant_net_id=$(openstack network list -f value | grep " ${TENANT_NETWORK_NAME}1 " | awk '{print $1}')
    set_tenant_scope
    execute_command "openstack server create --flavor ${FLAVOR_NAME} --image ${TEST_IMAGE_NAME} --nic net-id=${tenant_net_id} cephvm"
    sleep 10
    execute_command "openstack server list"
    instance_id=$(openstack server list | grep cephvm | awk '{print $2}')
    if [[ "$instance_id" != "" ]]
    then
        info "### Succesfully checked the existance of VM in Nova"
    else
        error "### Failed to check the existance of VM in Nova"
    fi
    ephemeral_volume_id=$(ssh ${SSH_OPTS} heat-admin@${CONTROLLER} "rbd -p vms ls | grep $instance_id")
    ephemeral_volume_id=${ephemeral_volume_id::-5}
    count_testcases=`expr ${count_testcases} + 1`
    info "### Verifying ephemeral volume of test VM exists in Ceph"
    if [[ "$instance_id" != "" ]]
    then
        if [[ "${ephemeral_volume_id}"  == "${instance_id}" ]]
        then
            ssh ${SSH_OPTS} heat-admin@${CONTROLLER} "rbd -p vms ls | grep $instance_id"
            echo
            info "Successfully Verified ephemeral volume of test VM exists in Ceph"
            TestReport="${TestReport}${count_testcases};Ceph Integration with Nova Booted from Image;SUCCESS;\n"
            echo
            echo "Testing Ceph Integration with Nova Booted from Image - SUCCESS"
        else
            error "Failed to Verifiy ephemeral volume of test VM exists in Ceph"
            testing_status="Ephemeral vol-\"${instance_id}\" does not exists."
            TestReport="${TestReport}${count_testcases};Ceph Integration with Nova Booted from Image;FAIL;${testing_status}\n"
            echo
            echo "Testing Ceph Integration with Nova Booted from Image - FAIL"
        fi
    else
    testing_status="VM creation failed in Nova."
    TestReport="${TestReport}${count_testcases};Ceph Integration with Nova Booted from Image;FAIL;${testing_status}\n"
    echo
    echo "Testing Ceph Integration with Nova Booted from Image - FAIL"
    fi
    echo "-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------"
}

test_ceph_integration_with_nova_booted_from_volume(){
    echo
    echo "+----------------------------------------------------------+"
    echo " Testing Ceph integration with Nova booted from Volume."
    echo "+----------------------------------------------------------+"
    set_tenant_scope
    execute_command "openstack volume create --image ${TEST_IMAGE_NAME}  --size 20 bootable_vol"
    execute_command "openstack volume list"
    vol_id=$(openstack volume list | grep bootable_vol | awk '{print $2}')
    if [[ "$vol_id" != "" ]]
    then
        info "### Successfully checked that the volume exists in Cinder"
    else
        info "### Failed to check the test volume in Cinder"
    fi
    info "### Verifying bootable_vol volume exists in Ceph"
    Check_Vol_in_Ceph=$(ssh ${SSH_OPTS} heat-admin@${CONTROLLER} "rbd -p volumes ls | grep $vol_id")
    Check_Vol_in_Ceph=$(echo "$Check_Vol_in_Ceph" | grep _disk)
    if [[ "$Check_Vol_in_Ceph" != "" ]]
    then
        Check_Vol_in_Ceph=$(echo ${Check_Vol_in_Ceph} | cut -c 8-)
        if [[ ${Check_Vol_in_Ceph}  == ${vol_id} ]]
        then
            echo "$Check_Vol_in_Ceph"
            echo
            info "### Successfully checked that the volume exists in Ceph"
        else
            info "### Failed to check the volume in Ceph"
        fi
    fi
    set_admin_scope
    tenant_net_id=$(openstack network list -f value | grep " ${TENANT_NETWORK_NAME}1 " | awk '{print $1}')
    set_tenant_scope
    execute_command "openstack server create --flavor ${FLAVOR_NAME} --volume bootable_vol --nic net-id=${tenant_net_id} cephvm2"
    instance_status=$(openstack server list | grep cephvm2 | awk '{print $6}')
    instance_id=$(openstack server list | grep cephvm2 | awk '{print $2}')
    sleep 10
    execute_command "openstack server list"
    info "### Successfully Checked that the VM is running"
    ephemeral_volume_id=$(ssh ${SSH_OPTS} heat-admin@${CONTROLLER} "rbd -p vms ls | grep $instance_id")
    count_testcases=`expr ${count_testcases} + 1`
    info "### Verfying absence of instance in Ceph, because we have booted it from a volume"
    if [[ "$ephemeral_volume_id"  == "" ]]
    then
        ssh ${SSH_OPTS} heat-admin@${CONTROLLER} "rbd -p vms ls | grep $instance_id"
        info "Executing : rbd -p vms ls | grep $instance_id"
        info "### Successfully verified that there is no instance id $instance_id  in Ceph for that VM, because we have booted it from a volume"
        TestReport="${TestReport}${count_testcases};Ceph Integration with Nova Booted from Volume;SUCCESS;\n"
        echo
        echo "Testing Ceph Integration with Nova Booted from Volume - SUCCESS"
    else
        info "### Failed because there is ephemeral volume in Ceph for that VM"
        testing_status="There is ephemeral volume in Ceph."
        TestReport="${TestReport}${count_testcases};Ceph Integration with Nova Booted from Volume;FAIL;${testing_status}\n"
        echo
        echo "Testing Ceph Integration with Nova Booted from Volume - FAIL"
    fi
    echo "-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------X-----------"
}

init

if [[ "$1" == "clean" ]]
then
    cleanup
fi
  
echo
echo "+--------------------------------------------------+"
echo "|           Starting Sanity Testing                |"
echo "+--------------------------------------------------+"
echo

check_pcs_status

info "### CREATION MODE"

get_unique_names
echo
generate_rc
echo
setup_project
echo
setup_user
echo
create_tenant_networks ${TENANT_NETWORK1} ${tenant_net_index}
echo
create_tenant_networks ${TENANT_NETWORK2} $((tenant_net_index+1))
echo
create_tenant_networks ${TENANT_NETWORK3} $((tenant_net_index+2))
echo
create_router
echo
add_router_interface ${tenant_net_index}
echo
add_router_interface $((tenant_net_index+1))
echo
add_router_interface $((tenant_net_index+2))
echo
create_external_network
echo
create_security_group
echo
setup_glance
echo
setup_nova
echo
create_instances
echo
list_resources

echo
echo "+--------------------------------------------------+"
echo "|         Executing Openstack Test cases           |"
echo "+--------------------------------------------------+"
echo

test_internal_connectivity ${TENANT_NETWORK_NAME} ${tenant_net_index}
echo
test_internal_connectivity ${TENANT_NETWORK_NAME} $((tenant_net_index+1))
echo
test_internal_connectivity ${TENANT_NETWORK_NAME} $((tenant_net_index+2))
echo
test_east_west_traffic ${TENANT_NETWORK_NAME} $((tenant_net_index+1))
echo
test_external_connectivity
echo

echo
echo "+--------------------------------------------------+"
echo "|           Executing Ceph Test cases              |"
echo "+--------------------------------------------------+"


test_ceph_status
echo
test_ceph_integration_with_glance
echo
test_ceph_integration_with_cinder
echo
test_ceph_integration_with_nova_from_image
echo
test_ceph_integration_with_nova_booted_from_volume
echo

echo
echo "+--------------------------------------------------+"
echo "|                  FINAL REPORT                    |"
echo "+--------------------------------------------------+"


DisplayReport=".TS\ntab(;) allbox;\n"
counter=2
while [[ ${counter} -le ${count_testcases} ]]
do
    DisplayReport="${DisplayReport}l l l l\n"
    counter=`expr ${counter} + 1`
done

DisplayReport="${DisplayReport}l l l l.\n${TestReport}\n.TE"
del_lines=`expr 66 - 2 \* ${count_testcases} - 3`
echo -e "${DisplayReport}" | tbl | nroff | head -n -${del_lines} 2> /dev/null

echo
echo "----------------##### SANITY TESTING SUCCESSFULLY COMPLETED #####----------------"
echo


### CLEANUP
if [[ "$CLEANUP" == "true" ]]
then
    cleanup
fi

exit
