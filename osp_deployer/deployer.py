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

import sys, getopt, time, subprocess, paramiko,logging, traceback, os.path, urllib2, shutil, socket
from osp_deployer.foreman import Foreman
from osp_deployer.ceph import Ceph
from auto_common import Ipmi, Ssh, FileHelper, Scp, UI_Manager
from osp_deployer import Settings, Deployer_sanity

logger = logging.getLogger(__name__)
ping_success = "packets transmitted, 3 received"

def log(message):
    print (message)
    logger.info(  message)

def verify_subscription_status(public_ip, user, password, retries):
    i = 0
    subscriptionStatus = Ssh.execute_command(public_ip, user, password, "subscription-manager status")[0]
    while("Current" not in subscriptionStatus and i < retries):
        if "Unknown" in subscriptionStatus:
            return subscriptionStatus
        log("...")
        time.sleep(60)
        subscriptionStatus = Ssh.execute_command(public_ip, user, password, "subscription-manager status")[0]
        i += 1;
    return subscriptionStatus

def verify_subscription_and_repos(ip_addr, user, password, logFile):
    # check the xxxxx-posts.log for pool id's/repo's related errors.
    logOut = Ssh.execute_command(ip_addr, user, password, "cat " + logFile)[0]

    error1 = 'No subscriptions are available from the pool with'
    error2 = 'is not a valid repository'
    if error1 in logOut or error2 in logOut:
        logger.info("*** post install log ***")
        logger.info(logOut)
        return False
    return True


