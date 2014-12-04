import ConfigParser, json
from osp_deployer import Node_Conf
 
class Settings():
    '''
    settings.ini & cluster.properties etc..
    '''

    def __init__(self, settingsFile):
       
        self.conf = ConfigParser.ConfigParser()
        self.conf.read(settingsFile)
        self.cluster_settings_map = self.getSettingsSection("Cluster Settings")
        self.network_conf = self.cluster_settings_map['cluster_nodes_configuration_file']
        self.domain = self.cluster_settings_map['domain']
        self.ipmi_user = self.cluster_settings_map['ipmi_user']
        self.ipmi_password = self.cluster_settings_map['ipmi_password']
        self.nodes_root_password = self.cluster_settings_map['nodes_root_password']
        self.subscription_manager_user = self.cluster_settings_map['subscription_manager_user']
        self.subscription_manager_password = self.cluster_settings_map['subscription_manager_password']
        self.subscription_manager_poolID = self.cluster_settings_map['subscription_manager_pool']
        self.ntp_server = self.cluster_settings_map['ntp_servers']
        self.time_zone = self.cluster_settings_map['time_zone']
        
        self.bastion_settings_map = self.getSettingsSection("Bastion Settings")
        self.rhl6_iso = self.bastion_settings_map['rhl6_iso']
        self.rhl7_iso = self.bastion_settings_map['rhl7_iso']
        self.ciros_image = self.bastion_settings_map['ciros_image']
        self.cygwin_installdir = self.bastion_settings_map['cygwin_installdir']
        self.rhel_install_location = self.bastion_settings_map['rhel_install_location']
        self.sah_kickstart= self.bastion_settings_map['sah_kickstart']
        self.foreman_deploy_sh = self.bastion_settings_map['foreman_deploy_sh']
        self.ceph_deploy_sh = self.bastion_settings_map['ceph_deploy_sh']
        
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
                    
                attrs = vars(node)
                print '\r '.join("%s: %s" % item for item in attrs.items())
                print "==========================================="
    
           
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
        