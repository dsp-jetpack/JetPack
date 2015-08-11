from osp_deployer.config import Settings
from auto_common import Ssh, Scp,  Widget, UI_Manager, FileHelper
import sys, logging, threading, time, shutil, os
logger = logging.getLogger(__name__)



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
        re, err = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,sResetPassword)
        try:
            foreman_password = re.split("password: ")[1].replace("\n", "").replace("\r", "")
        except:
            raise AssertionError("Could not reset the foreman password, this usually means foreman did not install properly" )
        self.settings.foreman_password = foreman_password
        Settings.settings.foreman_password = foreman_password
        logger.info( "foreman password :: [" + foreman_password   +"]")

    def update_and_upload_scripts(self):
        logger.info( "updating scripts before uploading them")
        #Copy it temporrly so we dont touch the workpace file.


        pilot_yaml = "/pilot/dell-pilot.yaml.erb"  if sys.platform.startswith('linux') else "\\pilot\\dell-pilot.yaml.erb"
        pilot_yamlTemp = "/dell-pilot.yaml.erb"  if sys.platform.startswith('linux') else "\\dell-pilot.yaml.erb"
        fileWS = self.settings.foreman_configuration_scripts + pilot_yaml
        file =  self.settings.foreman_configuration_scripts + pilot_yamlTemp
        shutil.copyfile(fileWS,file)

        if self.settings.debug is not None: 
            FileHelper.replaceExpressionTXT(file, 'dbug =.*',"dbug = '" + self.settings.debug + "'" )
        if self.settings.verbose is not None: 
            FileHelper.replaceExpressionTXT(file, 'vbose =.*',"vbose = '" + self.settings.verbose + "'" )
        if self.settings.heat_auth_key is not None:
            FileHelper.replaceExpressionTXT(file, 'heat_auth_key =.*',"heat_auth_key = '" + self.settings.heat_auth_key + "'" )
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
        FileHelper.replaceExpressionTXT(file, 'fence_ipmi_ip1 = .*',"fence_ipmi_ip1 = '"+ self.settings.controller_nodes[0].idrac_ip +"'" )
        FileHelper.replaceExpressionTXT(file, 'fence_ipmi_ip2 = .*',"fence_ipmi_ip2 = '"+ self.settings.controller_nodes[1].idrac_ip +"'" )
        FileHelper.replaceExpressionTXT(file, 'fence_ipmi_ip3 = .*',"fence_ipmi_ip3 = '"+ self.settings.controller_nodes[2].idrac_ip +"'" )
        FileHelper.replaceExpressionTXT(file, 'fence_ipmi_user = .*',"fence_ipmi_user = '" + self.settings.ipmi_user + "'" )
        FileHelper.replaceExpressionTXT(file, 'fence_ipmi_password = .*',"fence_ipmi_password = '" + self.settings.ipmi_password + "'" )
        FileHelper.replaceExpressionTXT(file, 'cluster_interconnect_iface = .*',"cluster_interconnect_iface = 'bond0."+ self.settings.controller_nodes[1].private_api_vlanid +"'" )
        FileHelper.replaceExpressionTXT(file, 'net_l3_iface = .*',"net_l3_iface = 'bond0."+ self.settings.controller_nodes[1].private_api_vlanid +"'" )
        FileHelper.replaceExpressionTXT(file, 'vip_ceilometer_adm = .*',"vip_ceilometer_adm = '" + self.settings.vip_ceilometer_private + "'" )
        FileHelper.replaceExpressionTXT(file, 'vip_ceilometer_pub = .*',"vip_ceilometer_pub = '" + self.settings.vip_ceilometer_public + "'" )
        FileHelper.replaceExpressionTXT(file, 'vip_ceilometer_redis = .*',"vip_ceilometer_redis = '" + self.settings.vip_ceilometer_redis + "'" )
        FileHelper.replaceExpressionTXT(file, 'vip_neutron_adm = .*',"vip_neutron_adm = '" + self.settings.vip_neutron_private + "'" )
        FileHelper.replaceExpressionTXT(file, 'vip_neutron_pub = .*',"vip_neutron_pub = '" + self.settings.vip_neutron_public + "'" )
        FileHelper.replaceExpressionTXT(file, 'c_ceph_cluster_network = .*',"c_ceph_cluster_network = '" + self.settings.storage_cluster_network + "'" )
        FileHelper.replaceExpressionTXT(file, 'c_ceph_osd_pool_size = .*',"c_ceph_osd_pool_size = '3'" )
        FileHelper.replaceExpressionTXT(file, 'c_ceph_osd_journal_size = .*',"c_ceph_osd_journal_size = '10000'" )

        if self.settings.use_eql_backend is True:
                    FileHelper.replaceExpressionTXT(file, 'c_be_eqlx = .*',"c_be_eqlx = true" )
                    FileHelper.replaceExpressionTXT(file, 'c_be_eqlx_name = .*',"c_be_eqlx_name = [\"" + self.settings.c_be_eqlx_name + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_eqlx_san_ip = .*',"c_eqlx_san_ip = [\"" + self.settings.c_eqlx_san_ip + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_eqlx_san_login = .*',"c_eqlx_san_login = [\"" + self.settings.c_eqlx_san_login + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_eqlx_san_password = .*',"c_eqlx_san_password = [\"" + self.settings.c_eqlx_san_password + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_eqlx_ch_login = .*',"c_eqlx_ch_login = [\"" + self.settings.c_eqlx_ch_login + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_eqlx_ch_pass = .*',"c_eqlx_ch_pass = [\"" + self.settings.c_eqlx_ch_pass + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_eqlx_group_n = .*',"c_eqlx_group_n = [\"" + self.settings.c_eqlx_group_n + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_eqlx_pool = .*',"c_eqlx_pool = [\"" + self.settings.c_eqlx_pool + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_eqlx_use_chap = .*',"c_eqlx_use_chap = [\"" + self.settings.c_eqlx_use_chap + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_mult_be = .*',"c_mult_be = '"+ self.settings.c_mult_be +"'" )		
 		
        if self.settings.use_dell_sc_backend is True:
                    FileHelper.replaceExpressionTXT(file, 'c_be_dell_sc = .*',"c_be_dell_sc = true" )
                    FileHelper.replaceExpressionTXT(file, 'c_be_dell_sc_name = .*',"c_be_dell_sc_name = [\"" + self.settings.c_be_dell_sc_name + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_dell_sc_api_port = .*',"c_dell_sc_api_port = [\"" + self.settings.c_dell_sc_api_port + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_dell_sc_iscsi_ip_address = .*',"c_dell_sc_iscsi_ip_address = [\"" + self.settings.c_dell_sc_iscsi_ip_address + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_dell_sc_iscsi_port = .*',"c_dell_sc_iscsi_port = [\"" + self.settings.c_dell_sc_iscsi_port + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_dell_sc_san_ip = .*',"c_dell_sc_san_ip = [\"" + self.settings.c_dell_sc_san_ip + '"]')
	            FileHelper.replaceExpressionTXT(file, 'c_dell_sc_san_login = .*',"c_dell_sc_san_login = [\"" + self.settings.c_dell_sc_san_login + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_dell_sc_san_password = .*',"c_eqlx_ch_pass = [\"" + self.settings.c_dell_sc_san_password + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_dell_sc_ssn = .*',"c_dell_sc_ssn = [\"" + self.settings.c_dell_sc_ssn + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_dell_sc_server_folder = .*',"c_dell_sc_server_folder = [\"" + self.settings.c_dell_sc_server_folder + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_dell_sc_volume_folder = .*',"c_dell_sc_volume_folder = [\"" + self.settings.c_dell_sc_volume_folder + '"]')
                    FileHelper.replaceExpressionTXT(file, 'c_mult_be = .*',"c_mult_be = '"+ self.settings.c_mult_be +"'" )
					
        ceph_hostsNames = ''
        ceph_hostsIps = ''

        for host in self.settings.controller_nodes :
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

        logger.info( "uploading deployment scripts .." )

        cmd = 'mkdir /root/pilot'
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        Scp.put_file(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, self.settings.foreman_configuration_scripts + pilot_yamlTemp, '/root/pilot/dell-pilot.yaml.erb')
        os.remove(self.settings.foreman_configuration_scripts + pilot_yamlTemp)

        hammer_scripts = ['hammer-configure-hostgroups.sh',
        'hammer-deploy-compute.sh',
        'hammer-deploy-controller.sh',
        'hammer-deploy-storage.sh',
        'hammer-configure-foreman.sh',
        'hammer-get-ids.sh',
        'hammer-dump-ids.sh',
        'hammer-ceph-fix.sh',
        'hammer-fencing.sh',
        'common.sh',
        'osp_config.sh',
        'radosgw_config.sh',
        'swift_config.sh',
        'provision.sh',
        'bond.sh'
         ]
        for file in hammer_scripts  :
            localfile = self.settings.foreman_configuration_scripts + "/utils/networking/" + file if sys.platform.startswith('linux') else  self.settings.foreman_configuration_scripts + "\\utils\\networking\\" + file
            remotefile = '/root/pilot/' + file
            print localfile + " >> " + remotefile
            Scp.put_file(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, localfile, remotefile)
            cmd = 'chmod u+x ' + remotefile
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        files_comon = ['bonding_snippet.template',
         'dell-osp-ks.template',
         'dell-osp-pxe.template',
         'interface_config.template'
         ]
        for file in files_comon :
            localfile = self.settings.foreman_configuration_scripts + "/common/" + file if sys.platform.startswith('linux') else  self.settings.foreman_configuration_scripts + "\\common\\" + file
            remotefile = '/root/pilot/' + file
            Scp.put_file(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, localfile, remotefile)

        files_partitions = ['dell-pilot.partition',
                 'dell-pilot-730xd.partition']
        for file in files_partitions :
            localfile = self.settings.foreman_configuration_scripts + "/pilot/" + file if sys.platform.startswith('linux') else  self.settings.foreman_configuration_scripts + "\\pilot\\" + file
            remotefile = '/root/pilot/' + file
            Scp.put_file(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, localfile, remotefile)


        if self.settings.version_locking_enabled is True:
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
        if self.settings.version_locking_enabled is True:
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

        print "uploading RHEL 7.1 iso to foreman node"
        Scp.put_file(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,
                         self.settings.rhl71_iso, "/root/RHEL7.iso")
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

    def configure_foreman(self):
        print "configure foreman"

        configFile = '/root/pilot/osp_config.sh'

        self.pilot_partition_table = 'dell-pilot'
        self.pilot_partition_table_730 = 'dell-pilot-730xd'


        cmd = "sed -i \"s|CHANGEME_IP|" + self.settings.foreman_node.provisioning_ip +"|\" " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i \"s|CHANGEME_PATH|iso|\" " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i \"s|CHANGEME_FOREMAN_PROVISIONING_IP|" + self.settings.foreman_node.provisioning_ip +"|\" " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i \"s|CHANGEME_SUBNET_START_IP|" + self.settings.foreman_provisioning_subnet_ip_start +"|\" " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))
        cmd = "sed -i \"s|CHANGEME_SUBNET_END_IP|" + self.settings.foreman_provisioning_subnet_ip_end +"|\" " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i \"s|CHANGEME_USERNAME|" + self.settings.subscription_manager_user +"|\" " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i \"s|CHANGEME_PASSWORD|" + self.settings.subscription_manager_password +"|\" " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i \"s|ROOT_PASSWORD='.*|ROOT_PASSWORD='" + self.settings.cluster_password +"'|\" " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i \"s|CHANGEME_POOL_ID|" + self.settings.subscription_manager_pool_phyical_openstack_nodes +"|\" " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i \"s|CHANGEME_STORAGE_POOL_ID|" + self.settings.subscription_manager_pool_physical_ceph +"|\" " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i 's|CONTROLLER_PARTITION_NAME=\".*|CONTROLLER_PARTITION_NAME=\""+self.pilot_partition_table+"\"|' " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))


        cmd = "sed -i 's|COMPUTE_PARTITION_NAME=\".*|COMPUTE_PARTITION_NAME=\""+self.pilot_partition_table+"\"|' " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        if self.settings.storage_nodes_are_730 == "true":
            logger.info("storage node partition .")
            cmd = "sed -i 's|STORAGE_PARTITION_NAME=\".*|STORAGE_PARTITION_NAME=\""+self.pilot_partition_table_730+"\"|' " + configFile
            logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))
        else:
            cmd = "sed -i 's|STORAGE_PARTITION_NAME=\".*|STORAGE_PARTITION_NAME=\""+self.pilot_partition_table+"\"|' " + configFile
            logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i \"s|CHANGEME_IDRAC_NIC|" + self.settings.controller_nodes[0].idrac_interface +"|\" " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i 's|R630_BONDS=\".*|R630_BONDS=\\\"( [bond0]=\\\\\""+self.settings.controller_nodes[0].bond0_interfaces+"\\\\\" [bond1]=\\\\\""+self.settings.controller_nodes[0].bond1_interfaces+"\\\\\" )\"|' " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i 's|R730_BONDS=\".*|R730_BONDS=\\\"( [bond0]=\\\\\""+self.settings.compute_nodes[0].bond0_interfaces+"\\\\\" [bond1]=\\\\\""+self.settings.compute_nodes[0].bond1_interfaces+"\\\\\" )\"|' " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i 's|R730XD_BONDS=\".*|R730XD_BONDS=\\\"( [bond0]=\\\\\""+self.settings.ceph_nodes[0].bond0_interfaces+"\\\\\" [bond1]=\\\\\""+self.settings.ceph_nodes[0].bond1_interfaces+"\\\\\" )\"|' " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        cmd = "sed -i 's|CONTROLLER_BOND_OPTS=\".*|CONTROLLER_BOND_OPTS=\\\""+self.settings.controller_bond_opts+"\\\"|' " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))
        cmd = "sed -i 's|COMPUTE_BOND_OPTS=\".*|COMPUTE_BOND_OPTS=\\\""+self.settings.compute_bond_opts+"\\\"|' " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))
        cmd = "sed -i 's|STORAGE_BOND_OPTS=\".*|STORAGE_BOND_OPTS=\\\""+self.settings.storage_bond_opts+"\\\"|' " + configFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password,cmd ))

        logger.info ("executing hammer-configure-foreman")
        cmd = 'cd /root/pilot\n./hammer-configure-foreman.sh'
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root",self.settings.foreman_node.root_password,cmd))


    def gather_values(self):

        print "gather a few more .. "

        hammer = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer environment list | grep "production" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")
        domain = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer environment list | grep "' + self.settings.domain+'" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")
        proxy = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer proxy list | grep "' + self.settings.domain+'" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")
        architecture = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, 'hammer environment list | grep "_64" | grep -o "^\w*\\b"')[0].replace("\n", "").replace("\r", "")

        cmd = 'hammer os list | grep "7.1" | grep -o "^\w*\\b"'
        r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        operatingsystem = r_out.replace("\n", "").replace("\r", "")

        cmd = 'hammer medium list | grep "Dell OSP Pilot" | grep -o "^\w*\\b"'
        r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        self.mediumID = r_out.replace("\n", "").replace("\r", "")
        print "medium ID ::: " + self.mediumID


        self.environment_Id = hammer
        self.domain_id = domain
        self.puppetProxy_id = proxy
        self.architecture_id = architecture
        self.rhel_7_osId = operatingsystem


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
        while save.exists():
                UI_Manager.driver().execute_script("window.scrollTo(0, 0);")
                save.click()
                time.sleep(5)



    def configure_controller_nodes(self):
        print "configuring the controller node(s)"
        for node in self.settings.controller_nodes:
            hostCreated = False
            while hostCreated != True:
                command = 'cd /root/pilot\n./hammer-deploy-controller.sh ' + node.hostname + " " + node.provisioning_mac_address + " " + node.provisioning_ip + " " + node.idrac_secondary_ip + " R630"
                re, err = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                if "Could not create the host" in err:
                    print "did not create the host , trying again... " + err
                    hostCreated = False
                else :
                    hostCreated = True
                    break


        if self.settings.version_locking_enabled is True:
            print "Configuring vesion locking for controller nodes"
            for node in self.settings.controller_nodes:
                cmd = 'hammer host list | grep "'+ node.hostname +'" | grep -o "^\w*\\b"'
                node.hostID = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")
                command = "hammer host set-parameter --host-id "+node.hostID+" --name yum_versionlock_file --value 'http://"+self.settings.foreman_node.provisioning_ip+"/vlock_files/controller.vlock'"
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)

    def configure_compute_nodes(self):
        print "configuring the compute node(s)"
        for node in self.settings.compute_nodes:
            hostCreated = False
            while hostCreated != True:
                command = 'cd /root/pilot\n./hammer-deploy-compute.sh ' + node.hostname + " " + node.provisioning_mac_address + " " + node.provisioning_ip  + " R730"
                re, err = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                if "Could not create the host" in err:
                    print "did not create the host , trying again... " + err
                    hostCreated = False
                else :
                    hostCreated = True
                    break

        if self.settings.version_locking_enabled is True:
            print "Configuring vesion locking for compute nodes"
            for node in self.settings.compute_nodes:
                cmd = 'hammer host list | grep "'+ node.hostname +'" | grep -o "^\w*\\b"'
                node.hostID = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")

                command = "hammer host set-parameter --host-id "+node.hostID+" --name yum_versionlock_file --value 'http://"+self.settings.foreman_node.provisioning_ip+"/vlock_files/compute.vlock'"
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)

    def configure_ceph_nodes(self):
        print "configuring the Ceph node(s)"
        for node in self.settings.ceph_nodes:
            hostCreated = False
            while hostCreated != True:
                command = 'cd /root/pilot\n./hammer-deploy-storage.sh ' + node.hostname + " " + node.provisioning_mac_address + " " + node.provisioning_ip  + " R730XD"
                re, err = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                if "Could not create the host" in err:
                    print "did not create the host , trying again... " + err
                    hostCreated = False
                else :
                    hostCreated = True
                    break

        if self.settings.version_locking_enabled is True:
            print "Configuring vesion locking for ceph nodes"
            for node in self.settings.ceph_nodes:
                cmd = 'hammer host list | grep "'+ node.hostname +'" | grep -o "^\w*\\b"'
                node.hostID = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")

                command = "hammer host set-parameter --host-id "+node.hostID+" --name yum_versionlock_file --value 'http://"+self.settings.foreman_node.provisioning_ip+"/vlock_files/ceph.vlock'"
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
        self.settings.fsid = fsidl_key
        logger.info("Updating erb file with ceph keys/fsid")

        erbFile = "~/pilot/dell-pilot.yaml.erb"
        cmd = "sed -i \"s|c_ceph_images_key = '.*|c_ceph_images_key = '"+img_key+"'|\" " + erbFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.ceph_node.root_password,cmd ))

        cmd = "sed -i \"s|c_ceph_volumes_key = '.*|c_ceph_volumes_key = '"+vol_key+"'|\" " + erbFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.ceph_node.root_password,cmd ))

        cmd = "sed -i \"s|c_ceph_fsid = .*|c_ceph_fsid = '"+fsidl_key+"'|\" " + erbFile
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.ceph_node.root_password,cmd ))

        cmd = "sed -i '/.*quickstack\/ceph-conf.erb.*/a  replace => false,' /usr/share/openstack-foreman-installer/puppet/modules/quickstack/manifests/ceph/config.pp"
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        cmd = "sed -i 's/allow rx pool=images/allow rwx pool=images/' /usr/share/openstack-foreman-installer/puppet/modules/quickstack/manifests/ceph/config.pp"
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)

        cmd = 'yum install -y rubygem-foreman_api'
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)


        file = '/root/pilot/hammer-configure-hostgroups.sh'

        logger.info ("executing hammer-configure-hostgroups")
        cmd =file
        logger.info( Ssh.execute_command(self.settings.foreman_node.public_ip, "root",self.settings.foreman_node.root_password,cmd))



    def cephConfigurtion(self):
         logger.info("Updating ceph configuration to prevent foreman/puppet to override ceph config on controller nodes")
         cmds = ["cp -v /usr/share/openstack-foreman-installer/puppet/modules/quickstack/manifests/ceph/config.pp{,.bak}",
                   "sed -i '/file { \"etc-ceph\":/,${s/^/#/;};$s/^#//' /usr/share/openstack-foreman-installer/puppet/modules/quickstack/manifests/ceph/config.pp "
                   ]
         for cmd in cmds:
             logger.info(Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd))

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

        logger.info("run puppet on controller nodes with fencing disabled")
        cmd = "/root/pilot/hammer-fencing.sh disabled"
        logger.info(Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd))

        if self.settings.ceph_version == "1.2.3":
            cmd = "/root/pilot/hammer-ceph-fix.sh"
            logger.info(Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd))

        controlerPuppetRuns = []
        for each in self.settings.controller_nodes:
            puppetRunThr = runThreadedPuppet(each.hostname, each)
            controlerPuppetRuns.append(puppetRunThr)
        for thr in controlerPuppetRuns:
            thr.start()
            time.sleep(60) # ...
        for thr in controlerPuppetRuns:
            thr.join()

        # we will notify the user at end of install that fencing is disabled


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

    def run_puppet_on_all(self):
        logger.info("Run puppet on all the nodes one last time on compute nodes to work around known issues post deployment")

        for each in self.settings.compute_nodes:
            cmd = 'puppet agent -t -dv |& tee /root/puppet.out'
            logger.info("running puppet on " + each.hostname)
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
            cmd = "rm -f /var/lib/puppet/state/agent_catalog_run.lock"
            Ssh.execute_command(each.provisioning_ip, "root", self.settings.nodes_root_password, cmd)


        #controlerPuppetRuns = []
        logger.info("removing lock if any on controller node ")
        for each in self.settings.controller_nodes:
            cmd = "rm -f /var/lib/puppet/state/agent_catalog_run.lock"
            Ssh.execute_command(each.provisioning_ip, "root", self.settings.nodes_root_password, cmd)
