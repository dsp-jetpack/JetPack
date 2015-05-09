import sys, getopt, time, subprocess, paramiko,logging, traceback, os.path, urllib2, shutil, socket
from osp_deployer.foreman import Foreman
from osp_deployer.ceph import Ceph
from auto_common import Ipmi, Ssh, FileHelper, Scp, UI_Manager
from osp_deployer import Settings

logger = logging.getLogger(__name__)

def log(message):
    print (message)
    logger.info(  message)

class Deployer_sanity():
    '''
    '''


    def __init__(self):
        self.settings = Settings.settings

    def isValidIp(self, address):
        try:
            socket.inet_aton(address)
            ip = True
        except socket.error:
            ip = False

        return ip


    def check_files(self):

        #Check new settings/properties are set
        assert hasattr(self.settings, 'cluster_password'), self.settings.settingsFile+ " has no cluster_password setting"

        assert os.path.isfile(self.settings.rhl71_iso) , self.settings.rhl71_iso + "ISO doesnn't seem to exist"
        assert os.path.isfile(self.settings.sah_kickstart) , self.settings.sah_kickstart + "kickstart file doesnn't seem to exist"
        assert os.path.isfile(self.settings.foreman_deploy_sh) , self.settings.foreman_deploy_sh + " script doesnn't seem to exist"

        hammer_scripts =['hammer-configure-hostgroups.sh',
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
        'provision.sh',
        'bond.sh'
         ]
        hammer_script_folder =  '/utils/networking/' if (sys.platform.startswith('linux')) else "\\utils\\networking\\"
        for file in hammer_scripts  :
            hammer_file = self.settings.foreman_configuration_scripts + hammer_script_folder + file
            assert os.path.isfile(hammer_file) , hammer_file + " script doesnn't seem to exist"

        assert os.path.isfile(self.settings.ceph_deploy_sh) , self.settings.ceph_deploy_sh + " script doesnn't seem to exist"
        assert os.path.isfile(self.settings.tempest_deploy_sh) , self.settings.tempest_deploy_sh + " script doesnn't seem to exist"



        try:
                urllib2.urlopen(self.settings.rhel_install_location +"/EULA").read()
        except:
            raise AssertionError(self.settings.rhel_install_location + "/EULA is not reachable")

        if sys.platform.startswith('linux') == False:
            if "RUNNING" in subprocess.check_output("sc query Tftpd32_svc",stderr=subprocess.STDOUT, shell=True):
                subprocess.check_output("net stop Tftpd32_svc",stderr=subprocess.STDOUT, shell=True)
        else:
            subprocess.check_output("service tftp stop",stderr=subprocess.STDOUT, shell=True)

    def check_ipmi_to_nodes(self):
        hdw_nodes = self.settings.controller_nodes + self.settings.compute_nodes + self.settings.ceph_nodes
        hdw_nodes.append(self.settings.sah_node)
        for node in hdw_nodes:
            try:
                ipmi_session = Ipmi(self.settings.cygwin_installdir, self.settings.ipmi_user, self.settings.ipmi_password, node.idrac_ip)
                print node.hostname +" :: "+ ipmi_session.get_power_state()
            except:
                raise AssertionError("Could not impi to host " + node.hostname)

    def check_network_settings(self):
        #

        # Verify SAH node network definition
        print "verifying sah network settings"
        shouldHaveAttrbutes = [ 'hostname','idrac_ip','anaconda_ip','root_password',
                              'public_bond','public_ip','public_netmask','public_slaves','public_gateway',
                              'private_bond','private_slaves',
                              'provisioning_vlanid','provisioning_ip','provisioning_netmask',
                              'storage_vlanid','storage_ip','storage_netmask',
                              'external_vlanid','external_ip','external_netmask',
                              'private_api_vlanid','private_api_ip','private_api_netmask',
                              'name_server'
                              ]
        for each in shouldHaveAttrbutes :
            assert hasattr(self.settings.sah_node, each), self.settings.network_conf + " SAH node has no " + each + " attribute"

        shouldBeValidIps = ['idrac_ip','anaconda_ip', 'public_ip', 'public_gateway', 'provisioning_ip', 'storage_ip','external_ip','private_api_ip']
        for each in shouldBeValidIps:
            assert self.isValidIp(getattr(self.settings.sah_node, each)), "SAH node " + each + " is not a valid ip"

        # Verify Foreman network definition
        print "verifying foreman vm network settings"
        shouldHaveAttrbutes = [  'hostname','root_password',
                                 'public_ip','public_gateway','public_bond','public_netmask',
                                 'provisioning_ip','provisioning_gateway','provisioning_bond','provisioning_netmask',
                                 'name_server'
                              ]
        for each in shouldHaveAttrbutes :
            assert hasattr(self.settings.foreman_node, each), self.settings.network_conf + " Foreman node has no " + each + " attribute"
            shouldBeValidIps = ['public_ip','public_gateway','provisioning_ip','provisioning_gateway']
        for each in shouldBeValidIps:
            assert self.isValidIp(getattr(self.settings.foreman_node, each)), "Foreman node " + each + " is not a valid ip"

        # Verify Ceph vm node network definition
        print "verifying ceph vm network settings"
        shouldHaveAttrbutes = [  'hostname','root_password',
                                 'public_ip','public_gateway','public_bond','public_netmask',
                                 'storage_ip','storage_gateway','storage_netmask',
                                 'name_server'
                              ]
        for each in shouldHaveAttrbutes :
            assert hasattr(self.settings.ceph_node, each), self.settings.network_conf + " Ceph Vm node has no " + each + " attribute"
            shouldBeValidIps = ['public_ip','public_gateway','storage_ip','storage_gateway']
        for each in shouldBeValidIps:
            assert self.isValidIp(getattr(self.settings.ceph_node, each)), "Ceph vm node " + each + " is not a valid ip"

        # Verify tempest vm network definition
        print "verifying tempest vm network settings"
        shouldHaveAttrbutes = [ 'hostname','root_password',
                                'public_ip','public_gateway','public_netmask',
                                'external_ip','external_netmask',
                                'private_api_ip','private_api_netmask',
                                'name_server'
                              ]
        for each in shouldHaveAttrbutes :
            assert hasattr(self.settings.sah_node, each), self.settings.network_conf + " Tempest Vm node has no " + each + " attribute"
            shouldBeValidIps = ['public_ip','public_gateway','external_ip','private_api_ip']
        for each in shouldBeValidIps:
            assert self.isValidIp(getattr(self.settings.tempest_node, each)), "Tempest vm node " + each + " is not a valid ip"

        # Verify Controller nodes network definition
        print "verifying controller nodes network settings"
        for controller in self.settings.controller_nodes:
            shouldHaveAttrbutes = [ 'hostname', 'idrac_ip',
                                    'provisioning_mac_address','provisioning_ip',
                                    'bond1_interfaces','bond0_interfaces',
                                    'public_ip','public_netmask',
                                    'private_api_vlanid','private_ip','private_netmask',
                                    'storage_vlanid','storage_ip','storage_netmask',
                                    'idrac_secondary_vlanid','idrac_interface','idrac_secondary_macaddress','idrac_secondary_ip','idrac_secondary_gateway','idrac_secondary_netmask'
                                     ]
            for each in shouldHaveAttrbutes :
                assert hasattr(controller, each), controller.hostname + " node has no " + each + " attribute"
                shouldBeValidIps = ['idrac_ip', 'provisioning_ip','public_ip','private_ip','storage_ip','idrac_secondary_ip','idrac_secondary_gateway']
            for each in shouldBeValidIps:
                assert self.isValidIp(getattr(controller, each)), controller.hostname + " node " + each + " is not a valid ip"


        # Verify Compute nodes network definition
        print "verifying compute nodes network settings"
        for compute in self.settings.compute_nodes:
            shouldHaveAttrbutes = ['hostname','idrac_ip',
                                   'provisioning_mac_address','provisioning_ip',
                                    'bond1_interfaces','bond0_interfaces',
                                    'nova_public_vlanid','nova_public_ip','nova_public_netmask',
                                    'private_api_vlanid','private_ip','private_netmask',
                                    'nova_private_vlanid','nova_private_ip','nova_private_netmask',
                                    'storage_vlanid','storage_ip','storage_netmask'
                                     ]
            for each in shouldHaveAttrbutes :
                assert hasattr(compute, each), compute.hostname + " node has no " + each + " attribute"
                shouldBeValidIps = ['idrac_ip','provisioning_ip','nova_public_ip','private_ip','nova_private_ip','storage_ip']
            for each in shouldBeValidIps:
                assert self.isValidIp(getattr(compute, each)), compute.hostname + " node " + each + " is not a valid ip"


        # Verify Storage nodes network definition
        print "verifying storage nodes network settings"
        for storage in self.settings.ceph_nodes:
            shouldHaveAttrbutes = [ 'hostname','is_730','idrac_ip',
                                    'provisioning_mac_address','provisioning_ip',
                                    'bond1_interfaces','bond0_interfaces',
                                    'storage_cluster_vlanid','storage_cluster_ip','storage_cluster_netmask',
                                    'storage_vlanid','storage_ip','storage_netmask',
                                    'osd_disks',
                                     ]
            for each in shouldHaveAttrbutes :
                assert hasattr(storage, each), storage.hostname + " node has no " + each + " attribute"
                shouldBeValidIps = ['idrac_ip','provisioning_ip','storage_cluster_ip','storage_ip']
            for each in shouldBeValidIps:
                assert self.isValidIp(getattr(storage, each)), storage.hostname + " node " + each + " is not a valid ip"




