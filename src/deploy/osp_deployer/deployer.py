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
    edge_group = parser.add_mutually_exclusive_group()
    edge_group.add_argument('-e', '--edge_site',
                            help='Deploy a single edge site defined in .ini '
                            'and .properties. Note: if overcloud is not '
                            'already deployed you will be prompted to deploy '
                            'the overcloud first',
                            required=False)
    edge_group.add_argument('-a', '--edge_site_all',
                            help='Deploy all edge sites defined in .ini and '
                            '.properties. Note: if overcloud is not already '
                            'deployed you will be prompted to deploy the '
                            'overcloud first',
                            action='store_true', required=False)
    edge_group.add_argument('-d', '--edge_site_delete',
                            help='Tear-down a single edge site defined in '
                            '.ini and .properties',
                            required=False)
    edge_group.add_argument('-f', '--edge_site_delete_all',
                            help='Tear-down all edge sites defined in .ini '
                            'and .properties',
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


def deploy_overcloud(director_vm):
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
    director_vm.configure_idracs_core()
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


def deploy_edge(args, director_vm):
    logger.info("=== Installing edge site(s)")
    if args.edge_site:
        logger.info("=== Installing edge site, args: %s", str(args.edge_site))
        director_vm.deploy_edge_site(args.edge_site)
    elif args.edge_site_all:
        logger.info("=== Installing all edge sites defined in ini")
        director_vm.deploy_edge_site_all()


def get_is_deploy_overcloud():
    _is_deploy_overcloud = False
    _input = input("Deploy the overcloud prior to deploying edge site(s)"
                   ", (y/N)? ")
    if _input.lower().strip() == "y":
        _is_deploy_overcloud = True
    return _is_deploy_overcloud

def get_is_deploy_undercloud():
    _is_deploy_undercloud = False
    _input = input("Deploy the undercloud and overcloud prior to "
                   "deploying edge site(s), (y/N)? ")
    if _input.lower().strip() == "y":
        _is_deploy_undercloud = True
    return _is_deploy_undercloud


def deploy_undercloud(setts, sah_node, tester):
    director_ip = setts.director_node.public_api_ip
    Ssh.execute_command(director_ip,
                        "root",
                        setts.director_node.root_password,
                        "subscription-manager remove --all")
    Ssh.execute_command(director_ip,
                        "root",
                        setts.director_node.root_password,
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
    _is_failed, _error = tester.verify_undercloud_installed()
    if _is_failed:
        raise _error


def deploy():
    ret_code = 0
    # noinspection PyBroadException

    logger.debug("=================================")
    logger.info("=== Starting up ...")
    logger.debug("=================================")
    try:
        settings, args = get_settings()
        is_deploy_edge_site = (bool(args.edge_site) or args.edge_site_all)
        is_delete_edge_site = (bool(args.edge_site_delete)
                               or args.edge_site_delete_all)
        logger.info("Deploying edge site(s)? %s", str(is_deploy_edge_site))
        logger.info("Tear down edge site(s)? %s", str(is_delete_edge_site))
        node_type = None

        # deploying or tearing down and edge site, validate arg is in ini.
        if bool(args.edge_site) or bool(args.edge_site_delete):
            try:
                if bool(settings.node_types_map[args.edge_site]):
                    node_type = args.edge_site
            except KeyError:
                raise AssertionError("Could not find valid edge site for: %s" %
                                     args.edge_site)

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
        if args.edge_site_all:
            sah_node.create_subnet_routes_edge_all()
            sah_node.restart_networks()
        elif bool(args.edge_site):
            sah_node.create_subnet_routes_edge(node_type)
            sah_node.restart_networks()

        sah_node.upload_iso()
        sah_node.upload_director_scripts()
        sah_node.enable_chrony_ports()
        director_vm = Director()
        if args.overcloud_only is False and is_deploy_edge_site is False:
            deploy_undercloud(settings, sah_node, tester)
            if args.undercloud_only:
                return
        elif is_deploy_edge_site is False:
            logger.info("=== Skipped Director VM/Undercloud install")
            logger.debug("Deleting overcloud stack")
            director_vm.delete_overcloud()

        _is_undercloud_failed, _error_uc = tester.verify_undercloud_installed()
        _is_overcloud_failed, _error_oc = tester.verify_overcloud_deployed()
        if (is_deploy_edge_site and _is_undercloud_failed):
            _is_deploy_undercloud = get_is_deploy_undercloud()
            if _is_deploy_undercloud:
                deploy_undercloud(settings, sah_node, tester)
                # recheck undercloud
                _is_uc_failed, _err_uc = tester.verify_undercloud_installed()
                if not _is_uc_failed:
                    deploy_overcloud(director_vm)
                else:
                    raise _err_uc

                _is_oc_failed, _err_oc = tester.verify_overcloud_deployed()
                if not _is_oc_failed:
                    deploy_edge(args, director_vm)
                else:
                    raise _err_oc
            else:
                logger.info("Attempted to deploy edge site(s) but the "
                            "undercloud and overcloud are not deployed "
                            "and the user declined to deploy "
                            "the them first, follwed by edge site(s). "
                            "Edge sites cannot be deployed without an "
                            "existing undercloud and overcloud, exiting")
                os._exit(0)
        elif is_deploy_edge_site and _is_overcloud_failed:
            is_deploy_overcloud = get_is_deploy_overcloud()
            if is_deploy_overcloud:
                deploy_overcloud(director_vm)
                _is_oc_failed, _err_oc = tester.verify_overcloud_deployed()
                if not _is_oc_failed:
                    deploy_edge(args, settings, director_vm)
                else:
                    raise _err_oc
            else:
                logger.info("Attempted to deploy edge site(s) but the "
                            "overcloud is not deployed and the user declined "
                            "to deploy the overcloud first, "
                            "follwed by edge site(s). "
                            "Edge sites cannot be deployed without an "
                            "existing overcloud, exiting")
                os._exit(0)
        elif is_deploy_edge_site:  # undercloud/overcloud deployed, edge only
            deploy_edge(args, settings, director_vm)
            os._exit(0)
        else:  # no edge sites, just do a normal overcloud deployment
            deploy_overcloud(director_vm)
            _is_oc_failed, _err_oc = tester.verify_overcloud_deployed()
            if _is_oc_failed:
                raise _err_oc

        if settings.hpg_enable:
            logger.info("HugePages has been successfully configured "
                        "with size: " + settings.hpg_size)
        if settings.numa_enable:
            logger.info("NUMA has been successfully configured "
                        "with hostos_cpus count: " + settings.hostos_cpu_count)

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
