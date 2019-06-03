#!/usr/bin/python

# Copyright (c) 2018-2019 Dell Inc. or its subsidiaries.
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

from ironic.drivers.modules import deploy_utils

DRAC_BOOT_MODE_BIOS = 'Bios'
DRAC_BOOT_MODE_UEFI = 'Uefi'

DRAC_BOOT_MODE_TO_IRONIC_BOOT_MODE_CAP = {
    DRAC_BOOT_MODE_BIOS: deploy_utils.SUPPORTED_CAPABILITIES['boot_mode'][0],
    DRAC_BOOT_MODE_UEFI: deploy_utils.SUPPORTED_CAPABILITIES['boot_mode'][1]
}

IRONIC_BOOT_MODE_CAP_TO_DRAC_BOOT_MODE = \
    dict((v, k) for (k, v) in DRAC_BOOT_MODE_TO_IRONIC_BOOT_MODE_CAP.items())


class BootModeHelper(object):

    @staticmethod
    def is_boot_order_flexibly_programmable(drac_client, bios_settings=None):
        if not bios_settings:
            bios_settings = drac_client.list_bios_settings(by_name=True)
        return 'SetBootOrderFqdd1' in bios_settings

    @staticmethod
    def get_boot_mode(drac_client, bios_settings=None):
        if not bios_settings:
            bios_settings = drac_client.list_bios_settings(by_name=True)
        return bios_settings['BootMode'].current_value
