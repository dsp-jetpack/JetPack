#!/usr/bin/python

# Copyright (c) 2016-2018 Dell Inc. or its subsidiaries.
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

import logging
import os
import sys

from ironic.common import boot_devices

DRAC_BOOT_MODE_BIOS = 'Bios'
DRAC_BOOT_MODE_UEFI = 'Uefi'

DRAC_BOOT_MODES = {

}

# TODO(Update Ironic Boot Modes)
"""For Rocky release, boot modes are defined in boot_modes.py file,
When we upgrade to next version, we need to import ironic boot modes
instead of [boot_devices.BIOS and uefi]."""
DRAC_BOOT_MODES = {
    DRAC_BOOT_MODE_BIOS: boot_devices.BIOS,
    DRAC_BOOT_MODE_UEFI: "uefi"
}

IRONIC_BOOT_MODES = dict((v, k) for (k, v) in DRAC_BOOT_MODES.items())


class BootModeHelper(object):
    path = os.path.basename(sys.argv[0])[0]
    LOG = logging.getLogger(os.path.splitext(path)[0])

    @staticmethod
    def is_boot_order_flexibly_programmable(drac_client, bios_settings=None):
        if not bios_settings:
            bios_settings = drac_client.list_bios_settings()
        return 'SetBootOrderFqdd1' in bios_settings

    @staticmethod
    def determine_boot_mode(drac_client, bios_settings=None):
        bios_settings = drac_client.list_bios_settings(by_name=True)
        if is_boot_order_flexibly_programmable(drac_client, bios_settings):
            drac_boot_mode = bios_settings['BootMode'].current_value
            if drac_boot_mode not in [DRAC_BOOT_MODE_BIOS,
                                      DRAC_BOOT_MODE_UEFI]:
                message = "DRAC reported unknown boot mode "" \
                ""{}".format(drac_boot_mode)
                raise BootModeHelper.LOG.error(message)

            return drac_boot_mode
