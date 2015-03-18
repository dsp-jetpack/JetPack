from osp_deployer.config import Settings
from auto_common import Ssh, Scp,  Widget, UI_Manager, FileHelper

import sys
import time
import logging
logger = logging.getLogger(__name__)

import threading
import time

exitFlag = 0

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

class Foreman():
    '''
    '''


    def __init__(self):
        self.settings = Settings.settings
        self.mediumID = ''
        self.controller_partition_tableID = ''
        self.compute_partition_tableID = ''
        self.pilot_partition_table = ''
        self.pilot_partition_table_730 = ''
        self.rhel_7_osId = ''
        self.openstack_subnet_id = ''
        self.environment_Id = ''
        self.domain_id = ''
        self.puppetProxy_id = ''
        self.architecture_id = ''

    def reset_password(self):
        logger.info(("=== resetting the foreman admin password"))
        sResetPassword = 'foreman-rake permissions:reset';
        re, err = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.sah_node.root_password,sResetPassword )
        foreman_password = re.split("password: ")[1].replace("\n", "").replace("\r", "")
        self.settings.foreman_password = foreman_password
        Settings.settings.foreman_password = foreman_password
        logger.info( "foreman password :: [" + foreman_password   +"]")

    def update_scripts(self):
        logger.info( "updating scripts before uploading them")
        pilot_yaml = "/dell-pilot.yaml.erb"  if sys.platform.startswith('linux') else "\\dell-pilot.yaml.erb"
        file = self.settings.foreman_configuration_scripts + pilot_yaml

        FileHelper.replaceExpressionTXT(file, 'passwd_auto =.*',"passwd_auto = '" + self.settings.openstack_services_password + "'" )

        FileHelper.replaceExpressionTXT(file, 'cluster_member_ip1 =.*',"cluster_member_ip1 = '" + self.settings.controller_nodes[0].private_ip + "'" )
        FileHelper.replaceExpressionTXT(file, 'cluster_member_name1 =.*',"cluster_member_name1 = '" + self.settings.controller_nodes[0].hostname + "'" )

        FileHelper.replaceExpressionTXT(file, 'cluster_member_ip2 =.*',"cluster_member_ip2 = '" + self.settings.controller_nodes[1].private_ip + "'" )
        FileHelper.replaceExpressionTXT(file, 'cluster_member_name2 =.*',"cluster_member_name2 = '" + self.settings.controller_nodes[1].hostname + "'" )

        FileHelper.replaceExpressionTXT(file, 'cluster_member_ip3 =.*',"cluster_member_ip3 = '" + self.settings.controller_nodes[2].private_ip + "'" )
        FileHelper.replaceExpressionTXT(file, 'cluster_member_name3 =.*',"cluster_member_name3 = '" + self.settings.controller_nodes[2].hostname + "'" )


        FileHelper.replaceExpressionTXT(file, 'vip_cinder_adm = .*',"vip_cinder_adm = '" + self.settings.vip_cinder_private + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_cinder_pub = .*',"vip_cinder_pub = '" +self.settings.vip_cinder_public + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_db = .*',"vip_db = '" + self.settings.vip_mysql_private + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_glance_adm = .*',"vip_glance_adm = '" + self.settings.vip_glance_private + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_glance_pub = .*',"vip_glance_pub = '" + self.settings.vip_glance_public + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_heat_adm = .*',"vip_heat_adm = '" + self.settings.vip_heat_private + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_heat_pub = .*',"vip_heat_pub = '" + self.settings.vip_heat_public + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_heat_cfn_adm = .*',"vip_heat_cfn_adm = '" + self.settings.vip_heat_cfn_private + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_heat_cfn_pub = .*',"vip_heat_cfn_pub = '" + self.settings.vip_heat_cfn_public + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_horizon_adm = .*',"vip_horizon_adm = '" + self.settings.vip_horizon_private  + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_horizon_pub = .*',"vip_horizon_pub = '" + self.settings.vip_horizon_public + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_keystone_adm = .*',"vip_keystone_adm = '" + self.settings.vip_keystone_private + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_keystone_pub = .*',"vip_keystone_pub = '" + self.settings.vip_keystone_public + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_nova_adm = .*',"vip_nova_adm = '" + self.settings.vip_nova_private + "'" )
        FileHelper.replaceExpressionTXT(file, 'vip_nova_priv = .*',"vip_nova_priv = '" + self.settings.vip_nova_private + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_nova_pub = .*',"vip_nova_pub = '" + self.settings.vip_nova_public + "'" )

        FileHelper.replaceExpressionTXT(file, 'fence_ipmi_ip1 = .*',"fence_ipmi_ip1 = '"+ self.settings.controller_nodes[0].idrac_secondary_ip +"'" )
        FileHelper.replaceExpressionTXT(file, 'fence_ipmi_ip2 = .*',"fence_ipmi_ip2 = '"+ self.settings.controller_nodes[1].idrac_secondary_ip +"'" )
        FileHelper.replaceExpressionTXT(file, 'fence_ipmi_ip3 = .*',"fence_ipmi_ip3 = '"+ self.settings.controller_nodes[2].idrac_secondary_ip +"'" )

        FileHelper.replaceExpressionTXT(file, 'cluster_interconnect_iface = .*',"cluster_interconnect_iface = 'bond0."+ self.settings.controller_nodes[1].private_api_vlanid +"'" )
        FileHelper.replaceExpressionTXT(file, 'net_l3_iface = .*',"net_l3_iface = 'bond0."+ self.settings.controller_nodes[1].private_api_vlanid +"'" )
        FileHelper.replaceExpressionTXT(file, 'vip_ceilometer_adm = .*',"vip_ceilometer_adm = '" + self.settings.vip_ceilometer_private + "'" )
        FileHelper.replaceExpressionTXT(file, 'vip_ceilometer_pub = .*',"vip_ceilometer_pub = '" + self.settings.vip_ceilometer_public + "'" )

        FileHelper.replaceExpressionTXT(file, 'vip_neutron_adm = .*',"vip_neutron_adm = '" + self.settings.vip_neutron_private + "'" )
        FileHelper.replaceExpressionTXT(file, 'vip_neutron_pub = .*',"vip_neutron_pub = '" + self.settings.vip_neutron_public + "'" )

        FileHelper.replaceExpressionTXT(file, 'c_ceph_cluster_network = .*',"c_ceph_cluster_network = '" + self.settings.storage_cluster_network + "'" )
        ceph_hostsNames = ''
        ceph_hostsIps = ''

        for host in self.settings.ceph_nodes :
            ceph_hostsNames = ceph_hostsNames +  host.hostname + ' '
            ceph_hostsIps = ceph_hostsIps + host.storage_ip + " "

        FileHelper.replaceExpressionTXT(file, 'c_ceph_mon_host = .*',"c_ceph_mon_host = [\"" + ceph_hostsIps + "\"]" )
        FileHelper.replaceExpressionTXT(file, 'c_ceph_mon_initial_members = .*',"c_ceph_mon_initial_members = [\"" + ceph_hostsNames + "\"]" )

        FileHelper.replaceExpressionTXT(file, 'c_ceph_public_network = .*',"c_ceph_public_network = '" + self.settings.storage_network + "'" )

        FileHelper.replaceExpressionTXT(file, 'node_access_iface = .*',"node_access_iface = 'bond0."+ self.settings.controller_nodes[1].private_api_vlanid +"'" )

        FileHelper.replaceExpressionTXT(file, 'net_tenant_iface = .*',"net_tenant_iface = 'bond0'" )
        FileHelper.replaceExpressionTXT(file, 'net_l3_iface = .*',"net_l3_iface = 'bond1'" )
        FileHelper.replaceExpressionTXT(file, 'tenant_vlan_range = .*',"tenant_vlan_range = '" + self.settings.tenant_vlan_range +"'" )



        FileHelper.replaceExpressionTXT(file, 'vip_loadbalancer = .*',"vip_loadbalancer = '" + self.settings.vip_load_balancer_private + "'" )
        FileHelper.replaceExpressionTXT(file, 'vip_amqp = .*',"vip_amqp = '" + self.settings.vip_rabbitmq_private + "'" )


        FileHelper.replaceExpressionTXT(file, 'net_fix = .*',"net_fix = '" + self.settings.nova_private_network + "'" )
        FileHelper.replaceExpressionTXT(file, 'net_float = .*',"net_float = '" + self.settings.nova_public_network + "'" )

        FileHelper.replaceExpressionTXT(file, 'net_priv_iface = .*',"net_priv_iface = 'bond0'" )
        FileHelper.replaceExpressionTXT(file, 'net_pub_iface = .*',"net_pub_iface = 'bond1" + "'" )


    def upload_scripts(self):
        files = ['bonding_snippet.template',
                 'dell-osp-ks.template',
                 'dell-osp-pxe.template',
                 'dell-pilot.partition',
                 'dell-pilot-730xd.partition',
                 'dell-pilot.yaml.erb',
                 'interface_config.template',
                 'hammer-deploy-compute.sh',
                 'hammer-deploy-controller.sh',
                 'hammer-deploy-storage.sh',
                 ]

        logger.info( "uploading deployment scripts .." )
        for file in files :
            localfile = self.settings.foreman_configuration_scripts + "/" + file if sys.platform.startswith('linux') else  self.settings.foreman_configuration_scripts + "\\" + file

            remotefile = '/root/' + file
            Scp.put_file(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, localfile, remotefile)

        if self.settings.version_locking_enabled:
            logger.info("Uploading version locking files")
            files  = [
                'ceph.vlock',
                'compute.vlock',
                'controller.vlock',
                ]
            cmd = 'mkdir /root/vlock_files'
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
            for file in files :
                if sys.platform.startswith('linux'):
                    localfile = self.settings.lock_files_dir + "/" + file
                else:
                    localfile = self.settings.lock_files_dir + "\\" + file

                remotefile = '/root/vlock_files/' + file
                print localfile + " >> " + remotefile
                Scp.put_file( self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, localfile, remotefile)

    def enable_version_locking(self):
        if self.settings.version_locking_enabled:
            logger.info("enable version locking")
            cmd = 'cp -r /root/vlock_files /usr/share/foreman/public'
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

    def install_hammer(self):
        install = 'yum -y install "*hammer*"'
        logger.info ("installing hammer")
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, install) )

        hammerConf = '/etc/hammer/cli_config.yml'

        print "configure hammer to display 200 lines"
        cmd = "sed -i 's/per_page:.*/per_page: 200/' /etc/hammer/cli_config.yml"
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        print "configure hammer not to prompt for a username/password when connecting"
        cmd = "sed -i '1s/^/:foreman:\\n    :username: 'admin'\\n    :password: '"+self.settings.foreman_password+"'\\n/' /etc/hammer/cli_config.yml"
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        return


    def configure_installation_medium(self):

        print "uploading RHEL 7 iso to foreman node"
        Scp.put_file(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,
                         self.settings.rhl7_iso, "/root/RHEL7.iso")
        cmd = 'mkdir /usr/share/foreman/public/iso'
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        print "mount iso on foreman node"
        cmd = 'echo "/root/RHEL7.iso /usr/share/foreman/public/iso iso9660 loop,ro 0 0" >> /etc/fstab'
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        cmd = 'mount -a'
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        cmd = 'hammer medium create --name "Dell OSP Pilot" --os-family Redhat --path \'http://'+ self.settings.foreman_node.provisioning_ip +'/iso\''
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        cmd = 'hammer medium list | grep "Dell OSP Pilot" | grep -o "^\w*\\b"'
        r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        self.mediumID = r_out.replace("\n", "").replace("\r", "")
        print "medium ID ::: " + self.mediumID
    def configure_partitionts_tables(self):
        print "configure partition tables"

        pilot_partition_table ='dell-pilot.partition'
        pilot_partition_table_730 ='dell-pilot-730xd.partition'
        cmds = [
            'hammer partition-table create --name dell-pilot --os-family Redhat --file /root/' + str(pilot_partition_table),
            'hammer partition-table create --name dell-pilot-730xd --os-family Redhat --file /root/' + str(pilot_partition_table_730),
                    ]
        for cmd in cmds:
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        cmd = 'hammer partition-table list | grep "dell-pilot " | grep -o "^\w*\\b"'
        r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        self.pilot_partition_table = r_out.replace("\n", "").replace("\r", "")

        cmd = 'hammer partition-table list | grep "dell-pilot-730xd" | grep -o "^\w*\\b"'
        r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        self.pilot_partition_table_730 = r_out.replace("\n", "").replace("\r", "")

    def configure_operating_systems(self):
        print "configure operating systems"
        print "create RHEl7 OS"

        cmd = 'hammer os list | grep "7.0" | grep -o "^\w*\\b"'
        r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        self.rhel_7_osId = r_out.replace("\n", "").replace("\r", "")

        print "associate architecture to OS/s"

        cmds = ['hammer os add-architecture --architecture x86_64 --id ' + self.rhel_7_osId,
                    ]
        for cmd in cmds :
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        print "associate parition/Os"

        cmds = ['hammer os add-ptable --ptable-id '+self.pilot_partition_table+' --id '+self.rhel_7_osId,
                    ]
        for cmd in cmds :
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)



    def configure_subnets(self):
        print "configure subnets"

        cmd = 'hammer subnet list | grep "OpenStack" | grep -o "^\w*\\b"'
        r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        self.openstack_subnet_id = r_out.replace("\n", "").replace("\r", "")

        cmd = 'hammer subnet update --id '+self.openstack_subnet_id +' --from '+self.settings.foreman_provisioning_subnet_ip_start+' --to '+self.settings.foreman_provisioning_subnet_ip_end+' --gateway '+self.settings.foreman_node.provisioning_ip
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)



    def configure_templates(self):
        print "configure templates"
        ks_template = 'dell-osp-ks.template'
        pxe_template = 'dell-osp-pxe.template'
        interface_template = 'interface_config.template'
        bonding_template = 'bonding_snippet.template'
        cmds = [
            'hammer template create --name "Dell OpenStack Kickstart Template" --type provision --operatingsystem-ids "'+self.rhel_7_osId +'" --file /root/' + ks_template,
            'hammer template create --name "Dell OpenStack PXE Template" --type PXELinux --operatingsystem-ids "'+self.rhel_7_osId+'" --file /root/'+ pxe_template,
            'hammer template create --name "bond_interfaces" --type snippet --file /root/' + bonding_template,
            'hammer template create --name "interface_config" --type snippet --file /root/' + interface_template,
            ]
        for cmd in cmds :
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        cmd = 'hammer template list | grep "Dell OpenStack Kickstart Template" | grep -o "^\w*\\b"'
        r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        self.kickstart_templateID = r_out.replace("\n", "").replace("\r", "")
        cmd = 'hammer template list | grep "Dell OpenStack PXE Template" | grep -o "^\w*\\b"'
        r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        self.pxe_templateID = r_out.replace("\n", "").replace("\r", "")

        cmds = ['hammer os update --config-template-ids "'+self.kickstart_templateID+', '+ self.pxe_templateID+'" --medium-ids '+self.mediumID+' --id '+self.rhel_7_osId,
                    ]
        for cmd in cmds:
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        cmds = ['hammer os set-default-template --config-template-id '+self.kickstart_templateID +' --id ' + self.rhel_7_osId,
                'hammer os set-default-template --config-template-id '+self.pxe_templateID +' --id ' + self.rhel_7_osId ,
                ]
        for cmd in cmds:
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, "hammer os info --id 1")
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, "hammer os info --id 2")

        print "gather a few more .. "

        hammer = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer environment list | grep "production" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")
        domain = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer environment list | grep "' + self.settings.domain+'" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")
        proxy = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer proxy list | grep "' + self.settings.domain+'" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")
        architecture = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer environment list | grep "_64" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")

        self.environment_Id = hammer
        self.domain_id = domain
        self.puppetProxy_id = proxy
        self.architecture_id = architecture

        print "''''''''''''''"
        attrs = vars(self)
        print ', '.join("%s: %s" % item for item in attrs.items())
        print "''''''''''''''"


    def set_ignore_puppet_facts_for_provisioning(self):
        print "configure facts updates"
        __locator_user_input = Widget("//input[@id='login_login']")
        __locator_password_input = Widget("//input[@id='login_password']")
        __locator_login_button = Widget("//input[@name='commit']")
        url = self.settings.foreman_node.public_ip
        UI_Manager.driver().get("http://" + url)

        __locator_user_input.setText("admin")
        __locator_password_input.setText(self.settings.foreman_password)
        __locator_login_button.click()


        time.sleep(10)
        UI_Manager.driver().get('https://'+str(self.settings.foreman_node.public_ip)+'/settings')

        Widget("//a[.='Provisioning']").waitFor(10)

        Widget("//a[.='Provisioning']").click()
        setting = Widget("//tr//td[.='ignore_puppet_facts_for_provisioning']/..//span")
        setting.waitFor(10)
        setting.click()

        dropdown = Widget("//tr//td[.='ignore_puppet_facts_for_provisioning']/..//select")
        save = Widget("//tr//td[.='ignore_puppet_facts_for_provisioning']/..//button[.='Save']")
        dropdown.waitFor(10)
        dropdown.select('true')
        save.click()
        time.sleep(10)


    def register_hosts(self):
        print "Registering nodes & get their id's"

        for each in self.settings.controller_nodes:
            hostCreated = False
            while hostCreated != True:
                command = 'hammer host create --name "'+ each.hostname +'" --root-password "'+ self.settings.nodes_root_password+'" --build true --enabled true --managed true --environment-id '+self.environment_Id+' --domain-id 1 --puppet-proxy-id 1 --operatingsystem-id '+self.rhel_7_osId+' --ip '+ each.provisioning_ip + ' --subnet-id 1 --architecture-id 1 --medium-id '+self.mediumID+' --partition-table-id '+self.pilot_partition_table +' --mac "'+each.provisioning_mac_address+'"'

                re, err = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                if "Could not create the host" in err:
                    print "did not create the host , trying again... " + err
                    hostCreated = False
                else :
                    hostCreated = True
                    break
            Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer environment list | grep "production" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")
            each.hostID = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer host list | grep "'+each.hostname+'" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")
            print each.hostname + " host id :: " + each.hostID
        for each in self.settings.compute_nodes:
            hostCreated = False
            while hostCreated != True:
                command = 'hammer host create --name "'+ each.hostname +'" --root-password "'+ self.settings.nodes_root_password+'" --build true --enabled true --managed true --environment-id '+self.environment_Id+' --domain-id 1 --puppet-proxy-id 1 --operatingsystem-id '+ self.rhel_7_osId+' --ip '+each.provisioning_ip +' --subnet-id 1 --architecture-id 1 --medium-id '+self.mediumID+' --partition-table-id '+self.pilot_partition_table +' --mac "'+each.provisioning_mac_address+'"'
                re, err = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                if "Could not create the host" in err:
                    print "did not create the host , trying again... " + err
                    hostCreated = False
                else :
                    hostCreated = True
                    break
            each.hostID = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer host list | grep "'+each.hostname+'" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")
            print each.hostname + " host id :: " + each.hostID
        if self.settings.stamp_storage == "ceph":
            for each in self.settings.ceph_nodes:
                hostCreated = False
                while hostCreated != True:
                    if each.is_730 == True:
                        command = 'hammer host create --name "'+ each.hostname +'" --root-password "'+ self.settings.nodes_root_password+'" --build true --enabled true --managed true --environment-id '+self.environment_Id+' --domain-id 1 --puppet-proxy-id 1 --operatingsystem-id '+ self.rhel_7_osId+' --ip '+each.provisioning_ip +' --subnet-id 1 --architecture-id 1 --medium-id '+self.mediumID+' --partition-table-id '+self.pilot_partition_table_730 +' --mac "'+each.provisioning_mac_address+'"'
                    else:
                        command = 'hammer host create --name "'+ each.hostname +'" --root-password "'+ self.settings.nodes_root_password+'" --build true --enabled true --managed true --environment-id '+self.environment_Id+' --domain-id 1 --puppet-proxy-id 1 --operatingsystem-id '+ self.rhel_7_osId+' --ip '+each.provisioning_ip +' --subnet-id 1 --architecture-id 1 --medium-id '+self.mediumID+' --partition-table-id '+self.pilot_partition_table +' --mac "'+each.provisioning_mac_address+'"'
                    re, err = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                    if "Could not create the host" in err:
                        print "did not create the host , trying again... " + err
                        hostCreated = False
                    else :
                        hostCreated = True
                        break
                each.hostID = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer host list | grep "'+each.hostname+'" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")
                print each.hostname + " host id :: " + each.hostID


    def configure_os_updates(self):
        print "configuring OS updates"

        commands = [
                'hammer os set-parameter --operatingsystem-id '+ self.rhel_7_osId +' --name subscription_manager --value true',
               'hammer os set-parameter --operatingsystem-id '+ self.rhel_7_osId +' --name subscription_manager_username --value '+ self.settings.subscription_manager_user,
               'hammer os set-parameter --operatingsystem-id '+ self.rhel_7_osId  +' --name subscription_manager_password --value "'+ self.settings.subscription_manager_password+'"',
                    ]
        for each in commands :
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, each)





    def configure_controller_nic(self):
        print "configuring the controller node(s) nics"
        for node in self.settings.controller_nodes:
            print "Configure non bonded interfaces"
            # management vlan.
            command = "hammer host set-parameter --host-id "+node.hostID+" --name nics --value '(["+node.idrac_interface+"]=\"onboot static " + node.idrac_secondary_ip+"/"+node.idrac_secondary_netmask+"\")'"
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)

            print "configure bonded interfaces"

            commands = ["hammer host set-parameter --host-id "+node.hostID+" --name bonds --value '( [bond0]=\"onboot none\" [bond0."+node.private_api_vlanid+"]=\"onboot static vlan "+node.private_ip+"/"+node.private_netmask+"\" [bond0."+node.storage_vlanid+"]=\"onboot static vlan "+node.storage_ip+"/"+node.storage_netmask+"\" [bond1]=\"onboot static "+node.public_ip+"/"+node.public_netmask+"\")'",
                        "hammer host set-parameter --host-id "+node.hostID+" --name bond_ifaces  --value '( [bond0]=\""+node.bond0_interfaces+"\" [bond1]=\""+node.bond1_interfaces+"\")'",
                        "hammer host set-parameter --host-id "+node.hostID+" --name bond_opts --value '( [bond0]=\"mode="+self.settings.bond_mode_controller_nodes+" miimon=100\" [bond1]=\"mode="+self.settings.bond_mode_controller_nodes+" miimon=100\")'"]

            for command in commands:
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)

    def configure_controller_version_locking(self):
        if self.settings.version_locking_enabled:
            print "Configuring vesion locking for controller nodes"
            for node in self.settings.controller_nodes:
                command = "hammer host set-parameter --host-id "+node.hostID+" --name yum_versionlock_file --value 'http://"+self.settings.foreman_node.provisioning_ip+"/vlock_files/controller.vlock'"
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)


    def configure_compute_nic(self):
        print "configuring the compute node(s) nics"
        for node in self.settings.compute_nodes:
            print "configure bonded interfaces"
            logger.info("nova_public_netmask :: ?" + node.nova_public_netmask)
            commands = ["hammer host set-parameter --host-id "+node.hostID+" --name bonds --value '( [bond0]=\"onboot none promisc\" [bond0."+node.private_api_vlanid+"]=\"onboot static vlan "+node.private_ip+"/"+node.private_netmask+"\" [bond1]=\"onboot static vlan "+node.storage_ip+"/"+node.storage_netmask+"\")'",
                        "hammer host set-parameter --host-id "+node.hostID+" --name bond_ifaces --value '( [bond0]=\""+node.bond0_interfaces+"\" [bond1]=\""+node.bond1_interfaces+"\")'",
                        "hammer host set-parameter --host-id "+node.hostID+" --name bond_opts --value '( [bond0]=\"mode="+self.settings.bond_mode_compute_nodes+" miimon=100\" [bond1]=\"mode="+self.settings.bond_mode_compute_nodes+" miimon=100\")'"]
            for command in commands:
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)

    def configure_compute_version_locking(self):
        if self.settings.version_locking_enabled:
            print "Configuring vesion locking for compute nodes"
            for node in self.settings.compute_nodes:
                command = "hammer host set-parameter --host-id "+node.hostID+" --name yum_versionlock_file --value 'http://"+self.settings.foreman_node.provisioning_ip+"/vlock_files/compute.vlock'"
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)

    def configure_ceph_version_locking(self):
        if self.settings.version_locking_enabled:
            print "Configuring vesion locking for ceph nodes"
            for node in self.settings.ceph_nodes:
                command = "hammer host set-parameter --host-id "+node.hostID+" --name yum_versionlock_file --value 'http://"+self.settings.foreman_node.provisioning_ip+"/vlock_files/ceph.vlock'"
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)

    def configure_ceph_nic(self):
        print "configuring the Ceph node(s) nics"
        for node in self.settings.ceph_nodes:
            print "configure bonded interfaces"

            commands = ["hammer host set-parameter --host-id "+node.hostID+" --name bonds --value '( [bond0]=\"onboot none\" [bond0]=\"onboot static vlan "+node.storage_ip+"/"+node.storage_netmask+"\" [bond1]=\"onboot static "+node.storage_cluster_ip+"/"+node.storage_cluster_netmask+"\")'",
                       "hammer host set-parameter --host-id "+node.hostID+" --name bond_ifaces  --value '( [bond0]=\""+node.bond0_interfaces+"\" [bond1]=\""+node.bond1_interfaces+"\")'",
                       "hammer host set-parameter --host-id "+node.hostID+" --name bond_opts --value '( [bond0]=\"mode="+self.settings.bond_mode_storage_nodes+"\" [bond1]=\"mode="+self.settings.bond_mode_storage_nodes+"\")'"]

            for command in commands:
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
    def configure_pool_ids(self):
        print "Configuring pool id's"
        # Below moved further down the steps/process but commands should apply still ( new RPM's probably )
        for node in self.settings.controller_nodes:
            command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_pool --value '+self.settings.subscription_manager_poolID
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
            #command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_repos --value "rhel-server-rhscl-7-rpms, rhel-7-server-rpms, rhel-7-server-openstack-5.0-rpms,rhel-ha-for-rhel-7-server-rpms"'
            #print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
        for node in self.settings.compute_nodes:
            command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_pool --value '+self.settings.subscription_manager_poolID
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
            #command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_repos --value "rhel-server-rhscl-7-rpms, rhel-7-server-rpms, rhel-7-server-openstack-5.0-rpms"'
            #print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
        if self.settings.stamp_storage == "ceph":
            for node in self.settings.ceph_nodes:
                command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_pool --value '+self.settings.subscription_manager_poolID
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                #command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_repos --value "rhel-server-rhscl-7-rpms, rhel-7-server-rpms, rhel-7-server-openstack-5.0-rpms,rhel-ha-for-rhel-7-server-rpms"'
                #print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)

    def configure_repositories(self):
        print "configuring repo's"

        for node in self.settings.controller_nodes:
           command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_repos --value "rhel-server-rhscl-7-rpms, rhel-7-server-openstack-6.0-rpms, rhel-7-server-rpms, rhel-ha-for-rhel-7-server-rpms"'
           print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
        for node in self.settings.compute_nodes:
            command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_repos --value "rhel-server-rhscl-7-rpms, rhel-7-server-openstack-6.0-rpms, rhel-7-server-rpms"'
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
        if self.settings.stamp_storage == "ceph":
            for node in self.settings.ceph_nodes:
               command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_repos --value "rhel-7-server-rpms"'
               print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
               command = 'hammer host set-parameter --name storagenode_iptables --value true --host-id '+node.hostID
               print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)


    def configureHostGroups_Parameters(self):
        print "Configure the hostgroups parameter"

        logger.info("generating ceph keys/fsid")
        createKeys = [ 'mkdir /root/ceph_keys',
            'cd /root/ceph_keys;ceph-authtool -C -n client.volumes --gen-key client.volumes',
            'cd /root/ceph_keys;ceph-authtool -C -n client.images --gen-key client.images',
            'cd /root/ceph_keys; uuidgen > c_ceph_fsid']
        for cmd in createKeys:
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        cmd = "cat /root/ceph_keys/client.volumes | awk '/key = / {print $3}'"
        vol_key  = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")

        cmd = "cat /root/ceph_keys/client.images | awk '/key = / {print $3}'"
        img_key  = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")

        cmd = "cat /root/ceph_keys/c_ceph_fsid"
        fsidl_key  = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")

        logger.info("Updating erb file with ceph keys/fsid")

        erbFile = "~/dell-pilot.yaml.erb"
        cmd = "sed -i \"s/c_ceph_images_key = '.*/c_ceph_images_key = '"+img_key+"'/\" " + erbFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.ceph_node.root_password,cmd ))

        cmd = "sed -i \"s/c_ceph_volumes_key = '.*/c_ceph_volumes_key = '"+vol_key+"'/\" " + erbFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.ceph_node.root_password,cmd ))

        cmd = "sed -i \"s/c_ceph_fsid = .*/c_ceph_fsid = '"+fsidl_key+"'/\" " + erbFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.ceph_node.root_password,cmd ))

        #TODO :: equaogic step here.

        cmd = 'yum install -y rubygem-foreman_api'
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        erbFile = 'dell-pilot.yaml.erb'

        cmd = 'cd /usr/share/openstack-foreman-installer; bin/quickstack_defaults.rb -g config/hostgroups.yaml -d ~/'+erbFile+' -v parameters'
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)



    def cephConfigurtion(self):
         logger.info("Updating ceph configuration to prevent foreman/puppet to override ceph config on controller nodes")
         cmds = ["cp -v /usr/share/openstack-foreman-installer/puppet/modules/quickstack/manifests/ceph/config.pp{,.bak}",
                   "sed -i '/file { \"etc-ceph\":/,${s/^/#/;};$s/^#//' /usr/share/openstack-foreman-installer/puppet/modules/quickstack/manifests/ceph/config.pp "
                   ]
         for cmd in cmds:
             logger.info(Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd))

    def applyHostGroups_to_nodes(self):
        print "Apply host groups to nodes"

        cmd = 'hammer hostgroup list | grep "Controller (Nova Network)" | grep -o "^\w*\\b"'
        controllerGroupId = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")
        print "controllerGroupId : " + controllerGroupId
        cmd = 'hammer hostgroup list | grep "Compute (Nova Network)" | grep -o "^\w*\\b"'
        computeGroupId = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")
        print "computeGroupId : " + computeGroupId

        print "Apply hostgroup to controller node(s)"
        for each in self.settings.controller_nodes:
            cmd = 'hammer host list | grep "'+ each.hostname +'" | grep -o "^\w*\\b"'
            hostID = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")
            hostUpdated = False
            while hostUpdated != True:
                cmd = 'hammer host update --hostgroup-id '+controllerGroupId+' --id '+hostID
                out, err = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
                if ("Could not update the host" in err) or ( "Could not update the host" in out):
                    print "did not update the host , trying again... " + err
                    hostUpdated = False
                else :
                    hostUpdated = True
                    break
        controlerPuppetRuns = []
        for each in self.settings.controller_nodes:
            puppetRunThr = runThreadedPuppet(each.hostname, each)
            controlerPuppetRuns.append(puppetRunThr)
        for thr in controlerPuppetRuns:
            thr.start()
        for thr in controlerPuppetRuns:
            thr.join()

        print "Apply hostgroup to compute nodes "
        for each in self.settings.compute_nodes:
            cmd = 'hammer host list | grep "'+ each.hostname +'" | grep -o "^\w*\\b"'
            hostID = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")


            hostUpdated = False
            while hostUpdated != True:
                cmd = 'hammer host update --hostgroup-id '+computeGroupId+' --id '+hostID
                out, err  = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
                if ("Could not update the host" in err) or ( "Could not update the host" in out):
                    print "did not update the host , trying again... " + err
                    hostUpdated = False
                else :
                    hostUpdated = True
                    break

            print "running puppet on " + each.hostname
            cmd = 'puppet agent -t -dv |& tee /root/puppet.out'
            didNotRun = True
            while didNotRun == True:
                bla ,err = Ssh.execute_command(each.provisioning_ip, "root", self.settings.nodes_root_password, cmd)
                if  "Run of Puppet configuration client already in progress" in bla:
                    didNotRun = True
                    logger.info("puppet s busy ... give it a while & retry")
                    time.sleep(30)
                else :
                    didNotRun = False
                    break





    def configureNodes(self):

        cmd = 'hammer hostgroup list | grep "HA All In One Controller" | grep -o "^\w*\\b"'
        controllerGroupId = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")
        print "controllerGroupId : " + controllerGroupId
        cmd = 'hammer hostgroup list | grep "Compute (Neutron)" | grep -o "^\w*\\b"'
        computeGroupId = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")
        print "computeGroupId : " + computeGroupId


        for each in self.settings.controller_nodes:
            cmd = 'hammer host list | grep "'+ each.hostname +'" | grep -o "^\w*\\b"'
            hostID = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")
            hostUpdated = False
            while hostUpdated != True:
                cmd = 'hammer host update --hostgroup-id '+controllerGroupId+' --id '+hostID
                out, err = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
                if ("Could not update the host" in err) or ( "Could not update the host" in out):
                    print "did not update the host , trying again... " + err
                    hostUpdated = False
                else :
                    hostUpdated = True
                    break

        cmd = "sed -i \"s/\\$known_stores    .*/\\$known_stores = \\['glance.store.rbd.Store'\\],/\"" + " /usr/share/openstack-puppet/modules/glance/manifests/api.pp"
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        logger.info("run puppet on controller nodes")
        controlerPuppetRuns = []
        for each in self.settings.controller_nodes:
            puppetRunThr = runThreadedPuppet(each.hostname, each)
            controlerPuppetRuns.append(puppetRunThr)
        for thr in controlerPuppetRuns:
            thr.start()
            time.sleep(60) # ...
        for thr in controlerPuppetRuns:
            thr.join()


        logger.info("Apply the host group & run puppet on the compute nodes")
        for each in self.settings.compute_nodes:
            cmd = 'hammer host list | grep "'+ each.hostname +'" | grep -o "^\w*\\b"'
            hostID = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")
            hostUpdated = False
            while hostUpdated != True:
                cmd = 'hammer host update --hostgroup-id '+computeGroupId+' --id '+hostID
                out, err = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
                if ("Could not update the host" in err) or ( "Could not update the host" in out):
                    print "did not update the host , trying again... " + err
                    hostUpdated = False
                else :
                    hostUpdated = True
                    break

            cmd = 'puppet agent -t -dv |& tee /root/puppet.out'
            didNotRun = True
            while didNotRun == True:
                bla ,err = Ssh.execute_command(each.provisioning_ip, "root", self.settings.nodes_root_password, cmd)
                if  "Run of Puppet configuration client already in progress" in bla:
                    didNotRun = True
                    logger.info("puppet s busy ... give it a while & retry")
                    time.sleep(30)
                else :
                    didNotRun = False
                    break

