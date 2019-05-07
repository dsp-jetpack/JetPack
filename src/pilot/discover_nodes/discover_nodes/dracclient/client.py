# Copyright (c) 2016-2019 Dell Inc. or its subsidiaries.
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

"""
Wrapper for pywsman.Client
"""

from __future__ import absolute_import
from __future__ import print_function

import dracclient.client as ironic_client
import dracclient.resources.uris as ironic_uris

import logging

from .resources import uris
LOG = logging.getLogger(__name__)


class DRACClient(ironic_client.DRACClient):
    """Manage a Dell Integrated Dell Remote Access Controller (iDRAC).
    """

    def __init__(self,
                 host,
                 username,
                 password,
                 port=443,
                 path='/wsman',
                 protocol='https'):
        """Construct a DRACClient object.

        :param host: hostname or IP of the iDRAC interface
        :param username: username for accessing the iDRAC interface
        :param password: password for accessing the iDRAC interface
        :param port: port for accessing the iDRAC interface
        :param path: path for accessing the iDRAC interface
        :param protocol: protocol for accessing the iDRAC interface
        """
        super(DRACClient, self).__init__(host,
                                         username,
                                         password,
                                         port,
                                         path,
                                         protocol)

    def commit_pending_idrac_changes(
            self,
            idrac_fqdd='iDRAC.Embedded.1',
            reboot=False,
            start_time='TIME_NOW'):
        """Creates a configuration job for applying all pending changes to an
        iDRAC.

        :param idrac_fqdd: the FQDD of the iDRAC.
        :param reboot: indication of whether to also create a reboot job
        :param start_time: start time for job execution in format
                           yyyymmddhhmmss; the string 'TIME_NOW' means
                           immediately and None means unspecified
        :returns: id of the created configuration job
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: DRACUnexpectedReturnValue on return value mismatch
        """
        return self._job_mgmt.create_config_job(
            resource_uri=uris.DCIM_iDRACCardService,
            cim_creation_class_name='DCIM_iDRACCardService',
            cim_name='DCIM:iDRACCardService',
            target=idrac_fqdd,
            reboot=reboot,
            start_time=start_time)

    def abandon_pending_idrac_changes(self, idrac_fqdd):
        """Abandon all pending changes to a NIC.

        :param idrac_fqdd: the FQDD of the iDRAC.
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: DRACUnexpectedReturnValue on return value mismatch
        """
        self._job_mgmt.delete_pending_config(
            resource_uri=uris.DCIM_iDRACCardService,
            cim_creation_class_name='DCIM_iDRACCardService',
            cim_name='DCIM:iDRACCardService',
            target=idrac_fqdd)

    def commit_pending_bios_changes(self, reboot=False, start_time='TIME_NOW'):
        """Applies all pending changes on the BIOS by creating a config job

        :param reboot: indicates whether a RebootJob should also be
                       created or not
        :param start_time: start time for job execution in format
                           yyyymmddhhmmss; the string 'TIME_NOW' means
                           immediately and None means unspecified
        :returns: id of the created job
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the DRAC
                 interface
        :raises: DRACUnexpectedReturnValue on return value mismatch
        """
        return self._job_mgmt.create_config_job(
            resource_uri=ironic_uris.DCIM_BIOSService,
            cim_creation_class_name='DCIM_BIOSService',
            cim_name='DCIM:BIOSService',
            target=self.BIOS_DEVICE_FQDD,
            reboot=reboot,
            start_time=start_time)

    def abandon_pending_nic_changes(self, nic_id):
        """Abandon all pending changes to a NIC.

        :param nic_id: id of the network interface controller (NIC)
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: DRACUnexpectedReturnValue on return value mismatch
        """
        self._job_mgmt.delete_pending_config(
            resource_uri=uris.DCIM_NICService,
            cim_creation_class_name='DCIM_NICService',
            cim_name='DCIM:NICService',
            target=nic_id)

    def commit_pending_nic_changes(self, nic_id, reboot=False):
        """Apply all pending changes to a NIC by creating a configuration job.

        :param nic_id: id of the network interface controller (NIC)
        :param reboot: indication of whether to also create a reboot job
        :returns: id of the created configuration job
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: DRACUnexpectedReturnValue on return value mismatch
        """
        return self._job_mgmt.create_config_job(
            resource_uri=uris.DCIM_NICService,
            cim_creation_class_name='DCIM_NICService',
            cim_name='DCIM:NICService',
            target=nic_id,
            reboot=reboot)

    def create_nic_config_job(
            self,
            nic_id,
            reboot=False,
            start_time='TIME_NOW'):
        """Creates a configuration job for applying all pending changes to a
        NIC.

        :param nic_id: id of the network interface controller (NIC)
        :param reboot: indication of whether to also create a reboot job
        :param start_time: start time for job execution in format
                           yyyymmddhhmmss; the string 'TIME_NOW' means
                           immediately and None means unspecified
        :returns: id of the created configuration job
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: DRACUnexpectedReturnValue on return value mismatch
        """
        return self._job_mgmt.create_config_job(
            resource_uri=uris.DCIM_NICService,
            cim_creation_class_name='DCIM_NICService',
            cim_name='DCIM:NICService',
            target=nic_id,
            reboot=reboot,
            start_time=start_time)
