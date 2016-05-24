#!/usr/bin/env python

# (c) 2015-2016 Dell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import time
import subprocess
import logging
import traceback
import argparse
import os
from osp_deployer.director import Director
from osp_deployer.sah import Sah, Settings
from checkpoints import Checkpoints
from auto_common import Ipmi, Ssh


logger = logging.getLogger("osp_deployer")


def setup_logging():
    import logging.config

    path = '/auto_results'
    if not os.path.exists(path):
        os.makedirs(path)
    logging.config.fileConfig('logging.conf')


def run_tempest():
    parser = argparse.ArgumentParser(description='Jetstream 5.x deployer')
    parser.add_argument('-s', '--settings',
                        help='ini settings file, e.g settings/acme.ini',
                        required=True)
    parser.add_argument('-skip_sah', '--skip_sah',
                        help='Do not reinstall the SAH node',
                        action='store_true',
                        required=False)
    parser.add_argument('-skip_undercloud', '--skip_undercloud',
                        help='Do not reinstall the SAH or Undercloud',
                        action='store_true', required=False)
    parser.add_argument('-skip_ceph_vm', '--skip_ceph_vm',
                        help='Do not reinstall the ceph vm',
                        action='store_true',
                        required=False)

    args, ignore = parser.parse_known_args()
    settings = Settings(args.settings)

    if settings.run_tempest is True:
        logger.info("=== Running tempest ==")
        director_vm = Director()
        director_vm.run_tempest()
    else:
        logger.debug("not running tempest")


