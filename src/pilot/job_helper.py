#!/usr/bin/python

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

import logging
import os
import sys

from time import sleep


class JobHelper:
    LOG = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])

    @staticmethod
    def wait_for_job_completions(ironic_client, node_uuid):
        while ironic_client.node.vendor_passthru(
                node_uuid,
                'list_unfinished_jobs',
                http_method='GET').unfinished_jobs:
            sleep(10)

    @staticmethod
    def determine_job_outcomes(drac_client, job_ids):
        all_succeeded = True

        for job_id in job_ids:
            job_status = drac_client.get_job(job_id).status

            if JobHelper.job_succeeded(job_status):
                continue

            all_succeeded = False
            JobHelper.LOG.error(
                "Configuration job {} encountered issues; its final status is "
                "{}".format(job_id, job_status))

        return all_succeeded

    @staticmethod
    def job_succeeded(job_status):
        return job_status == 'Completed' or job_status == 'Reboot Completed'
