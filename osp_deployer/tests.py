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
import traceback, os.path, urllib2, subprocess

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

    settings = Settings('settings\settings_sample.ini')

    #nodes = [
    #    settings.foreman_node,
    #    settings.ceph_node,
    #]
    #others = settings.controller_nodes + settings.compute_nodes + settings.ceph_nodes

    #for node in nodes:
    #    remoteLocks =  Ssh.execute_command_readlines(node.provisioning_ip, "root", "QaCl0ud",'rpm -qa | sort' )[0]
    #    print "::::::::: " + node.hostname + "::::::::: "
    #    for each in remoteLocks:
    #        print each#

    #for node in others:
    #    remoteLocks =  Ssh.execute_command_readlines(node.provisioning_ip, "root", "QaCl0ud2014",'rpm -qa | sort' )[0]
    #    print "::::::::: " + node.hostname + "::::::::: "
    #    for each in remoteLocks:
    #        print each#

    print("==== Running envirnment sanity tests")
    assert os.path.isfile(settings.rhl6_iso) , settings.rhl6_iso + "ISO  doesnn't seem to exist"
    assert os.path.isfile(settings.rhl7_iso) , settings.rhl7_iso + "ISO doesnn't seem to exist"
    assert os.path.isfile(settings.sah_kickstart) , settings.sah_kickstart + "kickstart file doesnn't seem to exist"
    assert os.path.isfile(settings.foreman_deploy_sh) , settings.foreman_deploy_sh + " script doesnn't seem to exist"
    assert os.path.isfile(settings.ceph_deploy_sh) , settings.ceph_deploy_sh + " script doesnn't seem to exist"

    try:
            urllib2.urlopen(settings.rhel_install_location +"/eula").read()
    except:
        raise AssertionError(settings.rhel_install_location + "/eula is not reachable")

    if "RUNNING" in subprocess.check_output("sc query Tftpd32_svc",stderr=subprocess.STDOUT, shell=True):
        subprocess.check_output("net stop Tftpd32_svc",stderr=subprocess.STDOUT, shell=True)

    hdw_nodes = settings.controller_nodes + settings.compute_nodes + settings.ceph_nodes
    hdw_nodes.append(settings.sah_node)
    for node in hdw_nodes:
        try:
            ipmi_session = Ipmi(settings.cygwin_installdir, settings.ipmi_user, settings.ipmi_password, node.idrac_ip)
            print node.hostname +" :: "+ ipmi_session.get_power_state()
        except:
            raise AssertionError("Could not impi to host " + node.hostname)



    
    
     