def ping_host(public_ip, user, passwd, targetHost):
    subscriptionStatus = Ssh.execute_command(public_ip, user, passwd, "ping " + targetHost + " -c 3 -w 30 ")[0]
    return subscriptionStatus




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
        checks = Deployer_sanity()
        checks.check_network_settings()
        checks.check_files()
        checks.check_ipmi_to_nodes()

        #######
        log ("=== Unregister the hosts")
        hosts = [ settings.sah_node, settings.foreman_node]
        hosts.append(settings.ceph_node)
        hosts.append(settings.tempest_node)
        for each in hosts:
            log (Ssh.execute_command(each.public_ip, "root", each.root_password, "subscription-manager remove --all"))
            log (Ssh.execute_command(each.public_ip, "root", each.root_password, "subscription-manager unregister"))
        others =  settings.controller_nodes + settings.compute_nodes
        nonSAHnodes = others + settings.ceph_nodes
        for each in nonSAHnodes :
            log (Ssh.execute_command(each.provisioning_ip, "root", settings.previous_deployment_cluster_password, "subscription-manager remove --all"))
            log (Ssh.execute_command(each.provisioning_ip, "root", settings.previous_deployment_cluster_password, "subscription-manager unregister"))


        log ("=== powering down the admin")
        ipmi_sah = Ipmi(settings.cygwin_installdir, settings.ipmi_user, settings.ipmi_password, settings.sah_node.idrac_ip)
        ipmi_sah.power_off()

        log ("=== powering down other hosts")
        for each in nonSAHnodes:
            ipmi_session = Ipmi(settings.cygwin_installdir, settings.ipmi_user, settings.ipmi_password, each.idrac_ip)
            ipmi_session.power_off()

        log ("=== updating the sah kickstart based on settings")
        shutil.copyfile(settings.sah_ks , settings.sah_kickstart)
        FileHelper.replaceExpression(settings.sah_kickstart, "^cdrom",'url --url='+settings.rhel_install_location )
        FileHelper.replaceExpression(settings.sah_kickstart, '^url --url=.*','url --url='+settings.rhel_install_location )
        FileHelper.replaceExpression(settings.sah_kickstart, '^HostName=.*','HostName="'+settings.sah_node.hostname + "." + settings.domain + '"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^SystemPassword=.*','SystemPassword="'+settings.sah_node.root_password +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^SubscriptionManagerUser=.*','SubscriptionManagerUser="'+settings.subscription_manager_user +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^SubscriptionManagerPassword=.*','SubscriptionManagerPassword="'+settings.subscription_manager_password +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^SubscriptionManagerPool=.*','SubscriptionManagerPool="'+ settings.subscription_manager_pool_sah +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^Gateway=.*','Gateway="'+settings.sah_node.public_gateway +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^NameServers=.*','NameServers="'+settings.sah_node.name_server +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^NTPServers=.*','NTPServers="'+settings.ntp_server +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^TimeZone=.*','TimeZone="'+settings.time_zone +'"')

        FileHelper.replaceExpression(settings.sah_kickstart, '^anaconda_interface=.*','anaconda_interface="'+settings.sah_node.anaconda_ip+ '/'+ settings.sah_node.public_netmask+' '+settings.sah_node.anaconda_iface+' no"')

        FileHelper.replaceExpression(settings.sah_kickstart, '^public_bond_name=.*','public_bond_name="'+settings.sah_node.public_bond +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^public_ifaces=.*','public_ifaces="'+settings.settings.sah_node.public_slaves +'"')

        FileHelper.replaceExpression(settings.sah_kickstart, '^private_bond_name=.*','private_bond_name="'+settings.sah_node.private_bond +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^private_ifaces=.*','private_ifaces="'+settings.settings.sah_node.private_slaves +'"')

        FileHelper.replaceExpression(settings.sah_kickstart, '^provision_bond_name=.*','provision_bond_name=bond0."'+settings.sah_node.provisioning_vlanid +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^storage_bond_name=.*','storage_bond_name=bond0."'+settings.sah_node.storage_vlanid +'"')

        FileHelper.replaceExpression(settings.sah_kickstart, '^external_bond_name=.*','external_bond_name=bond0."'+settings.sah_node.external_vlanid +'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^private_api_bond_name=.*','private_api_bond_name=bond0."'+settings.sah_node.private_api_vlanid +'"')


        FileHelper.replaceExpression(settings.sah_kickstart, '^public_bridge_boot_opts=.*','public_bridge_boot_opts="onboot static '+settings.sah_node.public_ip + '/'+ settings.sah_node.public_netmask+'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^provision_bridge_boot_opts=.*','provision_bridge_boot_opts="onboot static '+settings.sah_node.provisioning_ip+ '/'+ settings.sah_node.provisioning_netmask+'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^storage_bridge_boot_opts=.*','storage_bridge_boot_opts="onboot static '+settings.sah_node.storage_ip+ '/'+ settings.sah_node.storage_netmask+'"')

        FileHelper.replaceExpression(settings.sah_kickstart, '^external_bridge_boot_opts=.*','external_bridge_boot_opts="onboot static '+settings.sah_node.external_ip+ '/'+ settings.sah_node.external_netmask+'"')
        FileHelper.replaceExpression(settings.sah_kickstart, '^private_api_bridge_boot_opts=.*','private_api_bridge_boot_opts="onboot static '+settings.sah_node.private_api_ip+ '/'+ settings.sah_node.private_api_netmask+'"')


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
        log ("sahh node is up @ " + settings.sah_node.public_ip)


        log("*** Verify the SAH node registered properly ***")
        subscriptionStatus = verify_subscription_status(settings.sah_node.public_ip, "root", settings.sah_node.root_password, settings.subscription_check_retries)
        if "Current" not in subscriptionStatus:
            raise AssertionError("SAH did not register properly : " + subscriptionStatus)

        log("*** Verify all pools registered & repositories subscribed ***")
        if verify_subscription_and_repos(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "/root/" + settings.sah_node.hostname + "-post-ks.log" ) is False:
            raise AssertionError("SAH did not subscribe/attach repos properly, see log.")

        log("*** Verify the SAH can ping its public gateway")
        test = ping_host(settings.sah_node.public_ip, "root", settings.sah_node.root_password, settings.sah_node.public_gateway)
        if ping_success not in test:
            raise AssertionError("SAH cannot ping its public gateway : " + test)

        log("*** Verify the SAH can ping the outside world (ip)")
        test = ping_host(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "8.8.8.8")
        if ping_success not in test:
            raise AssertionError("SAH cannot ping the outside world (ip) : " + test)

        log("*** Verify the SAH can ping the outside world (dns)")
        test = ping_host(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "google.com")
        if ping_success not in test:
            raise AssertionError("SAH cannot ping the outside world (dns) : " + test)


        log ("=== uploading iso's to the sah node")
        Scp.put_file( settings.sah_node.public_ip, "root", settings.sah_node.root_password, settings.rhl71_iso, "/store/data/iso/RHEL7.iso")

        log("=== Done with the solution admin host");


        if settings.version_locking_enabled is True:
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
                "smpool " + settings.subscription_manager_pool_vm_rhel ,
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
        subscriptionStatus = verify_subscription_status(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password, settings.subscription_check_retries)
        if "Current" not in subscriptionStatus:
            raise AssertionError("Foreman VM did not register properly : " + subscriptionStatus)

        log("*** Verify all pools registered & repositories subscribed ***")
        if verify_subscription_and_repos(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password, "/root/" + settings.foreman_node.hostname + "-posts.log" ) is False:
            raise AssertionError("Foreman vm did not subscribe/attach repos properly, see log.")

        log("*** Verify the Foreman VM can ping its public gateway")
        test = ping_host(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password, settings.foreman_node.public_gateway)
        if ping_success not in test:
            raise AssertionError("Foreman VM cannot ping its public gateway : " + test)

        log("*** Verify the Foreman VM can ping the outside world (ip)")
        test = ping_host(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password, "8.8.8.8")
        if ping_success not in test:
            raise AssertionError("Foreman VM cannot ping the outside world (ip) : " + test)

        log("*** Verify the Foreman VM can ping the outside world (dns)")
        test = ping_host(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password, "google.com")
        if ping_success not in test:
            raise AssertionError("Foreman VM cannot ping the outside world (dns) : " + test)

        log("*** Verify the Foreman VM can ping the SAH node through the provisioning network")
        test = ping_host(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password, settings.sah_node.provisioning_ip)
        if ping_success not in test:
            raise AssertionError("Foreman VM cannot ping the SAH node through the provisioning network : " + test)

        log("*** Verify the Foreman VM can ping the SAH node through the public network")
        test = ping_host(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password, settings.sah_node.public_ip)
        if ping_success not in test:
            raise AssertionError("Foreman VM cannot ping the SAH node through the provisioning network : " + test)


        log("=== installing foreman")

        ### Add the internal repo. & if going down that road, and re pull down foreman with the new version
        if settings.internal_repos is True:
            count = 1
            for repo in settings.internal_repos_urls:
                cmd = 'curl ' + repo + " > /etc/yum.repos.d/internal_" + str(count) + ".repo"
                logger.info( Ssh.execute_command(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password,cmd))
                logger.info( Ssh.execute_command(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password,"echo 'priority=1' >> /etc/yum.repos.d/internal_" + str(count) + ".repo"))
                count += 1

            cmds = [
                'yum remove openstack-foreman-installer -y',
                'yum clean all',
                'yum makecache',
                'yum repolist all',
                'yum install openstack-foreman-installer -y',
                'yum update -y',
                'yum info openstack-foreman-installer',
            ]
            for cmd in cmds:
                logger.info( Ssh.execute_command(settings.foreman_node.public_ip, "root", settings.foreman_node.root_password,cmd))

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
                "smpool " + settings.subscription_manager_vm_ceph ,
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
        subscriptionStatus = verify_subscription_status(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, settings.subscription_check_retries)
        if "Current" not in subscriptionStatus:
            raise AssertionError("Ceph VM did not register properly : " + subscriptionStatus)

        log("*** Verify all pools registered & repositories subscribed ***")
        if verify_subscription_and_repos(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, "/root/" + settings.ceph_node.hostname + "-post.log" ) is False:
            raise AssertionError("Ceph vm did not subscribe/attach repos properly, see log.")

        log("*** Verify the Ceph VM can ping its public gateway")
        test = ping_host(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, settings.foreman_node.public_gateway)
        if ping_success not in test:
            raise AssertionError("Ceph VM cannot ping its public gateway : " + test)

        log("*** Verify the Ceph VM can ping the outside world (ip)")
        test = ping_host(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, "8.8.8.8")
        if ping_success not in test:
            raise AssertionError("Ceph VM cannot ping the outside world (ip) : " + test)

        log("*** Verify the Ceph VM can ping the outside world (dns)")
        test = ping_host(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, "google.com")
        if ping_success not in test:
            raise AssertionError("Ceph VM cannot ping the outside world (dns) : " + test)

        log("*** Verify the Ceph VM can ping the SAH node through the storage network")
        test = ping_host(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, settings.sah_node.storage_ip)
        if ping_success not in test:
            raise AssertionError("Ceph VM cannot ping the SAH node through the storage network : " + test)

        log("*** Verify the Ceph VM can ping the SAH node through the public network")
        test = ping_host(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, settings.sah_node.public_ip)
        if ping_success not in test:
            raise AssertionError("Ceph VM cannot ping the SAH node through the public network : " + test)

        log("*** Verify the Ceph VM can ping the Foreman VM through the public network")
        test = ping_host(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, settings.foreman_node.public_ip)
        if ping_success not in test:
            raise AssertionError("Ceph VM cannot ping the Foreman VM through the provisioning network : " + test)


        log ("=== Configuring the foreman server")
        foremanHost.set_ignore_puppet_facts_for_provisioning()

        foremanHost.update_and_upload_scripts()
        foremanHost.enable_version_locking()
        foremanHost.install_hammer()
        foremanHost.configure_installation_medium()
        foremanHost.configure_foreman()
        foremanHost.gather_values()

        foremanHost.configure_controller_nodes()
        foremanHost.configure_compute_nodes()
        if settings.stamp_storage == "ceph":
            foremanHost.configure_ceph_nodes()

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

            # Common tests

            log("*** Verify " + each.hostname + " registered properly ***")
            subscriptionStatus = verify_subscription_status(each.provisioning_ip, "root", settings.nodes_root_password, settings.subscription_check_retries)
            if "Current" not in subscriptionStatus:
                raise AssertionError(" " + each.hostname + " did not register properly : " + subscriptionStatus)

            log("*** Verify all pools registered & repositories subscribed ***")
            if verify_subscription_and_repos(each.provisioning_ip, "root", settings.nodes_root_password, "/root/install.post.log") is False:
                raise AssertionError(" " + each.hostname +" did not subscribe/attach repos properly, see log.")

            log("*** Verify " + each.hostname + " can ping the outside world (ip)")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, "8.8.8.8")
            if ping_success not in test:
                raise AssertionError(" " + each.hostname + " cannot ping the outside world (ip) : " + test)

            log("*** Verify " + each.hostname + " can ping the outside world (dns)")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, "google.com")
            if ping_success not in test:
                raise AssertionError(" " + each.hostname + " cannot ping the outside world (dns) : " + test)

            log("*** Verify  " + each.hostname + " can ping the SAH node through the provisioning network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.sah_node.provisioning_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping the SAH node through the provisioning network : " + test)

            log("*** Verify  " + each.hostname + " can ping the Foreman node through the provisioning network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.foreman_node.provisioning_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping the foreman node through the provisioning network : " + test)

            log("*** Verify  " + each.hostname + " can ping the Foreman node through its public ip")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.foreman_node.public_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping the foreman node through its public ip : " + test)

            log("*** Verify  " + each.hostname + " can ping the ceph node through its public ip")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.ceph_node.public_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping the ceph node through its public ip : " + test)

            log("*** Verify  " + each.hostname + " can ping the SAH node through the storage network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.sah_node.storage_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping the SAH node through the storage network : " + test)

            log("*** Verify  " + each.hostname + " can ping the ceph node over the storage network")
    	    test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.ceph_node.storage_ip)
    	    if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping the ceph node over the storage network : " + test)

            if each.is_controller == True or each.is_compute == True  :
                log("Disable puppet on the node for now to avoid race conditions later.")
                log(Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password, "service puppet stop")[0])

                # Controller / Compute tests
                if "3.6" not in Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password, "puppet --version")[0]:
                    raise AssertionError(" " + each.hostname + " : Puppet did not install  : " + subscriptionStatus)

                log("*** Verify  " + each.hostname + " can ping the SAH node through the private API network")
                test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.sah_node.private_api_ip)
                if ping_success not in test:
                    raise AssertionError("  " + each.hostname + " cannot ping the SAH node through the private API network : " + test)

            if each.is_controller == True :

                # Controller tests

                log("*** Verify  " + each.hostname + " can ping the SAH node through the external network")
                test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.sah_node.external_ip)
                if ping_success not in test:
                    raise AssertionError("  " + each.hostname + " cannot ping the SAH node through the external network : " + test)

            if each.is_compute == True :

                # Compute  tests
                log ("*** no compute only tests defined ***")

            if each.is_storage == True :

                # Storage tests

                log ("*** no storage only tests defined ***")


            # Enable the internal repo's if we re going down that route
            if settings.internal_repos is True:
                count = 1
                for repo in settings.internal_repos_urls:
                    cmd = 'curl ' + repo + " > /etc/yum.repos.d/internal_" + str(count) + ".repo"
                    logger.info( Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password,cmd))
                    logger.info( Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password,"echo 'priority=1' >> /etc/yum.repos.d/internal_" + str(count) + ".repo"))
                    count += 1

                cmds = [
                    'yum clean all',
                    'yum makecache',
                    'yum repolist all',
                    'yum update -y'
                ]
                for cmd in cmds:
                    logger.info( Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password,cmd))

        # Check connectivity between all the nodes now they're all up.
        # Controllers
        target = 1
        for each in settings.controller_nodes:
            if target ==  len(settings.controller_nodes ):
                target = 0

            log ("*** "+ each.hostname + " -> " + settings.controller_nodes[target].hostname)

            log("*** Verify the controller nodes can ping each other over the provisioning network ")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.controller_nodes[target].provisioning_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping " + settings.controller_nodes[target].hostname +" over the provisioning network  : " + test)

            log("*** Verify the controller nodes can ping each other over the private api  network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.controller_nodes[target].private_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping " + settings.controller_nodes[target].hostname +" over the private api network  : " + test)

            log("*** Verify the controller nodes can ping each other over the Storage network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.controller_nodes[target].storage_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping " + settings.controller_nodes[target].hostname +" over the storage network  : " + test)

            log("*** Verify the controller nodes can ping each other over the External network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.controller_nodes[target].public_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping " + settings.controller_nodes[target].hostname +" over the external network  : " + test)
            target += 1

        # Computes
        target = 1
        for each in settings.compute_nodes:
            if target == len(settings.compute_nodes ):
                target = 0
            log ("*** "+ each.hostname + " -> " + settings.compute_nodes[target].hostname)
            log("*** Verify the compute nodes can ping each other over the provisioning network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.compute_nodes[target].provisioning_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping " + settings.compute_nodes[target].hostname +" over the provisioning network  : " + test)

            log("*** Verify the compute nodes can ping each other over the private api  network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.compute_nodes[target].private_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping " + settings.compute_nodes[target].hostname +" over the private api network  : " + test)

            log("*** Verify the compute nodes can ping each other over the Storage network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.compute_nodes[target].storage_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping " + settings.compute_nodes[target].hostname +" over the storage network  : " + test)

            target += 1

        # Storage
        target = 1
        for each in settings.ceph_nodes:
            if target == len(settings.ceph_nodes ) :
                target = 0
            log ("*** "+ each.hostname + " -> " + settings.ceph_nodes[target].hostname)
            log("*** Verify the Storage nodes can ping each other over the provisioning network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.ceph_nodes[target].provisioning_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping " + settings.ceph_nodes[target].hostname +" over the provisioning network  : " + test)

            log("*** Verify the Storage nodes can ping each other over the storage network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.ceph_nodes[target].storage_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping " + settings.ceph_nodes[target].hostname +" over the storage network  : " + test)

            log("*** Verify the Storage nodes can ping each other over the cluster network")
            test = ping_host(each.provisioning_ip, "root", settings.nodes_root_password, settings.ceph_nodes[target].storage_cluster_ip)
            if ping_success not in test:
                raise AssertionError("  " + each.hostname + " cannot ping " + settings.ceph_nodes[target].hostname +" over the cluster network  : " + test)

            target += 1



        foremanHost.configureHostGroups_Parameters()
        foremanHost.configureNodes()

        ceph = Ceph()
        ceph.pre_installation_configuration()
        ceph.setup_calamari_node()
        ceph.configure_monitor()
        ceph.configure_osd()
        ceph.connectHostsToCalamari()
        ceph.modifyOSDPlacementGroups()
        ceph.pool_and_keyRing_configuration()
        ceph.libvirt_configuation()
        ceph.setup_radosgw()


        foremanHost.run_puppet_on_all()


        log("re enable puppet service on the nodes")
        for each in nonSAHnodes:
            log(Ssh.execute_command(each.provisioning_ip, "root", settings.nodes_root_password, "service puppet start")[0])

        # Ceph - restart cinder services
        log("restart cinder services")
        cmds = [
            "pcs resource restart cinder-api-clone",
            "pcs resource restart cinder-scheduler-clone",
            "pcs resource restart cinder-volume",

        ]
        for cmd in cmds:
            log( Ssh.execute_command(settings.controller_nodes[0].provisioning_ip, "root", settings.nodes_root_password,cmd )[0])

        UI_Manager.driver().close()

