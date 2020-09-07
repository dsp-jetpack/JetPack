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
from osp_deployer.powerflexgw import Powerflexgw

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
        sah_node.clear_known_hosts()
        sah_node.upload_iso()


        #ADD

        powerflexgw_vm = Powerflexgw()
        sah_node.delete_powerflexgw_vm()
        logger.info("=== Creating the powerflex gateway vm")
        sah_node.create_powerflexgw_vm()
        tester.powerlexgw_vm_health_check()
        logger.info("Installing the powerflex gateway UI")
        powerflexgw_vm.upload_rpm()
        powerflexgw_vm.install_gateway()
        logger.info("Configuring the powerflex gateway vm")
        powerflexgw_vm.configure_gateway()
        logger.info("Retrieving and injecting SSL certificates")
        powerflexgw_vm.get_ssl_certificates()
        powerflexgw_vm.inject_ssl_certificates()
        powerflexgw_vm.restart_gateway()
        powerflexgw_vm.restart_cinder_volume()

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
