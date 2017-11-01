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

from __future__ import absolute_import
from __future__ import print_function

import dracclient.exceptions as exceptions
import dracclient.resources.job as ironic_job
import dracclient.utils as utils
import dracclient.wsman as wsman

from . import uris

REBOOT_TYPES = {
    'power_cycle': '1',
    'graceful_reboot_without_forced_shutdown': '2',
    'graceful_reboot_with_forced_shutdown': '3',
}


class JobManagement(ironic_job.JobManagement):

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

        selectors = {'SystemCreationClassName': cim_system_creation_class_name,
                     'SystemName': cim_system_name,
                     'CreationClassName': cim_creation_class_name,
                     'Name': cim_name}

        properties = {'Target': target}

        if reboot:
            properties['RebootJobType'] = '3'

        if start_time is not None:
            properties['ScheduledStartTime'] = start_time

        doc = self.client.invoke(resource_uri,
                                 'CreateTargetedConfigJob',
                                 selectors, properties,
                                 expected_return_value=utils.RET_CREATED)

        return self._get_job_id(doc)

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

        try:
            drac_reboot_type = REBOOT_TYPES[reboot_type]
        except KeyError:
            msg = ("'%(reboot_type)s' is not supported. "
                   "Supported reboot types: %(supported_reboot_types)r") % {
                       'reboot_type': reboot_type,
                       'supported_reboot_types': list(REBOOT_TYPES)}
            raise exceptions.InvalidParameterValue(reason=msg)

        selectors = {'SystemCreationClassName': 'DCIM_ComputerSystem',
                     'SystemName': 'idrac',
                     'CreationClassName': 'DCIM_JobService',
                     'Name': 'JobService'}

        properties = {'RebootJobType': drac_reboot_type}

        doc = self.client.invoke(uris.DCIM_JobService,
                                 'CreateRebootJob',
                                 selectors,
                                 properties,
                                 expected_return_value=utils.RET_CREATED)

        return self._get_job_id(doc)

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

        # If the list of job identifiers is empty, there is nothing to do.
        if not job_ids:
            return

        selectors = {'SystemCreationClassName': 'DCIM_ComputerSystem',
                     'SystemName': 'idrac',
                     'CreationClassName': 'DCIM_JobService',
                     'Name': 'JobService'}

        properties = {'JobArray': job_ids,
                      'StartTimeInterval': start_time}

        self.client.invoke(uris.DCIM_JobService,
                           'SetupJobQueue',
                           selectors,
                           properties,
                           expected_return_value=utils.RET_SUCCESS)

    def _get_job_id(self, doc):
        query = (
            './/{%(namespace)s}%(item)s[@%(attribute_name)s='
            '"%(attribute_value)s"]' % {
                'namespace': wsman.NS_WSMAN,
                'item': 'Selector',
                'attribute_name': 'Name',
                'attribute_value': 'InstanceID'})
        job_id = doc.find(query).text
        return job_id

    def delete_jobs(self, job_ids=['JID_CLEARALL_FORCE']):
        """Deletes the given jobs.  If no jobs are given, all jobs are
            deleted.

        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: DRACUnexpectedReturnValue on non-success
        """
        selectors = {'SystemCreationClassName': 'DCIM_ComputerSystem',
                     'SystemName': 'idrac',
                     'CreationClassName': 'DCIM_JobService',
                     'Name': 'JobService'}

        for job_id in job_ids:
            properties = {'JobID': job_id}

            self.client.invoke(uris.DCIM_JobService,
                               'DeleteJobQueue',
                               selectors,
                               properties,
                               expected_return_value=utils.RET_SUCCESS)
