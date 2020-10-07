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
from auto_common.constants import *
from pprint import pformat

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
    edge_group.add_argument('-e', '--edge_sites', nargs="+",
                            help='Deploy edge site(s) defined in .ini '
                            'and .properties. Note: if the overcloud is not '
                            'already deployed you cannot deploy edge sites.',
                            required=False)
    # parser.add_argument("--foo", action="extend", nargs="+", type=str)
    edge_group.add_argument('-a', '--edge_sites_all',
                            help='Deploy all the edge sites defined '
                            'in the .ini and .properties files.',
                            action='store_true',
                            required=False)
    edge_group.add_argument('-l', '--list_edge_sites',
                            help='Show a list of available edge sites to '
                            'deploy, and their deployment status.',
                            action='store_true',
                            required=False)

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


def run_tempest(director_vm):
    settings, args = get_settings()
    if settings.run_tempest is True or args.run_tempest_only:
        logger.info("=== Running tempest ==")
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


def deploy_edge_site(sah_node, director_vm, node_type):
    logger.info("=== Installing edge site: %s", str(node_type))
    # first delete site if it exists
    delete_edge_site(sah_node, director_vm, node_type)
    sah_node.subnet_routes_edge(node_type)
    director_vm.deploy_edge_site(node_type)


def deploy_edge_sites(sah_node, director_vm, edge_sites):
    for node_type in edge_sites:
        deploy_edge_site(sah_node, director_vm, node_type)


def delete_edge_site(sah_node, director_vm, node_type):
    logger.info("=== Deleting edge site: %s", node_type)
    director_vm.delete_edge_site(node_type)
    sah_node.subnet_routes_edge(node_type, False)


def delete_edge_sites(sah_node, director_vm, edge_sites):
    for site in edge_sites:
        delete_edge_site(sah_node, director_vm, site)


def deploy_undercloud(setts, sah_node, tester, director_vm):
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


def list_edge_sites(settings, director_vm):
    logger.info("====================================")
    logger.info("Edge sites:")
    for node_type in settings.edge_sites:
        stk_info = director_vm.fetch_stack_info_edge(node_type)
        logger.info("Site Name: {}".format(node_type))
        logger.info("Heat Stack Name: {}".format(stk_info["stack_name"]))
        logger.info("Status: {}".format(stk_info["stack_status"]))
        logger.info("Creation Time: {}\n".format(stk_info["creation_time"]))
    for node_type, node_type_data in settings.node_type_data_map.items():
        logger.debug("\nEdge site {} "
                     "metadata:"
                     "\n{}\n".format(node_type, pformat(node_type_data)))
        nodes = settings.node_types_map[node_type]
        logger.debug("\nEdge site: {} nodes:".format(node_type))
        for node in nodes:
            logger.debug("\n{}\n".format(pformat(node.__dict__)))


def validate_edge_sites_in_settings(args, setts):
    _sites = setts.edge_sites if args.edge_sites_all else args.edge_sites
    _not_found = list(filter(lambda s: s not in setts.node_types_map, _sites))
    if _not_found:
        raise AssertionError("Could not find valid edge site(s) "
                             "for: {}, please verify your .ini and "
                             ".properties and try "
                             "again".format(str(', '.join(_not_found))))
    else:
        return _sites


def deploy():
    ret_code = 0
    # noinspection PyBroadException

    logger.debug("=================================")
    logger.info("=== Starting up ...")
    logger.debug("=================================")
    try:
        settings, args = get_settings()
        director_vm = Director()
        sah_node = Sah()

        if args.list_edge_sites:
            list_edge_sites(settings, director_vm)
            os._exit(0)

        is_deploy_edge_site = bool(args.edge_sites) or args.edge_sites_all
        logger.info("Deploying edge site(s)? %s", str(is_deploy_edge_site))
        edge_sites = None

        # deploying edge site(s)?, validate sites are in settings, if
        # valid return a list of sites based on args.
        if is_deploy_edge_site:
            edge_sites = validate_edge_sites_in_settings(args, settings)

        logger.info("Edge sites after validation: {}".format(str(edge_sites)))

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
        tester.sah_health_check()
        # mutually exclusive command, configure tempest and quit.
        if args.tempest_config_only:
            logger.info("Only (re-)generating tempest.conf")
            director_vm.configure_tempest()
            os._exit(0)

        # mutually exclusive command, run tempest and quit.
        if args.run_tempest_only:
            logger.info("Only running tempest, will configure "
                        + "tempest.conf if needed.")
            director_vm.run_tempest()
            os._exit(0)

        logger.info("Uploading configs/iso/scripts.")
        sah_node.clear_known_hosts()
        sah_node.handle_lock_files()

        sah_node.upload_iso()
        sah_node.upload_director_scripts()
        sah_node.enable_chrony_ports()
        if args.overcloud_only is False and is_deploy_edge_site is False:
            deploy_undercloud(settings, sah_node, tester, director_vm)
            if args.undercloud_only:
                return
        elif is_deploy_edge_site is False:
            logger.info("=== Skipped Director VM/Undercloud install")
            logger.debug("Deleting overcloud stack")
            director_vm.delete_overcloud()

        if is_deploy_edge_site:
            _is_oc_failed, _error_oc = tester.verify_overcloud_deployed()
            if _is_oc_failed:
                logger.error("Attempted to deploy edge site(s) but the "
                             "overcloud has not been deployed, "
                             "or failed to deploy. "
                             "Edge sites cannot be deployed without an "
                             "existing overcloud, exiting")
                os._exit(0)
            deploy_edge_sites(sah_node, director_vm, edge_sites)
            os._exit(0)
        else:  # no edge sites arguments, just deploy overcloud
            deploy_overcloud(director_vm)
            _is_oc_failed, _err_oc = tester.verify_overcloud_deployed()
            if _is_oc_failed:
                raise _err_oc
            # lastly, if there are edge sites defined in .ini
            # and deploy_edge_sites is set to true in ini deploy the sites
            if settings.deploy_edge_sites and settings.edge_sites:
                deploy_edge_sites(sah_node, director_vm, settings.edge_sites)

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

        run_tempest(director_vm)

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
