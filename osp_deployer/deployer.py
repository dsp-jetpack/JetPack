from osp_deployer.foreman import Foreman
from osp_deployer.ceph import Ceph
import sys, getopt
from osp_deployer import Settings
from auto_common import Ipmi, Ssh, FileHelper, Scp, UI_Manager
from datetime import datetime
import time,subprocess
import paramiko, re
import logging
logger = logging.getLogger(__name__)
import traceback, os.path, urllib2, shutil

def log(message):
    print (message)
    logger.info(  message)
    

def execute_as_shell(address,usr, pwd, command):
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
        #print">" + resp +"<"
    return buff

if __name__ == '__main__':
    
    
    try :
        log ("=================================")
        isLinux = False
        if sys.platform.startswith('linux'):
            isLinux = True
            log ("=== Linux System")
        else:
           log ("=== Windows System")
        log ("=================================")


        import logging.config
        logging.basicConfig(filename='/deployer.log' if isLinux else 'c:/auto_results/deployer.log',
           format="%(asctime)-15s:%(name)s:%(process)d:%(levelname)s:%(message)s",
                       filemode='w',
                       level=logging.INFO)    
        
        log ("=================================")
        log ("=== Starting up ...")
        log ("=================================")
        log ("=== loading up Cluster/Bastion Settings")  
        
        opts, args = getopt.getopt(sys.argv[1:], ":s:", ["help", "settingsFile="])
        if len(opts)!= 1:
            logger.fatal( "usage : python deployer.py -s settingFile")
            logger.fatal( "eg : python deployer.py -s settings/settings.ini")
    	    print( "usage : python deployer.py -s settingFile")
            print( "eg : python deployer.py -s settings/settings.ini")
            sys.exit(2)
        for opt, arg in opts:
            if str(opt) == '-s':
                settingsFile = str(arg)
                logger.info( "settings file : " + settingsFile)
            else:
                logger.info( "usage : python deployer.py -s settingFile")
                logger.info( "eg : python deployer.py -s settings/settings.ini")
                sys.exit(2)         
        logger.info("loading settings files " + settingsFile)
        settings = Settings(settingsFile)   
        attrs = vars(settings)

        print("==== Running envirnment sanity tests")
        assert os.path.isfile(settings.rhl7_iso) , settings.rhl7_iso + "ISO doesnn't seem to exist"
        assert os.path.isfile(settings.sah_kickstart) , settings.sah_kickstart + "kickstart file doesnn't seem to exist"
        assert os.path.isfile(settings.foreman_deploy_sh) , settings.foreman_deploy_sh + " script doesnn't seem to exist"
        assert os.path.isfile(settings.ceph_deploy_sh) , settings.ceph_deploy_sh + " script doesnn't seem to exist"

        try:
                urllib2.urlopen(settings.rhel_install_location +"/EULA").read()
        except:
            raise AssertionError(settings.rhel_install_location + "/EULA is not reachable")

        if isLinux == False:
            if "RUNNING" in subprocess.check_output("sc query Tftpd32_svc",stderr=subprocess.STDOUT, shell=True):
                subprocess.check_output("net stop Tftpd32_svc",stderr=subprocess.STDOUT, shell=True)
        else:
            subprocess.check_output("service tftp stop",stderr=subprocess.STDOUT, shell=True)
        
        hdw_nodes = settings.controller_nodes + settings.compute_nodes + settings.ceph_nodes
        hdw_nodes.append(settings.sah_node)
        for node in hdw_nodes:
            try:
                ipmi_session = Ipmi(settings.cygwin_installdir, settings.ipmi_user, settings.ipmi_password, node.idrac_ip)
                print node.hostname +" :: "+ ipmi_session.get_power_state()
            except:
                raise AssertionError("Could not impi to host " + node.hostname)

        #######
        log ("=== Unregister the hosts")
        hosts = [ settings.sah_node, settings.foreman_node] 
        hosts.append(settings.ceph_node)
        for each in hosts:
            log (Ssh.execute_command(each.public_ip, "root", each.root_password, "subscription-manager remove --all"))
            log (Ssh.execute_command(each.public_ip, "root", each.root_password, "subscription-manager unregister"))
        others =  settings.controller_nodes + settings.compute_nodes
        nonSAHnodes = others + settings.ceph_nodes
        for each in nonSAHnodes : 
            log (Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password, "subscription-manager remove --all"))
            log (Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password, "subscription-manager unregister"))
            
        
        log ("=== powering down the admin")
        ipmi_sah = Ipmi(settings.cygwin_installdir, settings.ipmi_user, settings.ipmi_password, settings.sah_node.idrac_ip)
        ipmi_sah.power_off()
        
        log ("=== powering down other hosts")
        for each in nonSAHnodes:
            ipmi_session = Ipmi(settings.cygwin_installdir, settings.ipmi_user, settings.ipmi_password, each.idrac_ip)
            ipmi_session.power_off()
        
        log ("=== updating the sah kickstart based on settings")
        if(sys.platform.startswith('linux')):
            shutil.copyfile(settings.foreman_configuration_scripts + "/osp-sah.ks" , settings.sah_kickstart)
        else:
            shutil.copyfile(settings.foreman_configuration_scripts + "\\osp-sah.ks" , settings.sah_kickstart)
        FileHelper.replaceExpression(settings.sah_kickstart, "^cdrom",'url --url='+settings.rhel_install_location )
        FileHelper.replaceExpression(settings.sah_kickstart, '^url --url=.*','url --url='+settings.rhel_install_location )
        FileHelper.replaceExpression(settings.sah_kickstart, '^HostName=.*','HostName="'+settings.sah_node.hostname + "." + settings.domain + '"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^SystemPassword=.*','SystemPassword="'+settings.sah_node.root_password +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^SubscriptionManagerUser=.*','SubscriptionManagerUser="'+settings.subscription_manager_user +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^SubscriptionManagerPassword=.*','SubscriptionManagerPassword="'+settings.subscription_manager_password +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^SubscriptionManagerPool=.*','SubscriptionManagerPool="'+ settings.subscription_manager_poolID +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^Gateway=.*','Gateway="'+settings.sah_node.public_gateway +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^NameServers=.*','NameServers="'+settings.sah_node.name_server +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^NTPServers=.*','NTPServers="'+settings.ntp_server +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^TimeZone=.*','TimeZone="'+settings.time_zone +'"')

        FileHelper.replaceExpression(settings.sah_kickstart, '^anaconda_interface=.*','anaconda_interface="'+settings.sah_node.anaconda_ip+ '/'+ settings.sah_node.public_netmask+' '+settings.sah_node.anaconda_iface+'"')

        FileHelper.replaceExpression(settings.sah_kickstart, '^public_bond_name=.*','public_bond_name="'+settings.sah_node.public_bond +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^public_bond_opts="mode=(.*?)\s','public_bond_opts="mode='+ settings.bond_mode_sah + ' ')
        FileHelper.replaceExpression(settings.sah_kickstart, '^public_ifaces=.*','public_ifaces="'+settings.settings.sah_node.public_slaves +'"')

        FileHelper.replaceExpression(settings.sah_kickstart, '^private_bond_name=.*','private_bond_name="'+settings.sah_node.private_bond +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^private_bond_opts="mode=(.*?)\s','private_bond_opts="mode='+ settings.bond_mode_sah + ' ')
        FileHelper.replaceExpression(settings.sah_kickstart, '^private_ifaces=.*','private_ifaces="'+settings.settings.sah_node.private_slaves +'"')

        FileHelper.replaceExpression(settings.sah_kickstart, '^provision_bond_name=.*','provision_bond_name=bond0."'+settings.sah_node.provisioning_vlanid +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^storage_bond_name=.*','storage_bond_name=bond0."'+settings.sah_node.storage_vlanid +'"')

        FileHelper.replaceExpression(settings.sah_kickstart, '^public_bridge_boot_opts="onboot static .*','public_bridge_boot_opts="onboot static '+settings.sah_node.public_ip + '/'+ settings.sah_node.public_netmask+'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^provision_bridge_boot_opts="onboot static .*','provision_bridge_boot_opts="onboot static '+settings.sah_node.provisioning_ip+ '/'+ settings.sah_node.provisioning_netmask+'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^storage_bridge_boot_opts="onboot static .*','storage_bridge_boot_opts="onboot static '+settings.sah_node.storage_ip+ '/'+ settings.sah_node.storage_netmask+'"')

        #public_bridge_boot_opts="onboot static 10.148.44.41/255.255.255.0"
        #provision_bridge_boot_opts="onboot static 192.168.120.41/255.255.255.0"
        #storage_bridge_boot_opts="onboot static 192.168.170.41/255.255.255.0"

        log ("=== starting the tftp service & power on the admin")
        log (subprocess.check_output("service tftp start" if isLinux else "net start Tftpd32_svc",stderr=subprocess.STDOUT, shell=True))
        time.sleep(60)
        
        
        #linux, dhcp is a separate service
        if(isLinux):
           log ("=== starting dhcpd service")
           log (subprocess.check_output("service dhcpd start",stderr=subprocess.STDOUT, shell=True))

       
        log ("=== power on the admin node & wait for the system to start installing")
        ipmi_sah.set_boot_to_pxe()
        ipmi_sah.power_on()
        time.sleep(400)
        
        log ("=== stopping tftp service")
        log (subprocess.check_output("service tftp stop" if isLinux else "net stop Tftpd32_svc",stderr=subprocess.STDOUT, shell=True))
        
        if(isLinux):
            log ("=== stopping dhcpd service")
            log (subprocess.check_output("service dhcpd stop",stderr=subprocess.STDOUT, shell=True))

        
        log ("=== waiting for the sah installed to be complete, might take a while")
        while (not "root" in Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "whoami")[0]):
            log ("...")
            time.sleep(100);
            #log (Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "whoami"))
        log ("sahh node is up @ " + settings.sah_node.public_ip)

        log("*** Verify the SAH node registered properly ***")
        subscriptionStatus = Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "subscription-manager status")[0]
        if "Current" not in subscriptionStatus:
            raise AssertionError("SAH did not register properly : " + subscriptionStatus)

        log ("=== uploading iso's to the sah node")
        Scp.put_file( settings.sah_node.public_ip, "root", settings.sah_node.root_password, settings.rhl7_iso, "/store/data/iso/RHEL7.iso")
        
        log("=== Done with the solution admin host");

        if settings.version_locking_enabled:
            log("Uploading version locking files for foreman & ceph vm's")
            files  = [
                'ceph_vm.vlock',
                'foreman_vm.vlock',
                ]
            for file in files :
                if isLinux == False:
                    localfile = settings.lock_files_dir + "\\" + file
                else:
                    localfile = settings.lock_files_dir + "/" + file
                remotefile = '/root/' + file
                print localfile + " >> " + remotefile
                Scp.put_file( settings.sah_node.public_ip, "root", settings.sah_node.root_password, localfile, remotefile)

        log("=== creating foreman VM");
        log("=== uploading the foreman vm sh script")
        remoteSh = "/root/deploy-foreman-vm.sh";
        Scp.put_file( settings.sah_node.public_ip, "root", settings.sah_node.root_password, settings.foreman_deploy_sh, remoteSh);
    
        log("=== create foreman.cfg") 
        foremanConf = "/root/foreman.cfg";
        Conf =  ("rootpassword " + settings.foreman_node.root_password,
                "timezone " + settings.time_zone,
                "smuser " + settings.subscription_manager_user ,
                "smpassword "+settings.subscription_manager_password ,
                "smpool " + settings.subscription_manager_poolID ,
                "hostname "+ settings.foreman_node.hostname + "." + settings.domain ,
                "gateway " + settings.foreman_node.public_gateway ,
                "nameserver " + settings.foreman_node.name_server ,
                "ntpserver "+ settings.ntp_server ,
                "# Iface     IP               NETMASK    " ,
                "eth0        "+ settings.foreman_node.public_ip +"     "+ settings.foreman_node.public_netmask ,
                "eth1        "+ settings.foreman_node.provisioning_ip +"    "+ settings.foreman_node.provisioning_netmask,
                )
        for comd in Conf:
            Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "echo '"+ comd+"' >> "+ foremanConf)
        log("=== kick off the foreman vm deployment")
        sH = "sh " + remoteSh + " /root/foreman.cfg /store/data/iso/RHEL7.iso";
        Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, sH)
        
        log("=== wait for the foreman vm install to be complete & power it on")
        while (not "shut off" in Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "virsh list --all")[0]):
            log ("...")
            time.sleep(60);
        log ("=== power on the foreman VM ")
        Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "virsh start foreman")
        while (not "root" in Ssh.execute_command(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password, "whoami")[0]):
            log ("...")
            time.sleep(30);
        log("foreman host is up")

        log("*** Verify the Foreman VM registered properly ***")
        subscriptionStatus = Ssh.execute_command(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password, "subscription-manager status")[0]
        if "Current" not in subscriptionStatus:
            raise AssertionError("Foreman VM did not register properly : " + subscriptionStatus)

        log("=== installing foreman")
        
        cmd = "sed -i '/^read -p/d' /usr/share/openstack-foreman-installer/bin/foreman_server.sh"
        logger.info( Ssh.execute_command(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password,cmd))      
        
        cmd = 'cd /usr/share/openstack-foreman-installer/bin;FOREMAN_PROVISIONING=true FOREMAN_GATEWAY='+settings.foreman_node.provisioning_ip+' PROVISIONING_INTERFACE=eth1 ./foreman_server.sh 2>&1 | tee /root/foreman_server.out'
        logger.info( execute_as_shell(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password,cmd))      
            
        cmd = "puppet agent  -t"
        logger.info( Ssh.execute_command(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password,cmd))      

        foremanHost = Foreman()
        foremanHost.reset_password()

        cmd = "sed -i \"s/options.password = '.*'/options.password = '"+ settings.foreman_password +"'/\" /usr/share/openstack-foreman-installer/bin/quickstack_defaults.rb"
        logger.info( Ssh.execute_command(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password,cmd))
        
        log("=== done with foreman")
        

        logger.info( "=== creating ceph VM")
        remoteSh = "/root/deploy-ceph-vm.sh";
        Scp.put_file( settings.sah_node.public_ip, "root", settings.sah_node.root_password, settings.ceph_deploy_sh, remoteSh);

        log("=== create ceph.cfg")
        cephConf = "/root/ceph.cfg";
        Conf =  ("rootpassword " + settings.ceph_node.root_password,
                "timezone " + settings.time_zone,
                "smuser " + settings.subscription_manager_user ,
                "smpassword "+settings.subscription_manager_password ,
                "smpool " + settings.subscription_manager_poolID ,
                "hostname "+ settings.ceph_node.hostname + "." + settings.domain ,
                "gateway " + settings.ceph_node.public_gateway ,
                "nameserver " + settings.ceph_node.name_server ,
                "ntpserver "+ settings.ntp_server ,
                "# Iface     IP               NETMASK    " ,
                "eth0        "+ settings.ceph_node.public_ip +"     "+ settings.ceph_node.public_netmask ,
                "eth1        "+ settings.ceph_node.storage_ip +"    "+ settings.ceph_node.storage_netmask,
                )
        for comd in Conf:
            Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "echo '"+ comd+"' >> "+ cephConf)
        log("=== kick off the ceph vm deployment")
        sH = "sh " + remoteSh + " /root/ceph.cfg /store/data/iso/RHEL7.iso";
        logger.info( Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, sH))

        log("=== wait for the ceph vm install to be complete & power it on")
        while (not "shut off" in Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "virsh list --all")[0]):
            log ("...")
            time.sleep(60);
        log ("=== power on the ceph VM ")
        Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "virsh start ceph")
        while (not "root" in Ssh.execute_command(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, "whoami")[0]):
            log ("...")
            time.sleep(30);
        log("ceph host is up")

        log("*** Verify the Ceph VM registered properly ***")
        subscriptionStatus = Ssh.execute_command(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, "subscription-manager status")[0]
        if "Current" not in subscriptionStatus:
            raise AssertionError("Ceph VM did not register properly : " + subscriptionStatus)
            

        
        log ("=== Configuring the foreman server")
        foremanHost.set_ignore_puppet_facts_for_provisioning()

        foremanHost.update_scripts()
        foremanHost.upload_scripts()
        foremanHost.enable_version_locking()
        foremanHost.install_hammer()
        foremanHost.configure_installation_medium()
        foremanHost.configure_partitionts_tables()
        foremanHost.configure_operating_systems()
        foremanHost.configure_subnets()
        foremanHost.configure_templates()

        foremanHost.register_hosts()
        foremanHost.configure_os_updates()
        foremanHost.configure_controller_nic()
        foremanHost.configure_controller_version_locking()
        foremanHost.configure_compute_nic()
        foremanHost.configure_compute_version_locking()
        if settings.stamp_storage == "ceph":
            foremanHost.configure_ceph_version_locking()

        
        #######
        print settings.stamp_type
        
        print settings.stamp_storage
        
        if settings.stamp_type == "pilot" and settings.stamp_storage == "ceph":
            foremanHost.configure_ceph_nic()
        
        
        logger.info( "==== Power on/PXE boot the Controller/Compute/Storage nodes")
        for each in nonSAHnodes:
            ipmiSession = Ipmi(settings.cygwin_installdir, settings.ipmi_user, settings.ipmi_password, each.idrac_ip)
            ipmiSession.set_boot_to_pxe()
            ipmiSession.power_on()
            
        logger.info( "wait for the nodes to be up")
        for each in nonSAHnodes:
            log("waiting for " + each.hostname +" to be up @" + each.provisioning_ip)
            while (not "root" in Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password, "whoami")[0]):
                log("...")
                time.sleep(100);
            log("Disable puppet on the node for now to avoid race conditions later.")
            log(Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password, "service puppet stop")[0])

        if settings.stamp_storage == "ceph":
            ceph = Ceph()
            ceph.copy_installer()
            ceph.install_ice()
            ceph.configure_monitor()
            ceph.configure_osd()
            ceph.connectHostsToCalamari()
            ceph.grantAdminRightsToOSD()
            ceph.modifyOSDPlacementGroups()
            ceph.pool_and_keyRing_configuration()
            ceph.foreman_config_ha_all_in_One()
            ceph.foreman_config_compute()
                
                
            foremanHost.configureHostGroups_Parameters()
            foremanHost.cephConfigurtion()
            foremanHost.configureNodes()
            
            if settings.stamp_storage == "ceph":
                # bugs here with docs, if done earlier as suggeste ceph wont be installed on the compute nodes
                ceph.libvirt_config()
                ceph.deploy_ceph_to_compute_hosts()
                ceph.configure_cinder_for_backup() 
                ceph.configure_missing_bits_from_docs()
                
        log("re enable puppet service on the nodes")
        for each in nonSAHnodes:
            log(Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password, "service puppet start")[0])
            
        UI_Manager.driver().close()
        ceph.restart_ha_services()
            
        log (" that's all folks "    )
        logger.info( "foreman admin password :: " + settings.foreman_password  )
        print "All done - foreman admin password :: " + settings.foreman_password
    except:
        logger.info(traceback.format_exc())
        e = sys.exc_info()[0]
        logger.info(e)
        print e
        print traceback.format_exc()

    
    
