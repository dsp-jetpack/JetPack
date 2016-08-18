#!/usr/bin/python
######################################################################################
# This script should be run from the director node as the director's admin user. 
# This script assumes the update_ssh_config.py is present and has not been modified.
######################################################################################

# IMPORTS
import argparse
import os
import sys
import subprocess
import shlex
import re
import paramiko

# Dell utilities
from identify_nodes import main as identify_nodes
from credential_helper import CredentialHelper
from update_ssh_config import main as update_ssh_config

# CONSTANTS

# METHOD DEFINITION

def ssh_cmd(address, user, command):
  try:
    cmd = "ssh " + user + "@" + address + " \"" + command + "\""
    #  print "CommandStr: \"{}\"".format( cmd )
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(address, username=user)
    stdin, ss_stdout, ss_stderr = client.exec_command(command)
    r_out, r_err = ss_stdout.read(), ss_stderr.read()
    client.close()
  except IOError:
    print ".. host " + address + " is not up"
    return "host not up"
  return r_out, r_err

def awk_it(instring,index,delimiter=" "): 
  try: 
    return [instring,instring.split(delimiter)[index-1]][max(0,min(1,index))] 
  except: 
    return "" 

def check_ip_validity(ipaddr):
    ValidIpAddressRegex = '^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    ip_match = re.search(ValidIpAddressRegex,ipaddr)
    if ip_match:
       ip = 1
    else:
       ip = 0
    return ip

def stop_disable_openstack_services(compute_nodes_ip):
  # Stop and disable openstack-service and libvirtd on all Compute nodes
  print "INFO: Disable compute node libvirtd and openstack services."

  for compute_node_ip in compute_nodes_ip:
    ssh_cmd(compute_node_ip, "heat-admin",
            "sudo openstack-service stop")
    ssh_cmd(compute_node_ip, "heat-admin", 
            "sudo openstack-service disable")
    ssh_cmd(compute_node_ip, "heat-admin",
            "sudo systemctl stop libvirtd")
    ssh_cmd(compute_node_ip, "heat-admin", 
            "sudo systemctl disable libvirtd")

def create_authkey(first_compute_node_ip):
  # Create auth_key on first compute node 
  print "INFO: Create auth_key on node: {}".format( first_compute_node_ip )

  ssh_cmd(first_compute_node_ip, "heat-admin", 
          "sudo mkdir -p /etc/pacemaker")
  ssh_cmd(first_compute_node_ip, "heat-admin",
          "sudo dd if=/dev/urandom of=/etc/pacemaker/authkey bs=4096 count=1")
  ssh_cmd(first_compute_node_ip, "heat-admin", 
          "sudo cp /etc/pacemaker/authkey ~heat-admin/")
  ssh_cmd(first_compute_node_ip, "heat-admin", 
          "sudo chown heat-admin:heat-admin ~heat-admin/authkey")

  # Copy authkey to back to local node 
  cmd =  "scp heat-admin@" + first_compute_node_ip + ":~/authkey ~/authkey" 
  os.system(cmd)

def distribute_all_authkey(compute_nodes_ip, controller_nodes_ip):
  for compute_node_ip in compute_nodes_ip:
    distribute_node_authkey(compute_node_ip)

  for controller_node_ip in controller_nodes_ip:
    distribute_node_authkey(controller_node_ip)

def distribute_node_authkey(node_ip):
  # Then distribute authkey to node 
  print "INFO: Distribute auth_key to node {}.".format(node_ip)

  cmd = "scp ~/authkey heat-admin@" + node_ip + ":~/authkey" 
  os.system(cmd)
  ssh_cmd(node_ip, "heat-admin", 
          "sudo mkdir -p /etc/pacemaker")
  ssh_cmd(node_ip, "heat-admin", 
          "sudo mv ~heat-admin/authkey /etc/pacemaker/")
  ssh_cmd(node_ip,"heat-admin", 
          "sudo chown root:root /etc/pacemaker/authkey")

def enable_start_pacemaker(compute_nodes_ip):
  for compute_node_ip in compute_nodes_ip:
    enable_start_compute_pacemaker(compute_node_ip)

def enable_start_compute_pacemaker(compute_node_ip):
  # Enable and start pacemaker remote on compute nodes 
  print "INFO: Enable and start pacemaker_remote service on compute node {}.".format(compute_node_ip)
  
  ssh_cmd(compute_node_ip, "heat-admin", 
          "sudo sudo systemctl enable pacemaker_remote")
  ssh_cmd(compute_node_ip, "heat-admin", 
          "sudo systemctl start pacemaker_remote")

