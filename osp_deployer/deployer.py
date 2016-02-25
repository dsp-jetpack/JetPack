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

import sys,time, subprocess, logging, traceback, argparse, os
from osp_deployer.director import Director
from osp_deployer.sah import Sah, Settings
from checkpoints import Checkpoints
from auto_common import Ipmi, Ssh

from datetime import datetime


logger = logging.getLogger("osp_deployer")

def setup_logging():
    import logging.config
    if sys.platform.startswith('linux'):
        isLinux = True
    path = '/auto_results'
    if not os.path.exists(path):
        os.makedirs(path)
    logging.config.fileConfig('logging.conf')


def deploy():
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
        logger.info("Settings .ini: " + settings.settingsFile)
        logger.info("Settings .properties " + settings.network_conf)

        tester = Checkpoints()
        tester.verify_deployer_settings()

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

            tester.sah_health_check()

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

            tester.director_vm_health_check()

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
            tester.verify_undercloud_installed()
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

            tester.ceph_vm_health_check()

        else :
            logger.info("Skipped the ceph vm install")


        logger.info("=== Preparing the undercloud ===")
        for each in nonSAHnodes:
                ipmi_session = Ipmi(settings.cygwin_installdir, settings.ipmi_user, settings.ipmi_password, each.idrac_ip)
                ipmi_session.power_off()
                ipmi_session.set_boot_to_pxe()

        director_vm.node_discovery()
        director_vm.assign_node_roles()


        director_vm.setup_templates()
        logger.info("=== Installing the overcloud ")
        logger.debug ("installing the overcloud ... this might take a while")
        director_vm.deploy_overcloud()
        director_vm.retreive_nodes_ips()

        cmd = "source ~/stackrc;heat stack-list | grep overcloud | awk '{print $6}'"
        overcloud_status = Ssh.execute_command_tty(settings.director_node.external_ip, settings.director_install_account_user, settings.director_install_account_pwd,cmd)[0]
        logger.debug("=== Overcloud stack state : "+ overcloud_status )
        director_vm.fix_controllers_vlan_range()
	director_vm.fix_cinder_conf()

        logger.info("====================================")
        logger.info(" OverCloud deployment status: " + overcloud_status)
        logger.info(" log : /auto_results/ ")
        logger.info("====================================")
        if not "CREATE_COMPLETE" in overcloud_status:
            raise AssertionError("OverCloud did not install properly : " + overcloud_status)

    except:
        logger.error(traceback.format_exc())
        e = sys.exc_info()[0]
        logger.error(e)
        print e
        print traceback.format_exc()
	logger.info("log : /auto_results/ ")


if __name__ == "__main__":
        setup_logging()
        deploy()

