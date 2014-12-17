from osp_deployer.config import Settings
from auto_common import Ssh, Scp,  Widget, UI_Manager, FileHelper
from osp_deployer.foreman_ui.login import Login
import time
import logging
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
        cmd = ' ssh-keyscan -H '+ self.settings.ceph_node.hostname +'.' + self.settings.domain +' >> ~/.ssh/known_hosts'
        
        print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        
        logger.info("updating host files for controller nodes & upload ssh keys to enable password less ssh between ceph/controllers")
        cmd = 'cat ~/.ssh/id_rsa.pub'
        myKey, err = Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
        monitorList = ''
        for host in self.settings.controller_nodes :
            cmd = 'echo "'+ host.provisioning_ip+' '+ host.hostname +'" >> /etc/hosts'
            print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
            monitorList = monitorList +  host.hostname + ' '
            cmd = ' ssh-keyscan -H '+ host.hostname +' >> ~/.ssh/known_hosts'
            Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )
            cmds = [ 'mkdir ~/.ssh',
                    'echo "' + myKey + '" >> ~/.ssh/authorized_keys'
                    ]
            for cmd in cmds : 
                logger.info("Executing " + cmd + " on " + host.hostname)
                print Ssh.execute_command(host.public_ip, "root", self.settings.nodes_root_password,cmd )
        time.sleep(30)
        cmd = 'cd ~/cluster;ceph-deploy new ' + monitorList
        print Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd )    
        