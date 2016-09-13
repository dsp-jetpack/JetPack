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
from osp_deployer.settings.config import Settings
from osp_deployer.sah import Sah

logger = logging.getLogger("osp_deployer")


def setup_networking():
    try:

        logger.debug("=================================")
        logger.info("=== Setting up  ...")
        logger.debug("=================================")

        parser = argparse.ArgumentParser(description='Jetstream 5.x deployer')
        parser.add_argument('-s', '--settings',
                            help='ini settings file, e.g settings/acme.ini',
                            required=True)
        args, ignore = parser.parse_known_args()

        logger.debug("loading settings files " + args.settings)
        settings = Settings(args.settings)
        logger.info("Settings .ini: " + settings.settings_file)
        logger.info("Settings .properties " + settings.network_conf)

        # Check to verify ~/JetStream/rhel72.iso exists
        assert os.path.isfile("/root/JetStream/rhel72.iso"), "~/JetStream/\
                              rhel72.iso file is not present"

        sah = Sah()
        sah.update_kickstart_usb()

        # Create the usb Media & update path references
        # Create the usb image (todo move to script ?)

        current_path = subprocess.check_output("cd ~;pwd",
                                               stderr=subprocess.STDOUT,
                                               shell=True).strip()
        target_ini = settings.settings_file.replace(current_path, "/mnt/usb")
        cmds = ['cd ~;rm -f osp_ks.img',
                'cd ~;dd if=/dev/zero of=osp_ks.img bs=1M count=5000',
                'cd ~;mkfs ext3 -F osp_ks.img',
                'mkdir -p /mnt/usb',
                'cd ~;mount -o loop osp_ks.img /mnt/usb',
                'cd ~;cp -R ~/JetStream /mnt/usb',
                "sed -i 's|" + current_path + "|/root|' " + target_ini,
                'sync; umount /mnt/usb']
        for cmd in cmds:
            print "> " + cmd
            print subprocess.check_output(cmd,
                                          stderr=subprocess.STDOUT,
                                          shell=True)

        # TODO: copy custom overcloud image if applicable
        # ? do we still want to support this ?

        print "All done - please attach ~/osp_ks.img to the node & continue \
        with the setup.... "

    except:
        logger.error(traceback.format_exc())
        e = sys.exc_info()[0]
        logger.error(e)
        print e
        print traceback.format_exc()
    logger.info("log : /auto_results/ ")


if __name__ == "__main__":
    setup_networking()
    #####