def create_nova_evacuate_resource(overcloudrc_name, first_controller_node_ip):
  # Create a NovaEvacuate active/passive resource using the overcloudrc file 
  # to provide the auth_url, username, tenant and password values
  print "INFO: Create the nova-evacuate active/passive resource."

  overcloud_auth_url = get_overcloud_auth_url(overcloudrc_name)
  overcloud_username = get_overcloud_username(overcloudrc_name)
  overcloud_password = get_overcloud_password(overcloudrc_name)
  overcloud_tenant_name = get_overcloud_tenant_name(overcloudrc_name)
  
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource create nova-evacuate ocf:openstack:NovaEvacuate auth_url=" + overcloud_auth_url + " username=" + overcloud_username + " password=" + overcloud_password + " tenant_name=" + overcloud_tenant_name)

def confirm_nova_evacuate_resource(first_controller_node_ip):
  # Confirm that nova-evacuate is started after the floating IP resources, and the Image Service (glance), 
  # OpenStack Networking (neutron), Compute (nova) services
  print "INFO: Confirm nova-evacuate is started after glance, neutron and nova services."

  # Get IP list from PCS cluster 
  out, err = ssh_cmd(first_controller_node_ip, "heat-admin", 
                   "sudo pcs status | grep IP ")
  list = out.split()
  IPS = [ entry for entry in list if entry.startswith('ip-')]

  for ip in IPS: 
    ssh_cmd(first_controller_node_ip, "heat-admin", 
            "sudo pcs constraint order start " + ip + " then nova-evacuate")

  resource_list = ['openstack-glance-api-clone', 'neutron-metadata-agent-clone', 'openstack-nova-conductor-clone']
  for res in resource_list: 
    ssh_cmd(first_controller_node_ip, "heat-admin", 
            "sudo pcs constraint order start " + res + " then nova-evacuate require-all=false")
  
def disable_all_openstack_resource(first_controller_node_ip):
  # Disable all OpenStack resources across the control plane.
  print "INFO: Disable all OpenStack resources across the control plane."
  
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource disable openstack-keystone --wait=1000s")

def tag_controllers_with_osprole(first_controller_node_ip):
  # Create a list of the current controllers using cibadmin data.
  # Use this list to tag these nodes as controllers with the osprole=controller property.
  print "INFO: Get a list of current controllers & tag them with the osprole=controller property."
  
  out, err = ssh_cmd(first_controller_node_ip, "heat-admin", 
                   "sudo cibadmin -Q -o nodes | grep uname")
  out_list = out.split()
  controllers = [ entry for entry in out_list if entry.startswith('uname')]
  for controller in controllers:
    controller = re.findall(r'"([^"]*)"', controller)
    ssh_cmd(first_controller_node_ip, "heat-admin", 
            "sudo pcs property set --node " + controller[0] + " osprole=controller")

def tag_the_control_plane(first_controller_node_ip):
  # Build a list of stonith devices already present in the environment.
  # Tag the control plane services to make sure they only run on the controllers identified above, 
  # skipping any stonith devices listed.
  print "INFO: Get a list of stonith devices & tag the control plane services."
  
  # Build stonithdevs list
  stonithdevs = []
  out, err = ssh_cmd(first_controller_node_ip, "heat-admin", 
                     "sudo pcs stonith")
  list = out.split('\n')
  for line in list:
    if len(line.strip()) != 0:
      x =  ''.join(line).lstrip(" ")
      y = awk_it(x,1,"\t")
      stonithdevs.append(y)
  
  if not stonithdevs:
    print "ERROR: No stonith devices found, please ensure fencing is enabled."
    exit (-1)

  # Build resources list
  resources = []
  out, err = ssh_cmd(first_controller_node_ip, "heat-admin", 
		     "sudo cibadmin -Q --xpath //primitive --node-path")
  list = out.split('\n')
  for line in list:
    if len(line.strip()) != 0:
      x =  ''.join(line)
      y = awk_it(x,2,"id='")
      z = awk_it(y,1,"']")
      resources.append(z)
    
  # Process stonithdevs and resources lists -- setting constraints
  for res in resources: 
    found = 0 
    for stdev in stonithdevs: 
      if  stdev == res:  
        found = 1
    if found == 0: 
      #print "INSIDE found == 0: {} ".format(res)
      ssh_cmd(first_controller_node_ip, "heat-admin", 
              "sudo pcs constraint location " + res + " rule resource-discovery=exclusive score=0 osprole eq controller")