### Jstream 4.0 patches 

        log("=== Applying horizon patch");
        log("=== uploading the horizon.patch")
        for host in settings.controller_nodes:
            localfile = settings.cloud_repo_dir + '/src/utils/networking/horizon.patch'
            remotefile =  '/tmp/horizon.patch'
            print localfile + " >> " + remotefile
            Scp.put_file(host.provisioning_ip, "root", settings.nodes_root_password, localfile, remotefile)
   
        log("=== stop horizon service")
        cmd = 'pcs resource disable horizon'
        logger.info( Ssh.execute_command(settings.controller_nodes[0].provisioning_ip, "root", settings.nodes_root_password, cmd ))

        log("=== Apply the horizon.patch")
        for host in settings.controller_nodes:
            cmd = '( cd /usr/share/openstack-dashboard;patch -p1 < /tmp/horizon.patch )'
            logger.info( Ssh.execute_command(host.provisioning_ip, "root", settings.nodes_root_password, cmd))

        log("=== start horizon service")
        cmd = 'pcs resource enable horizon'
        logger.info( Ssh.execute_command(settings.controller_nodes[0].provisioning_ip, "root", settings.nodes_root_password, cmd ))

        log("=== Applying live migration patch");
        log("=== uploading the live migration script")
        for host in settings.compute_nodes:
            localfile = settings.cloud_repo_dir + '/src/utils/networking/enable_live_migration.sh'
            remotefile =  '/tmp/enable_live_migration.sh'
            print localfile + " >> " + remotefile
            Scp.put_file(host.provisioning_ip, "root", settings.nodes_root_password, localfile, remotefile)

        log("=== Apply the Live migration patch")
        for host in settings.compute_nodes:
            cmd = '( chmod a+x /tmp/enable_live_migration.sh; /tmp/enable_live_migration.sh )'
            logger.info( Ssh.execute_command(host.provisioning_ip, "root", settings.nodes_root_password, cmd))

        log("=== Applying Calamari patch");
        log("=== uploading the calamari.patch")
        localfile = settings.cloud_repo_dir + '/src/utils/networking/calamari.patch'
        remotefile =  '/tmp/calamari.patch'
        print localfile + " >> " + remotefile
        Scp.put_file(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, localfile, remotefile)
   
        log("=== Apply the calamari.patch")
        cmd = '( cd /opt/calamari/venv/lib/python2.7/site-packages/calamari_cthulhu-0.1-py2.7.egg/cthulhu/manager; patch -p0 < /tmp/calamari.patch )'
        logger.info( Ssh.execute_command(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, cmd ))

        log("=== restart cthulhu services per the patch instructions from RH ")
        cmd = '( source /opt/calamari/venv/bin/activate; supervisorctl restart cthulhu )'
        logger.info( Ssh.execute_command(settings.ceph_node.public_ip, "root", settings.ceph_node.root_password, cmd ))


