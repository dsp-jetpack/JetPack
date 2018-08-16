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

_DRAC_BOOT_MODES = ['Bios', 'Uefi']


class BootModeHelper(object):
    path = os.path.basename(sys.argv[0])[0]
    LOG = logging.getLogger(os.path.splitext(path)[0])

    def is_boot_order_flexibly_programmable(drac_client, bios_settings=None):
        if not bios_settings:
            bios_settings = drac_client.list_bios_settings()
        return 'SetBootOrderFqdd1' in bios_settings

    def determine_boot_mode(drac_client, node):
        bios_settings = drac_client.list_bios_settings(by_name=True)
        if is_boot_order_flexibly_programmable(drac_client, bios_settings):
            drac_boot_mode = bios_settings['BootMode'].current_value
            if drac_boot_mode not in _DRAC_BOOT_MODES:
                message = "DRAC reported unknown boot mode "" \
                ""{}".format(drac_boot_mode)

                raise BootModeHelper.LOG.error(message)

            return drac_boot_mode