def populate_compute_nodes_resources(first_controller_node_ip, overcloudrc_name):
  # Populate the Compute node resources within pacemaker, starting with neutron-openvswitch-agent:  
  print "INFO: Populate the compute node resources within pacemaker."
 
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource create neutron-openvswitch-agent-compute systemd:neutron-openvswitch-agent --clone interleave=true --disabled --force")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint location neutron-openvswitch-agent-compute-clone rule resource-discovery=exclusive score=0 osprole eq compute")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint order start neutron-server-clone then neutron-openvswitch-agent-compute-clone require-all=false")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource create libvirtd-compute systemd:libvirtd --clone interleave=true --disabled --force")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint location libvirtd-compute-clone rule resource-discovery=exclusive score=0 osprole eq compute")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint order start neutron-openvswitch-agent-compute-clone then libvirtd-compute-clone")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint colocation add libvirtd-compute-clone with neutron-openvswitch-agent-compute-clone")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource create ceilometer-compute systemd:openstack-ceilometer-compute --clone interleave=true --disabled --force")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint location ceilometer-compute-clone rule resource-discovery=exclusive score=0 osprole eq compute")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint order start openstack-ceilometer-notification-clone then ceilometer-compute-clone require-all=false")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint order start libvirtd-compute-clone then ceilometer-compute-clone")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint colocation add ceilometer-compute-clone with libvirtd-compute-clone")

  overcloud_auth_url = get_overcloud_auth_url(overcloudrc_name)
  overcloud_username = get_overcloud_username(overcloudrc_name)
  overcloud_password = get_overcloud_password(overcloudrc_name)
  overcloud_tenant_name = get_overcloud_tenant_name(overcloudrc_name)

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource create nova-compute-checkevacuate ocf:openstack:nova-compute-wait auth_url=" + overcloud_auth_url + " username=" + overcloud_username + " password=" + overcloud_password + " tenant_name=" + overcloud_tenant_name + " op start timeout=300 --clone interleave=true --disabled --force")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint location nova-compute-checkevacuate-clone rule resource-discovery=exclusive score=0 osprole eq compute")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint order start openstack-nova-conductor-clone then nova-compute-checkevacuate-clone require-all=false")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource create nova-compute systemd:openstack-nova-compute --clone interleave=true --disabled --force")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint location nova-compute-clone rule resource-discovery=exclusive score=0 osprole eq compute")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint order start nova-compute-checkevacuate-clone then nova-compute-clone require-all=true")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint order start nova-compute-clone then nova-evacuate require-all=false")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint order start libvirtd-compute-clone then nova-compute-clone")

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs constraint colocation add nova-compute-clone with libvirtd-compute-clone")

def add_compute_nodes_stonith_devices(compute_nodes_ip, undercloud_config, first_controller_node_ip, instack_file):
  # Add stonith devices for the compute nodes. Replace the ipaddr, login and passwd values to 
  # suit your IPMI device. Run ~/pilot/identify_nodes.sh  to see which idrac is associated 
  # with which host and crm_node -n to get the hostname. 
  for compute_node_ip in compute_nodes_ip:
    add_compute_node_stonith_devices(compute_node_ip, undercloud_config, first_controller_node_ip, instack_file)

