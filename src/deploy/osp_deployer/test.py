#!/usr/bin/env python

# Copyright (c) 2015-2017 Dell Inc. or its subsidiaries.
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
from auto_common import Ipmi, Ssh, Scp


logger = logging.getLogger("osp_deployer")


def setup_logging():
    import logging.config

    path = '/auto_results'
    if not os.path.exists(path):
        os.makedirs(path)
    logging.config.fileConfig('logging.conf')


def get_settings():
    parser = argparse.ArgumentParser(
        description='JetPack 10.x deployer')
    parser.add_argument('-s', '--settings',
                        help='ini settings file, e.g settings/acme.ini',
                        required=True)
    parser.add_argument('-undercloud_only', '--undercloud_only',
                        help='Only reinstall the undercloud',
                        action='store_true', required=False)
    parser.add_argument('-overcloud_only', '--overcloud_only',
                        help='Only reinstall the overcloud',
                        action='store_true', required=False)
    parser.add_argument('-skip_rhscon_vm', '--skip_rhscon_vm',
                        help='Do not reinstall the Storage Console VM',
                        action='store_true',
                        required=False)
    parser.add_argument('-validate_settings_only', '--validate_settings_only',
                        help='Only validate ini and properties files (no deployment)',
                        action='store_true', required=False)
    args, ignore = parser.parse_known_args()
    settings = Settings(args.settings)
    return settings


def run_tempest():
    settings = get_settings()
    if settings.run_tempest is True:
        logger.info("=== Running tempest ==")
        director_vm = Director()
        director_vm.run_tempest()
    else:
        logger.debug("not running tempest")


def deploy():
    ret_code = 0
    # noinspection PyBroadException
    try:

        logger.debug("=================================")
        logger.info("=== Starting up ...")
        logger.debug("=================================")

        parser = argparse.ArgumentParser(
            description='JetPack 10.x deployer')
        parser.add_argument('-s', '--settings',
                            help='ini settings file, e.g settings/acme.ini',
                            required=True)
        parser.add_argument('-undercloud_only', '--undercloud_only',
                            help='Only reinstall the undercloud',
                            action='store_true', required=False)
        parser.add_argument('-overcloud_only', '--overcloud_only',
                            help='Only reinstall the overcloud',
                            action='store_true', required=False)
        parser.add_argument('-skip_rhscon_vm', '--skip_rhscon_vm',
                            help='Do not reinstall the Storage Console VM',
                            action='store_true',
                            required=False)
        parser.add_argument('-validate_only', '--validate_only',
                            help='No deployment - just validate config values',
                            action='store_true',
                            required=False)
        args, ignore = parser.parse_known_args()

        if args.validate_only is True:
            logger.info("Only validating ini/properties config values")
        else:
            if args.overcloud_only is True:
                logger.info("Only redeploying the overcloud")
            if args.skip_rhscon_vm is True:
                logger.info("Skipping Storage Console VM install")

        logger.debug("loading settings files " + args.settings)
        settings = Settings(args.settings)
        logger.info("Settings .ini: " + settings.settings_file)
        logger.info("Settings .properties " + settings.network_conf)
        settings.get_version_info()
        logger.info("source version # : " + settings.source_version)
        director_vm = Director()
        director_vm.update_hostsfiles()

    except:
        logger.error(traceback.format_exc())
        e = sys.exc_info()[0]
        logger.error(e)
        print e
        print traceback.format_exc()
        ret_code = 1
    logger.info("log : /auto_results/ ")
    sys.exit(ret_code)


if __name__ == "__main__":
    setup_logging()
    deploy()
