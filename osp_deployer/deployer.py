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

import sys,time, subprocess, logging, traceback, argparse
from osp_deployer.director import Director
from osp_deployer.sah import Sah
from auto_common import Ipmi, Ssh
from osp_deployer import Settings, Deployer_sanity
from datetime import datetime

ping_success = "packets transmitted, 3 received"
logger = logging.getLogger("osp_deployer")

def verify_subscription_status(external_ip, user, password, retries):
    i = 0
    subscriptionStatus = Ssh.execute_command(external_ip, user, password, "subscription-manager status")[0]
    while("Current" not in subscriptionStatus and i < retries):
        if "Unknown" in subscriptionStatus:
            return subscriptionStatus
        logger.debug("...")
        time.sleep(60)
        subscriptionStatus = Ssh.execute_command(external_ip, user, password, "subscription-manager status")[0]
        i += 1;
    return subscriptionStatus

def ping_host(external_ip, user, passwd, targetHost):
    subscriptionStatus = Ssh.execute_command(external_ip, user, passwd, "ping " + targetHost + " -c 3 -w 30 ")[0]
    return subscriptionStatus


def deploy():
    import logging.config
    logging.config.fileConfig('logging.conf')
    isLinux = False
    if sys.platform.startswith('linux'):
        isLinux = True

   
    try:

        logger.debug ("=================================")
        logger.info ("=== Starting up ...")
        logger.debug ("=================================")

        parser = argparse.ArgumentParser(description='Jetstream 5.x deployer')
        parser.add_argument('-s','--settings', help='ini settings file, e.g settings/acme.ini', required=True)
        parser.add_argument('-skip_sah','--skip_sah', help='Do not reinstall the SAH node',action='store_true', required=False)
        parser.add_argument('-skip_undercloud','--skip_undercloud', help='Do not reinstall the SAH or Undercloud',action='store_true', required=False)
        parser.add_argument('-skip_ceph_vm','--skip_ceph_vm', help='Do not reinstall the ceph vm',action='store_true', required=False)
        args = parser.parse_args()

        if args.skip_undercloud is True :
            logger.info("Skipping SAH & Undercloud install")
            args.skip_sah = True
        if args.skip_sah is True :
            logger.info("Skipping SAH install")
        if args.skip_ceph_vm is True:
            logger.info("Skipping ceph vm install")

        logger.debug("loading settings files " + args.settings)
        settings = Settings(args.settings)
        attrs = vars(settings)

        logger.info("==== Running environment sanity tests")
        checks = Deployer_sanity()
        checks.check_network_settings()
        checks.check_files()
        checks.check_ipmi_to_nodes()

        hosts = [settings.sah_node, settings.director_node]
        hosts.append(settings.ceph_node)
        others =  settings.controller_nodes + settings.compute_nodes
        nonSAHnodes = others + settings.ceph_nodes


        sah_node = Sah()

        if args.skip_sah is False :
            logger.info ("=== Unregister the hosts")
            logger.debug (Ssh.execute_command(settings.sah_node.external_ip, "root", settings.sah_node.root_password, "subscription-manager remove --all"))
            logger.debug (Ssh.execute_command(settings.sah_node.external_ip, "root", settings.sah_node.root_password, "subscription-manager unregister"))

            logger.debug (Ssh.execute_command(settings.ceph_node.external_ip, "root", settings.sah_node.root_password, "subscription-manager remove --all"))
            logger.debug (Ssh.execute_command(settings.ceph_node.external_ip, "root", settings.sah_node.root_password, "subscription-manager unregister"))

            logger.debug (Ssh.execute_command(settings.director_node.external_ip, "root", settings.sah_node.root_password, "subscription-manager remove --all"))
            logger.debug (Ssh.execute_command(settings.director_node.external_ip, "root", settings.sah_node.root_password, "subscription-manager unregister"))

            #TODO unregister tempest VM when available ( if on SAH )

            logger.info("preparing the SAH installation")

            logger.debug ("=== powering down the SAH node & all the nodes")
            ipmi_sah = Ipmi(settings.cygwin_installdir, settings.ipmi_user, settings.ipmi_password, settings.sah_node.idrac_ip)
            ipmi_sah.power_off()

            logger.debug ("=== powering down other hosts")
            for each in nonSAHnodes:
                ipmi_session = Ipmi(settings.cygwin_installdir, settings.ipmi_user, settings.ipmi_password, each.idrac_ip)
                ipmi_session.power_off()
                ipmi_session.set_boot_to_pxe()

            logger.info ("=== updating the sah kickstart based on settings")

            sah_node.update_kickstart()

            logger.debug ("=== starting the tftp service & power on the admin")
            logger.debug (subprocess.check_output("service tftp start" if isLinux else "net start Tftpd32_svc",stderr=subprocess.STDOUT, shell=True))
            time.sleep(60)

            #linux, dhcp is a separate service
            if(isLinux):
               logger.debug ("=== starting dhcpd service")
               logger.debug (subprocess.check_output("service dhcpd start",stderr=subprocess.STDOUT, shell=True))


            logger.debug ("=== power on the admin node & wait for the system to start installing")
            ipmi_sah.set_boot_to_pxe()
            ipmi_sah.power_on()
            time.sleep(400)

            logger.debug ("=== stopping tftp service")
            logger.debug (subprocess.check_output("service tftp stop" if isLinux else "net stop Tftpd32_svc",stderr=subprocess.STDOUT, shell=True))

            if(isLinux):
                logger.debug ("=== stopping dhcpd service")
                logger.debug (subprocess.check_output("service dhcpd stop",stderr=subprocess.STDOUT, shell=True))


            logger.info ("=== Installing the SAH node")
            while (not "root" in Ssh.execute_command(settings.sah_node.external_ip, "root", settings.sah_node.root_password, "whoami")[0]):
                logger.debug ("...")
                time.sleep(100)
            logger.debug ("sahh node is up @ " + settings.sah_node.external_ip)


            logger.info("SAH node health check")
            logger.debug("*** Verify the SAH node registered properly ***")
            subscriptionStatus = verify_subscription_status(settings.sah_node.external_ip, "root", settings.sah_node.root_password, settings.subscription_check_retries)
            if "Current" not in subscriptionStatus:
                raise AssertionError("SAH did not register properly : " + subscriptionStatus)

            logger.debug("*** Verify the SAH can ping its public gateway")
            test = ping_host(settings.sah_node.external_ip, "root", settings.sah_node.root_password, settings.external_gateway)
            if ping_success not in test:
                raise AssertionError("SAH cannot ping its public gateway : " + test)

            logger.debug("*** Verify the SAH can ping the outside world (ip)")
            test = ping_host(settings.sah_node.external_ip, "root", settings.sah_node.root_password, "8.8.8.8")
            if ping_success not in test:
                raise AssertionError("SAH cannot ping the outside world (ip) : " + test)

            logger.debug("*** Verify the SAH can ping the outside world (dns)")
            test = ping_host(settings.sah_node.external_ip, "root", settings.sah_node.root_password, "google.com")
            if ping_success not in test:
                raise AssertionError("SAH cannot ping the outside world (dns) : " + test)

            logger.debug("*** Verify the SAH has KVM enabled *** ")
            cmd = 'ls -al /dev/kvm'
            if "No such file" in Ssh.execute_command(settings.sah_node.external_ip, "root", settings.sah_node.root_password, cmd)[1]:
                raise AssertionError("KVM Not running on the SAH node - make sure the node has been DTK'ed/Virtualization enabled in the Bios")

            logger.info("Uploading configs/iso/scripts..")
            logger.debug ("=== uploading iso's to the sah node")
            sah_node.upload_iso()

            if settings.version_locking_enabled is True:
                logger.debug("Uploading version locking files for director & ceph vm's")
                sah_node.upload_lock_files()

            logger.debug("=== uploading the director vm sh script")
            sah_node.upload_director_scripts()

            logger.debug("=== Done with the solution admin host");
        else:
            logger.info("=== Skipped SAH install")
            if args.skip_undercloud is False :
                logger.debug("Delete the Director VM")

                logger.debug (Ssh.execute_command(settings.director_node.external_ip, "root", settings.sah_node.root_password, "subscription-manager remove --all"))
                logger.debug (Ssh.execute_command(settings.director_node.external_ip, "root", settings.sah_node.root_password, "subscription-manager unregister"))

                sah_node.delete_director_vm()



        if args.skip_undercloud is False :
            logger.info("=== create the director vm")
            sah_node.create_director_vm()

            logger.info("Director VM health checks")
            logger.debug("*** Verify the Director VM registered properly ***")
            subscriptionStatus = verify_subscription_status(settings.director_node.external_ip, "root", settings.director_node.root_password, settings.subscription_check_retries)
            if "Current" not in subscriptionStatus:
                raise AssertionError("Director VM did not register properly : " + subscriptionStatus)

            logger.debug("*** Verify the Director VM can ping its public gateway")
            test = ping_host(settings.director_node.external_ip, "root", settings.director_node.root_password, settings.external_gateway)
            if ping_success not in test:
                raise AssertionError("Director VM cannot ping its public gateway : " + test)

            logger.debug("*** Verify the Director VM can ping the outside world (ip)")
            test = ping_host(settings.director_node.external_ip, "root", settings.director_node.root_password, "8.8.8.8")
            if ping_success not in test:
                raise AssertionError("Director VM cannot ping the outside world (ip) : " + test)

            logger.debug("*** Verify the Director VM can ping the outside world (dns)")
            test = ping_host(settings.director_node.external_ip, "root", settings.director_node.root_password, "google.com")
            if ping_success not in test:
                raise AssertionError("Director VM cannot ping the outside world (dns) : " + test)

            logger.debug("*** Verify the Director VM can ping the SAH node through the provisioning network")
            test = ping_host(settings.director_node.external_ip, "root", settings.director_node.root_password, settings.sah_node.provisioning_ip)
            if ping_success not in test:
                raise AssertionError("Director VM cannot ping the SAH node through the provisioning network : " + test)

            logger.debug("*** Verify the Director VM can ping the SAH node through the public network")
            test = ping_host(settings.director_node.external_ip, "root", settings.director_node.root_password, settings.sah_node.external_ip)
            if ping_success not in test:
                raise AssertionError("Director VM cannot ping the SAH node through the provisioning network : " + test)

            logger.info("Preparing the Director VM")
            ## Temporary till packages are available on the CDN and installed by the kickstart
            logger.debug(" *** install RDO bits since not available on the cdn yet")
            director_vm = Director()
            director_vm.apply_internal_repos()

            logger.debug("===  Uploading & configuring undercloud.conf . environment yaml ===")
            director_vm.upload_update_conf_files()

            logger.info("=== installing the director & undercloud ===")
            director_vm.upload_cloud_images()
            director_vm.install_director()
        else :
            logger.info("=== Skipped Director VM/Undercloud install")
            director_vm = Director()
            logger.debug("Deleting overcloud stack")
            director_vm.delete_overcloud()


        if args.skip_ceph_vm is False :
            if args.skip_sah is True:
                logger.debug("Delete the ceph VM")
                logger.debug (Ssh.execute_command(settings.director_node.external_ip, "root", settings.ceph_node.root_password, "subscription-manager remove --all"))
                logger.debug (Ssh.execute_command(settings.director_node.external_ip, "root", settings.ceph_node.root_password, "subscription-manager unregister"))

                sah_node.delete_ceph_vm()

            logger.info( "=== creating ceph VM")
            sah_node.create_ceph_vm()

            logger.info("Ceph VM health checks")
            logger.debug("*** Verify the Ceph VM registered properly ***")
            subscriptionStatus = verify_subscription_status(settings.ceph_node.external_ip, "root", settings.ceph_node.root_password, settings.subscription_check_retries)
            if "Current" not in subscriptionStatus:
                raise AssertionError("Ceph VM did not register properly : " + subscriptionStatus)

            logger.debug("*** Verify the Ceph VM can ping its public gateway")
            test = ping_host(settings.ceph_node.external_ip, "root", settings.ceph_node.root_password, settings.public_gateway)
            if ping_success not in test:
                raise AssertionError("Ceph VM cannot ping its public gateway : " + test)

            logger.debug("*** Verify the Ceph VM can ping the outside world (ip)")
            test = ping_host(settings.ceph_node.external_ip, "root", settings.ceph_node.root_password, "8.8.8.8")
            if ping_success not in test:
                raise AssertionError("Ceph VM cannot ping the outside world (ip) : " + test)

            logger.debug("*** Verify the Ceph VM can ping the outside world (dns)")
            test = ping_host(settings.ceph_node.external_ip, "root", settings.ceph_node.root_password, "google.com")
            if ping_success not in test:
                raise AssertionError("Ceph VM cannot ping the outside world (dns) : " + test)

            logger.debug("*** Verify the Ceph VM can ping the SAH node through the storage network")
            test = ping_host(settings.ceph_node.external_ip, "root", settings.ceph_node.root_password, settings.sah_node.storage_ip)
            if ping_success not in test:
                raise AssertionError("Ceph VM cannot ping the SAH node through the storage network : " + test)

            logger.debug("*** Verify the Ceph VM can ping the SAH node through the public network")
            test = ping_host(settings.ceph_node.external_ip, "root", settings.ceph_node.root_password, settings.sah_node.external_ip)
            if ping_success not in test:
                raise AssertionError("Ceph VM cannot ping the SAH node through the public network : " + test)

            logger.debug("*** Verify the Ceph VM can ping the Director VM through the public network")
            test = ping_host(settings.ceph_node.external_ip, "root", settings.ceph_node.root_password, settings.director_node.external_ip)
            if ping_success not in test:
                raise AssertionError("Ceph VM cannot ping the Director VM through the provisioning network : " + test)
        else :
            logger.info("Skipped the ceph vm install")


        logger.info("=== Preparing the undercloud ===")
        for each in nonSAHnodes:
                ipmi_session = Ipmi(settings.cygwin_installdir, settings.ipmi_user, settings.ipmi_password, each.idrac_ip)
                ipmi_session.power_off()
                ipmi_session.set_boot_to_pxe()

        director_vm.node_discovery()
        director_vm.assign_node_roles()


        director_vm.setup_networking()
        logger.info("=== Installing the overcloud ")
        logger.debug ("installing the overcloud ... this might take a while")
        director_vm.deploy_overcloud()

        logger.info  ("**** Retreiving nodes information ")
        ip_info = []
        try:
            logger.debug("retreiving node ip details ..")

            ip_info.append(  "====================================")
            ip_info.append(  "### nodes ip information ###")
            known_hosts_filename = "~/.ssh/known_hosts"
            cmd = "source ~/stackrc;nova list | grep controller"
            re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)

            ip_info.append(  "### Controllers ###" )
            list = re[0].split("\n")
            list.pop()
            for each in list:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]
                cmd = "ssh-keyscan -H {} >> ~/.ssh/known_hosts".format(provisioning_ip)
                re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)

                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+settings.private_api_vlanid+".*netmask "+settings.private_api_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)
                private_api = re[0].split("\n")[0]

                cmd = "ssh heat-admin@"+provisioning_ip+ "/sbin/ifconfig | grep \"inet.*"+settings.public_api_vlanid+".*netmask "+settings.public_api_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)
                nova_public_ip = re[0].split("\n")[0]


                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+settings.storage_vlanid+".*netmask "+settings.storage_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)
                storage_ip = re[0].split("\n")[0]

                ip_info.append(  hostname + ":")
                ip_info.append("     - provisioning ip  : " + provisioning_ip)
                ip_info.append("     - nova private ip  : " + private_api)
                ip_info.append("     - nova public ip   : " + nova_public_ip)
                ip_info.append("     - storage ip       : " + storage_ip)


            cmd = "source ~/stackrc;nova list | grep compute"
            re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)

            ip_info.append(  "### Compute  ###" )
            list = re[0].split("\n")
            list.pop()
            for each in list:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]
                cmd = "ssh-keyscan -H {} >> ~/.ssh/known_hosts".format(provisioning_ip)
                re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)

                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+settings.private_api_vlanid+".*netmask "+settings.private_api_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)
                private_api = re[0].split("\n")[0]

                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+settings.storage_vlanid+".*netmask "+settings.storage_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)
                storage_ip = re[0].split("\n")[0]

                ip_info.append( hostname + ":")
                ip_info.append( "     - provisioning ip  : " + provisioning_ip)
                ip_info.append( "     - nova private ip  : " + private_api)
                ip_info.append( "     - storage ip       : " + storage_ip)

            cmd = "source ~/stackrc;nova list | grep storage"
            re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)

            ip_info.append ("### Storage  ###")
            list = re[0].split("\n")
            list.pop()
            for each in list:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]
                cmd = "ssh-keyscan -H {} >> ~/.ssh/known_hosts".format(provisioning_ip)
                re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)

                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+settings.storage_cluster_vlanid+".*netmask 255.255.255.0.*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)
                cluster_ip = re[0].split("\n")[0]

                cmd = "ssh heat-admin@"+provisioning_ip+ " /sbin/ifconfig | grep \"inet.*"+settings.storage_vlanid+".*netmask "+settings.storage_netmask+".*\" | awk '{print $2}'"
                re = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)
                storage_ip = re[0].split("\n")[0]

                ip_info.append ( hostname + ":")
                ip_info.append ("     - provisioning ip    : " + provisioning_ip)
                ip_info.append( "     - storage cluster ip : " + cluster_ip)
                ip_info.append ("     - storage ip         : " + storage_ip)
            ip_info.append ("====================================")

            try:
                overcloud_endpoint = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,'grep "OS_AUTH_URL=" ~/overcloudrc')[0].split('=')[1].replace(':5000/v2.0/','')
                overcloud_pass = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,'grep "OS_PASSWORD=" ~/overcloudrc')[0].split('=')[1]
                ip_info.append("OverCloud Horizon        : " + overcloud_endpoint)
                ip_info.append("OverCloud admin password : " + overcloud_pass)
            except:
                pass
            ip_info.append ("====================================")
            for each in ip_info:
                logger.debug(each)

        except:
                for each in ip_info:
                    logger.debug(each)
                logger.debug(" Failed to retreive the nodes ip information ")


        cmd = "source ~/stackrc;heat stack-list | grep overcloud | awk '{print $6}'"
        overcloud_status = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)[0]
        logger.debug("=== Overcloud stack state : "+ overcloud_status )
        logger.info("Applyin neutron vlan config workaround (note : it might take a few minutes for the controlers to come back up)")
        director_vm.fix_controllers_vlan_range()

        logger.debug("====================================")
        logger.info(" OverCloud deployment status: " + overcloud_status)
	logger.debug("====================================")
        logger.info("Deployment complete, see log for details ")

    except:
        logger.error(traceback.format_exc())
        e = sys.exc_info()[0]
        logger.error(e)
        print e
        print traceback.format_exc()


if __name__ == "__main__":

        deploy()

