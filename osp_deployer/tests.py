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
from osp_deployer.foreman import Foreman
from osp_deployer.ceph import Ceph
import sys, getopt
from osp_deployer import Settings
from auto_common import Ipmi, Ssh, FileHelper, Scp, UI_Manager
from datetime import datetime
import time,subprocess
import paramiko, re
import logging
logger = logging.getLogger(__name__)
import traceback, os.path, urllib2

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

    opts, args = getopt.getopt(sys.argv[1:], ":s:", ["help", "settingsFile="])
    if len(opts)!= 1:
        logger.fatal( "usage : python deployer.py -s settingFile")
        logger.fatal( "eg : python deployer.py -s settings/settings.ini")
        print( "usage : python deployer.py -s settingFile")
        print( "eg : python deployer.py -s settings/settings.ini")
        sys.exit(2)
    for opt, arg in opts:
        if str(opt) == '-s':
            settingsFile = str(arg)
            logger.info( "settings file : " + settingsFile)
        else:
            logger.info( "usage : python deployer.py -s settingFile")
            logger.info( "eg : python deployer.py -s settings/settings.ini")
            sys.exit(2)
    logger.info("loading settings files " + settingsFile)
    settings = Settings(settingsFile)
    attrs = vars(settings)

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

    foreman = Foreman()
    foreman.update_scripts()



