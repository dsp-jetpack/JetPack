# Copyright (c) 2016-2017 Dell Inc. or its subsidiaries.
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

import dracclient.resources.lifecycle_controller as ironic_lc
import dracclient.utils as utils

from . import uris


class LifecycleControllerManagement(ironic_lc.LifecycleControllerManagement):

    def is_idrac_ready(self):
        """Returns a boolean indicating if the iDRAC is ready to accept
        commands

        :returns: Boolean indicating iDRAC readiness
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the DRAC
                 interface
        :raises: DRACUnexpectedReturnValue on return value mismatch
        """

        selectors = {'SystemCreationClassName': 'DCIM_ComputerSystem',
                     'SystemName': 'DCIM:ComputerSystem',
                     'CreationClassName': 'DCIM_LCService',
                     'Name': 'DCIM:LCService'}

        result = self.client.invoke(uris.DCIM_LCService,
                                    'GetRemoteServicesAPIStatus',
                                    selectors,
                                    {},
                                    expected_return_value=utils.RET_SUCCESS)

        is_ready = False
        message_id = utils.find_xml(result,
                                    'MessageID',
                                    uris.DCIM_LCService).text
        if message_id == "LC061":
            is_ready = True

        return is_ready
