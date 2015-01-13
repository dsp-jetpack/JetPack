from osp_deployer.config import Settings
from auto_common import Ssh, Scp,  Widget, UI_Manager, FileHelper

import time
import logging
logger = logging.getLogger(__name__)

class Foreman():
    '''
    '''

    
    def __init__(self):
        self.settings = Settings.settings
        self.mediumID = ''
        self.controller_partition_tableID = ''
        self.compute_partition_tableID = ''
        self.pilot_partition_table = ''
        self.rhel_65_osId = ''
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
        if self.settings.stamp_type =='poc' :
            file = self.settings.foreman_configuration_scripts + "\\dell-poc.yaml.erb"
            
            FileHelper.replaceExpressionTXT(file, 'passwd_auto =.*',"passwd_auto = '" + self.settings.openstack_services_password + "'" )
            
            FileHelper.replaceExpressionTXT(file, 'controller_admin_host =.*',"controller_admin_host = '" + self.settings.controller_nodes[0].provisioning_ip + "'" )
            FileHelper.replaceExpressionTXT(file, 'controller_priv_host =.*',"controller_priv_host = '" + self.settings.controller_nodes[0].private_ip + "'" )
            FileHelper.replaceExpressionTXT(file, 'controller_pub_host =.*',"controller_pub_host = '" + self.settings.controller_nodes[0].public_ip + "'" )
        
            FileHelper.replaceExpressionTXT(file, 'nova_public_net =.*',"nova_public_net = '" + self.settings.nova_public_network + "'" )
            FileHelper.replaceExpressionTXT(file, 'nova_public_iface =.*',"nova_public_iface = '" + self.settings.compute_nodes[0].nova_public_interface + "'" )

            FileHelper.replaceExpressionTXT(file, 'nova_private_net =.*',"nova_private_net = '" + self.settings.nova_private_network + "'" )
            FileHelper.replaceExpressionTXT(file, 'nova_private_iface =.*',"nova_private_iface = '" + self.settings.compute_nodes[0].nova_private_interface + "'" )
 
            FileHelper.replaceExpressionTXT(file, 'private_api_net =.*',"private_api_net = '" + self.settings.nova_private_network + "'" )
            FileHelper.replaceExpressionTXT(file, 'private_api_iface =.*',"private_api_iface = '" + self.settings.compute_nodes[0].private_interface + "'" )
 
    
        elif self.settings.stamp_type =='pilot' :
            file = self.settings.foreman_configuration_scripts + "\\dell-pilot.yaml.erb"
            
            FileHelper.replaceExpressionTXT(file, 'passwd_auto =.*',"passwd_auto = '" + self.settings.openstack_services_password + "'" )
            
            FileHelper.replaceExpressionTXT(file, 'cluster_member_ip1 =.*',"cluster_member_ip1 = '" + self.settings.controller_nodes[0].private_ip + "'" )
            FileHelper.replaceExpressionTXT(file, 'cluster_member_name1 =.*',"cluster_member_name1 = '" + self.settings.controller_nodes[0].hostname + "'" )
            
            FileHelper.replaceExpressionTXT(file, 'cluster_member_ip2 =.*',"cluster_member_ip2 = '" + self.settings.controller_nodes[1].private_ip + "'" )
            FileHelper.replaceExpressionTXT(file, 'cluster_member_name2 =.*',"cluster_member_name2 = '" + self.settings.controller_nodes[1].hostname + "'" )
            
            FileHelper.replaceExpressionTXT(file, 'cluster_member_ip3 =.*',"cluster_member_ip3 = '" + self.settings.controller_nodes[2].private_ip + "'" )
            FileHelper.replaceExpressionTXT(file, 'cluster_member_name3 =.*',"cluster_member_name3 = '" + self.settings.controller_nodes[2].hostname + "'" )
            
            startipS_p = self.settings.vip_private_network_range_start.split(".")[3]
            vip_ip_private = int(startipS_p)
            priv_net =  self.settings.vip_private_network_range_start.split(".")[0]+"." + self.settings.vip_private_network_range_start.split(".")[1] + "." + self.settings.vip_private_network_range_start.split(".")[2] + "."
            
            startipS_pb = self.settings.vip_public_network_range_start.split(".")[3]
            vip_ip_public = int(startipS_pb)
            pub_net = self.settings.vip_public_network_range_start.split(".")[0]+"." + self.settings.vip_public_network_range_start.split(".")[1] + "." + self.settings.vip_public_network_range_start.split(".")[2] + "."
            
            FileHelper.replaceExpressionTXT(file, 'vip_amqp = .*',"vip_amqp = '" + priv_net+ str(vip_ip_private) + "'" )
            vip_ip_private +=1
            FileHelper.replaceExpressionTXT(file, 'vip_cinder_adm = .*',"vip_cinder_adm = '" + priv_net+ str(vip_ip_private) + "'" )
            vip_ip_private +=1
            FileHelper.replaceExpressionTXT(file, 'vip_cinder_pub = .*',"vip_cinder_pub = '" + pub_net + str(vip_ip_public) + "'" )
            vip_ip_public +=1        
            FileHelper.replaceExpressionTXT(file, 'vip_db = .*',"vip_db = '" + priv_net+ str(vip_ip_private) + "'" )
            vip_ip_private +=1
            FileHelper.replaceExpressionTXT(file, 'vip_glance_adm = .*',"vip_glance_adm = '" + priv_net+ str(vip_ip_private) + "'" )
            vip_ip_private +=1
            FileHelper.replaceExpressionTXT(file, 'vip_glance_pub = .*',"vip_glance_pub = '" + pub_net + str(vip_ip_public) + "'" )
            vip_ip_public +=1 
            FileHelper.replaceExpressionTXT(file, 'vip_heat_adm = .*',"vip_heat_adm = '" + priv_net+ str(vip_ip_private) + "'" )
            vip_ip_private +=1
            FileHelper.replaceExpressionTXT(file, 'vip_heat_pub = .*',"vip_heat_pub = '" +pub_net + str(vip_ip_public) + "'" )
            vip_ip_public +=1         
            FileHelper.replaceExpressionTXT(file, 'vip_heat_cfn_adm = .*',"vip_heat_cfn_adm = '" + priv_net+ str(vip_ip_private) + "'" )
            vip_ip_private +=1
            FileHelper.replaceExpressionTXT(file, 'vip_heat_cfn_pub = .*',"vip_heat_cfn_pub = '" + pub_net + str(vip_ip_public) + "'" )
            vip_ip_public +=1 
            FileHelper.replaceExpressionTXT(file, 'vip_horizon_adm = .*',"vip_horizon_adm = '" +priv_net+  str(vip_ip_private) + "'" )
            vip_ip_private +=1
            FileHelper.replaceExpressionTXT(file, 'vip_horizon_pub = .*',"vip_horizon_pub = '" +pub_net + str(vip_ip_public) + "'" )
            vip_ip_public +=1 
            FileHelper.replaceExpressionTXT(file, 'vip_keystone_adm = .*',"vip_keystone_adm = '" + priv_net+ str(vip_ip_private) + "'" )
            vip_ip_private +=1
            FileHelper.replaceExpressionTXT(file, 'vip_keystone_pub = .*',"vip_keystone_pub = '" +pub_net + str(vip_ip_public) + "'" )
            vip_ip_public +=1 
            FileHelper.replaceExpressionTXT(file, 'vip_loadbalancer = .*',"vip_loadbalancer = '" +priv_net+  str(vip_ip_private) + "'" )
            vip_ip_private +=1
            FileHelper.replaceExpressionTXT(file, 'vip_nova_adm = .*',"vip_nova_adm = '" + priv_net+ str(vip_ip_private) + "'" )
            vip_ip_private +=1
            FileHelper.replaceExpressionTXT(file, 'vip_nova_priv = .*',"vip_nova_priv = '" + priv_net+ str(vip_ip_private) + "'" )
            vip_ip_private +=1
            FileHelper.replaceExpressionTXT(file, 'vip_nova_pub = .*',"vip_nova_pub = '" + pub_net + str(vip_ip_public) + "'" )
            vip_ip_public +=1 
            FileHelper.replaceExpressionTXT(file, 'fence_clu_iface = .*',"fence_clu_iface = '" + priv_net+ str(vip_ip_private) + "'" )
            vip_ip_private +=1
            
            FileHelper.replaceExpressionTXT(file, 'net_fix = .*',"net_fix = '" + self.settings.nova_public_network + "'" )
            FileHelper.replaceExpressionTXT(file, 'net_float = .*',"net_float = '" + self.settings.nova_private_network + "'" )

            FileHelper.replaceExpressionTXT(file, 'net_priv_iface = .*',"net_priv_iface = 'bond0." + self.settings.controller_nodes[1].private_api_vlanid + "'" )
            FileHelper.replaceExpressionTXT(file, 'net_pub_iface = .*',"net_pub_iface = 'bond1" + "'" )

            
            
    def upload_scripts(self):
        if self.settings.stamp_type =='poc' :
            files = ['bonding_snippet.template',
                     'dell-osp-ks.template',
                     'dell-osp-pxe.template',
                     'dell-poc.yaml.erb',
                     'dell-poc-compute.partition',
                     'dell-poc-controller.partition',
                     'interface_config.template',
                     ]
        elif self.settings.stamp_type =='pilot' :
            files = ['bonding_snippet.template',
                     'dell-osp-ks.template',
                     'dell-osp-pxe.template',
                     'dell-pilot.partition',
                     'dell-pilot.yaml.erb',
                     'interface_config.template',
                     ]
        
        print "uploading deployment scripts .."
        for file in files :
            localfile = self.settings.foreman_configuration_scripts + "\\" + file
            remotefile = '/root/' + file
            Scp.put_file(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, localfile, remotefile)

        
    def install_hammer(self):
        install = 'yum -y install "*hammer*"'
        print ("installing hammer")
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, install)
        
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
        print "mount iso on foreman node"
        cmd = 'echo "/root/RHEL7.iso /usr/share/foreman/public/iso iso9660 loop,ro 0 0" >> /etc/fstab'
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        cmd = 'mkdir /usr/share/foreman/public/iso'
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
        print "Stamp Type :: " + self.settings.stamp_type
        if self.settings.stamp_type =='poc' :
            compute_parition_table = 'dell-poc-compute.partition'
            controler_partition_table = 'dell-poc-controller.partition'
            cmds = ['hammer partition-table create --name dell-poc-controller --os-family Redhat --file /root/' + str(controler_partition_table),
                'hammer partition-table create --name dell-poc-compute --os-family Redhat --file /root/' + str(compute_parition_table),
                ]
        elif self.settings.stamp_type == 'pilot': 
            pilot_partition_table ='dell-pilot.partition'
            cmds = ['hammer partition-table create --name dell-pilot --os-family Redhat --file /root/' + str(pilot_partition_table),
                    ]   
        for cmd in cmds:
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        
        if self.settings.stamp_type =='poc' :
            cmd = 'hammer partition-table list | grep "dell-poc-controller" | grep -o "^\w*\\b"'
            r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
            self.controller_partition_tableID = r_out.replace("\n", "").replace("\r", "")  
            cmd = 'hammer partition-table list | grep "dell-poc-compute" | grep -o "^\w*\\b"'
            r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
            self.compute_partition_tableID = r_out.replace("\n", "").replace("\r", "")  
            print "Controlller parition table ID  : " + self.controller_partition_tableID
            print "Compute partition talbe iD : " + self.compute_partition_tableID
        elif self.settings.stamp_type == 'pilot': 
            cmd = 'hammer partition-table list | grep "dell-pilot" | grep -o "^\w*\\b"'
            r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
            self.pilot_partition_table = r_out.replace("\n", "").replace("\r", "")  
        
    def configure_operating_systems(self):
        print "configure operating systems"
        print "create RHEl7 OS"
        cmd = 'hammer os create --name "RedHat" --major 7 --minor 0 --family Redhat'
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        cmd = 'hammer os list | grep "6.6" | grep -o "^\w*\\b"'
        r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        self.rhel_65_osId = r_out.replace("\n", "").replace("\r", "")  
        cmd = 'hammer os list | grep "7.0" | grep -o "^\w*\\b"'
        r_out, r_err =   Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)       
        self.rhel_7_osId = r_out.replace("\n", "").replace("\r", "")  
        
        print "associate architecture to OS/s"
        if self.settings.stamp_type =='poc' :
            cmds = ['hammer os add-architecture --architecture x86_64 --id '+ self.rhel_65_osId,
                    'hammer os add-architecture --architecture x86_64 --id ' + self.rhel_7_osId,
                    ]
        elif self.settings.stamp_type == 'pilot':
            cmds = ['hammer os add-architecture --architecture x86_64 --id ' + self.rhel_7_osId,
                    ]
        for cmd in cmds : 
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        
        print "associate parition/Os"
        
        if self.settings.stamp_type =='poc' :
            cmds = ['hammer os add-ptable --ptable-id '+self.controller_partition_tableID+' --id '+self.rhel_65_osId,
                    'hammer os add-ptable --ptable-id '+self.controller_partition_tableID+' --id '+self.rhel_7_osId,
                    'hammer os add-ptable --ptable-id '+self.compute_partition_tableID+' --id '+self.rhel_65_osId,
                    'hammer os add-ptable --ptable-id '+self.compute_partition_tableID+' --id '+self.rhel_7_osId,
                    ]
        elif self.settings.stamp_type == 'pilot':
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
        if self.settings.stamp_type =='poc' :
            ks_template = 'dell-osp-ks.template'
            pxe_template ='dell-osp-pxe.template'
            interface_template = 'interface_config.template'
            bonding_template = 'bonding_snippet.template'
        elif self.settings.stamp_type == 'pilot': 
            ks_template = 'dell-osp-ks.template'
            pxe_template = 'dell-osp-pxe.template'
            interface_template = 'interface_config.template'
            bonding_template = 'bonding_snippet.template'
        if self.settings.stamp_type =='poc' :
            cmds = [ 
                'hammer template create --name "Dell OpenStack Kickstart Template" --type provision --operatingsystem-ids "'+self.rhel_65_osId+', '+self.rhel_7_osId +'" --file /root/' + ks_template,
                'hammer template create --name "Dell OpenStack PXE Template" --type PXELinux --operatingsystem-ids "'+self.rhel_65_osId+', '+self.rhel_7_osId+'" --file /root/'+ pxe_template,
                'hammer template create --name "bond_interfaces" --type snippet --file /root/' + bonding_template,
                'hammer template create --name "interface_config" --type snippet --file /root/' + interface_template,
                ]
        elif self.settings.stamp_type =='pilot' :
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
        
        if self.settings.stamp_type =='poc' :
            cmds = ['hammer os update --config-template-ids "'+self.kickstart_templateID+', '+ self.pxe_templateID+'" --medium-ids '+self.mediumID+' --id '+self.rhel_65_osId,
                    'hammer os update --config-template-ids "'+self.kickstart_templateID+', '+ self.pxe_templateID+'" --medium-ids '+self.mediumID+' --id '+self.rhel_7_osId,
                    ]
        elif self.settings.stamp_type =='pilot' :
            cmds = ['hammer os update --config-template-ids "'+self.kickstart_templateID+', '+ self.pxe_templateID+'" --medium-ids '+self.mediumID+' --id '+self.rhel_7_osId,
                    ]
        for cmd in cmds:
            print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        
        if self.settings.stamp_type =='poc' :
            cmds = ['hammer os set-default-template --config-template-id '+self.kickstart_templateID +' --id ' + self.rhel_65_osId,
                    'hammer os set-default-template --config-template-id '+self.kickstart_templateID +' --id ' + self.rhel_7_osId,
                    'hammer os set-default-template --config-template-id '+self.pxe_templateID +' --id ' + self.rhel_65_osId,
                    'hammer os set-default-template --config-template-id '+self.pxe_templateID +' --id ' + self.rhel_7_osId ,
                    ]
        elif self.settings.stamp_type =='pilot' :
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
                if self.settings.stamp_type =='poc' :
                    command = 'hammer host create --name "'+ each.hostname +'" --root-password "'+ self.settings.nodes_root_password+'" --build true --enabled true --managed true --environment-id '+self.environment_Id+' --domain-id 1 --puppet-proxy-id 1 --operatingsystem-id '+self.rhel_7_osId+' --ip '+ each.provisioning_ip + ' --subnet-id 1 --architecture-id 1 --medium-id '+self.mediumID+' --partition-table-id '+self.controller_partition_tableID +' --mac "'+each.provisioning_mac_address+'"'
                elif self.settings.stamp_type =='pilot' :
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
                if self.settings.stamp_type =='poc' :
                    command = 'hammer host create --name "'+ each.hostname +'" --root-password "'+ self.settings.nodes_root_password+'" --build true --enabled true --managed true --environment-id '+self.environment_Id+' --domain-id 1 --puppet-proxy-id 1 --operatingsystem-id '+ self.rhel_7_osId+' --ip '+each.provisioning_ip +' --subnet-id 1 --architecture-id 1 --medium-id '+self.mediumID+' --partition-table-id '+self.compute_partition_tableID +' --mac "'+each.provisioning_mac_address+'"'
                if self.settings.stamp_type =='pilot' :
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
        
        if self.settings.stamp_type == 'poc':
            commands =[
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_65_osId +' --name subscription_manager --value true',
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_65_osId +' --name subscription_manager_username --value '+ self.settings.subscription_manager_user,
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_65_osId  +' --name subscription_manager_password --value "'+ self.settings.subscription_manager_password+'"',
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_65_osId  +' --name subscription_manager_pool --value ' + self.settings.subscription_manager_poolID,
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_65_osId +' --name subscription_manager_repos --value "rhel-server-rhscl-6-rpms, rhel-6-server-rpms, rhel-6-server-openstack-5.0-rpms"',
                   
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_7_osId +' --name subscription_manager --value true',
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_7_osId +' --name subscription_manager_username --value '+ self.settings.subscription_manager_user,
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_7_osId  +' --name subscription_manager_password --value "'+ self.settings.subscription_manager_password+'"',
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_7_osId  +' --name subscription_manager_pool --value ' + self.settings.subscription_manager_poolID,
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_7_osId +' --name subscription_manager_repos --value "rhel-server-rhscl-7-rpms, rhel-7-server-rpms, rhel-7-server-openstack-5.0-rpms"'
                   ]
            for each in commands :
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, each)
        elif self.settings.stamp_type == 'pilot':
            commands = [
                    'hammer os set-parameter --operatingsystem-id '+ self.rhel_7_osId +' --name subscription_manager --value true',
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_7_osId +' --name subscription_manager_username --value '+ self.settings.subscription_manager_user,
                   'hammer os set-parameter --operatingsystem-id '+ self.rhel_7_osId  +' --name subscription_manager_password --value "'+ self.settings.subscription_manager_password+'"',
                        ]
            for each in commands :
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, each)
            for node in self.settings.controller_nodes:
                command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_pool --value '+self.settings.subscription_manager_poolID
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_repos --value "rhel-server-rhscl-7-rpms, rhel-7-server-rpms, rhel-7-server-openstack-5.0-rpms,rhel-ha-for-rhel-7-server-rpms"'
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
            for node in self.settings.compute_nodes:
                command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_pool --value '+self.settings.subscription_manager_poolID
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_repos --value "rhel-server-rhscl-7-rpms, rhel-7-server-rpms, rhel-7-server-openstack-5.0-rpms"'
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
            if self.settings.stamp_storage == "ceph":
                for node in self.settings.ceph_nodes:
                    command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_pool --value '+self.settings.subscription_manager_poolID
                    print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                    command = 'hammer host set-parameter --host-id '+node.hostID+' --name subscription_manager_repos --value "rhel-server-rhscl-7-rpms, rhel-7-server-rpms, rhel-x86_64-server-7"'
                    print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                    

        
    def configure_controller_nic(self): 
        print "configuring the controller node(s) nics"    
        for node in self.settings.controller_nodes:
            if self.settings.stamp_type =='poc' :
                command = "hammer host set-parameter --host-id "+node.hostID+" --name nics --value '(["+node.public_interface+"]=\"onboot static "+node.public_mac_address+" "+ node.public_ip +"/"+ node.public_netmask +"\" ["+node.private_interface+"]=\"onboot static "+node.private_mac_address+" "+node.private_ip+"/"+node.private_netmask+"\")'"
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)   
            elif self.settings.stamp_type == 'pilot':
                print "Configure non bonded interfaces"
                # management vlan.
                command = "hammer host set-parameter --host-id "+node.hostID+" --name nics --value '(["+node.idrac_interface+"]=\"onboot static "+ node.idrac_secondary_macaddress+" "+node.idrac_secondary_ip+"/"+node.idrac_secondary_netmask+"\")'"        
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)

                print "configure bonded interfaces"
                
                commands = ["hammer host set-parameter --host-id "+node.hostID+" --name bonds --value '( [bond0]=\"onboot none\" [bond0."+node.private_api_vlanid+"]=\"onboot static vlan "+node.private_ip+"/"+node.private_netmask+"\" [bond0."+node.storage_vlanid+"]=\"onboot static vlan "+node.storage_ip+"/"+node.storage_netmask+"\" [bond1]=\"onboot static "+node.public_ip+"/"+node.public_netmask+"\")'",
                            "hammer host set-parameter --host-id "+node.hostID+" --name bond_ifaces  --value '( [bond0]=\""+node.bond0_interfaces+"\" [bond1]=\""+node.bond1_interfaces+"\")'",
                            "hammer host set-parameter --host-id "+node.hostID+" --name bond_opts --value '( [bond0]=\"mode=balance-tlb miimon_100\" [bond1]=\"mode=balance-tlb miimon_100\")'"]
                
                for command in commands:
                    print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                
    def configure_compute_nic(self): 
        print "configuring the compute node(s) nics"      
        for node in self.settings.compute_nodes:
            if self.settings.stamp_type =='poc' :
                cmd = "hammer host set-parameter --host-id "+node.hostID+" --name nics --value '(["+node.nova_public_interface+"]=\"onboot static "+node.nova_public_mac_address+" "+ node.nova_public_ip +"/"+ node.nova_public_netmask +"\" ["+node.private_interface+"]=\"onboot static "+node.private_mac_address+" "+node.private_ip+"/"+node.private_netmask+"\" ["+node.nova_private_interface+"]=\"onboot none "+node.nova_private_mac_address +"\")'"
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)   
            elif self.settings.stamp_type == 'pilot':
                print "configure bonded interfaces"
                
                commands = ["hammer host set-parameter --host-id "+node.hostID+" --name bonds --value '( [bond0]=\"onboot none\" [bond0."+node.nova_private_vlanid+"]=\"onboot static vlan "+node.nova_private_ip+"/"+node.nova_private_netmask+"\" [bond0."+node.private_api_vlanid+"]=\"onboot static vlan "+node.private_ip+"/"+node.private_netmask+"\" [bond0."+node.storage_vlanid+"]=\"onboot static vlan "+node.storage_ip+"/"+node.storage_netmask+"\" [bond1]=\"onboot static "+node.storage_netmask+"/"+node.nova_public_netmask+"\")'",
                            "hammer host set-parameter --host-id "+node.hostID+" --name bond_ifaces --value '( [bond0]=\""+node.bond0_interfaces+"\" [bond1]=\""+node.bond1_interfaces+"\")'",
                            "hammer host set-parameter --host-id "+node.hostID+" --name bond_opts --value '( [bond0]=\"mode=balance-tlb PROMISC=yes\" [bond1]=\"mode=balance-tlb PROMISC=yes\")'"]
                for command in commands:
                    print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
    
    def configure_ceph_nic(self): 
        print "configuring the Ceph node(s) nics"  
        for node in self.settings.ceph_nodes:
            print "configure bonded interfaces"
            
            commands = ["hammer host set-parameter --host-id "+node.hostID+" --name bonds --value '( [bond0]=\"onboot none\" [bond0]=\"onboot static vlan "+node.storage_ip+"/"+node.storage_netmask+"\" [bond1]=\"onboot static "+node.storage_cluster_ip+"/"+node.storage_cluster_netmask+"\")'",
                       "hammer host set-parameter --host-id "+node.hostID+" --name bond_ifaces  --value '( [bond0]=\""+node.bond0_interfaces+"\" [bond1]=\""+node.bond1_interfaces+"\")'",
                       "hammer host set-parameter --host-id "+node.hostID+" --name bond_opts --value '( [bond0]=\"mode=mode=balance-tlb\" [bond1]=\"mode=mode=balance-tlb\")'"]
                
            for command in commands:
                print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, command)
                
    def configureHostGroups_Parameters(self):
        print "Configure the hostgroups parameter"
        
        cmd = 'yum install -y rubygem-foreman_api'
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        
        # Log a bug :: below missing from the Pilot guide
        cmd = "sed -i \"s/options.password = '.*'/options.password = '"+ self.settings.foreman_password +"'/\" /usr/share/openstack-foreman-installer/bin/quickstack_defaults.rb"
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        
        if self.settings.stamp_type =='poc' :
            erbFile = 'dell-poc.yaml.erb'
        elif self.settings.stamp_type == 'pilot':
            erbFile = 'dell-pilot.yaml.erb'
            
        cmd = 'cd /usr/share/openstack-foreman-installer; bin/quickstack_defaults.rb -g config/hostgroups.yaml -d ~/'+erbFile+' -v parameters'
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        
        cmd = "hammer sc-param list --per-page 1000 --search network_overrides | awk '/network_overrides/ {print $1}'"
        paramID = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")
        
        cmd = "hammer sc-param update --id "+paramID+" --default-value \"{'vlan_start': "+self.settings.nova_private_vlanID+", 'force_dhcp_release': 'false'}\" --parameter-type hash --override yes"
        print Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)
        
        if self.settings.stamp_type =='pilot' :
            logger.info("Disabling Neutron")
            
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
       
            override = Widget("//span[.='quickstack::pacemaker::neutron']/../..//span[.='enabled']/../..//a[.='override']")
            override.click()
            
            inputs =   UI_Manager.driver().find_elements_by_xpath("//textarea[@placeholder='Value']")
            
            neutronEnabled = inputs[0];
            
            neutronEnabled.clear();
            neutronEnabled.send_keys("false");
            
            sub = Widget("//input[@value='Submit']")
            sub.click()
            time.sleep(10)
            
            
        
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
   
            print "running puppet on " + each.hostname
            cmd = 'puppet agent -t -dv |& tee /root/puppet.out'
            Ssh.execute_command(each.provisioning_ip, "root", self.settings.nodes_root_password, cmd)
            
            
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
            Ssh.execute_command(each.provisioning_ip, "root", self.settings.nodes_root_password, cmd)
        
        
    def configureNodes(self):
            
        cmd = 'hammer hostgroup list | grep "HA All In One Controller" | grep -o "^\w*\\b"'
        controllerGroupId = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")  
        print "controllerGroupId : " + controllerGroupId
        cmd = 'hammer hostgroup list | grep "Compute (Nova Network)" | grep -o "^\w*\\b"'
        computeGroupId = Ssh.execute_command(self.settings.foreman_node.public_ip, "root", self.settings.foreman_node.root_password, cmd)[0].replace("\n", "").replace("\r", "")
        print "computeGroupId : " + computeGroupId
        
        print "Apply hostgroup to controller node(s)"
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
            
            url = 'https://10.21.148.112/hosts/'+each.hostname+'.' + self.settings.domain+'/edit'
            UI_Manager.driver().get(url)
           
            paramLink = Widget("//a[.='Parameters']")
            paramLink.waitFor(20)
            paramLink.click()
           
            # quickstack::pacemaker::common fence_ipmilan_address 
            ipmiAdress_override = Widget("//span[.='fence_ipmilan_address']/../..//a[.='override']")
            # quickstack::pacemaker::common fence_ipmilan_username 
            ipmiUser_override = Widget("//span[.='fence_ipmilan_username']/../..//a[.='override']")
            # quickstack::pacemaker::common fence_ipmilan_password 
            ipmiPassword_override = Widget("//span[.='fence_ipmilan_password']/../..//a[.='override']")
            # quickstack::pacemaker::params::private_ip IP address of the controllers nic on the Private API network 
            privateIp = Widget("//span[.='private_ip']/../..//a[.='override']")
            
            
            ipmiAdress_override.waitFor(20)
            
            ipmiAdress_override.click()
            ipmiUser_override.click()
            ipmiPassword_override.click()
            privateIp.click()
            
            
            inputs =   UI_Manager.driver().find_elements_by_xpath("//textarea[@placeholder='Value']")
            
            ipmiAddress = inputs[0];
            ipmiUser = inputs[1];
            ipmiPass = inputs[2];
            privIp = inputs[3];
            
            ipmiAddress.clear();
            ipmiAddress.send_keys(each.idrac_secondary_ip);
            ipmiUser.clear();
            ipmiUser.send_keys(self.settings.ipmi_user);
            ipmiPass.clear();
            ipmiPass.send_keys(self.settings.ipmi_password);
            privIp.clear();
            privIp.send_keys(each.private_ip);
            
            sub = Widget("//input[@value='Submit']")
            sub.click()
            time.sleep(10)

        logger.info("run puppet on controller nodes")
        for each in self.settings.controller_nodes:
            cmd = 'puppet agent -t -dv |& tee /root/puppet.out'
            logger.info(Ssh.execute_command(each.provisioning_ip, "root", self.settings.nodes_root_password, cmd))
            
        logger.info("Apply the host group on the compute nodes")
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
        for each in self.settings.compute_nodes:
            cmd = 'puppet agent -t -dv |& tee /root/puppet.out'
            logger.info(Ssh.execute_command(each.provisioning_ip, "root", self.settings.nodes_root_password, cmd))