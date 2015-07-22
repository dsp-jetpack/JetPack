import sys, getopt, time, subprocess, paramiko,logging, traceback, os.path, urllib2, shutil
from osp_deployer.foreman import Foreman
from osp_deployer.ceph import Ceph
from auto_common import Ipmi, Ssh, FileHelper, Scp, UI_Manager
from osp_deployer import Settings

logger = logging.getLogger(__name__)

def log(message):
    print (message)
    logger.info(  message)

def verify_subscription_status(public_ip, user, password, retries):
    i = 0
    subscriptionStatus = "Invalid."
    while("Current" not in subscriptionStatus and i < retries):
        if "Unknown" in subscriptionStatus:
            return subscriptionStatus
        log("...")
        time.sleep(10)
        subscriptionStatus = "Current"
        i += 1;
    return subscriptionStatus

def execute_as_shell(address,usr, pwd, command):
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
        #print">" + resp +"<"
    return buff

if __name__ == '__main__':


    try :

        verify_subscription_status("sfsdsdfsdf", "root", "pasas", 2)


    except:
        logger.info(traceback.format_exc())
        e = sys.exc_info()[0]
        logger.info(e)
        print e
        print traceback.format_exc()



