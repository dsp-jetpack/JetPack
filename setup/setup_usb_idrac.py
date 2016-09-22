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
        hdlr = logging.FileHandler('setup_usb_idrac.log')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)
        logger.setLevel(logging.DEBUG)
        out = logging.StreamHandler(sys.stdout)
        out.setLevel(logging.INFO)
        logger.addHandler(out)
        logger.info("* Creating the SAH node usb image.")
        parser = argparse.ArgumentParser(description='Jetstream 6.x usb ' +
                                                     ' image  prep.')
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
            logger.debug("running " + cmd)
            logger.debug(subprocess.check_output(cmd,
                                                 stderr=subprocess.STDOUT,
                                                 shell=True))

        logger.info("All done - attach ~/osp_ks.img to the sah node" +
                    " & continue with the deployment ...")

    except:
        logger.error(traceback.format_exc())
        e = sys.exc_info()[0]
        logger.error(e)
        print e
        print traceback.format_exc()


if __name__ == "__main__":
    setup_networking()
