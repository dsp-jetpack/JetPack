import sys, time
from auto_common import Ipmi, Ssh, FileHelper, Scp, UI_Manager, Widget
from datetime import datetime
from osp_deployer import *
from selenium import webdriver
import paramiko, re
from osp_deployer.config import Settings
from auto_common import Ssh, Scp, UI_Manager, Widget
import time
import logging
from math import log
logger = logging.getLogger(__name__)
import uuid
from itertools import imap
import threading

class runThreadedPuppet (threading.Thread):
    def __init__(self, threadID, host):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.host = host
        self.settings = Settings.settings
    
    def run(self):
        cmd = 'puppet agent -t -dv |& tee /root/puppet.out'
        print "Starting Puppet run on " + self.host.hostname
        
        didNotRun = True
        while didNotRun == True:
            bla ,err = Ssh.execute_command(self.host.provisioning_ip, "root", self.settings.nodes_root_password, cmd)
            if  "Run of Puppet configuration client already in progress" in bla:
                didNotRun = True
                logger.info("puppet s busy ... give it a while & retry")
                time.sleep(20)
            else :
                didNotRun = False
                logger.info(self.host.hostname + "Puppet run ::")
                logger.info(bla)
                break
        print "Done running puppet on  " + self.host.hostname

def execute_as_shell( address,usr, pwd, command):
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(address,username = usr,password = pwd)
        channel = conn.invoke_shell()
        time.sleep(1)
        channel.recv(9999) 
        channel.send(command  + "\n")     
        buff = ''
        while not buff.endswith(']# '):
            resp = channel.recv(9999)
            buff += resp
        return buff     
    
def execute_as_shell_expectPasswords( address,usr, pwd, command):
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(address,username = usr,password = pwd)
        channel = conn.invoke_shell()
        time.sleep(1)
        channel.recv(9999) 
        channel.send(command  + "\n")     
        buff = ''
        while not buff.endswith(']# '):
            resp = channel.recv(9999)
            buff += resp
            print " >> [[" + buff  +"]]"
            if buff.endswith("'s password: "):
                channel.send(settings.nodes_root_password + "\n")
            if buff.endswith("(yes/no)? "):
                channel.send("yes\n")
 
                 
        return buff
    


if __name__ == '__main__':
   
    import logging.config
    logging.basicConfig(filename='c:/auto_results/deployer.log',
                    format="%(asctime)-15s:%(name)s:%(process)d:%(levelname)s:%(message)s",
                    filemode='w',
                    level=logging.INFO)
    
    settings = Settings('settings\settings.ini')  
    
    attrs = vars(settings)
    #foremanHost= Foreman()
    #settings.foreman_password = 'tewFMD7VQgXKRT5b'
    
    #ceph = Ceph()
    #ceph.grantAdminRightsToOSD()
    #ceph.modifyOSDPlacementGroups()
    #ceph.pool_and_keyRing_configuration()
    #ceph.foreman_config_ha_all_in_One()
    #ceph.foreman_config_compute()
        
    
    #foremanHost.configureHostGroups_Parameters()
    #foremanHost.cephConfigurtion()
    #foremanHost.configureNodes()
    
    # bugs here with docs, if done earlier as suggeste ceph wont be installed on the compute nodes
    #ceph.libvirt_config()
    #ceph.deploy_ceph_to_compute_hosts()
    #ceph.configure_cinder_for_backup() 
    
    for each in settings.controller_nodes:
        print each.hostname
        print each.provisioning_ip
        print settings.nodes_root_password
        Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password, "service puppet start")
        
    
    
    
    