### END Jstream 4.0 patches 
        
        
        fencing_enabled = foremanHost.check_services_and_enable_fencing()

        log("=== creating tempest VM");
        log("=== uploading the tempest vm sh script")
        remoteSh = "/root/deploy-tempest-vm.sh";
        Scp.put_file( settings.sah_node.public_ip, "root", settings.sah_node.root_password, settings.tempest_deploy_sh, remoteSh);

        log("=== create tempest.cfg")
        # grab git commit id from actual tempest.cfg
        commit = subprocess.Popen("grep tempestcommit /root/cloud_repo/src/mgmt/tempest.cfg", shell=True, stdout=subprocess.PIPE).stdout.read().rstrip()
        tempestConf = "/root/tempest.cfg";
        Conf =  ("rootpassword " + settings.tempest_node.root_password,
                "timezone " + settings.time_zone,
                "smuser " + settings.subscription_manager_user ,
                "smpassword "+settings.subscription_manager_password ,
                "smpool " + settings.subscription_manager_pool_vm_rhel ,
                "hostname "+ settings.tempest_node.hostname + "." + settings.domain ,
                "gateway " + settings.tempest_node.public_gateway ,
                "nameserver " + settings.tempest_node.name_server ,
                "ntpserver "+ settings.ntp_server ,
                "# Iface     IP               NETMASK    " ,
                "eth0        "+ settings.tempest_node.public_ip +"    "+ settings.tempest_node.public_netmask ,
                "eth1        "+ settings.tempest_node.external_ip +"    "+ settings.tempest_node.external_netmask,
                "eth2        "+ settings.tempest_node.private_api_ip +"    "+ settings.tempest_node.private_api_netmask,
                commit,
                )

        for comd in Conf:
            Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "echo '"+ comd+"' >> "+ tempestConf)
        log("=== kick off the tempest vm deployment")
        sH = "sh " + remoteSh + " /root/tempest.cfg /store/data/iso/RHEL7.iso";
        Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, sH)

        log("=== wait for the tempest vm install to be complete & power it on")
        while (not "shut off" in Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "virsh list --all")[0]):
            log ("...")
            time.sleep(60);
        log ("=== power on the tempest VM ")
        Ssh.execute_command(settings.sah_node.public_ip, "root", settings.sah_node.root_password, "virsh start tempest")
        while (not "root" in Ssh.execute_command(settings.tempest_node.public_ip, "root", settings.tempest_node.root_password, "whoami")[0]):
            log ("...")
            time.sleep(30);
        log("Tempest host is up")

        log("*** Verify the Tempest VM registered properly ***")
        subscriptionStatus = verify_subscription_status(settings.tempest_node.public_ip, "root", settings.tempest_node.root_password, settings.subscription_check_retries)
        if "Current" not in subscriptionStatus:
            raise AssertionError("Tempest VM did not register properly : " + subscriptionStatus)

        log("*** Verify the Tempest VM can ping the outside world (ip)")
        test = ping_host(settings.tempest_node.public_ip, "root", settings.tempest_node.root_password, "8.8.8.8")
        if ping_success not in test:
            raise AssertionError("Tempest VM cannot ping the outside world (ip) : " + test)

        log("*** Verify the Tempest VM can ping the outside world (dns)")
        test = ping_host(settings.tempest_node.public_ip, "root", settings.tempest_node.root_password, "google.com")
        if ping_success not in test:
            raise AssertionError("Tempest VM cannot ping the outside world (dns) : " + test)

        log("*** Verify the Tempest VM can ping the controller Nodes over the External networkk")
        for each in settings.controller_nodes:
            test = ping_host(settings.tempest_node.public_ip, "root", settings.tempest_node.root_password, each.public_ip)
            if ping_success not in test:
                raise AssertionError("Tempest VM cannot ping the "+ each.hostname +" through the External network : " + test)

        log("*** Verify the Tempest VM can ping the controller Nodes over the Private API networkk")
        for each in settings.controller_nodes:
            test = ping_host(settings.tempest_node.public_ip, "root", settings.tempest_node.root_password, each.private_ip)
            if ping_success not in test:
                raise AssertionError("Tempest VM cannot ping the "+ each.hostname +" through the Private api network : " + test)

        log("*** Verify the Tempest VM can ping the compute Nodes over the Private API networkk")
        for each in settings.compute_nodes:
            test = ping_host(settings.tempest_node.public_ip, "root", settings.tempest_node.root_password, each.private_ip)
            if ping_success not in test:
                raise AssertionError("Tempest VM cannot ping the "+ each.hostname +" through the Private api network : " + test)

        log (" that's all folks "    )
        log ("")
        if fencing_enabled :
            log (" Fencing is enabled")
        else :
            log (" FENCING COULD NOT BE ENABLED!")
            log (" You can use the 'hammer-fencing.sh enable' command to enable fencing after you fixed pcs resource issues.")
        log ("")
        log ("  Some useful ip/passwords  ...")
        log ("")
        log (" Foreman public ip       : " + settings.foreman_node.public_ip)
        log (" Foreman admin password  : " + settings.foreman_password)
        log ("")
        log ("  Horizon public ip        : " + settings.vip_horizon_public)
        log ("  Horizon admin password   : " + settings.openstack_services_password)
        log ("")
        log ("  Ceph/Calamari public ip  : " + settings.ceph_node.public_ip )
        log ("  Calamari root password   : " + settings.ceph_node.root_password)
        log ("")

    except:
        logger.info(traceback.format_exc())
        e = sys.exc_info()[0]
        logger.info(e)
        print e
        print traceback.format_exc()

