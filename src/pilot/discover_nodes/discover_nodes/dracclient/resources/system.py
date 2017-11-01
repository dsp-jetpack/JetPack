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

from __future__ import absolute_import
from __future__ import print_function

from dracclient import utils
from dracclient.resources import uris


class SystemManagement(object):

    def __init__(self, client):
        """Construct a SystemManagement object.

        :param client: an instance of WSManClient
        """
        self.client = client

    def get_system_id(self):
        """Return the system id.

        :returns: system model id
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        filter_query = ('select UUID '
                        'from DCIM_SystemView')
        doc = self.client.enumerate(uris.DCIM_SystemView,
                                    filter_query=filter_query)

        return utils.find_xml(doc, 'UUID', uris.DCIM_SystemView).text

    def get_system_model_name(self):
        """Return the system model name.

        :returns: system model name
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        filter_query = ('select Model '
                        'from DCIM_SystemView')
        doc = self.client.enumerate(uris.DCIM_SystemView,
                                    filter_query=filter_query)

        return utils.find_xml(doc, 'Model', uris.DCIM_SystemView).text

    def get_system_service_tag(self):
        """Return the system service tag.

        :returns: system service tag
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        filter_query = ('select ChassisServiceTag '
                        'from DCIM_SystemView')
        doc = self.client.enumerate(uris.DCIM_SystemView,
                                    filter_query=filter_query)

        return utils.find_xml(doc,
                              'ChassisServiceTag',
                              uris.DCIM_SystemView).text
