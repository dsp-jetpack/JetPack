from osp_deployer.config import Settings
from auto_common import Ssh, Scp,  Widget, UI_Manager, FileHelper
import time
import logging, paramiko
logger = logging.getLogger(__name__)
from math import log
import uuid
class Ceph():
    '''
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
                'iptables -I INPUT 1 -p tcp -m multiport --dports 6800:6840 -j ACCEPT',
                'service iptables save'
                ]
        for host in self.settings.ceph_nodes:
            for each in cmds :
                logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password,each))
        
                logger.info("list disks (?)")
                cmd = 'cd ~/cluster;ceph-deploy disk list ' + host.hostname
                logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
                logger.info("clear partitions")
                # Cgecj ,, NOT osd disk zap in docs , else update docs..
                #    ':/dev/sdk',#:/dev/sdm
                     
                logger.info("Partition data disks & recreate disks ")
                for disk in host.osd_disks:
                    cmds = [
                            'cd ~/cluster;ceph-deploy disk zap ' + host.hostname + disk,
                            'cd ~/cluster;ceph-deploy osd create ' + host.hostname + disk
                            ]
                
                    for cmd in cmds:
                        logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
    
    def connectHostsToCalamari(self):
        logger.info("Connect the hosts to the calamari server")     
        for host in self.settings.controller_nodes:
            cmd = 'cd ~/cluster;ceph-deploy calamari connect ' + host.hostname
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
        for host in self.settings.ceph_nodes:
            cmd = 'cd ~/cluster;ceph-deploy calamari connect ' + host.hostname
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
        url = self.settings.ceph_node.public_ip
        UI_Manager.driver().get("http://" + url)   
        
        username = Widget("//input[@name='username']")
        password = Widget("//input[@name='password']")
        
        username.setText("root")
        password.setText(self.settings.ceph_node.root_password)
        
        login = Widget("//button[@name='login']")
        login.click()
        
        addButton = Widget("//button[.='ADD']")
        addButton.waitFor(20)
        addButton.click()
        
        initialized = Widget("//div[.='Cluster Initialized.']")
        while initialized.exists() ==  False:
            time.sleep(5)
            logger.info("waitinf for cluster to initialize .")
        closeButton = Widget("//button[.='Close']")
        closeButton.click()
        
        
    def grantAdminRightsToOSD(self):
        logger.info("grant admin rights to the storage nodes")
        for each in self.settings.ceph_nodes:
            cmd = 'cd ~/cluster;ceph-deploy admin ' + each.hostname
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
            
    def modifyOSDPlacementGroups(self):
        logger.info("mofidy the OSD placement groups")
        osds = 0
        for each in self.settings.ceph_nodes:
            add = len(each.osd_disks) -1
            osds = osds +  add
        cal =   (osds * 100) / 2
        pgroups = pow(2, int(log(cal, 2) + 0.5))
        cmds = [
                'ceph osd pool set data pg_num ' + str(pgroups),
                'ceph osd pool set data pgp_num '+ str(pgroups)
                ]    
        self.settings.placement_groups = str(pgroups)
        for cmd in cmds:
            logger.info(Ssh.execute_command(self.settings.controller_nodes[0].provisioning_ip, "root", self.settings.nodes_root_password, cmd))
      
    def pool_and_keyRing_configuration(self):
        logger.info("ceph pool creation and keyring configuration")
        cmds = [
                'ceph osd pool create images ' + self.settings.placement_groups,
                'ceph osd pool create volumes ' + self.settings.placement_groups,
                'ceph osd pool create backups ' + self.settings.placement_groups,
                'ceph osd lspools',
                "ceph auth get-or-create client.images mon 'allow r' osd 'allow class-read object_prefix rbd_children, allow rwx pool=images'",
                "ceph auth get-or-create client.images > /etc/ceph/ceph.client.images.keyring",
                "ceph auth get-or-create client.volumes mon 'allow r' osd 'allow class-read object_prefix rbd_children, allow rwx pool=volumes, allow rx pool=images'",
                "ceph auth get-or-create client.volumes > /etc/ceph/ceph.client.volumes.keyring",
                "ceph auth get-or-create client.backups mon 'allow r' osd 'allow class-read object_prefix rbd_children, allow rwx pool=backups'",
                "ceph auth get-or-create client.backups > /etc/ceph/ceph.client.backups.keyring ",
                "ceph auth list"
                ] 
        for cmd in cmds:
            logger.info(Ssh.execute_command(self.settings.controller_nodes[0].provisioning_ip, "root", self.settings.nodes_root_password, cmd))
        logger.info("updating ceph.conf")
        moreCmds = [
                    'echo "[client.images]" >> /etc/ceph/ceph.conf',
                    'echo "keyring = /etc/ceph/ceph.client.images.keyring" >> /etc/ceph/ceph.conf',
                    'echo "[client.volumes]" >> /etc/ceph/ceph.conf',
                    'echo "keyring = /etc/ceph/ceph.client.volumes.keyring" >> /etc/ceph/ceph.conf',
                    'echo "[client.backups]" >> /etc/ceph/ceph.conf',
                    'echo "keyring = /etc/ceph/ceph.client.backups.keyring" >> /etc/ceph/ceph.conf'
                    ]   
        for cmd in moreCmds:
            logger.info(Ssh.execute_command(self.settings.controller_nodes[0].provisioning_ip, "root", self.settings.nodes_root_password, cmd))
        
        logger.info("Pull the new configuration file to the ICE Administration host.")
        cmd = 'cd ~/cluster/;ceph-deploy --overwrite-conf config pull ' + self.settings.controller_nodes[0].hostname
        logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        
        logger.info("Copy the clients keyrings to the ICE admin host")
        cmds = [
                'ssh '+ self.settings.controller_nodes[0].hostname +' "cat /etc/ceph/ceph.client.backups.keyring" >  ~/cluster/ceph.client.backups.keyring',
                'ssh '+ self.settings.controller_nodes[0].hostname +' "cat /etc/ceph/ceph.client.images.keyring" >  ~/cluster/ceph.client.images.keyring',
                'ssh '+ self.settings.controller_nodes[0].hostname +' "cat /etc/ceph/ceph.client.volumes.keyring" >  ~/cluster/ceph.client.volumes.keyring',
                ]
        for cmd in cmds:
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
        logger.info("Deploy new config file to all configured OSP controller and Ceph nodes.")
        cmd = 'cd ~/cluster/;ceph-deploy --overwrite-conf config push'
        for each in self.settings.controller_nodes:
            if each.hostname != self.settings.controller_nodes[0].hostname:
                cmd = cmd + " " + each.hostname
        for each in self.settings.ceph_nodes:
            cmd = cmd + " " + each.hostname
        logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
    
        logger.info("Copy the /etc/ceph/ceph.client.images.keyring, /etc/ceph/ceph.client.volumes.keyring and /etc/ceph/ceph.client.backups.keyring to each monitor's /etc/ceph directory. ")
        
        for each in self.settings.controller_nodes:
            if each.hostname != self.settings.controller_nodes[0].hostname:
                cmds = [
                    'cd ~/cluster/;scp ceph.client.backups.keyring ceph.client.images.keyring ceph.client.volumes.keyring '+each.hostname+':', 
                    'ssh '+each.hostname+' "cp ceph.client.images.keyring /etc/ceph"',
                    'ssh '+each.hostname+' "cp ceph.client.volumes.keyring /etc/ceph"' 
                    'ssh '+each.hostname+' "cp ceph.ceph.client.backups.keyring /etc/ceph"' 
                    ]
                for cmd in cmds :
                    logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
    
    def foreman_config_ha_all_in_One(self):
        logger.info("Foreman Configuration All in One Controler")
        
        cmd = 'uuidgen -t'
        r_out, r_err =   Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password, cmd)
        uuid = r_out.replace("\n", "").replace("\r", "")  
        print "uuid  ::: [" + uuid + "]"
        self.settings.uuid = str(uuid)
        
        
        __locator_user_input = Widget("//input[@id='login_login']")
        __locator_password_input = Widget("//input[@id='login_password']")
        __locator_login_button = Widget("//input[@name='commit']")
        url = self.settings.foreman_node.public_ip
        UI_Manager.driver().get("http://" + url)
        if __locator_user_input.exists():
            __locator_user_input.setText("admin")
            __locator_password_input.setText(self.settings.foreman_password)
            __locator_login_button.click()
            time.sleep(10)
        
        
        url = self.settings.foreman_node.public_ip
        UI_Manager.driver().get("http://" + url +"/hostgroups/")
        
        allInOne = Widget("//a[.='HA All In One Controller']")
        allInOne.waitFor(20)
        allInOne.click()
        
        paramLink = Widget("//a[.='Parameters']")
        paramLink.waitFor(20)
        paramLink.click()
   
        
        backend_rbd_override = Widget("//span[.='quickstack::pacemaker::cinder']/../..//span[.='backend_rbd']/../..//a[.='override']")
        rdb_secret_override = Widget("//span[.='quickstack::pacemaker::cinder']/../..//span[.='rbd_secret_uuid']/../..//a[.='override']")
        backend_rbd_override.click()
        rdb_secret_override.click()
        
        glance_backEnd_override = Widget("//span[.='quickstack::pacemaker::glance']/../..//span[.='backend']/../..//a[.='override']")
        pcmk_fs_manage_override = Widget("//span[.='quickstack::pacemaker::glance']/../..//span[.='pcmk_fs_manage']/../..//a[.='override']")
        glance_backEnd_override.click()
        pcmk_fs_manage_override.click()
        
        #VolumeOverrride = Widget(" //span[.='quickstack::pacemaker::cinder']/../..//span[.='volume']/../..//a[.='override']")
        #VolumeOverrride.click()
       
        
        inputs =   UI_Manager.driver().find_elements_by_xpath("//textarea[@placeholder='Value']")
        
        inputs[0].clear();
        inputs[0].send_keys("true");
        
        inputs[1].clear();
        inputs[1].send_keys(self.settings.uuid);
        
        inputs[2].clear();
        inputs[2].send_keys("rbd");
        
        inputs[3].clear();
        inputs[3].send_keys("false");
        
        #inputs[4].clear();
        #inputs[4].send_keys("true");
        
        sub = Widget("//input[@value='Submit']")
        sub.click()
        time.sleep(10)
        
    def foreman_config_compute(self):
        logger.info("Foreman Configuration Compute ( Nova )")
        
        __locator_user_input = Widget("//input[@id='login_login']")
        __locator_password_input = Widget("//input[@id='login_password']")
        __locator_login_button = Widget("//input[@name='commit']")
        url = self.settings.foreman_node.public_ip
        UI_Manager.driver().get("http://" + url)
        if __locator_user_input.exists():
            __locator_user_input.setText("admin")
            __locator_password_input.setText(self.settings.foreman_password)
            __locator_login_button.click()
            time.sleep(10)
        
        
        url = self.settings.foreman_node.public_ip
        UI_Manager.driver().get("http://" + url +"/hostgroups/")
        
        compute = Widget("//a[.='Compute (Nova Network)']")
        compute.waitFor(20)
        compute.click()
        
        paramLink = Widget("//a[.='Parameters']")
        paramLink.waitFor(20)
        paramLink.click()
   
        
        
        cinder_backend_rbd = Widget("//span[.='quickstack::nova_network::compute']/../..//span[.='cinder_backend_rbd']/../..//a[.='override']")
        rbd_secret_uuid = Widget("//span[.='quickstack::nova_network::compute']/../..//span[.='rbd_secret_uuid']/../..//a[.='override']")
        
        cinder_backend_rbd.click()
        rbd_secret_uuid.click()
        
        inputs =   UI_Manager.driver().find_elements_by_xpath("//textarea[@placeholder='Value']")
        
        inputs[0].clear();
        inputs[0].send_keys("true");
        
        inputs[1].clear();
        inputs[1].send_keys(self.settings.uuid);
        
        
        
        sub = Widget("//input[@value='Submit']")
        sub.click()
        time.sleep(10)
        
        
        
        
        
        
    def libvirt_config(self):
        logger.info("Libvirst Configuration")
        cmd = "cd ~/cluster;cat ceph.client.volumes.keyring | grep key | awk '{print $3}'| tee client.volumes.key"
        logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd))
        ls = [
              "<secret ephemeral='no' private='no'>",
            "<uuid>"+self.settings.uuid+"</uuid>",
            "<usage type='ceph'>",
            "<name>client.volumes secret</name>",
            "</usage>",
            "</secret>"
            ]
        for each in ls:
            cmd = 'echo "' + each + '" >> ~/cluster/secret.xml'
            logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd))
        logger.info("Copy the secret.xml file and client.volumes.key file to each compute node")
        for host in self.settings.compute_nodes:
            cmd = 'echo "' + host.provisioning_ip + '  ' + host.hostname + "." + self.settings.domain +'  ' + host.hostname + ' " >> /etc/hosts'
            logger.info( Ssh.execute_command(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd))
            cmd = 'cd ~/cluster/;scp secret.xml client.volumes.key ' + host.hostname+':'
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
            cmd = 'virsh secret-define --file secret.xml'
            logger.info( self.execute_as_shell_expectPasswords(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd ))
            cmd = "virsh secret-set-value --secret "+self.settings.uuid+" --base64 `cat client.volumes.key`"
            logger.info( self.execute_as_shell_expectPasswords(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd ))
            cmd = 'virsh secret-list'
            logger.info( self.execute_as_shell_expectPasswords(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd ))
            
    def deploy_ceph_to_compute_hosts(self):
        logger.info("Deploy ceph configuration to compute hosts")
        for each in self.settings.compute_nodes:
            cmd = 'cd ~/cluster;ceph-deploy config push ' + each.hostname
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
            
            cmd = 'scp ~/cluster/ceph.client.images.keyring ~/cluster/ceph.client.volumes.keyring ~/cluster/ceph.client.backups.keyring '+ each.hostname + ":"
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
            
            cmd = 'ssh '+ each.hostname + ' cp ceph.client.images.keyring ceph.client.volumes.keyring ceph.client.backups.keyring /etc/ceph'
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.provisioning_ip, "root", self.settings.ceph_node.root_password,cmd ))
            
            
    def configure_cinder_for_backup(self):
        logger.info("Configure Cinder for backups")
        for each in self.settings.controller_nodes:
            cmds = [
                    'openstack-config --set /etc/cinder/cinder.conf DEFAULT backup_ceph_conf /etc/ceph/ceph.conf',
                    'openstack-config --set /etc/cinder/cinder.conf DEFAULT backup_ceph_user backups',
                    'openstack-config --set /etc/cinder/cinder.conf DEFAULT backup_ceph_chunk_size 13421772',
                    'openstack-config --set /etc/cinder/cinder.conf DEFAULT backup_ceph_pool backup',
                    'openstack-config --set /etc/cinder/cinder.conf DEFAULT backup_ceph_stripe_unit 0',
                    'openstack-config --set /etc/cinder/cinder.conf DEFAULT backup_ceph_stripe_count 0',
                    'openstack-config --set /etc/cinder/cinder.conf DEFAULT restore_discard_excess_bytes true',
                    'openstack-config --set /etc/cinder/cinder.conf DEFAULT backup_driver cinder.backup.drivers.ceph',
                    'pcs resource disable openstack-cinder-backup',
                    'pcs resource enable openstack-cinder-backup',
                    ]
        for each in self.settings.controller_nodes:
             for cmd in cmds:
                 logger.info(Ssh.execute_command(each.provisioning_ip, "root", self.settings.nodes_root_password, cmd)[0])
       
    def configure_missing_bits_from_docs(self):
        logger.info("Configure Additional ceph/cinder settings on controller & compute nodes")
        cmds = [
             'openstack-config --set /etc/glance/glance-api.conf DEFAULT default_store rbd',
             'openstack-config --set /etc/glance/glance-api.conf DEFAULT show_image_direct_url true', 
             'openstack-config --set /etc/glance/glance-api.conf DEFAULT rbd_store_ceph_conf /etc/ceph/ceph.conf', 
             'openstack-config --set /etc/glance/glance-api.conf DEFAULT rbd_store_user images', 
             'openstack-config --set /etc/glance/glance-api.conf DEFAULT rbd_store_pool images', 
             'openstack-config --set /etc/glance/glance-api.conf DEFAULT rbd_store_chunk_size 8',
             'pcs resource disable openstack-glance-api',
             'pcs resource enable openstack-glance-ap',
             'openstack-config --set /etc/cinder/cinder.conf DEFAULT rbd_pool volumes',
             'openstack-config --set /etc/cinder/cinder.conf DEFAULT rbd_user volumes',
             'openstack-config --set /etc/cinder/cinder.conf DEFAULT rbd_flatten_volume_from_snapshot false',
             'openstack-config --set /etc/cinder/cinder.conf DEFAULT rbd_ceph_conf /etc/ceph/ceph.conf',
             'openstack-config --set /etc/cinder/cinder.conf DEFAULT rbd_secret_uuid ' + self.settings.uuid,
             'openstack-config --set /etc/cinder/cinder.conf DEFAULT volume_driver cinder.volume.drivers.rbd.RBDDriver', 
             'openstack-config --set /etc/cinder/cinder.conf DEFAULT rbd_max_clone_depth 5', 
             'systemctl start openstack-cinder-volume'
              #'pcs resource disable openstack-cinder-volume',    
              #'pcs resource enable openstack-cinder-volume' 
            ]
        for host in self.settings.controller_nodes:
            for cmd in cmds:
                logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password, cmd)[0])
        
        cmds = [
                'yum -y install openstack-utils',
                'openstack-config --set /etc/nova/nova.conf libvirt libvirt_images_type rbd', 
                'openstack-config --set /etc/nova/nova.conf libvirt libvirt_images_rbd_pool volumes', 
                'openstack-config --set /etc/nova/nova.conf libvirt libvirt_images_rbd_ceph_conf /etc/ceph/ceph.conf', 
                'openstack-config --set /etc/nova/nova.conf libvirt libvirt_inject_password false',
                'openstack-config --set /etc/nova/nova.conf libvirt libvirt_inject_key false',
                'openstack-config --set /etc/nova/nova.conf libvirt libvirt_inject_partition -2', 
                'openstack-config --set /etc/nova/nova.conf libvirt rbd_user volumes ',
                'openstack-config --set /etc/nova/nova.conf libvirt rbd_secret_uuid ' + self.settings.uuid,
                'systemctl restart openstack-nova-compute'
                ]
        for host in self.settings.compute_nodes:
            for cmd in cmds:
                logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password, cmd)[0])
        
        cmds = [
                'systemctl start openstack-cinder-volume',
                'pcs resource disable openstack-nova-consoleauth',
               'pcs resource disable openstack-nova-api',
               'pcs resource disable openstack-nova-conductor',
               'pcs resource disable openstack-nova-scheduler',
               'pcs resource disable openstack-glance-registry',
               'pcs resource disable openstack-glance-api',
               'pcs resource enable openstack-nova-consoleauth',
               'pcs resource enable openstack-nova-api',
               'pcs resource enable openstack-nova-conductor',
               'pcs resource enable openstack-nova-scheduler',
               'pcs resource enable openstack-glance-registry',
               'pcs resource enable openstack-glance-api',
                'pcs resource disable openstack-cinder-api',
               'pcs resource disable openstack-cinder-scheduler',
               'pcs resource enable openstack-cinder-api',
               'pcs resource enable openstack-cinder-scheduler'
               'pcs resource disable openstack-cinder-volume',
               'resource enable openstack-cinder-volume'
            ]
        for each in self.settings.controller_nodes:
            for cmd in cmds:
                logger.info(Ssh.execute_command(each.provisioning_ip, "root", self.settings.nodes_root_password, cmd)[0])
   
            
    
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