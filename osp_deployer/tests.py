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

logger = logging.getLogger(__name__)

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
    
    ceph = Ceph()
    ceph.configure_osd()
    
    
    
    
    