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
        logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ) )
        file = 'ICE-1.2.2-rhel7.tar.gz'
        localfile = self.settings.foreman_configuration_scripts + "\\" + file
        logger.info( "local file " + localfile)
        remotefile = '/root/ice-1.2/' + file
        logger.info( "remote file " + remotefile)
        Scp.put_file(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password, localfile, remotefile)
        cmd = 'cd ~/ice-1.2;tar -zxvf ' + remotefile
        logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ) )
        
        
    def install_ice(self):
        logger.info("removing installation prompts")
        commands = ['sed -i "s/fqdn = prompt.*/return \'http\', fallback_fqdn/" /root/ice-1.2/ice_setup.py',
                    "sed -i 's/prompt_continue()$//' /root/ice-1.2/ice_setup.py"
                    ]
        for cmd in commands :
            logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ) )
        cmd = 'cd /root/ice-1.2/;python ice_setup.py'
        logger.info("installing ice")
        logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
        cmd = 'mkdir ~/cluster && cd ~/cluster'
        logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
        cmd = 'cd ~/cluster;calamari-ctl initialize --admin-username root --admin-password '+self.settings.ceph_node.root_password+' --admin-email gael_rehault@dell.com'
        logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
       
    def configure_monitor(self):
        cmd = 'mkdir ~/.ssh; ssh-keygen -q -f /root/.ssh/id_rsa -P "";touch ~/.ssh/known_hosts'
        logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        cmd = ' ssh-keyscan -H '+ self.settings.ceph_node.hostname +'.' + self.settings.domain +' >> ~/.ssh/known_hosts'
        logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
        logger.info("updating host files for controller nodes & upload ssh keys to enable password less ssh between ceph/controllers")
        cmd = 'cat /root/.ssh/id_rsa.pub'
        myKey, err = Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd )
        monitorList = ''
        monitorListShort = ''
        monHosts = 'mon_host = '
        
        logger.info("build up storage network host file for all the controllers")
        controllersEtcHosts = []
        for host in self.settings.controller_nodes :
            etc = cmd = 'echo "' + host.provisioning_ip + '  ' + host.hostname + "-storage." + self.settings.domain +'  ' + host.hostname + '-storage" >> /etc/hosts'
            controllersEtcHosts.append(etc)
        for host in self.settings.controller_nodes :
            monitorList = monitorList +  host.hostname + '-storage '
            monitorListShort = monitorListShort + host.hostname + " "
            
            cmd = 'echo "' + self.settings.ceph_node.provisioning_ip+ '  ' + self.settings.ceph_node.hostname + "." + self.settings.domain +'  ' + self.settings.ceph_node.hostname + ' " >> /etc/hosts'
            logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd))
            
            cmd = 'echo "' + host.provisioning_ip + '  ' + host.hostname + "." + self.settings.domain +'  ' + host.hostname + ' " >> /etc/hosts'
            logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd))
            
            cmd = 'echo "' + host.provisioning_ip + '  ' + host.hostname + "-storage." + self.settings.domain +'  ' + host.hostname + '-storage" >> /etc/hosts'
            logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd))
            monHosts = monHosts + host.storage_ip + ', ' 
            # Update the /etc/hosts on all controller so they can resolve each others over the storage network.
            for each in controllersEtcHosts:
                logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password,each))
                
        monHosts = monHosts[:-1]
        monHosts = monHosts[:-1]
        cmd = 'cd ~/cluster;ceph-deploy new ' + monitorList
        logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd)    )
        
        logger.info("Updating ceph.conf")
        logger.info("ceph.conf before updating :: ")
        logger.info(Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,"cat /root/cluster/ceph.conf" ))
        toAdd = ['public network = ' + self.settings.storage_network.replace('\n', ""),
                 'cluster network = ' + self.settings.storage_cluster_network.replace('\n', ""),
                 'osd pool default size = 2'
                 ]
        for sett in toAdd:
            cmd = 'echo "'+ sett +'" >> /root/cluster/ceph.conf'
            logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        logger.info("ceph.conf updating mon_hosts to use the public network")
        cmd = 'sed -i "s/mon_host =.*/'+monHosts+'/" /root/cluster/ceph.conf'
        logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
        logger.info("ceph deploy.")
        cmd = 'cd ~/cluster;ceph-deploy install ' + monitorListShort
        logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
        logger.info("temporary rename the host to the storage network")
        for host in self.settings.controller_nodes :
            cmd = 'hostname ' + host.hostname + "-storage"
            logger.info( self.execute_as_shell(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd ))
        
        logger.info("The hostname of each Ceph monitor host must be temporarily changed to the storage network hostname.")
        for host in self.settings.controller_nodes :
            cmds = [
                    #'hostname ' + host.hostname + "-storage",
                    'iptables -I INPUT 1 -p tcp --dport 6789 -j ACCEPT',
                    'service iptables save',
                    'iptables -I INPUT 1 -p tcp --dport 6789 -j  ACCEPT',
                    'service iptables save',
                    'iptables -I INPUT 1 -p tcp --dport 6789 -j  ACCEPT',
                    'service iptables save'
                    ]
            for each in cmds :
                logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password,each))
            
        logger.info("Create the initial monitors")
        cmd = 'cd ~/cluster;ceph-deploy mon create-initial'
        logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
        logger.info("revert the host names")
        for host in self.settings.controller_nodes :
            cmd = 'hostname ' + host.hostname 
            logger.info( self.execute_as_shell(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd ))
    
    
    def configure_osd(self):
        logger.info("OSD configuration")
        
        
        logger.info("build up storage network host file for all the storage nodes/ on ice controller & for the storage nodes to resolve the cpeh host")
        
        for host in self.settings.ceph_nodes :

            cmd = 'echo "' + self.settings.ceph_node.provisioning_ip+ '  ' + self.settings.ceph_node.hostname + "." + self.settings.domain +'  ' + self.settings.ceph_node.hostname + ' " >> /etc/hosts'
            logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd))
            
            cmd = 'echo "' + host.provisioning_ip + '  ' + host.hostname + "." + self.settings.domain +'  ' + host.hostname + ' " >> /etc/hosts'
            logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd))
            
        
        logger.info("installing ceph on storage nodes")
        for each in self.settings.ceph_nodes:
            cmd = 'cd ~/cluster;ceph-deploy install ' + each.hostname
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
            
        logger.info("open up ports on storage nodes")
        cmds = [
                'iptables -I INPUT 1 -p tcp -m multiport --dports 6800-6840 -j ACCEPT',
                'service iptables save'
                ]
        for host in self.settings.ceph_nodes:
            for each in cmds :
                logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password,each))
        
                logger.info("list disks (?)")
                cmd = 'cd ~/cluster;ceph-deploy disk list ' + host.hostname
                logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
                logger.info("clear partitions")
                cmd = 'cd ~/cluster;ceph-deploy osd disk zap ' + host.hostname + ':/dev/sdb'
                logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
                
                logger.info("Partition data disks ")
                disksCmds = [
                            'cd ~/cluster;ceph-deploy osd create ' + host.hostname + ':/dev/sdb',    #:/dev/sdl
                            'cd ~/cluster;ceph-deploy osd create ' + host.hostname + ':/dev/sdc',    #:/dev/sdl
                            'cd ~/cluster;ceph-deploy osd create ' + host.hostname + ':/dev/sdd',   #
                            'cd ~/cluster;ceph-deploy osd create ' + host.hostname + ':/dev/sde', #:/dev/sdl
                            'cd ~/cluster;ceph-deploy osd create ' + host.hostname + ':/dev/sdf',  #:/dev/sdl
                            'cd ~/cluster;ceph-deploy osd create ' + host.hostname + ':/dev/sdg',  #:/dev/sdm
                            'cd ~/cluster;ceph-deploy osd create ' + host.hostname + ':/dev/sdh', #:/dev/sdm
                            'cd ~/cluster;ceph-deploy osd create ' + host.hostname + ':/dev/sdi', #:/dev/sdm
                            'cd ~/cluster;ceph-deploy osd create ' + host.hostname + ':/dev/sdj', #:/dev/sdm
                            'cd ~/cluster;ceph-deploy osd create ' + host.hostname + ':/dev/sdk', #:/dev/sdm
                         ]
                for cmd in disksCmds:
                    logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
    
    
    def connectHostsToCalamari(self):
        logger.info("Connect the hosts to the calamari server")     
        for host in self.settings.controller_nodes:
            cmd = 'cd ~/cluster;ceph-deploy calamari connect ' + host.hostname
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
        for host in self.settings.ceph_nodes:
            cmd = 'cd ~/cluster;ceph-deploy calamari connect ' + host.hostname
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
                
    
    def execute_as_shell(self, address,usr, pwd, command):
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
            if buff.endswith("'s password: "):
                channel.send(self.settings.nodes_root_password + "\n")
            if buff.endswith("(yes/no)? "):
                channel.send("yes\n")
 
                 
        return buff