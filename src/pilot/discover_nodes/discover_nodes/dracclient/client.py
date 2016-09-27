# Copyright (c) 2016 Dell Inc. or its subsidiaries.
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

from .resources import nic
from .resources import uris
# import discover_nodes.dracclient.resources.nic as nic

LINK_SPEED_UNKNOWN = nic.LINK_SPEED_UNKNOWN
LINK_SPEED_10_MBPS = nic.LINK_SPEED_10_MBPS
LINK_SPEED_100_MBPS = nic.LINK_SPEED_100_MBPS
LINK_SPEED_1_GBPS = nic.LINK_SPEED_1_GBPS
LINK_SPEED_2_5_GBPS = nic.LINK_SPEED_2_5_GBPS
LINK_SPEED_10_GBPS = nic.LINK_SPEED_10_GBPS
LINK_SPEED_20_GBPS = nic.LINK_SPEED_20_GBPS
LINK_SPEED_25_GBPS = nic.LINK_SPEED_25_GBPS
LINK_SPEED_40_GBPS = nic.LINK_SPEED_40_GBPS
LINK_SPEED_50_GBPS = nic.LINK_SPEED_50_GBPS
LINK_SPEED_100_GBPS = nic.LINK_SPEED_100_GBPS


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
        self._nic_cfg = nic.NICConfiguration(self.client)
        self._nic_mgmt = nic.NICManagement(self.client)

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

    def get_nic_legacy_boot_protocol(self, nic_id):
        """Obtain the legacy, non-UEFI, boot protocol of a NIC.

        :param nic_id: id of the network interface controller (NIC)
        :returns: legacy boot protocol
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        """
        return self._nic_cfg.get_nic_legacy_boot_protocol(nic_id)

    def get_nic_link_status(self, nic_id):
        """Obtain the link status, up or down, of a NIC.

        :param nic_id: id of the network interface controller (NIC)
        :returns: link status
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        """
        return self._nic_mgmt.get_nic_link_status(nic_id)

    def get_nic_setting(self, nic_id, attribute_name):
        """Obtain a setting of a NIC.

        :param nic_id: id of the network interface controller (NIC)
        :param attribute_name: name of the setting
        :returns: value of the attribute
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        """
        return self._nic_cfg.get_nic_setting(nic_id, attribute_name)

    def get_nic_statistics(self, nic_id):
        """Obtain the statistics of a NIC.

        :param nic_id: id of the network interface controller (NIC)
        :returns: NICStatistics object
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        return self._nic_mgmt.get_nic_statistics(nic_id)

    def is_nic_legacy_boot_protocol_pxe(self, nic_id):
        """Return true if the legacy, non-UEFI, boot protocol of a NIC is PXE,
           false otherwise.

        :param nic_id: id of the network interface controller (NIC)
        :returns: boolean indicating whether or not the legacy,
                  non-UEFI, boot protocol is PXE
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        """
        return self._nic_cfg.is_nic_legacy_boot_protocol_pxe(nic_id)

    def is_nic_link_up(self, nic_id):
        """Return true if the link status of a NIC is up, false otherwise.

        :param nic_id: id of the network interface controller (NIC)
        :returns: boolean indicating whether or not the link is up
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        return self._nic_mgmt.is_nic_link_up(nic_id)

    def list_integrated_nics(self, sort=False):
        """Return the list of integrated NICs.

        :param sort: indication of whether to sort the returned list by
                     network interface controller (NIC) id
        :returns: list of NIC objects for the integrated NICs
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        return self._nic_mgmt.list_integrated_nics(sort)

    def list_nic_settings(self, nic_id):
        """Return the list of attribute settings of a NIC.

        :param nic_id: id of the network interface controller (NIC)
        :returns: dictionary containing the NIC settings. The keys are
                  attribute names. Each value is a
                  NICEnumerationAttribute, NICIntegerAttribute, or
                  NICStringAttribute object.
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        """
        return self._nic_cfg.list_nic_settings(nic_id)

    def list_nics(self, sort=False):
        """Return the list of NICs.

        :param sort: indication of whether to sort the returned list by
                     network interface controller (NIC) id
        :returns: list of NIC objects
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        return self._nic_mgmt.list_nics(sort)

    def set_nic_legacy_boot_protocol(self, nic_id, value):
        """Set the legacy, non-UEFI, boot protocol of a NIC.

        If successful, the pending value of the NIC's legacy boot
        protocol attribute is set. For the new value to be applied, a
        configuration job must be created and the node must be rebooted.

        :param nic_id: id of the network interface controller (NIC)
        :param value: legacy boot protocol
        :returns: dictionary containing a 'commit_required' key with a
                  boolean value indicating whether a configuration job
                  must be created for the new legacy boot protocol
                  setting to be applied
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        """
        return self._nic_cfg.set_nic_legacy_boot_protocol(nic_id, value)

    def set_nic_legacy_boot_protocol_pxe(self, nic_id):
        """Set the legacy, non-UEFI, boot protocol of a NIC to PXE.

        If successful, the pending value of the NIC's legacy boot
        protocol attribute is set. For the new value to be applied, a
        configuration job must be created and the node must be rebooted.

        :param nic_id: id of the network interface controller (NIC)
        :returns: dictionary containing a 'commit_required' key with a
                  boolean value indicating whether a configuration job
                  must be created for the new legacy boot protocol
                  setting to be applied
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        """
        return self._nic_cfg.set_nic_legacy_boot_protocol(nic_id, 'PXE')

    def set_nic_setting(self, nic_id, attribute_name, value):
        """Modify a setting of a NIC.

        If successful, the pending value of the attribute is set. For
        the new value to be applied, a configuration job must be created
        and the node must be rebooted.

        :param nic_id: id of the network interface controller (NIC)
        :param attribute_name: name of the setting
        :param value: value of the attribute
        :returns: dictionary containing a 'commit_required' key with a
                  boolean value indicating whether a configuration job
                  must be created for the new setting to be applied
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: InvalidParameterValue on invalid NIC attribute
        """
        return self._nic_cfg.set_nic_setting(nic_id, attribute_name, value)

    def set_nic_settings(self, nic_id, settings):
        """Modify one or more settings of a NIC.

        If successful, the pending values of the attributes are set. For
        the new values to be applied, a configuration job must be
        created and the node must be rebooted.

        :param nic_id: id of the network interface controller (NIC)
        :param settings: dictionary containing the proposed values, with
                         each key being the name of an attribute and the
                         value being the proposed value
        :returns: dictionary containing a 'commit_required' key with a
                  boolean value indicating whether a configuration job
                  must be created for the new settings to be applied
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: InvalidParameterValue on invalid NIC attribute
        """
        return self._nic_cfg.set_nic_settings(nic_id, settings)
