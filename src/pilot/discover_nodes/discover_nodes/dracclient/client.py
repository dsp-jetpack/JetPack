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

"""
Wrapper for pywsman.Client
"""

from __future__ import absolute_import
from __future__ import print_function

import dracclient.client as ironic_client
import dracclient.resources.uris as ironic_uris

import logging
import os
import sys

from dracclient import exceptions
from time import sleep
from .resources import idrac_card
from .resources import job
from .resources import nic
from .resources import system
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
        self._job_mgmt = job.JobManagement(self.client)
        self._idrac_cfg = idrac_card.iDRACCardConfiguration(self.client)
        self._nic_cfg = nic.NICConfiguration(self.client)
        self._nic_mgmt = nic.NICManagement(self.client)

    def list_idrac_settings(self):
        """List the iDRAC configuration settings

        :returns: a dictionary with the iDRAC settings using its name as the
                  key. The attributes are either iDRACCArdEnumerableAttribute,
                  iDRACCardStringAttribute or iDRACCardIntegerAttribute
                  objects.
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the DRAC
                 interface
        """
        return self._idrac_cfg.list_idrac_settings()

    def set_idrac_settings(self, settings, idrac_fqdd='iDRAC.Embedded.1'):
        """Sets the iDRAC configuration settings

        To be more precise, it sets the pending_value parameter for each of the
        attributes passed in. For the values to be applied, a config job must
        be created and the node must be rebooted.

        :param settings: a dictionary containing the proposed values, with
                         each key being the name of attribute and the value
                         being the proposed value.
        :param idrac_fqdd: the FQDD of the iDRAC.
        :returns: a dictionary containing the commit_needed key with a boolean
                  value indicating whether a config job must be created for the
                  values to be applied.
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the DRAC
                 interface
        :raises: DRACUnexpectedReturnValue on return value mismatch
        :raises: InvalidParameterValue on invalid attribute
        """
        return self._idrac_cfg.set_idrac_settings(idrac_fqdd, settings)

    def reset_idrac(self, force=False):
        """Resets the iDRAC

        :param force: does a force reset when True and a graceful reset when
               False
        :returns: True on success and False on failure.
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        return self._idrac_cfg.reset_idrac(force)

    def wait_until_idrac_is_reset(self, force=False):
        """Resets the iDRAC and waits for it to become ready

        :param force: does a force reset when True and a graceful reset when
               False
        :returns: None.
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on failure to reset iDRAC
        """
        return_value = self.reset_idrac(force)

        if not return_value:
            LOG.debug("iDRAC failed to reset")
            raise exceptions.DRACOperationFailed(
                drac_messages="Failed to reset iDRAC")
        else:
            LOG.debug("iDRAC was successfully reset")

        LOG.info("Waiting for the iDRAC to become not pingable")
        retries = 24
        ping_fail_count = 0
        while retries > 0:
            response = os.system("ping -c 1 {} 2>&1 1>/dev/null".format(
                self.client.host))
            retries -= 1
            if response != 0:
                ping_fail_count += 1
                LOG.debug("The iDRAC is not pingable, ping_fail_count="
                          "{}".format(ping_fail_count))
                if ping_fail_count == 3:
                    LOG.debug("Breaking")
                    break
            else:
                ping_fail_count = 0
                LOG.debug("The iDRAC is pingable")

            sleep(10)

        if retries == 0 and ping_fail_count < 3:
            raise exceptions.DRACOperationFailed(drac_messages="Timed out "
                                                 "waiting for the iDRAC to "
                                                 "become not pingable")

        LOG.info("The iDRAC has become not pingable")

        LOG.info("Waiting for the iDRAC to become pingable")
        retries = 24
        ping_success_count = 0
        while retries > 0:
            response = os.system("ping -c 1 {} 2>&1 1>/dev/null".format(
                self.client.host))
            retries -= 1
            if response != 0:
                LOG.debug("The iDRAC is not pingable")
                ping_success_count = 0
            else:
                ping_success_count += 1
                LOG.debug("The iDRAC is pingable, ping_success_count="
                          "{}".format(ping_success_count))
                if ping_success_count == 3:
                    LOG.debug("Breaking")
                    break

            sleep(10)

        if retries == 0 and ping_success_count < 3:
            raise exceptions.DRACOperationFailed(drac_messages="Timed out "
                                                 "waiting for the iDRAC to "
                                                 "become pingable")

        LOG.info("The iDRAC has become pingable")
        sleep(30)

        LOG.info("Waiting for the iDRAC to become ready")
        retries = 24
        while retries > 0:
            try:
                is_ready = self.is_idrac_ready()
                if is_ready:
                    LOG.info("The iDRAC is ready")
                    break
                else:
                    LOG.debug("The iDRAC is not ready")
            except:
                # It is normal to get a series of connection errors before
                # the iDRAC becomes ready
                ex = sys.exc_info()[0]
                LOG.debug("An exception occurred while checking iDRAC ready "
                          "state. Ignoring.: {}".format(str(ex)))
                pass
            retries -= 1
            sleep(10)

        if retries == 0:
            raise exceptions.DRACOperationFailed(drac_messages="Timed out "
                                                 "waiting for the iDRAC to "
                                                 "become ready")

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

    def create_config_job(self,
                          resource_uri,
                          cim_creation_class_name,
                          cim_name,
                          target,
                          cim_system_creation_class_name='DCIM_ComputerSystem',
                          cim_system_name='DCIM:ComputerSystem',
                          reboot=False,
                          start_time='TIME_NOW'):
        """Creates a configuration job.

        In CIM (Common Information Model), weak association is used to name an
        instance of one class in the context of an instance of another class.
        SystemName and SystemCreationClassName are the attributes of the
        scoping system, while Name and CreationClassName are the attributes of
        the instance of the class, on which the CreateTargetedConfigJob method
        is invoked.

        :param resource_uri: URI of resource to invoke
        :param cim_creation_class_name: creation class name of the CIM object
        :param cim_name: name of the CIM object
        :param target: target device
        :param cim_system_creation_class_name: creation class name of the
                                               scoping system
        :param cim_system_name: name of the scoping system
        :param reboot: indicates whether or not a RebootJob should also be
                       created
        :param start_time: start time for job execution in format
                           yyyymmddhhmmss; the string 'TIME_NOW' means
                           immediately and None means unspecified
        :returns: id of the created job
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: DRACUnexpectedReturnValue on return value mismatch
        """
        return self._job_mgmt.create_config_job(
            resource_uri,
            cim_creation_class_name,
            cim_name,
            target,
            cim_system_creation_class_name,
            cim_system_name,
            reboot,
            start_time)

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

    def create_reboot_job(self,
                          reboot_type='graceful_reboot_with_forced_shutdown'):
        """Creates a reboot job.

        :param reboot_type: type of reboot
        :returns id of the created job
        :raises: InvalidParameterValue on invalid reboot type
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: DRACUnexpectedReturnValue on return value mismatch
        """
        return self._job_mgmt.create_reboot_job(reboot_type)

    def delete_jobs(self, job_ids=['JID_CLEARALL_FORCE']):
        """Deletes the given jobs.  If no jobs are given, all jobs are
            deleted.

        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: DRACUnexpectedReturnValue on non-success
        """
        return self._job_mgmt.delete_jobs(job_ids)

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

    def get_system_model_name(self):
        """Return the system model name.

        :returns: system model name
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        return system.SystemManagement(self.client).get_system_model_name()

    def get_system_service_tag(self):
        """Return the system service tag.

        :returns: system service tag
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        return system.SystemManagement(self.client).get_system_service_tag()

    def is_nic_legacy_boot_protocol_none(self, nic_id):
        """Return true if the legacy, non-UEFI, boot protocol of a NIC is NONE,
        false otherwise.

        :param nic_id: id of the network interface controller (NIC)
        :returns: boolean indicating whether or not the legacy,
                  non-UEFI, boot protocol is NONE
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        """
        return self._nic_cfg.is_nic_legacy_boot_protocol_none(nic_id)

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

    def schedule_job_execution(self, job_ids, start_time='TIME_NOW'):
        """Schedules jobs for execution in a specified order.

        :param job_ids: list of job identifiers
        :param start_time: start time for job execution in format
                           yyyymmddhhmmss; the string 'TIME_NOW' means
                           immediately
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: DRACUnexpectedReturnValue on return value mismatch
        """
        return self._job_mgmt.schedule_job_execution(job_ids, start_time)

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

    def set_nic_legacy_boot_protocol_none(self, nic_id):
        """Set the legacy, non-UEFI, boot protocol of a NIC to NONE.

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
        return self._nic_cfg.set_nic_legacy_boot_protocol(nic_id, 'NONE')

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

    def commit_pending_raid_changes(self, raid_controller, reboot=False,
                                    start_time='TIME_NOW'):
        """Applies all pending changes on a RAID controller

         ...by creating a config job.

        :param raid_controller: id of the RAID controller
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
            resource_uri=ironic_uris.DCIM_RAIDService,
            cim_creation_class_name='DCIM_RAIDService',
            cim_name='DCIM:RAIDService',
            target=raid_controller,
            reboot=reboot,
            start_time=start_time)