def add_compute_node_stonith_devices(compute_node_ip, undercloud_config, first_controller_node_ip, instack_file):
  print "INFO: Add stonith devices for the compute node {}.".format(compute_node_ip)

  out, err = ssh_cmd(compute_node_ip, "heat-admin", 
                     "sudo crm_node -n")
  crm_node_name = out.strip()
  nova_compute_name = awk_it(crm_node_name,1,".")

  # Get first_compute_node_ip
  p1 = subprocess.Popen(['grep', nova_compute_name ,undercloud_config], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('cut -d" " -f2'),stdin=p1.stdout,
                        stdout=subprocess.PIPE)
  compute_node_drac_ip = p2.communicate()[0].rstrip()

  # Get drac_user  
  p1 = subprocess.Popen(['cat', instack_file], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('grep -n2 ' + compute_node_drac_ip),stdin=p1.stdout,
                        stdout=subprocess.PIPE)
  p3 = subprocess.Popen(shlex.split('awk -F\'"\' \'/pm_user/ {print $4}\''),stdin=p2.stdout,
                        stdout=subprocess.PIPE)
  drac_user = p3.communicate()[0].rstrip()

  # Get drac_password
  p1 = subprocess.Popen(['cat', instack_file], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('grep -n2 ' + compute_node_drac_ip),stdin=p1.stdout,
                        stdout=subprocess.PIPE)
  p3 = subprocess.Popen(shlex.split('awk -F\'"\' \'/pm_pass/ {print $4}\''),stdin=p2.stdout,
                        stdout=subprocess.PIPE)
  drac_password = p3.communicate()[0].rstrip()

  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs stonith create ipmilan-" + nova_compute_name + " fence_ipmilan pcmk_host_list=" + crm_node_name + " ipaddr=" + compute_node_drac_ip + " login=" + drac_user + " passwd=" + drac_password + " lanplus=1 cipher=1 op monitor interval=60s")

def create_fence_nova_device(first_controller_node_ip, overcloudrc_name):
  # Create a seperate fence-nova stonith device.
  print "INFO: Create a seperate fence-nova stonith device."

  overcloud_auth_url = get_overcloud_auth_url(overcloudrc_name)
  overcloud_username = get_overcloud_username(overcloudrc_name)
  overcloud_password = get_overcloud_password(overcloudrc_name)
  overcloud_tenant_name = get_overcloud_tenant_name(overcloudrc_name)
  
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs stonith create fence-nova fence_compute auth_url=" + overcloud_auth_url + " username=" + overcloud_username + " password=" + overcloud_password + " tenant_name=" + overcloud_tenant_name + " record-only=1 --force")



def enable_compute_nodes_recovery(first_controller_node_ip):
  # Make certain the Compute nodes are able to recover after fencing. 
  print "INFO: Ensure the Compute nodes are able to recover after fencing."
  
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs property set cluster-recheck-interval=1min")


def create_compute_nodes_resources(compute_nodes_ip, first_controller_node_ip):
  # Create Compute node resources and set the stonith level 1 to include both the nodes's physical 
  # fence device and fence-nova.
  for compute_node_ip in compute_nodes_ip:
    create_compute_node_resources(compute_node_ip, first_controller_node_ip)

def create_compute_node_resources(compute_node_ip, first_controller_node_ip):
  # Create Compute node resources and set the stonith level 1 to include both the nodes's physical 
  # fence device and fence-nova.
  print "INFO: Create Compute node:{} resources and set the stonith level 1.".format(compute_node_ip)

  out, err = ssh_cmd(compute_node_ip, "heat-admin", 
                     "sudo crm_node -n")
  crm_node_name = out.strip()
  crm_node_sname = awk_it(crm_node_name,1,".")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource create " + crm_node_name + " ocf:pacemaker:remote reconnect_interval=60 op monitor interval=20")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs property set --node " + crm_node_name + " osprole=compute")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs stonith level add 1 " + crm_node_name + " ipmilan-" + crm_node_sname + ",fence-nova")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs stonith")
  
def enable_control_plane_services(first_controller_node_ip):
  # Enable the control and Compute plane services. 
  print "INFO: Enable the control and Compute plane services."
  
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource enable openstack-keystone")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource enable neutron-openvswitch-agent-compute")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource enable libvirtd-compute")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource enable ceilometer-compute")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource enable nova-compute")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource enable nova-compute-checkevacuate")

def final_resource_cleanup(first_controller_node_ip):
  # Allow some time for the environment to settle before cleaning up any failed resources. 
  print "INFO: Clean up any failed resources."
  
  os.system("sleep 60")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs resource cleanup")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs status")
  ssh_cmd(first_controller_node_ip, "heat-admin", 
          "sudo pcs property set stonith-enabled=true")


