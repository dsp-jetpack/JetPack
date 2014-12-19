from osp_deployer.config import Settings
from auto_common import Ssh, Scp,  Widget, UI_Manager, FileHelper
import time
import logging, paramiko
logger = logging.getLogger(__name__)

class Ceph():
    '''
    TODO:: add debugged/logging
    '''
    
    def __init__(self):
        self.settings = Settings.settings
        
    
    def copy_installer(self):
        logger.info( "copying Ceph installer" ) 
        cmd = "mkdir ~/ice-1.2"
        print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        file = 'ICE-1.2.2-rhel7.tar.gz'
        localfile = self.settings.foreman_configuration_scripts + "\\" + file
        print "local file " + localfile
        remotefile = '/root/ice-1.2/' + file
        print "remote file " + remotefile
        Scp.put_file(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password, localfile, remotefile)
        cmd = 'cd ~/ice-1.2;tar -zxvf ' + remotefile
        print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        
    def install_ice(self):
        logger.info("removing installation prompts")
        commands = ['sed -i "s/fqdn = prompt.*/return \'http\', fallback_fqdn/" /root/ice-1.2/ice_setup.py',
                    "sed -i 's/prompt_continue()$//' /root/ice-1.2/ice_setup.py"
                    ]
        for cmd in commands :
            print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        cmd = 'cd /root/ice-1.2/;python ice_setup.py'
        logger.info("installing ice")
        print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        
        cmd = 'mkdir ~/cluster && cd ~/cluster'
        print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        
        cmd = 'cd ~/cluster;calamari-ctl initialize --admin-username root --admin-password '+self.settings.ceph_node.root_password+' --admin-email gael_rehault@dell.com'
        print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
       
    def configure_monitor(self):
        cmd = 'mkdir ~/.ssh; ssh-keygen -q -f /root/.ssh/id_rsa -P '';touch ~/.ssh/known_hosts'
        print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        cmd = ' ssh-keyscan -H '+ self.settings.ceph_node.hostname +'.' + self.settings.domain +' >> ~/.ssh/known_hosts'
        print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        
        logger.info("updating host files for controller nodes & upload ssh keys to enable password less ssh between ceph/controllers")
        cmd = 'cat /root/.ssh/id_rsa.pub'
        myKey, err = Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        monitorList = ''
        monitorListShort = ''
        for host in self.settings.controller_nodes :
            cmd = 'echo "'+ host.provisioning_ip+' '+ host.hostname +'-storage" >> /etc/hosts'
            print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
            cmd = 'echo "'+ host.provisioning_ip+' '+ host.hostname +'" >> /etc/hosts'
            print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        time.sleep(20)
        for host in self.settings.controller_nodes :
            monitorList = monitorList +  host.hostname + '-storage '
            monitorListShort = monitorListShort + host.hostname + " "
            cmd = 'echo "' + self.settings.ceph_node.provisioning_ip + '  ' + self.settings.ceph_node.hostname + "." + self.settings.domain +'" >> /etc/hosts'
            print Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd)
        cmd = 'cd ~/cluster;ceph-deploy new ' + monitorList
        print self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd)    
        
        logger.info("Updating ceph.conf")
        toAdd = ['public network = ' + self.settings.storage_network,
                 'cluster network = ' + self.settings.storage_cluster_network,
                 'osd pool default size = 2'
                 ]
        for sett in toAdd:
            cmd = 'echo "'+ sett +'" >> ~/cluster/ceph.conf'
        print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        
        logger.info("ceph deploy.")
        cmd = 'ceph-deploy install ' + monitorListShort
        print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        
    def execute_as_shell_expectPasswords(self, address,usr, pwd, command):
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
            if buff.endswith("storage's password: "):
                channel.send(self.settings.nodes_root_password + "\n")
            if buff.endswith("(yes/no)? "):
                channel.send("yes\n")
                
                
                
                
                 
        return buff