import ConfigParser, json, sys
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
        self.settingsFile = settingsFile
        self.cluster_settings_map = self.getSettingsSection("Cluster Settings")
        self.nodes_root_password = self.cluster_settings_map['cluster_password']
        self.cluster_password = self.cluster_settings_map['cluster_password']
        self.use_equalogic_backend = self.cluster_settings_map['use_equalogic_backend']
        if len(self.nodes_root_password) < 8 :
            raise IOError("cluster_password setting lenght should be > 8 characters")
        self.previous_deployment_cluster_password = self.cluster_settings_map['previous_deployment_cluster_password']
        self.openstack_services_password = self.nodes_root_password
        self.nova_public_network = self.cluster_settings_map['nova_public_network']
        self.nova_private_network = self.cluster_settings_map['nova_private_network']
        self.private_api_network = self.cluster_settings_map['private_api_network']
        self.tenant_vlan_range = self.cluster_settings_map['tenant_vlan_range']
        self.ceph_user_password = self.cluster_settings_map['ceph_user_password']
        self.ceph_admin_email = self.cluster_settings_map['ceph_admin_email']

        self.vip_cinder_private = self.cluster_settings_map['vip_cinder_private']
        self.vip_cinder_public = self.cluster_settings_map['vip_cinder_public']
        self.vip_mysql_private = self.cluster_settings_map['vip_mysql_private']
        self.vip_glance_private = self.cluster_settings_map['vip_glance_private']
        self.vip_glance_public = self.cluster_settings_map['vip_glance_public']
        self.vip_heat_private = self.cluster_settings_map['vip_heat_private']
        self.vip_heat_public = self.cluster_settings_map['vip_heat_public']
        self.vip_heat_cfn_private = self.cluster_settings_map['vip_heat_cfn_private']
        self.vip_heat_cfn_public = self.cluster_settings_map['vip_heat_cfn_public']
        self.vip_horizon_private = self.cluster_settings_map['vip_horizon_private']
        self.vip_horizon_public = self.cluster_settings_map['vip_horizon_public']
        self.vip_keystone_private = self.cluster_settings_map['vip_keystone_private']
        self.vip_keystone_public = self.cluster_settings_map['vip_keystone_public']
        self.vip_nova_private = self.cluster_settings_map['vip_nova_private']
        self.vip_nova_public = self.cluster_settings_map['vip_nova_public']
        self.vip_load_balancer_private = self.cluster_settings_map['vip_load_balancer_private']
        self.vip_rabbitmq_private = self.cluster_settings_map['vip_rabbitmq_private']
        self.vip_ceilometer_private = self.cluster_settings_map['vip_ceilometer_private']
        self.vip_ceilometer_public = self.cluster_settings_map['vip_ceilometer_public']
        self.vip_ceilometer_redis = self.cluster_settings_map['vip_ceilometer_redis_public']

        self.vip_neutron_public = self.cluster_settings_map['vip_neutron_public']
        self.vip_neutron_private = self.cluster_settings_map['vip_neutron_private']

        self.storage_nodes_are_730 = self.cluster_settings_map['storage_nodes_are_730xd']

        self.storage_network = self.cluster_settings_map['storage_network']
        self.storage_cluster_network = self.cluster_settings_map['storage_cluster_network']
        self.public_network = self.cluster_settings_map['public_network']
        self.provisioning_network = self.cluster_settings_map['provisioning_network']
        self.network_conf = self.cluster_settings_map['cluster_nodes_configuration_file']
        self.domain = self.cluster_settings_map['domain']
        self.ipmi_user = self.cluster_settings_map['ipmi_user']
        self.ipmi_password = self.cluster_settings_map['ipmi_password']

        self.subscription_manager_user = self.cluster_settings_map['subscription_manager_user']
        self.subscription_manager_password = self.cluster_settings_map['subscription_manager_password']

        self.subscription_manager_pool_sah = self.cluster_settings_map['subscription_manager_pool_sah']
        self.subscription_manager_pool_vm_rhel = self.cluster_settings_map['subscription_manager_pool_vm_rhel']
        self.subscription_manager_pool_phyical_openstack_nodes = self.cluster_settings_map['subscription_manager_pool_phyical_openstack_nodes']
        self.subscription_manager_pool_vm_openstack_nodes = self.cluster_settings_map['subscription_manager_pool_vm_openstack_nodes']
        self.subscription_manager_vm_ceph = self.cluster_settings_map['subscription_manager_vm_ceph']
        self.subscription_manager_pool_physical_ceph = self.cluster_settings_map['subscription_manager_pool_physical_ceph']
        if 'subscription_check_retries' in self.cluster_settings_map:
            self.subscription_check_retries = self.cluster_settings_map['subscription_check_retries']
        else:
            self.subscription_check_retries = 20
        self.controller_bond_opts=self.cluster_settings_map['controller_bond_opts']
        self.compute_bond_opts=self.cluster_settings_map['compute_bond_opts']
        self.storage_bond_opts=self.cluster_settings_map['storage_bond_opts']
        self.debug=None
        self.verbose=None

        self.debug = self.cluster_settings_map['debug']
        self.verbose = self.cluster_settings_map['verbose']
        self.heat_auth_key = self.cluster_settings_map['heat_auth_key']

        self.ntp_server = self.cluster_settings_map['ntp_servers']
        self.time_zone = self.cluster_settings_map['time_zone']
        self.stamp_storage = self.cluster_settings_map['storage']

        if self.cluster_settings_map['use_internal_repo'].lower() == 'true':
            self.internal_repos= True
            self.internal_repos_urls= []
            for each in self.cluster_settings_map['internal_repos_locations'].split(';'):
                self.internal_repos_urls.append(each)
        else:
            self.internal_repos= False


        if self.cluster_settings_map['use_equalogic_backend'].lower() == 'true':
            self.use_eql_backend = True
            self.c_be_eqlx_name  = self.cluster_settings_map['c_be_eqlx_name']
            self.c_eqlx_san_ip = self.cluster_settings_map['c_eqlx_san_ip']
            self.c_eqlx_san_login = self.cluster_settings_map['c_eqlx_san_login']
            self.c_eqlx_san_password = self.cluster_settings_map['c_eqlx_san_password']
            self.c_eqlx_ch_login = self.cluster_settings_map['c_eqlx_ch_login']
            self.c_eqlx_ch_pass = self.cluster_settings_map['c_eqlx_ch_pass']
            self.c_eqlx_group_n = self.cluster_settings_map['c_eqlx_group_n']
            self.c_eqlx_pool = self.cluster_settings_map['c_eqlx_pool']
            self.c_eqlx_use_chap = self.cluster_settings_map['c_eqlx_use_chap']
            self.c_mult_be = self.cluster_settings_map['c_mult_be']
        else:
            self.use_eql_backend = False

        if self.cluster_settings_map['use_compellent_backend'].lower() == 'true':
            self.use_dell_sc_backend = True
            self.c_be_dell_sc_name  = self.cluster_settings_map['c_be_dell_sc_name']
            self.c_dell_sc_api_port = self.cluster_settings_map['c_dell_sc_api_port']
            self.c_dell_sc_iscsi_ip_address = self.cluster_settings_map['c_dell_sc_iscsi_ip_address']
            self.c_dell_sc_iscsi_port = self.cluster_settings_map['c_dell_sc_iscsi_port']
            self.c_dell_sc_san_ip = self.cluster_settings_map['c_dell_sc_san_ip']
            self.c_dell_sc_san_login = self.cluster_settings_map['c_dell_sc_san_login']
            self.c_dell_sc_san_password = self.cluster_settings_map['c_dell_sc_san_password']
            self.c_dell_sc_ssn = self.cluster_settings_map['c_dell_sc_ssn']
            self.c_dell_sc_server_folder = self.cluster_settings_map['c_dell_sc_server_folder']
            self.c_dell_sc_volume_folder = self.cluster_settings_map['c_dell_sc_volume_folder']        
            self.c_mult_be = self.cluster_settings_map['c_mult_be']
        else:
            self.use_dell_sc_backend = False



        if self.cluster_settings_map['enable_version_locking'].lower() == 'true':
            self.version_locking_enabled = True
        else:
            self.version_locking_enabled = False

        self.foreman_provisioning_subnet_ip_start = self.cluster_settings_map['foreman_provisioning_subnet_ip_start']
        self.foreman_provisioning_subnet_ip_end=self.cluster_settings_map['foreman_provisioning_subnet_ip_end']

        self.bastion_settings_map = self.getSettingsSection("Bastion Settings")
        self.rhl71_iso = self.bastion_settings_map['rhl71_iso']
        self.ceph_iso = self.bastion_settings_map['ceph_iso']
        self.ciros_image = self.bastion_settings_map['ciros_image']
        self.cygwin_installdir = self.bastion_settings_map['cygwin_installdir']
        self.rhel_install_location = self.bastion_settings_map['rhel_install_location']
        self.sah_kickstart= self.bastion_settings_map['sah_kickstart']
        self.cloud_repo_dir = self.bastion_settings_map['cloud_repo_dir']

        if sys.platform.startswith('linux'):
            self.lock_files_dir = self.cloud_repo_dir + "/data/vlock_files"
            self.foreman_configuration_scripts = self.cloud_repo_dir + "/src"
            self.foreman_deploy_sh = self.foreman_configuration_scripts + '/mgmt/deploy-foreman-vm.sh'
            self.sah_ks = self.foreman_configuration_scripts + "/mgmt/osp-sah.ks"
            self.ceph_deploy_sh = self.foreman_configuration_scripts + '/mgmt/deploy-ceph-vm.sh'
            self.tempest_deploy_sh =  self.foreman_configuration_scripts + '/mgmt/deploy-tempest-vm.sh'
            self.hammer_configure_hostgroups_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-configure-hostgroups.sh'
            self.hammer_deploy_compute_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-deploy-compute.sh'
            self.hammer_deploy_controller_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-deploy-controller.sh'
            self.hammer_deploy_storage_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-deploy-storage.sh'
            self.hammer_configure_foreman_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-configure-foreman.sh'
            self.hammer_get_ids_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-get-ids.sh'
            self.hammer_dump_ids_sh = self.foreman_configuration_scripts + '/utils/networking/hammer-dump-ids.sh'
        else:
            self.lock_files_dir = self.cloud_repo_dir + "\\data\\vlock_files"
            self.foreman_configuration_scripts = self.cloud_repo_dir + "\\src"
            self.foreman_deploy_sh = self.foreman_configuration_scripts + "\\mgmt\\deploy-foreman-vm.sh"
            self.sah_ks = self.foreman_configuration_scripts + "\\mgmt\\osp-sah.ks"
            self.ceph_deploy_sh = self.foreman_configuration_scripts + "\\mgmt\\deploy-ceph-vm.sh"
            self.tempest_deploy_sh = self.foreman_configuration_scripts + "\\mgmt\\deploy-tempest-vm.sh"
            self.hammer_configure_hostgroups_sh = self.foreman_configuration_scripts + "\\utils\\networking\\hammer-configure-hostgroups.sh"
            self.hammer_deploy_compute_sh = self.foreman_configuration_scripts + "\\utils\\networking\\hammer-deploy-compute.sh"
            self.hammer_deploy_controller_sh = self.foreman_configuration_scripts + "\\utils\\networking\\hammer-deploy-controller.sh"
            self.hammer_deploy_storage_sh = self.foreman_configuration_scripts + "\\utils\\networking\\hammer-deploy-storage.sh"
            self.hammer_configure_foreman_sh = self.foreman_configuration_scripts + "\\utils\\networking\\hammer-configure-foreman.sh"
            self.hammer_get_ids_sh = self.foreman_configuration_scripts + "\\utils\\networking\\hammer-get-ids.sh"
            self.hammer_dump_ids_sh = self.foreman_configuration_scripts + "\\utils\\networking\\hammer-dump-ids.sh"

        self.controller_nodes = []
        self.compute_nodes = []
        self.ceph_nodes = []

        with open(self.network_conf) as config_file:
            json_data = json.load(config_file)
            for each in json_data:
                node = Node_Conf(each)

                try:
                    if node.is_sah == "true":
                        self.sah_node = node
                        print "SAH Node :: " + self.sah_node.hostname
                except:
                    pass
                try:
                    if node.is_foreman == "true":
                        self.foreman_node = node
                        print "Foreman Node :: " + self.foreman_node.hostname
                except:
                    pass
                try:
                    if node.is_ceph == "true":
                        self.ceph_node = node
                        print "Ceph Node :: " + self.ceph_node.hostname
                except:
                    pass
                try:
                    if node.is_tempest == "true":
                        self.tempest_node = node
                        print "Tempest Node :: " + self.tempest_node.hostname
                except:
                    pass
                try:
                    if node.is_controller == "true":
                        node.is_controller = True
                        self.controller_nodes.append(node)
                        print "Controller Node :: " + node.hostname
                except:
                    node.is_controller = False
                    pass

                try:
                    if node.is_compute == "true":
                        node.is_compute = True
                        self.compute_nodes.append(node)
                        print "Compute Node :: " + node.hostname
                except:
                    node.is_compute = False
                    pass
                try:
                    if self.stamp_storage == "ceph" and node.is_ceph_storage == "true":
                        self.ceph_nodes.append(node)
                        node.is_storage = True
                        print "Ceph Node :: " + node.hostname
                except:
                    node.is_storage = False
                    pass


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