# MAIN 
def main():

  parser = argparse.ArgumentParser()
  group = parser.add_mutually_exclusive_group()
  group.add_argument("-compute", "--compute", dest="compute_node_ip", action="store", default='')
  group.add_argument("-controller", "--controller", dest="controller_node_ip", action="store", default='')
  parser.add_argument('-f', '--file', help='name of json file containing the node being set',
                      default='instackenv.json')
  parser.add_argument('-d', '--debug', action='store_true', default=False)
  args = parser.parse_args()

  home_dir = os.path.expanduser('~')
  undercloudrc_name =  os.path.join(home_dir, 'stackrc')
  overcloudrc_name = CredentialHelper.get_overcloudrc_name()
  overcloud_stack_name = CredentialHelper.get_stack_name()
  ssh_config = os.path.join(home_dir, '.ssh/config')
  undercloud_config = os.path.join(home_dir, 'undercloud_nodes.txt')
  instack_file = os.path.join(home_dir, args.file)

  # Source ~/stackrc
  os.system("source {}".format(undercloudrc_name))

  # Run ~/pilot/update_ssh_config.py
  cmd = os.path.join(home_dir, 'pilot/update_ssh_config.py')
  os.system(cmd)

  # Run ~/pilot/identify_nodes.py > ~/undercloud_nodes.txt
  cmd = os.path.join(home_dir, 'pilot/identify_nodes.py > ~/undercloud_nodes.txt')
  os.system(cmd)

  # Get first_controller_node
  p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('awk \'/cntl0/ {print $2}\''),stdin=p1.stdout,
                          stdout=subprocess.PIPE)
  first_controller_node = p2.communicate()[0].rstrip()

  # Get first_controller_node_ip
  p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('grep -A1 "cntl0"'),stdin=p1.stdout,
                          stdout=subprocess.PIPE)
  p3 = subprocess.Popen(shlex.split('awk \'/Hostname/ {print $2}\''),stdin=p2.stdout,
                          stdout=subprocess.PIPE)
  first_controller_node_ip = p3.communicate()[0].rstrip()

  # Get CONTROLLER_NODES
  p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('awk \'/cntl/ {print $2}\''),stdin=p1.stdout,
                          stdout=subprocess.PIPE)
  controller_nodes = p2.communicate()[0].split() 

  # Get COMPUTE_NODES_IP
  p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('grep -A1 "cntl"'),stdin=p1.stdout,
                          stdout=subprocess.PIPE)
  p3 = subprocess.Popen(shlex.split('awk \'/Hostname/ {print $2}\''),stdin=p2.stdout,
                          stdout=subprocess.PIPE)
  controller_nodes_ip = p3.communicate()[0].split()

  # Get first_compute_node
  p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('awk \'/nova0/ || /compute0/ {print $2}\''),stdin=p1.stdout,
                          stdout=subprocess.PIPE)
  first_compute_node = p2.communicate()[0].rstrip()

  # Get first_compute_node_ip
  p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('egrep -A1 -h "nova0|compute0"'),stdin=p1.stdout,
                          stdout=subprocess.PIPE)
  p3 = subprocess.Popen(shlex.split('awk \'/Hostname/ {print $2}\''),stdin=p2.stdout,
                          stdout=subprocess.PIPE)
  first_compute_node_ip = p3.communicate()[0].rstrip()

  # Get COMPUTE_NODES
  p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('awk \'/nova/ || /compute/ {print $2}\''),stdin=p1.stdout,
                          stdout=subprocess.PIPE)
  compute_nodes = p2.communicate()[0].split()

  # Get COMPUTE_NODES_IP
  p1 = subprocess.Popen(['cat', ssh_config], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('egrep -A1 -h "nova|compute"'),stdin=p1.stdout,
                          stdout=subprocess.PIPE)
  p3 = subprocess.Popen(shlex.split('awk \'/Hostname/ {print $2}\''),stdin=p2.stdout,
                          stdout=subprocess.PIPE)
  compute_nodes_ip = p3.communicate()[0].split()

  # Get COMPUTE_NOVA_NAMES
  p1 = subprocess.Popen(['nova', 'list'], stdout=subprocess.PIPE)
  p2 = subprocess.Popen(shlex.split('awk \'/compute/ {print $4}\''),stdin=p1.stdout,
                          stdout=subprocess.PIPE)
  compute_nova_names = p2.communicate()[0].split() 

  overcloud_auth_url, overcloud_tenant_name, overcloud_username, overcloud_password = CredentialHelper.get_creds(overcloudrc_name)
  
  if args.debug == True:
    print ""
    print "***  Dumping Global Variable Definitions  ***"
    print ""
    print "INFO: home_dir: {}".format( home_dir )
    print "INFO: overcloudrc_name: {}".format( overcloudrc_name )
    print "INFO: overcloud_stack_name: {}".format( overcloud_stack_name )
    print "INFO: overcloud_auth_url: {}".format( overcloud_auth_url )
    print "INFO: overcloud_username: {}".format( overcloud_username )
    print "INFO: overcloud_password: {}".format( overcloud_password )
    print "INFO: overcloud_tenant_name: {}".format( overcloud_tenant_name )
    print ""
    print "INFO: first_controller_node: {}".format( first_controller_node )
    print "INFO: first_controller_node_ip: {}".format( first_controller_node_ip )
    print "INFO: controller_nodes: {}".format( controller_nodes )
    print "INFO: controller_nodes_ip: {}".format( controller_nodes_ip )
    print ""
    print "INFO: first_compute_node: {}".format( first_compute_node )
    print "INFO: first_compute_node_ip: {}".format( first_compute_node_ip )
    print "INFO: compute_nodes: {}".format( compute_nodes )
    print "INFO: compute_nodes_ip: {}".format( compute_nodes_ip )
    print "INFO: compute_nova_names: {}".format( compute_nova_names )
    print ""

  if args.compute_node_ip == '' and args.controller_node_ip == '':
    print "***  Configuring Instance HA for stack {}  ***".format( overcloud_stack_name )
    print ""

    stop_disable_openstack_services(compute_nodes_ip)
    create_authkey(first_compute_node_ip)
    distribute_all_authkey(compute_nodes_ip, controller_nodes_ip)
    enable_start_pacemaker(compute_nodes_ip)
    create_nova_evacuate_resource(overcloudrc_name, first_controller_node_ip)
    confirm_nova_evacuate_resource(first_controller_node_ip)
    disable_all_openstack_resource(first_controller_node_ip)
    tag_controllers_with_osprole(first_controller_node_ip)
    tag_the_control_plane(first_controller_node_ip)
    populate_compute_nodes_resources(first_controller_node_ip, overcloudrc_name)
    add_compute_nodes_stonith_devices(compute_nodes_ip, undercloud_config, first_controller_node_ip, instack_file)
    create_fence_nova_device(first_controller_node_ip, overcloudrc_name)
    enable_compute_nodes_recovery(first_controller_node_ip)
    create_compute_nodes_resources(compute_nodes_ip, first_controller_node_ip)
    enable_control_plane_services(first_controller_node_ip)
    final_resource_cleanup(first_controller_node_ip)

  if args.compute_node_ip != '':
    compute_node_ip = args.compute_node_ip.rstrip()
    print "***  Adding a compute node {} to Instance HA configuration  ***".format(compute_node_ip)
    print ""

    if check_ip_validity(compute_node_ip):
      if args.debug == True:
        print "***  Dumping local Variable Definitions  ***"
        print "INFO: compute_nodes_ip: {}".format( compute_nodes_ip )
        print "INFO: compute_node_ip: {}".format( compute_node_ip )
        print "INFO: first_controller_node_ip: {}".format( first_controller_node_ip )
        print "INFO: undercloud_config: {}".format( undercloud_config )
        print "INFO: instack_file: {}".format( instack_file )

      stop_disable_openstack_services(compute_nodes_ip)
      distribute_node_authkey(compute_node_ip)
      enable_start_compute_pacemaker(compute_node_ip)
      add_compute_node_stonith_devices(compute_node_ip, undercloud_config, first_controller_node_ip, instack_file)
      create_compute_node_resources(compute_node_ip, first_controller_node_ip)
      enable_control_plane_services(first_controller_node_ip)
      final_resource_cleanup(first_controller_node_ip)

    else:
      print "!!! - Fatal Error: Invalid IP address: {}".format( compute_node_ip )
      exit (-1)

  if args.controller_node_ip != '':
    controller_node_ip = args.controller_node_ip.rstrip()
    print "***  Adding a controller node {} to Instance HA configuration  ***".format(controller_node_ip)
    print ""

    if check_ip_validity(controller_node_ip):
      if args.debug == True:
        print "***  Dumping local Variable Definitions  ***"
        print "INFO: controller_node_ip: {}".format( controller_node_ip )
        print "INFO: first_controller_node_ip: {}".format( first_controller_node_ip )

      distribute_node_authkey(controller_node_ip)
      tag_controllers_with_osprole(first_controller_node_ip)
      final_resource_cleanup(first_controller_node_ip)

    else:
      print "!!! - Fatal Error: Invalid IP address: {}".format( controller_node_ip )
      exit (-1)
  
exit

if __name__ == "__main__":
    main()
