import ConfigParser, json
from osp_deployer import Node_Conf
import logging
logger = logging.getLogger(__name__)

class Settings():
    '''
    settings.ini & cluster.properties etc..
    '''
    settings = '' # so it can be read by UI lib's etc..

    def __init__(self, settingsFile):
        self.foreman_password = ''
        self.conf = ConfigParser.ConfigParser()
        self.conf.read(settingsFile)
        self.cluster_settings_map = self.getSettingsSection("Cluster Settings")
        self.openstack_services_password = self.cluster_settings_map['openstack_services_password']
        self.nova_public_network = self.cluster_settings_map['nova_public_network']
        self.nova_private_network = self.cluster_settings_map['nova_private_network']
        self.private_api_network = self.cluster_settings_map['private_api_network']
        self.nova_private_vlanID = self.cluster_settings_map['nova_private_vlanid']
        
        self.vip_private_network_range_start = self.cluster_settings_map['vip_private_network_range_start']
        self.vip_public_network_range_start = self.cluster_settings_map['vip_public_network_range_start']

        self.storage_network = self.cluster_settings_map['storage_network']
        self.storage_cluster_network = self.cluster_settings_map['storage_cluster_network']
        self.public_network = self.cluster_settings_map['public_network']
        self.provisioning_network = self.cluster_settings_map['provisioning_network']
        self.network_conf = self.cluster_settings_map['cluster_nodes_configuration_file']
        self.domain = self.cluster_settings_map['domain']
        self.ipmi_user = self.cluster_settings_map['ipmi_user']
        self.ipmi_password = self.cluster_settings_map['ipmi_password']
        self.nodes_root_password = self.cluster_settings_map['nodes_root_password']
        if len(self.nodes_root_password) < 8 :
            raise IOError("nodes_root_password setting lenght should be > 8 characters")
        self.subscription_manager_user = self.cluster_settings_map['subscription_manager_user']
        self.subscription_manager_password = self.cluster_settings_map['subscription_manager_password']
        self.subscription_manager_poolID = self.cluster_settings_map['subscription_manager_pool']
        self.ntp_server = self.cluster_settings_map['ntp_servers']
        self.time_zone = self.cluster_settings_map['time_zone']
        self.stamp_type = self.cluster_settings_map['stamp_type']
        self.stamp_storage = self.cluster_settings_map['storage']
        
        self.foreman_provisioning_subnet_ip_start = self.cluster_settings_map['foreman_provisioning_subnet_ip_start']
        self.foreman_provisioning_subnet_ip_end=self.cluster_settings_map['foreman_provisioning_subnet_ip_end']
        
        self.bastion_settings_map = self.getSettingsSection("Bastion Settings")
        self.rhl6_iso = self.bastion_settings_map['rhl6_iso']
        self.rhl7_iso = self.bastion_settings_map['rhl7_iso']
        self.ciros_image = self.bastion_settings_map['ciros_image']
        self.cygwin_installdir = self.bastion_settings_map['cygwin_installdir']
        self.rhel_install_location = self.bastion_settings_map['rhel_install_location']
        self.sah_kickstart= self.bastion_settings_map['sah_kickstart']
        self.foreman_deploy_sh = self.bastion_settings_map['foreman_deploy_sh']
        self.ceph_deploy_sh = self.bastion_settings_map['ceph_deploy_sh']
        
        if self.stamp_type == 'poc':
            self.foreman_configuration_scripts = self.bastion_settings_map['poc_foreman_configuration_scripts_directory']
        elif self.stamp_type == 'pilot':
            self.foreman_configuration_scripts = self.bastion_settings_map['pilot_foreman_configuration_scripts_directory']
        
        self.controller_nodes = []
        self.compute_nodes = []
        self.ceph_nodes = []
        
        with open(self.network_conf) as config_file:    
            json_data = json.load(config_file)
            for each in json_data:
                node = Node_Conf(each)
                print "==========================================="
               
                try:
                    if node.is_sah == "true":
                        self.sah_node = node
                        print "SAH Node :: " + self.sah_node.hostname
                except:
                    print "."
                try:
                    if node.is_foreman == "true":
                        self.foreman_node = node
                        print "Foreman Node :: " + self.foreman_node.hostname
                except:
                    print "."
                try:
                    if node.is_ceph == "true":
                        self.ceph_node = node
                        print "Ceph Node :: " + self.ceph_node.hostname
                except:
                    print "."
                try:
                    if node.is_controller == "true":
                        self.controller_nodes.append(node)
                        print "Controller Node :: " + node.hostname
                except:
                    print "."
                try:
                    if node.is_compute == "true":
                        self.compute_nodes.append(node)
                        print "Compute Node :: " + node.hostname
                except:
                    print "."   
                try:
                    if self.stamp_storage == "ceph" and node.is_ceph_storage == "true":
                        self.ceph_nodes.append(node)
                        print "Ceph Node :: " + node.hostname
                    
                except:
                    print "." 
                attrs = vars(node)
                print '\r '.join("%s: %s" % item for item in attrs.items())
                print "==========================================="
    
        Settings.settings = self
           
    def getSettingsSection(self, section):
        dictr = {}
        options = self.conf.options(section)
        for option in options:
            try:
                dictr[option] = self.conf.get(section, option)
                if dictr[option] == -1:
                    print("skip: %s" % option)
            except:
                print("exception on %s!" % option)
                dictr[option] = None
        return dictr  
        