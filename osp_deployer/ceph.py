#!/usr/bin/env python

# OpenStack - A set of software tools for building and managing cloud computing
# platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.

from osp_deployer.config import Settings
from auto_common import Ssh, Scp,  Widget, UI_Manager, FileHelper
import time, os ,sys, logging, paramiko
logger = logging.getLogger(__name__)
from math import log
import uuid
class Ceph():
    '''
    '''

    def __init__(self):
        self.settings = Settings.settings


    def pre_installation_configuration(self):
        logger.info( "Ceph Pre-Installation Configuration Requirements")

        logger.info("Sudo access")
        allNodes = self.settings.controller_nodes + self.settings.compute_nodes + self.settings.ceph_nodes
        allNodes.append(self.settings.ceph_node)

        for each in allNodes:
            cmd = 'echo "' + each.storage_ip + ' ' + each.hostname + "." + self.settings.domain +' ' + each.hostname + ' " >> /etc/hosts'
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd))
        cmd = 'ssh-keygen'
        logger.info( self.execute_as_shell_for_sshkeygen(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd))

        cmd = 'HOSTS=`grep '+self.settings.domain+' /etc/hosts | grep -v '+self.settings.ceph_node.hostname+' | cut -d " " -f 3` ; echo $HOSTS;  for HOST in $HOSTS; do ssh-copy-id $HOST; done'
        logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password, cmd))

        cmd = 'HOSTS=`grep '+self.settings.domain +' /etc/hosts | grep -v '+self.settings.ceph_node.hostname+" | cut -d \" \" -f 3` ;for HOST in $HOSTS; do ssh $HOST 'echo -e \""+ self.settings.ceph_node.storage_ip + ' ' + self.settings.ceph_node.hostname + "." + self.settings.domain + ' ' + self.settings.ceph_node.hostname +"\" >> /etc/hosts';done"
        logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password, cmd))

        for host in self.settings.controller_nodes:
            cmds = [
                'yum -y install ceph-radosgw',
                "echo 'Defaults:root !requiretty' > /etc/sudoers.d/root",
                ]
            for cmd in cmds:
                logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd ))

        logger.info("Non-root Administrative User")

        cmd = 'HOSTS=`grep '+ self.settings.domain +" /etc/hosts | cut -d \" \" -f 3`; for HOST in $HOSTS; do ssh root@$HOST 'useradd -g adm -m ceph-user';done;for HOST in $HOSTS; do ssh root@$HOST 'passwd ceph-user'; done"
        logger.info( self.execute_as_shell_for_passwd(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd, self.settings.ceph_user_password))

        cmd = 'HOSTS=`grep '+ self.settings.domain +" /etc/hosts | cut -d \" \" -f 3`;for HOST in $HOSTS; do ssh root@$HOST 'echo -e \"ceph-user ALL = (root) NOPASSWD:ALL\" > /etc/sudoers.d/ceph-user';done"
        logger.info( self.execute_as_shell_for_passwd(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd, self.settings.ceph_user_password))

        cmd = 'HOSTS=`grep '+ self.settings.domain +" /etc/hosts | cut -d \" \" -f 3`;" + "for HOST in $HOSTS; do ssh root@$HOST 'echo -e \"Defaults:ceph-user !requiretty\" >> /etc/sudoers.d/ceph-user'; done"
        logger.info( self.execute_as_shell_for_passwd(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd, self.settings.ceph_user_password))

        cmd = 'HOSTS=`grep '+ self.settings.domain +" /etc/hosts | cut -d \" \" -f 3`;" + "for HOST in $HOSTS; do ssh root@$HOST 'chmod 0440 /etc/sudoers.d/ceph-user'; done"
        logger.info( self.execute_as_shell_for_passwd(self.settings.ceph_node.public_ip, "root", self.settings.ceph_node.root_password,cmd, self.settings.ceph_user_password))

        logger.info("SSH Key Authentication")

        cmd = 'ssh-keygen'
        logger.info( self.execute_as_shell_for_sshkeygen(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password,cmd))
        cmd = 'HOSTS=`grep '+self.settings.domain+' /etc/hosts | grep -v '+self.settings.ceph_node.hostname+' | cut -d " " -f 3` ; echo $HOSTS;  for HOST in $HOSTS; do ssh-copy-id $HOST; done'
        logger.info( self.execute_as_shell_for_sshkeygen(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password,cmd))



    def setup_calamari_node(self):

        if self.settings.ceph_version == "1.2.3":

            logger.info( "copying Ceph Iso" )
            cmd = "mkdir /home/ceph-user/ceph-iso"
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password, cmd))
            file = 'rhceph-1.2.3-rhel-7-x86_64.iso'
            localfile = self.settings.ceph_iso
            remotefile = '/home/ceph-user/ceph-iso/' + file
            logger.info( "remote file " + remotefile)
            print "local :-> " + localfile
            print "remote :-> " + remotefile
            Scp.put_file(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password, localfile, remotefile)
            cmd = 'sudo mount '+remotefile+' /mnt'
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password, cmd))

            logger.info("copying certificates")
            cmds = [
                'sudo cp /mnt/RHCeph-Calamari-1.2-x86_64-c1e8ca3b6c57-285.pem /etc/pki/product/285.pem',
                'sudo cp /mnt/RHCeph-Installer-1.2-x86_64-8ad6befe003d-281.pem /etc/pki/product/281.pem',
                'sudo cp /mnt/RHCeph-MON-1.2-x86_64-d8afd76a547b-286.pem /etc/pki/product/286.pem',
                'sudo cp /mnt/RHCeph-OSD-1.2-x86_64-25019bf09fe9-288.pem /etc/pki/product/288.pem'
            ]
            for cmd in cmds :
                logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password, cmd))

            logger.info("install the setup script")
            cmd = 'sudo yum -y install /mnt/ice_setup-*.rpm'
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password, cmd))

            cmd = 'mkdir ~/cluster && cd ~/cluster'
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            logger.info("removing installation prompts")
            commands = ['sudo sed -i "s/fqdn = prompt.*/return \'http\', fallback_fqdn/" /usr/lib/python2.7/site-packages/ice_setup/ice.py',
                        "sudo sed -i 's/prompt_continue()$//' /usr/lib/python2.7/site-packages/ice_setup/ice.py",
                        "sudo sed -i 's/package_path = get_package_path(package_path)/package_path = \"\\/mnt\"/' /usr/lib/python2.7/site-packages/ice_setup/ice.py"
                        ]
            for cmd in commands :
                logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            logger.info("installing ice")
            cmd = 'cd ~/cluster;sudo ice_setup -d /mnt'
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            cmd = 'cd ~/cluster;ceph-deploy config pull ' + self.settings.controller_nodes[0].hostname
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            cmd = "cd ~/cluster;sed -i '/osd_journal_size = .*/a [osd]\\nosd pool default pg num = 1024\\nosd pool default pgp num = 1024' ceph.conf"
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            cmd = 'cd ~/cluster;sudo calamari-ctl initialize --admin-username root --admin-password '+self.settings.ceph_node.root_password+' --admin-email ' + self.settings.ceph_admin_email
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

        elif self.settings.ceph_version == "1.3":

            logger.info (" installing ice ")
            cmd = "sudo yum install ice_setup* -y"
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password, cmd))

            cmd = 'mkdir ~/cluster && cd ~/cluster'
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            radosgw_scripts = [
                'radosgw_config.sh',
                'swift_config.sh'
                ]
            for file in radosgw_scripts  :
                localfile = self.settings.foreman_configuration_scripts + "/utils/networking/" + file if sys.platform.startswith('linux') else  self.settings.foreman_configuration_scripts + "\\utils\\networking\\" + file
                remotefile = '/home/ceph-user/cluster/' + file
                print localfile + " >> " + remotefile
                Scp.put_file(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password, localfile, remotefile)

                cmd = 'chmod u+x ' + remotefile
                print Ssh.execute_command(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password, cmd)

            logger.info("removing installation prompts")
            commands = ['sudo sed -i "s/fqdn = prompt.*/return \'http\', fallback_fqdn/" /usr/lib/python2.7/site-packages/ice_setup/ice.py',
                        "sudo sed -i 's/prompt_continue()$//' /usr/lib/python2.7/site-packages/ice_setup/ice.py",
                        "sudo sed -i 's/package_path = get_package_path(package_path)/package_path = \"\\/mnt\"/' /usr/lib/python2.7/site-packages/ice_setup/ice.py"
                        ]
            for cmd in commands :
                logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            cmds = ['sudo yum install ceph-deploy calamari-server calamari-clients -y',
                    'sudo ice_setup update all',
                    'cd ~/cluster;ceph-deploy config pull ' + self.settings.controller_nodes[0].hostname,
                    "cd ~/cluster;sed -i '/osd_pool_default_size = .*/a osd_pool_default_min_size = 2' ceph.conf",
                    "cd ~/cluster;sed -i '/osd_journal_size = .*/a osd pool default pg num = 4096\\nosd pool default pgp num = 4096\\nmax_open_files = 131072' ceph.conf",
                    'cd ~/cluster;sudo calamari-ctl initialize --admin-username root --admin-password '+self.settings.ceph_node.root_password+' --admin-email ' + self.settings.ceph_admin_email
                    ]
            for cmd in cmds :
                logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

        else:
            raise AssertionError("Somebody set us up the bomb, " +  self.settings.ceph_version + " is not a version we know about  (valid versions are 1.2.3 or 1.3 ")



    def configure_monitor(self):

        if self.settings.ceph_version == "1.2.3":

            cmd = 'HOSTS=`grep '+self.settings.domain+' /etc/hosts | cut -d " " -f 3` ;cd ~/cluster;for HOST in $HOSTS; do ceph-deploy install $HOST; done'
            logger.info( self.execute_as_shell(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))


            cmd = 'cd ~/cluster;ceph-deploy --overwrite-conf mon create-initial'
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            logger.info("gathering keys from the controller nodes ")
            cmd = 'cd ~/cluster;ceph-deploy gatherkeys '
            for host in self.settings.controller_nodes :
                cmd = cmd +  host.hostname + ' '
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            cmd = 'cd ~/cluster;ceph-deploy admin ' + self.settings.ceph_node.hostname
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))
        else:
            for host in self.settings.controller_nodes:
                cmd = "cd ~/cluster;ceph-deploy install --mon " + host.hostname
                logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            cmd  = "ceph-deploy install --cli "+ self.settings.ceph_node.hostname
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            cmd = 'cd ~/cluster;ceph-deploy --overwrite-conf mon create-initial'
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            cmd = 'cd ~/cluster;ceph-deploy admin ' + self.settings.ceph_node.hostname
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))








    def configure_osd(self):
       logger.info("OSD configuration")


       for host in self.settings.ceph_nodes:

            if self.settings.ceph_version != "1.2.3":
                cmd = "ceph-deploy install --osd " + host.hostname
                logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            logger.info("list disks (?)")
            cmd = 'cd ~/cluster;ceph-deploy disk list ' + host.hostname
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            logger.info("Partition data disks & recreate disks ")
            for disk in host.journal_disks:
                cmd = 'cd ~/cluster;ceph-deploy disk zap ' + host.hostname + disk
                logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))

            for disk in host.osd_disks:
                cmds = [
                        'cd ~/cluster;ceph-deploy disk zap ' + host.hostname + disk,
                        'cd ~/cluster;ceph-deploy --overwrite-conf osd create ' + host.hostname + disk
                        ]

                for cmd in cmds:
                    logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.public_ip,  "ceph-user", self.settings.ceph_user_password,cmd))


    def connectHostsToCalamari(self):
        logger.info("Connect the hosts to the calamari server")
        for host in self.settings.controller_nodes:
            if self.settings.ceph_version == "1.2.3":
                cmd = 'cd ~/cluster;ceph-deploy calamari connect ' + host.hostname
                logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password,cmd))
            else:
                cmd = 'cd ~/cluster;ceph-deploy calamari connect --master ' + self.settings.ceph_node.hostname + '.' + self.settings.domain + ' ' + host.hostname
                logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password,cmd))

        for host in self.settings.ceph_nodes:
            cmd = 'cd ~/cluster;ceph-deploy calamari connect ' + ("" if (self.settings.ceph_version == "1.2.3") else "--master " + self.settings.ceph_node.hostname + '.' + self.settings.domain)  + ' ' + host.hostname
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password,cmd))

        # ...
        print("give time to calamari to pick up the nodes.")
        time.sleep(180)

        url = self.settings.ceph_node.public_ip
        UI_Manager.driver().get("http://" + url)
        time.sleep(15)

        username = Widget("//input[@name='username']")
        password = Widget("//input[@name='password']")

        while username.exists() is False :
            UI_Manager.driver().get("http://" + url)
            time.sleep(20)

        username.setText("root")
        password.setText(self.settings.ceph_node.root_password)

        login = Widget("//button[@name='login']")
        login.click()

        addButton = Widget("//button[.='ADD']")
        addButton.waitFor(20)
        addButton.click()

        time.sleep(60)
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
            logger.info( self.execute_as_shell_expectPasswords(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password,cmd))

    def pool_and_keyRing_configuration(self):
        logger.info("ceph pool creation and keyring configuration")
        cmds = [
                'sudo chmod 644 /etc/ceph/ceph.client.admin.keyring',
                'cd ~/cluster;ceph osd pool create images 512 512',
                'cd ~/cluster;ceph osd pool create volumes 1024 1024',
                "cd ~/cluster;scp "+self.settings.controller_nodes[0].hostname+":/etc/ceph/ceph.client.volumes.keyring ~/cluster",
                "cd ~/cluster;scp "+self.settings.controller_nodes[0].hostname+":/etc/ceph/ceph.client.images.keyring ~/cluster",
                "cd ~/cluster;ceph auth import -i ceph.client.volumes.keyring",
                "cd ~/cluster;ceph auth import -i ceph.client.images.keyring",
                ]
        for cmd in cmds:
            logger.info(Ssh.execute_command(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password,cmd))

        ####

    def libvirt_configuation(self):
        logger.info("libvirt configuration")
        cmd = "cd ~/cluster;cat ceph.client.volumes.keyring | grep key | awk '{print $3}' > client.volumes.key"
        logger.info(Ssh.execute_command(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password,cmd))

        if self.settings.ceph_version == "1.2.3" :
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password,cmd))
            ls = [
                  "<secret ephemeral='no' private='no'>",
                "<uuid>"+self.settings.fsid+"</uuid>",
                "<usage type='ceph'>",
                "<name>client.volumes secret</name>",
                "</usage>",
                "</secret>"
                ]
            for each in ls:
                cmd = 'echo "' + each + '" >> ~/cluster/secret.xml'
                logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password,cmd))



            for host in self.settings.compute_nodes:
                cmds = [
                    'systemctl start libvirtd',
                    "sed -i '/catalog_info=volume:cinder:publicURL/a catalog_info=volume:cinder:internalURL' /etc/nova/nova.conf",
                    'openstack-service restart',
                    ]
                for cmd in cmds:
                    logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd ))
            for host in self.settings.controller_nodes:
                cmd = 'systemctl restart openstack-cinder-volume'
                logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd ))


            for host in self.settings.compute_nodes:
                cmd = 'cd ~/cluster;scp secret.xml client.volumes.key '+host.hostname+':'
                logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password,cmd))

        for host in self.settings.compute_nodes:

            if self.settings.ceph_version == "1.2.3" :
                cmds = [
                    'sudo virsh secret-define --file secret.xml',
                    "sudo virsh secret-set-value --secret "+self.settings.fsid+" --base64 `cat client.volumes.key`",
                    "sudo virsh secret-list"
                    #"rm client.volumes.key secret.xml",
                    ]
                for cmd in cmds:
                    logger.info( self.execute_as_shell(host.provisioning_ip, "ceph-user", self.settings.ceph_user_password,cmd))

            print "running puppet on " + host.hostname
            cmd = 'puppet agent -t -dv |& tee /root/puppet2.out'
            didNotRun = True
            while didNotRun == True:
                bla ,err = Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password, cmd)
                if  "Run of Puppet configuration client already in progress" in bla:
                    didNotRun = True
                    logger.info("puppet s busy ... give it a while & retry")
                    time.sleep(30)
                else :
                    didNotRun = False
                    break

    def setup_radosgw(self):
        logger.info("radosgw configuration")

        for host in self.settings.controller_nodes:
            cmd = 'cd ~/cluster;ceph-deploy install --rgw ' + host.hostname
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password, cmd))

        for host in self.settings.controller_nodes:
            cmd = 'cd ~/cluster;ceph-deploy --overwrite-conf rgw create ' + host.hostname
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password, cmd))

        cmd = 'cd ~/cluster;./swift_config.sh ' +self.settings.vip_radosgw_public+ ' ' +self.settings.vip_keystone_private+ ' ' + self.settings.cluster_password
        logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password, cmd))

        for host in self.settings.controller_nodes:
            cmd = 'cd ~/cluster;ceph-deploy --overwrite-conf --ceph-conf ceph.conf config push ' + host.hostname
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password, cmd))

        for host in self.settings.controller_nodes:
            cmd = 'cd ~/cluster;scp radosgw_config.sh ' +host.hostname+ ':/tmp/'
            logger.info( Ssh.execute_command(self.settings.ceph_node.public_ip, "ceph-user", self.settings.ceph_user_password, cmd))

        for host in self.settings.controller_nodes:
            cmds = [
                '/tmp/radosgw_config.sh ' +self.settings.vip_radosgw_public+ ' ' +self.settings.vip_radosgw_private+ ' ' +self.settings.controller_nodes[0].hostname+ ' ' +self.settings.controller_nodes[0].private_ip+ ' ' +self.settings.controller_nodes[1].hostname+ ' ' +self.settings.controller_nodes[1].private_ip+ ' ' +self.settings.controller_nodes[2].hostname+ ' '+ self.settings.controller_nodes[2].private_ip,
                'systemctl restart ceph-radosgw',
                ]
            for cmd in cmds:
                logger.info( Ssh.execute_command(host.provisioning_ip, "root", self.settings.nodes_root_password,cmd ))

        time.sleep(90)      

        cmd = 'pcs resource cleanup'
        logger.info( Ssh.execute_command(self.settings.controller_nodes[0].provisioning_ip, "root", self.settings.nodes_root_password, cmd ))

        time.sleep(30)      

        cmds = [
           "( . ~/keystonerc_admin; openstack service create --name=swift --description='Swift Service' object-store )",
           '( . ~/keystonerc_admin; openstack endpoint create --publicurl http://' +self.settings.vip_radosgw_public+ ':8087/swift/v1 --internalurl http://' +self.settings.vip_radosgw_private+ ':8087/swift/v1 --adminurl http://' +self.settings.vip_radosgw_private+ ':8087/swift/v1 --region RegionOne swift )'
           ]
        for cmd in cmds:
            logger.info( Ssh.execute_command(self.settings.controller_nodes[0].provisioning_ip, "root", self.settings.nodes_root_password, cmd ))

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
            logger.info(" - " + buff )
            if buff.endswith(']$ '):
                return buff
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
            #print " >> [[" + buff  +"]]"
            if buff.endswith("'s password: "):
                channel.send(self.settings.nodes_root_password + "\n")
            if buff.endswith("(yes/no)? "):
                channel.send("yes\n")
            if buff.endswith(']$ '):
                return buff


        return buff

    def execute_as_shell_for_sshkeygen(self, address,usr, pwd, command):
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(address,username = usr,password = pwd)
        channel = conn.invoke_shell()
        time.sleep(1)
        channel.recv(9999)
        channel.send(command  + "\n")
        buff = ''
        while not buff.endswith(']# ') :
            resp = channel.recv(9999)
            buff += resp
            #print " >> [[" + buff  +"]]"
            if buff.endswith("(yes/no)? "):
                channel.send("yes\n")
            if buff.endswith("'s password: "):
                if "ceph-user" in  buff:
                    channel.send(self.settings.ceph_user_password + "\n")
                else :
                    channel.send(self.settings.ceph_node.root_password + "\n")
            if buff.endswith("/root/.ssh/id_rsa): "):
                channel.send("\n")
            if buff.endswith("/ceph-user/.ssh/id_rsa): "):
                channel.send("\n")
            if buff.endswith("empty for no passphrase): "):
                channel.send("\n")
            if buff.endswith("passphrase again: "):
                channel.send("\n")
            if buff.endswith('~]$ '):
                return buff

        return buff

    def execute_as_shell_for_passwd(self, address,usr, pwd, command, ceph_user_password):
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(address,username = usr,password = pwd)
        channel = conn.invoke_shell()
        time.sleep(1)
        channel.recv(9999)
        channel.send(command  + "\n")
        buff = ''
        while not buff.endswith(']# ') :
            resp = channel.recv(9999)
            buff += resp
            #print " >> [[" + buff  +"]]"
            if buff.endswith("(yes/no)? "):
                channel.send("yes\n")
            if buff.endswith("'s password: "):
                channel.send(self.settings.ceph_node.root_password + "\n")
            if buff.endswith("/root/.ssh/id_rsa): "):
                channel.send(self.settings.nodes_root_password + "\n")
            if buff.endswith("New password: "):
                channel.send(ceph_user_password + "\n")
            if buff.endswith("Retype new password: "):
                channel.send(ceph_user_password + "\n")
            if buff.endswith('~]$ '):
                return buff
        return buff

    def modifyOSDPlacementGroups(self):
        logger.info("mofidy the OSD placement groups")
        osds = 0
        for each in self.settings.ceph_nodes:
            add = len(each.osd_disks) -1
            osds = osds +  add
        cal =   (osds * 100) / 2
        pgroups = pow(2, int(log(cal, 2) + 0.5))
        self.settings.placement_groups = str(pgroups)
