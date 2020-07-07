#!/usr/bin/env python3

# Copyright (c) 2015-2020 Dell Inc. or its subsidiaries.
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

import argparse
import logging
import os
import sys
import traceback
from osp_deployer.director import Director
from osp_deployer.sah import Sah
from osp_deployer.settings.config import Settings
from checkpoints import Checkpoints
from auto_common import Ipmi, Ssh, Scp

logger = logging.getLogger("osp_deployer")


def setup_logging():
    import logging.config

    path = '/auto_results'
    if not os.path.exists(path):
        os.makedirs(path)
    logging.config.fileConfig('logging.conf')

def setup_staging():
    staging_path = '/deployment_staging'
    staging_templates_path = staging_path + "/templates"
    if not os.path.exists(staging_path):
        os.makedirs(staging_path)
    if not os.path.exists(staging_templates_path):
        os.makedirs(staging_templates_path)

def get_settings():
    parser = argparse.ArgumentParser(
        description='JetPack 16.x deployer')
    parser.add_argument('-s', '--settings',
                        help='ini settings file, e.g settings/acme.ini',
                        required=True)
    parser.add_argument('-undercloud_only', '--undercloud_only',
                        help='Only reinstall the undercloud',
                        action='store_true', required=False)
    parser.add_argument('-overcloud_only', '--overcloud_only',
                        help='Only reinstall the overcloud',
                        action='store_true', required=False)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-validate_only', '--validate_only',
                       help='No deployment - just validate config values',
                       action='store_true',
                       required=False)
    group.add_argument('-tempest_config_only', '--tempest_config_only',
                       help='Only (re-)generate the tempest.conf file.',
                       action='store_true', required=False)
    group.add_argument('-run_tempest_only', '--run_tempest_only',
                       help='(Re-)generate the tempest.conf file if needed '
                       'and run tempest.',
                       action='store_true', required=False)

    args, unknown = parser.parse_known_args()
    if len(unknown) > 0:
        parser.print_help()
        msg = "Invalid argument(s) :"
        for each in unknown:
            msg += " " + each + ";"
        raise AssertionError(msg)

    logger.info("Loading settings file: " + args.settings)
    settings = Settings(args.settings)
    return settings, args


def run_tempest():
    settings, args = get_settings()
    if settings.run_tempest is True or args.run_tempest_only:
        logger.info("=== Running tempest ==")
        director_vm = Director()
        director_vm.run_tempest()
    else:
        logger.debug("Not running tempest")