def deploy():
    # noinspection PyBroadException
    try:

        logger.debug("=================================")
        logger.info("=== Starting up ...")
        logger.debug("=================================")

        parser = argparse.ArgumentParser(description='Jetstream 5.x deployer')
        parser.add_argument('-s', '--settings',
                            help='ini settings file, e.g settings/acme.ini',
                            required=True)
        parser.add_argument('-skip_sah', '--skip_sah',
                            help='Do not reinstall the SAH node',
                            action='store_true',
                            required=False)
        parser.add_argument('-skip_undercloud', '--skip_undercloud',
                            help='Do not reinstall the SAH or Undercloud',
                            action='store_true', required=False)
        parser.add_argument('-skip_ceph_vm', '--skip_ceph_vm',
                            help='Do not reinstall the ceph vm',
                            action='store_true',
                            required=False)
        args, ignore = parser.parse_known_args()

        if args.skip_undercloud is True:
            logger.info("Skipping SAH & Undercloud install")
            args.skip_sah = True
        if args.skip_sah is True:
            logger.info("Skipping SAH install")
        if args.skip_ceph_vm is True:
            logger.info("Skipping ceph vm install")

        logger.debug("loading settings files " + args.settings)
        settings = Settings(args.settings)
        logger.info("Settings .ini: " + settings.settings_file)
        logger.info("Settings .properties " + settings.network_conf)

        tester = Checkpoints()
        tester.verify_deployer_settings()
        if settings.retreive_switches_config is True:
            tester.retreive_switches_config()

        non_sah_nodes = (settings.controller_nodes +
                         settings.compute_nodes +
                         settings.ceph_nodes)

        logger.debug("=== powering the nodes")
        for each in non_sah_nodes:
            ipmi_session = Ipmi(settings.cygwin_installdir,
                                settings.ipmi_user,
                                settings.ipmi_password,
                                each.idrac_ip)
            ipmi_session.power_off()
            ipmi_session.set_boot_to_pxe()
        sah_node = Sah()

        if args.skip_sah is False:
            logger.info("=== Unregister the hosts")
            Ssh.execute_command(settings.sah_node.external_ip,
                                "root",
                                settings.sah_node.root_password,
                                "subscription-manager remove --all")
            Ssh.execute_command(settings.sah_node.external_ip,
                                "root",
                                settings.sah_node.root_password,
                                "subscription-manager unregister")

            Ssh.execute_command(settings.ceph_node.external_ip,
                                "root",
                                settings.sah_node.root_password,
                                "subscription-manager remove --all")
            Ssh.execute_command(settings.ceph_node.external_ip,
                                "root",
                                settings.sah_node.root_password,
                                "subscription-manager unregister")

            Ssh.execute_command(settings.director_node.external_ip,
                                "root",
                                settings.sah_node.root_password,
                                "subscription-manager remove --all")
            Ssh.execute_command(settings.director_node.external_ip,
                                "root",
                                settings.sah_node.root_password,
                                "subscription-manager unregister")

            logger.info("preparing the SAH installation")

            logger.debug("=== powering down the SAH node & all the nodes")
            ipmi_sah = Ipmi(settings.cygwin_installdir,
                            settings.ipmi_user,
                            settings.ipmi_password,
                            settings.sah_node.idrac_ip)
            ipmi_sah.power_off()

            logger.info("=== updating the sah kickstart based on settings")

            sah_node.update_kickstart()

            logger.debug("=== starting the tftp service & power on the admin")
            logger.debug(subprocess.check_output("service tftp start",
                                                 stderr=subprocess.STDOUT,
                                                 shell=True))
            time.sleep(60)

            logger.debug("=== enabling and starting dhcpd service")
            logger.debug(subprocess.check_output("systemctl enable dhcpd",
                                                 stderr=subprocess.STDOUT,
                                                 shell=True))
            logger.debug(subprocess.check_output("systemctl start dhcpd",
                                                 stderr=subprocess.STDOUT,
                                                 shell=True))

            logger.debug(
                "=== power on the admin node & wait for the system "
                "to start installing")
            ipmi_sah.set_boot_to_pxe()
            ipmi_sah.power_on()
            time.sleep(400)

            logger.debug("=== stopping tftp service")
            logger.debug(subprocess.check_output("service tftp stop",
                                                 stderr=subprocess.STDOUT,
                                                 shell=True))

            logger.debug("=== stopping and disabling dhcpd service")
            logger.debug(subprocess.check_output("systemctl stop dhcpd",
                                                 stderr=subprocess.STDOUT,
                                                 shell=True))
            logger.debug(subprocess.check_output("systemctl disable dhcpd",
                                                 stderr=subprocess.STDOUT,
                                                 shell=True))

            logger.info("=== Installing the SAH node")
            while "root" not in \
                    Ssh.execute_command(settings.sah_node.external_ip,
                                        "root",
                                        settings.sah_node.root_password,
                                        "whoami")[0]:
                logger.debug("...")
                time.sleep(100)
            logger.debug("sahh node is up @ " + settings.sah_node.external_ip)

            tester.sah_health_check()

            logger.info("Uploading configs/iso/scripts..")
            logger.debug("=== uploading iso's to the sah node")
            sah_node.upload_iso()

            if settings.version_locking_enabled is True:
                logger.debug(
                    "Uploading version locking files for director & ceph vm's")
                sah_node.upload_lock_files()

            logger.debug("=== uploading the director vm sh script")
            sah_node.upload_director_scripts()

            logger.debug("=== Done with the solution admin host")
        else:
            logger.info("=== Skipped SAH install")
            if args.skip_undercloud is False:
                logger.debug("Delete the Director VM")

                Ssh.execute_command(settings.director_node.external_ip,
                                    "root",
                                    settings.sah_node.root_password,
                                    "subscription-manager remove --all")
                Ssh.execute_command(settings.director_node.external_ip,
                                    "root",
                                    settings.sah_node.root_password,
                                    "subscription-manager unregister")

                sah_node.delete_director_vm()

        if args.skip_undercloud is False:
            logger.info("=== create the director vm")
            sah_node.create_director_vm()

            tester.director_vm_health_check()

            logger.info("Preparing the Director VM")
            # Temporary till packages are available on
            # the CDN and installed by the kickstart
            logger.debug(
                " *** install RDO bits since not available on the cdn yet")
            director_vm = Director()
            director_vm.apply_internal_repos()

            logger.debug(
                "===  Uploading & configuring undercloud.conf . "
                "environment yaml ===")
            director_vm.upload_update_conf_files()

            logger.info("=== installing the director & undercloud ===")
            director_vm.upload_cloud_images()
            director_vm.install_director()
            tester.verify_undercloud_installed()
        else:
            logger.info("=== Skipped Director VM/Undercloud install")
            director_vm = Director()
            logger.debug("Deleting overcloud stack")
            director_vm.delete_overcloud()

        if args.skip_ceph_vm is False:
            if args.skip_sah is True:
                logger.debug("Delete the ceph VM")
                logger.debug(
                    Ssh.execute_command(settings.ceph_node.external_ip,
                                        "root",
                                        settings.ceph_node.root_password,
                                        "subscription-manager remove --all"))
                Ssh.execute_command(settings.ceph_node.external_ip,
                                    "root",
                                    settings.ceph_node.root_password,
                                    "subscription-manager unregister")

                sah_node.delete_ceph_vm()

            logger.info("=== creating ceph VM")
            sah_node.create_ceph_vm()

            tester.ceph_vm_health_check()

        else:
            logger.info("Skipped the ceph vm install")

        logger.info("=== Preparing the overcloud ===")

        director_vm.node_discovery()
        director_vm.assign_node_roles()

        director_vm.setup_templates()
        logger.info("=== Installing the overcloud ")
        logger.debug("installing the overcloud ... this might take a while")
        director_vm.deploy_overcloud()
        director_vm.retreive_nodes_ips()
        tester.verify_computes_virtualization_enabled()

        cmd = "source ~/stackrc;heat stack-list | grep "+ settings.overcloud_name +" |" \
              " awk '{print $6}'"
        overcloud_status = \
            Ssh.execute_command_tty(settings.director_node.external_ip,
                                    settings.director_install_account_user,
                                    settings.director_install_account_pwd,
                                    cmd)[0]
        logger.debug("=== Overcloud stack state : " + overcloud_status)

        logger.info("====================================")
        logger.info(" OverCloud deployment status: " + overcloud_status)
        logger.info(" log : /auto_results/ ")
        logger.info("====================================")
        if "CREATE_COMPLETE" not in overcloud_status:
            raise AssertionError(
                "OverCloud did not install properly : " + overcloud_status)
        if args.skip_ceph_vm is False:
            director_vm.configure_calamari()
        director_vm.enable_fencing()
        director_vm.enable_instance_ha()
        director_vm.run_sanity_test()
        logger.info("Depoyment summary info; usefull ip's etc.. " + \
                    "/auto_results/deployment_summary.log")

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
    run_tempest()
