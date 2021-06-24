#!/usr/bin/env python3

# Copyright (c) 2015-2021 Dell Inc. or its subsidiaries.
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

from discover_nodes.dracclient.client import DRACClient
from infra_host import InfraHost
import logging, subprocess, yaml, time 
from ocp_deployer.settings.ocp_config import OCP_Settings
from ocp_deployer.checkpoints import Checkpoints
logger = logging.getLogger("ocp_deployer")
import requests, json, urllib3
from auto_common import Ssh, FileHelper
from collections import defaultdict
from generate_inventory_file import InventoryFile
import shutil, os

class CSah(InfraHost):

        def __init__(self):

            self.settings = OCP_Settings.settings
            self.root_user = "root"
            self_root_pwd = self.settings.csah_root_pwd


        def power_off_cluster_nodes(self):
            # Power off all control & compute nodes
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.info("Powering off Control & Compute nodes")
            for node in ( self.settings.controller_nodes + self.settings.compute_nodes):
                logger.debug("powering off " + node.name )
                drac_client = DRACClient(node.idrac_ip, self.settings.ipmi_user, self.settings.ipmi_pwd)
                if "POWER_ON" in drac_client.get_power_state():
                    drac_client.set_power_state('POWER_OFF')

        def cleanup_sah(self):
            logger.info("- Clean up any existing installation  ")
            cmds = [
                ' killall -u core',
                'userdel -r core',
                'rm -rf /var/lib/tftpboot/uefi/*']
            for cmd in cmds:
                Ssh.execute_command("localhost",
                                    "root",
                                    self.settings.csah_root_pwd,
                                    cmd)

        def delete_bootstrap_vm(self):
            logger.info(" Destroy any existing bootstrap Vm")
            cmd = 'virsh list --all'
            bBoostrapDestroyed = False
            while bBoostrapDestroyed is False:
                re = Ssh.execute_command("localhost",
                                         "root",
                                         self.settings.csah_root_pwd,
                                         cmd)
                if 'bootstrap' in str(re):
                    cmds = [
                        'virsh undefine --nvram "bootstrapkvm"',
                        'virsh destroy bootstrapkvm']
                    for cm in cmds:
                        Ssh.execute_command("localhost",
                                            "root",
                                            self.settings.csah_root_pwd,
                                            cm)
                else:
                    bBoostrapDestroyed = True
            cmd = 'rm -rf /home/bootstrapvm-disk.qcow2'
            Ssh.execute_command("localhost", "root", self.settings.csah_root_pwd, cmd)

        def run_playbooks(self):
            logger.info("- Run ansible playbook to generate ignition files etc")
            subprocess.call('ansible-playbook -i generated_inventory haocp.yaml', shell=True, cwd='/home/ansible/openshift-bare-metal/ansible')

        def create_bootstrap_vm(self):
            logger.info("- Create the bootstrap VM")
            bootstrap_mac = self.get_inventory()['all']['vars']['bootstrap_node'][0]['mac']
            cmd = 'virt-install --name bootstrapkvm --ram 20480 --vcpu 8 --disk path=/home/bootstrapvm-disk.qcow2,format=qcow2,size=20 --os-variant generic --network=bridge=br0,model=virtio,mac=' + bootstrap_mac + ' --pxe --boot uefi,hd,network --noautoconsole --autostart &'
            re = Ssh.execute_command("localhost",
                                    "root",
                                    self.settings.csah_root_pwd,
                                    cmd)
            time.sleep(320)

        def wait_for_bootstrap_ready(self):
            bBootstrap_ready = False
            while bBootstrap_ready is False:
                cmd = 'ssh -t root@localhost "sudo su - core -c \' ssh -o \\"StrictHostKeyChecking no \\" bootstrap sudo ss -tulpn | grep -E \\"6443|22623|2379\\"\'"'
                openedPorts= Ssh.execute_command_tty("localhost",
                                                 "root",
                                                 self.settings.csah_root_pwd,
                                                 cmd)
                if ("22623" in str(openedPorts)) and ("2379" in str(openedPorts)) and ("6443" in str(openedPorts)) :
                    logger.info(" ,, boostrap UP! ")
                    bBootstrap_ready = True
                re = Ssh.execute_command("localhost",
                                        "root",
                                        self.settings.csah_root_pwd,
                                        "virsh list --all | grep bootstrapkvm")[0]
                if "shut off" in re:
                    bPXe_complete = True
                    logger.info("- Powering on the bootstrap VM")
                    Ssh.execute_command("localhost",
                                    "root",
                                    self.settings.csah_root_pwd,
                                    "virsh start bootstrapkvm")
                time.sleep(60)
            logger.info("- Bootstrap VM is ready") 

        def get_inventory(sel):
            with open(r'/home/ansible/openshift-bare-metal/ansible/generated_inventory') as file:
                inventory = yaml.load(file)
            return inventory
        
        def pxe_boot_controllers(self):
            logger.info("Pxe boot the control nodes")
            for node in self.settings.controller_nodes:
                self.set_node_to_pxe(node)
                self.power_on_node(node)

        def pxe_boot_computes(self):
            logger.info("Pxe boot the compute nodes")
            for node in self.settings.compute_nodes:
                self.set_node_to_pxe(node)
                self.power_on_node(node)
            time.sleep(350)

            
        def set_node_to_pxe(self, node):
            logger.debug("Setting " + node.name + " to PXE on next boot")
            url = 'https://%s/redfish/v1/Systems/System.Embedded.1' % node.idrac_ip
            payload = {"Boot":{"BootSourceOverrideTarget":"Pxe"}}
            headers = {'content-type': 'application/json'}

            response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(self.settings.ipmi_user, self.settings.ipmi_pwd))
            data = response.json()
            statusCode = response.status_code
            if statusCode == 200:
                logger.debug(node.name + " set to Pxe on next boot")
            else:
                logger.debug("\n- Failed to set node "  + node.name + " to Pxe boot, errror code is %s" % statusCode)
                detail_message=str(response.__dict__)
                logger.debug(detail_message)

        def power_on_node(self, node):
            logger.debug("Powering on " + node.name)
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            drac_client = DRACClient(node.idrac_ip, self.settings.ipmi_user, self.settings.ipmi_pwd)
            if "POWER_OFF" in drac_client.get_power_state():
                drac_client.set_power_state('POWER_ON')


        def wait_for_controllers_ready(self):
            logger.info("Wait for the control nodes to be ready")
            time.sleep(180)
            for node in self.settings.controller_nodes:
                bNodeReady = False
                while bNodeReady is False:
                    cmd = 'ssh -t root@localhost "sudo su - core -c \' ssh -o \\"StrictHostKeyChecking no \\" ' + node.name + ' ls -lart /etc/kubernetes/manifests\'"'
                    ls  = Ssh.execute_command_tty("localhost",
                                                  "root",
                                                  self.settings.csah_root_pwd,
                                                  cmd)
                    if "kube-scheduler-pod.yaml" and "kube-controller-manager-pod.yaml" and "kube-apiserver-pod.yaml" and "etcd-pod.yaml" in str(ls):
                        bNodeReady = True
                        logger.debug(node.name  + " is ready")
                    else:
                        logger.debug("Waiting for" + node.name + " to be readdy...")
                        time.sleep(30)

        def complete_bootstrap_process(self):
            logger.info("Wait for the bootstrap node services to be up")
            cmd = 'ssh -t root@localhost "sudo su - core -c \' ssh -o \\"StrictHostKeyChecking no \\" bootstrap journalctl | grep \'bootkube.service complete\'\'"'
            bBootStrapReady = False
            while bBootStrapReady is False:
                journal =  Ssh.execute_command_tty("localhost",
                                                   "root",
                                                   self.settings.csah_root_pwd,
                                                   cmd)
                if 'bootkube.service complete' in str(journal):
                    bBootStrapReady = True
                    logger.info("Bootstrap node ready")
                else:
                    logger.debug("Waiting for bootstrap node to finish initializing services..")
                    time.sleep(30)

            logger.info("Complete the bootstrap process")
            cmd = 'ssh -t root@localhost "sudo su - core -c \' ./openshift-install --dir=openshift wait-for bootstrap-complete --log-level debug\'"'
            re =  Ssh.execute_command_tty("localhost",
                                          "root",
                                          self.settings.csah_root_pwd,
                                          cmd)
            cmd = 'ssh -t root@localhost "sudo su - core -c \'oc get nodes\'"'
            re =  Ssh.execute_command_tty("localhost",
                                          "root",
                                          self.settings.csah_root_pwd,
                                          cmd)


        def wait_for_operators_ready(self):
            logger.info(" - Wait for all operators to be available")
            bOperatorsReady = False
            while bOperatorsReady is False:
                cmd = 'ssh -t root@localhost "sudo su - core -c \'oc get csr -o name | xargs oc adm certificate approve\'"'
                Ssh.execute_command_tty("localhost","root", self.settings.csah_root_pwd, cmd)
                cmd = 'ssh -t root@localhost "sudo su - core -c \'oc get clusteroperators\'"'
                re =  Ssh.execute_command_tty("localhost",
                                              "root",
                                              self.settings.csah_root_pwd,
                                              cmd)
                notReady = []
                ls = str(re).split('\\r\\')
                for each in ls:
                    if "False" in each.split()[2].strip():
                        notReady.append(each.split()[0].strip())
                if len(notReady) > 0:
                    logger.debug(" Operators still not ready : " + str(notReady))
                    time.sleep(120)
                else:
                    logger.info (" All operators are up & running ")
                    bOperatorsReady = True

        def complete_cluster_setup(self):
            logger.info("- Complete the cluster setup")
            cmd = 'ssh -t root@localhost "sudo su - core -c \'./openshift-install --dir=openshift wait-for install-complete --log-level debug\'"'
            Ssh.execute_command_tty("localhost","root", self.settings.csah_root_pwd, cmd)

        def discover_nodes(self):
            logger.info("- Discover nodes")
            cmd = 'rm -rf instackenv.json'
            subprocess.call(cmd, shell=True, cwd='/home/ansible/')

            nodes = self.settings.controller_nodes  + self.settings.compute_nodes
            cmd = "./discover_nodes.py  -u " + \
                self.settings.ipmi_user + \
                " -p '" + self.settings.ipmi_pwd + "'"
            for node in nodes:
                cmd += ' ' + node.idrac_ip
            cmd += '> ~/instackenv.json'

            subprocess.call(cmd, shell=True, cwd='/home/ansible/JetPack/src/pilot/discover_nodes')

        def configure_idracs(self):
            logger.info("- Configure Idracs")
            json_config = defaultdict(dict)
            cmd = "/home/ansible/JetPack/src/pilot/config_idracs.py "
            for node in self.settings.controller_nodes:
                node_id = node.idrac_ip
                json_config[node_id]["pxe_nic"] = self.settings.controllers_pxe_nic
            for node in self.settings.compute_nodes:
                node_id = node.idrac_ip
                json_config[node_id]["pxe_nic"] = self.settings.controllers_pxe_nic
            if json_config.items():
                cmd += "-j '{}'".format(json.dumps(json_config))
            subprocess.call(cmd, shell=True, cwd='/home/ansible/JetPack/src/pilot')


        def generate_inventory_file(self):
            logger.info("- Generating inventory file")
            logger.debug(" remove any existing inventory")
            existing_inventory='/home/ansible/openshift-bare-metal/ansible/generated_inventory'
            if os.path.exists(existing_inventory):
                os.remove(existing_inventory)
            gen_inv_file = InventoryFile(id_user=self.settings.ipmi_user,
                                         id_pass=self.settings.ipmi_pwd,
                                         version=self.settings.ocp_version,
                                         nodes_inventory=self.settings.nodes_yaml,
                                         diskname_master=self.settings.boot_disk_controllers,
                                         diskname_worker=self.settings.boot_disk_computes,
                                         dns_forwarder=self.settings.dns,
                                         cluster_name=self.settings.cluster_name
                                         )                
            gen_inv_file.run()
            logger.debug("add pull secret to inventory")
            with open('generated_inventory', 'a') as file:
                file.write('    pull_secret_file: pullsecret')

            logger.debug("copy generated inventory filei & pullsecret")
            shutil.copyfile(self.settings.pull_secret_file, '/home/ansible/files/pullsecret')
            shutil.copyfile('generated_inventory', '/home/ansible/openshift-bare-metal/ansible/generated_inventory')

        def update_nodes_yaml(self):
            # Inject the NIC informations into the nodes.yml
            logger.info("- Update the nodes.yaml with NICs information")
            # ToDo : Add nodes

        def update_kickstart_usb(self):
            #tester = Checkpoints()
            #tester.verify_deployer_settings()
            sets = self.settings
            shutil.copyfile(sets.csah_kickstart, sets.cloud_repo_dir +
                        "/../ocp-csah.ks")
            sets.csah_kickstart = sets.cloud_repo_dir + "/../ocp-csah.ks"
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^SystemPassword=.*',
                                          'SystemPassword="' +
                                           sets.csah_root_pwd +
                                           '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^AnsiblePassword=.*',
                                          'AnsiblePassword="' +
                                           sets.ansible_password +
                                           '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^SubscriptionManagerUser=.*',
                                          'SubscriptionManagerUser="' +
                                           sets.subscription_manager_user +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^SubscriptionManagerPassword=.*',
                                          'SubscriptionManagerPassword="' +
                                          sets.subscription_manager_password +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^SubscriptionManagerPool=.*',
                                          'SubscriptionManagerPool="' +
                                          sets.subscription_manager_pool_csah +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^Gateway=.*',
                                          'Gateway="' +
                                          sets.gateway +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^NameServers=.*',
                                          'NameServers="' +
                                          sets.name_server +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^NTPServers=.*',
                                          'NTPServers="' +
                                          sets.ntp_server +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^TimeZone=.*',
                                          'TimeZone="' +
                                          sets.timezone +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^anaconda_interface=.*',
                                          'anaconda_interface="' +
                                          sets.anaconda_ip + '/' +
                                          sets.anaconda_netmask + ' ' +
                                          sets.anaconda_iface +
                                          ' no"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^extern_bond_name=.*',
                                          'extern_bond_name="' +
                                          sets.public_bond_name +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^extern_boot_opts=.*',
                                          'extern_boot_opts="' +
                                          sets.public_boot_opts +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^extern_bond_opts=.*',
                                          'extern_bond_opts="' +
                                          sets.public_bond_opts +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^extern_ifaces=.*',
                                          'extern_ifaces="' +
                                          sets.public_bond_ifaces +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^extern_bond_mtu=.*',
                                          'extern_bond_mtu="' +
                                          sets.public_bond_mtu +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^bridge_name=.*',
                                          'bridge_name="' +
                                          sets.bridge_name + 
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^bridge_bond_name=.*',
                                          'bridge_bond_name="' +
                                          sets.bridge_bond_name +
                                          '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^bridge_boot_opts=.*',
                                          'bridge_boot_opts="onboot static ' + 
                                          sets.bridge_ip + '/' +
                                          sets.bridge_netmask + '"')
            FileHelper.replace_expression(sets.csah_kickstart,
                                          '^bridge_mtu=.*',
                                          'bridge_mtu="' +
                                          sets.bridge_mtu +
                                          '"')

            time.sleep(3)






            
            