def deploy():
    ret_code = 0
    # noinspection PyBroadException

    logger.debug("=================================")
    logger.info("=== Starting up ...")
    logger.debug("=================================")
    try:
        settings, args = get_settings()
        if args.validate_only is True:
            logger.info("Only validating ini/properties config values")
        else:
            if args.overcloud_only is True:
                logger.info("Only redeploying the overcloud")

        logger.info("Settings .ini: " + settings.settings_file)
        logger.info("Settings .properties " + settings.network_conf)
        settings.get_version_info()
        logger.info("source version # : "
                    + settings.source_version.decode('utf-8'))
        tester = Checkpoints()
        tester.verify_deployer_settings()
        if args.validate_only is True:
            logger.info("Settings validated")
            os._exit(0)
        tester.retreive_switches_config()

        # non_sah_nodes = (settings.controller_nodes +
        #                 settings.compute_nodes +
        #                  settings.ceph_nodes)

        sah_node = Sah()

        tester.sah_health_check()
        # mutually exclusive command, configure tempest and quit.
        if args.tempest_config_only:
            logger.info("Only (re-)generating tempest.conf")
            director_vm = Director()
            director_vm.configure_tempest()
            os._exit(0)

        # mutually exclusive command, run tempest and quit.
        if args.run_tempest_only:
            logger.info("Only running tempest, will configure "
                        + "tempest.conf if needed.")
            director_vm = Director()
            director_vm.run_tempest()
            os._exit(0)

        logger.info("Uploading configs/iso/scripts.")
        sah_node.clear_known_hosts()
        sah_node.handle_lock_files()
        if settings.node_type_data_map:
            sah_node.create_subnet_routes_edge()
        sah_node.upload_iso()
        sah_node.upload_director_scripts()
        sah_node.enable_chrony_ports()

        director_ip = settings.director_node.public_api_ip
        if args.overcloud_only is False:
            Ssh.execute_command(director_ip,
                                "root",
                                settings.director_node.root_password,
                                "subscription-manager remove --all")
            Ssh.execute_command(director_ip,
                                "root",
                                settings.director_node.root_password,
                                "subscription-manager unregister")
            sah_node.delete_director_vm()

            logger.info("=== create the director vm")
            sah_node.create_director_vm()
            tester.director_vm_health_check()

            logger.info("Preparing the Director VM")
            director_vm = Director()
            director_vm.apply_internal_repos()

            logger.debug(
                "===  Uploading & configuring undercloud.conf . "
                "environment yaml ===")
            director_vm.upload_update_conf_files()

            logger.info("=== installing the director & undercloud ===")
            director_vm.inject_ssh_key()
            director_vm.upload_cloud_images()
            director_vm.install_director()
            if settings.node_type_data_map:
                director_vm.create_subnet_routes_edge()
                dir_pub_ip = settings.director_node.public_api_ip
                dir_pw = settings.director_node.root_password
                director_vm.wait_for_vm_to_come_up(dir_pub_ip,
                                                   "root",
                                                   dir_pw)
                logger.info('Director VM routes set and VM is running')
            director_vm.setup_roles_edge()
            tester.verify_undercloud_installed()
            if args.undercloud_only:
                return
        else:
            logger.info("=== Skipped Director VM/Undercloud install")
            director_vm = Director()
            logger.debug("Deleting overcloud stack")
            director_vm.delete_overcloud()

        logger.info("=== Preparing the overcloud ===")

        # The network-environment.yaml must be setup for use during DHCP
        # server configuration
        logger.info("Setting up network environment")
        director_vm.setup_net_envt()
        logger.info("Setting up dhcp server")
        director_vm.configure_dhcp_server()
        logger.info("Discovering nodes")
        director_vm.node_discovery()
        logger.info("Configuring iDRACs")
        director_vm.configure_idracs()
        logger.info("Importing nodes")
        director_vm.import_nodes()
        logger.info("Introspecting nodes")
        director_vm.node_introspection()
        logger.info("Assigning roles")
        director_vm.update_sshd_conf()
        director_vm.assign_node_roles()
        director_vm.revert_sshd_conf()

        logger.info("Configuring heat templates")
        director_vm.setup_templates()

        logger.info("=== Installing the overcloud ")
        logger.debug("installing the overcloud ... this might take a while")
        director_vm.deploy_overcloud()
        cmd = "source ~/stackrc; openstack stack list | grep " \
              + settings.overcloud_name + " | awk '{print $8}'"
        overcloud_status = \
            Ssh.execute_command_tty(director_ip,
                                    settings.director_install_account_user,
                                    settings.director_install_account_pwd,
                                    cmd)[0]
        logger.debug("=== Overcloud stack state : " + overcloud_status)
        if settings.hpg_enable:
            logger.info(
                " HugePages has been successfully configured with size: " +
                settings.hpg_size)
        if settings.numa_enable:
            logger.info(
                " NUMA has been successfully configured"
                " with hostos_cpus count: " +
                settings.hostos_cpu_count)

        logger.info("====================================")
        logger.info(" OverCloud deployment status: " + overcloud_status)
        logger.info(" log : /auto_results/ ")
        logger.info("====================================")
        if "CREATE_COMPLETE" not in overcloud_status:
            raise AssertionError(
                "OverCloud did not install properly : " + overcloud_status)

        director_vm.summarize_deployment()
        tester.verify_computes_virtualization_enabled()
        tester.verify_backends_connectivity()
        director_vm.enable_fencing()
        director_vm.run_sanity_test()

        external_sub_guid = director_vm.get_sanity_subnet()
        if external_sub_guid:
            director_vm.configure_tempest()

        run_tempest()

        logger.info("Deployment summary info; useful ip's etc.. " +
                    "/auto_results/deployment_summary.log")

    except:  # noqa: E722
        logger.error(traceback.format_exc())
        e = sys.exc_info()[0]
        logger.error(e)
        print(e)
        print(traceback.format_exc())
        ret_code = 1
    logger.info("log : /auto_results/ ")
    sys.exit(ret_code)


if __name__ == "__main__":
    setup_logging()
    setup_staging()
    deploy()
