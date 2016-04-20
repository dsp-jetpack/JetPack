#!/bin/bash 

IDRAC_USER=$1
IDRAC_PASS=$2
 
if [ $# -le 1 ]
then
  echo "Usage: $0 idrac_user idrac_pass"
  echo "Please provide the idrac user and password."
  exit -1
fi

############
# This script should be run from the director node as the director's admin user. 
# This script assumes the update_ssh_config.py is present and has not been modified.
########### 
source ~/stackrc
~/pilot/update_ssh_config.py
~/pilot/identify_nodes.py > ~/undercloud_nodes.txt
FIRST_CONTROLLER_NODE=`cat ~/.ssh/config | awk '/cntl0/ {print $2}'`
CONTROLLER_NODES=`cat ~/.ssh/config | awk '/cntl/ {print $2}'`
FIRST_COMPUTE_NODE=`cat ~/.ssh/config | awk '/nova0/ {print $2}'`
COMPUTE_NODES=`cat ~/.ssh/config | awk '/nova/ {print $2}'`
COMPUTE_NOVA_NAMES=`nova list | awk '/compute/ {print $4}'`
OVERCLOUD_NAME=`ssh $FIRST_COMPUTE_NODE "sudo crm_node -n | cut -d\- -f1"`
OVERCLOUDRC_NAME=${OVERCLOUD_NAME}rc

############
# Stop and disable openstack-service and libvirtd on all Compute nodes
############
echo ""
echo "INFO: Stopping and disabling libvirtd and openstack services on all compute nodes."

for compute_node in $COMPUTE_NODES
do
  ssh $compute_node "sudo openstack-service stop"
  ssh $compute_node "sudo openstack-service disable"
  ssh $compute_node "sudo systemctl stop libvirtd"
  ssh $compute_node "sudo systemctl disable libvirtd"
done

############
# Create auth_key on first compute node 
############
echo ""
echo "INFO: Create auth_key on compute_node $FIRST_COMPUTE_NODE."
ssh $FIRST_COMPUTE_NODE "sudo mkdir -p /etc/pacemaker"
ssh $FIRST_COMPUTE_NODE "sudo dd if=/dev/urandom of=/etc/pacemaker/authkey bs=4096 count=1"
ssh $FIRST_COMPUTE_NODE "sudo cp /etc/pacemaker/authkey ~heat-admin/"
ssh $FIRST_COMPUTE_NODE "sudo chown heat-admin:heat-admin ~heat-admin/authkey"

############
# Copy authkey to remaining controller nodes and compute nodes 
############
echo ""
echo "INFO: Distribute auth_key to all controller and compute nodes."

scp $FIRST_COMPUTE_NODE:~/authkey ~/authkey

for node in $CONTROLLER_NODES $COMPUTE_NODES
do
  scp ~/authkey $node:~/authkey
  ssh $node "sudo mkdir -p /etc/pacemaker"
  ssh $node "sudo mv ~heat-admin/authkey /etc/pacemaker/"
  ssh $node "sudo chown root:root /etc/pacemaker/authkey"
done

############
# Enable and start pacemaker remote on compute nodes 
############
echo ""
echo "INFO: Enable and start pacemaker_remote service on all compute nodes."

for compute_node in $COMPUTE_NODES
do
  ssh $compute_node "sudo systemctl enable pacemaker_remote" 
  ssh $compute_node "sudo systemctl start pacemaker_remote" 
done
 
############
# Create a NovaEvacuate active/passive resource using the overcloudrc file 
# to provide the auth_url, username, tenant and password values
############
echo ""
echo "INFO: Create a NovaEvacuate active/passive resource using the overcloudrc file to provide the auth_url, username, tenant and password values."

source ~/$OVERCLOUDRC_NAME
ssh $FIRST_CONTROLLER_NODE "sudo pcs resource create nova-evacuate ocf:openstack:NovaEvacuate auth_url=$OS_AUTH_URL username=$OS_USERNAME password=$OS_PASSWORD tenant_name=$OS_TENANT_NAME"

############
# Confirm that nova-evacuate is started after the floating IP resources, and the Image Service (glance), 
# OpenStack Networking (neutron), Compute (nova) services
############
echo ""
echo "INFO: Confirm that nova-evacuate is started after the floating IP resources and the glance, neutron and nova services."

IPS=`ssh $FIRST_CONTROLLER_NODE "sudo pcs status | grep IP " | awk '{ print $1 }'`
for ip in $IPS; do ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint order start $ip then nova-evacuate"; done
for res in openstack-glance-api-clone neutron-metadata-agent-clone openstack-nova-conductor-clone; do ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint order start $res then nova-evacuate require-all=false"; done

############
# Disable all OpenStack resources across the control plane.
############
echo ""
echo "INFO: Disable all OpenStack resources across the control plane."

ssh $FIRST_CONTROLLER_NODE "sudo pcs resource disable openstack-keystone --wait=1000s"

############
# Create a list of the current controllers using cibadmin data.
# Use this list to tag these nodes as controllers with the osprole=controller property.
############
echo ""
echo "INFO: Create a list of the current controllers using cibadmin data and these nodes as controllers with the osprole=controller property."

controllers=`ssh $FIRST_CONTROLLER_NODE "sudo cibadmin -Q -o nodes | grep uname" | sed s/.*uname..// | awk -F\" '{print $1}'`
for controller in ${controllers}; do ssh $FIRST_CONTROLLER_NODE "sudo pcs property set --node ${controller} osprole=controller"; done

############
# Build a list of stonith devices already present in the environment.
# Tag the control plane services to make sure they only run on the controllers identified above, 
# skipping any stonith devices listed.
############
echo ""
echo "INFO: Build a list of stonith devices already present in the environment and tag the control plane services to make sure they only run on the controllers."

stonithdevs=`ssh $FIRST_CONTROLLER_NODE "sudo pcs stonith "| awk '{print $1}'`
if [[ -z "$stonithdevs" ]]; then
  echo "ERROR: No stonith devices found, please ensure fencing is enabled."
  exit -1
fi

resources=`ssh $FIRST_CONTROLLER_NODE "sudo cibadmin -Q --xpath //primitive --node-path" | tr ' ' '\n' | awk -F "id='" '{print $2 }' | awk -F "'" '{print $1}' | uniq`
  
for res in $resources; do found=0; for stdev in $stonithdevs; do if [ $stdev = $res ]; then found=1; fi; done; if [ $found = 0 ]; then ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint location $res rule resource-discovery=exclusive score=0 osprole eq controller"; fi; done

############
# Populate the Compute node resources within pacemaker, starting with neutron-openvswitch-agent:  
############
echo ""
echo "INFO: Populate the Compute node resources within pacemaker."

ssh $FIRST_CONTROLLER_NODE "sudo pcs resource create neutron-openvswitch-agent-compute systemd:neutron-openvswitch-agent --clone interleave=true --disabled --force"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint location neutron-openvswitch-agent-compute-clone rule resource-discovery=exclusive score=0 osprole eq compute"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint order start neutron-server-clone then neutron-openvswitch-agent-compute-clone require-all=false"

ssh $FIRST_CONTROLLER_NODE "sudo pcs resource create libvirtd-compute systemd:libvirtd --clone interleave=true --disabled --force"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint location libvirtd-compute-clone rule resource-discovery=exclusive score=0 osprole eq compute"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint order start neutron-openvswitch-agent-compute-clone then libvirtd-compute-clone"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint colocation add libvirtd-compute-clone with neutron-openvswitch-agent-compute-clone"

ssh $FIRST_CONTROLLER_NODE "sudo pcs resource create ceilometer-compute systemd:openstack-ceilometer-compute --clone interleave=true --disabled --force"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint location ceilometer-compute-clone rule resource-discovery=exclusive score=0 osprole eq compute"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint order start openstack-ceilometer-notification-clone then ceilometer-compute-clone require-all=false"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint order start libvirtd-compute-clone then ceilometer-compute-clone"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint colocation add ceilometer-compute-clone with libvirtd-compute-clone"

ssh $FIRST_CONTROLLER_NODE "sudo pcs resource create nova-compute-checkevacuate ocf:openstack:nova-compute-wait auth_url=$OS_AUTH_URL username=$OS_USERNAME password=$OS_PASSWORD tenant_name=$OS_TENANT_NAME op start timeout=300 --clone interleave=true --disabled --force"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint location nova-compute-checkevacuate-clone rule resource-discovery=exclusive score=0 osprole eq compute"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint order start openstack-nova-conductor-clone then nova-compute-checkevacuate-clone require-all=false"
ssh $FIRST_CONTROLLER_NODE "sudo pcs resource create nova-compute systemd:openstack-nova-compute --clone interleave=true --disabled --force"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint location nova-compute-clone rule resource-discovery=exclusive score=0 osprole eq compute"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint order start nova-compute-checkevacuate-clone then nova-compute-clone require-all=true"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint order start nova-compute-clone then nova-evacuate require-all=false"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint order start libvirtd-compute-clone then nova-compute-clone"
ssh $FIRST_CONTROLLER_NODE "sudo pcs constraint colocation add nova-compute-clone with libvirtd-compute-clone"

############
# Add stonith devices for the compute nodes. Replace the ipaddr, login and passwd values to 
# suit your IPMI device. Run ~/pilot/identify_nodes.sh  to see which idrac is associated 
# with which host and crm_node -n to get the hostname. 
############
echo ""
echo "INFO: Add stonith devices for the compute nodes."

for compute_node in $COMPUTE_NODES
do
  crm_node_name=`ssh $compute_node "sudo crm_node -n"`
  nova_compute_name=`echo $crm_node_name | cut -d. -f1`
  compute_node_ip=`grep $nova_compute_name ~/undercloud_nodes.txt | cut -d" " -f2`
  
  ssh $FIRST_CONTROLLER_NODE "sudo pcs stonith create ipmilan-$nova_compute_name fence_ipmilan pcmk_host_list=$crm_node_name ipaddr=$compute_node_ip login=$IDRAC_USER passwd=$IDRAC_PASS lanplus=1 cipher=1 op monitor interval=60s"
done

	
############
# Create a seperate fence-nova stonith device.
############
echo ""
echo "INFO: Create a seperate fence-nova stonith device."

ssh $FIRST_CONTROLLER_NODE "sudo pcs stonith create fence-nova fence_compute auth-url=$OS_AUTH_URL login=$OS_USERNAME passwd=$OS_PASSWORD tenant-name=$OS_TENANT_NAME record-only=1 --force"

############
# Make certain the Compute nodes are able to recover after fencing. 
############
echo ""
echo "INFO: Ensure the Compute nodes are able to recover after fencing."

ssh $FIRST_CONTROLLER_NODE "sudo pcs property set cluster-recheck-interval=1min"

############
# Create Compute node resources and set the stonith level 1 to include both the nodes's physical 
# fence device and fence-nova.
############
echo ""
echo "INFO: Create Compute node resources and set the stonith level 1."

for compute_node in $COMPUTE_NODES
do
  crm_node_name=`ssh $compute_node "sudo crm_node -n"`

  ssh $FIRST_CONTROLLER_NODE "sudo pcs resource create $crm_node_name ocf:pacemaker:remote reconnect_interval=60 op monitor interval=20"
  ssh $FIRST_CONTROLLER_NODE "sudo pcs property set --node $crm_node_name osprole=compute"
  ssh $FIRST_CONTROLLER_NODE "sudo pcs stonith level add 1 $crm_node_name ipmilan-$crm_node_name,fence-nova"
done

ssh $FIRST_CONTROLLER_NODE "sudo pcs stonith"

############
# Enable the control and Compute plane services. 
############
echo ""
echo "INFO: Enable the control and Compute plane services."

ssh $FIRST_CONTROLLER_NODE "sudo pcs resource enable openstack-keystone"
ssh $FIRST_CONTROLLER_NODE "sudo pcs resource enable neutron-openvswitch-agent-compute"
ssh $FIRST_CONTROLLER_NODE "sudo pcs resource enable libvirtd-compute" 
ssh $FIRST_CONTROLLER_NODE "sudo pcs resource enable ceilometer-compute"
ssh $FIRST_CONTROLLER_NODE "sudo pcs resource enable nova-compute"
ssh $FIRST_CONTROLLER_NODE "sudo pcs resource enable nova-compute-checkevacuate"

############
# Allow some time for the environment to settle before cleaning up any failed resources. 
############
echo ""
echo "INFO: clean up any failed resources."

sleep 60 
ssh $FIRST_CONTROLLER_NODE "sudo pcs resource cleanup" 
ssh $FIRST_CONTROLLER_NODE "sudo pcs status" 
ssh $FIRST_CONTROLLER_NODE "sudo pcs property set stonith-enabled=true" 
