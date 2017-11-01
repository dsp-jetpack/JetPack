#!/usr/bin/python

# Copyright (c) 2017 Dell Inc. or its subsidiaries.
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

from dracclient import exceptions
from dracclient import utils


LOG = logging.getLogger(__name__)


def set_settings(client,
                 list_settings,
                 new_settings,
                 resource_uri,
                 cim_creation_class_name,
                 cim_name,
                 target):
    current_settings = list_settings()

    unknown_keys = set(new_settings) - set(current_settings)
    if unknown_keys:
        msg = ('Unknown attributes found: %(unknown_keys)r' %
               {'unknown_keys': unknown_keys})
        raise exceptions.InvalidParameterValue(reason=msg)

    read_only_keys = []
    unchanged_attribs = []
    invalid_attribs_msgs = []
    attrib_names = []
    candidates = set(new_settings)

    for attr in candidates:
        if str(new_settings[attr]) == str(
                current_settings[attr].current_value):
            unchanged_attribs.append(attr)
        elif current_settings[attr].read_only:
            read_only_keys.append(attr)
        else:
            validation_msg = current_settings[attr].validate(
                new_settings[attr])
            if validation_msg:
                invalid_attribs_msgs.append(validation_msg)
            else:
                attrib_names.append(attr)

    if unchanged_attribs:
        LOG.debug('Ignoring unchanged attributes: %r', unchanged_attribs)

    if invalid_attribs_msgs or read_only_keys:
        if read_only_keys:
            read_only_msg = ['Cannot set read-only attributes: %r.'
                             % read_only_keys]
        else:
            read_only_msg = []

        drac_messages = '\n'.join(invalid_attribs_msgs + read_only_msg)
        raise exceptions.DRACOperationFailed(
            drac_messages=drac_messages)

    if not attrib_names:
        return {'commit_required': False,
                'reboot_required': False}

    selectors = {'CreationClassName': cim_creation_class_name,
                 'Name': cim_name,
                 'SystemCreationClassName': 'DCIM_ComputerSystem',
                 'SystemName': 'DCIM:ComputerSystem'}
    properties = {'Target': target,
                  'AttributeName': attrib_names,
                  'AttributeValue': [new_settings[attr] for attr
                                     in attrib_names]}
    doc = client.invoke(resource_uri, 'SetAttributes',
                        selectors, properties)

    return {'commit_required': is_commit_required(
        doc, resource_uri),
            'reboot_required': utils.is_reboot_required(
        doc, resource_uri)}


def is_commit_required(doc, resource_uri):
    """Check the response document if commit is required.

    RebootRequired attribute in the response indicates whether a config job
    needs to be created and the node needs to be rebooted, so that the
    Lifecycle controller can commit the pending changes.

    :param doc: the element tree object.
    :param resource_uri: the resource URI of the namespace.
    :returns: a boolean value indicating commit is required or not.
    """

    commit_required = utils.find_xml(doc, 'SetResult', resource_uri)
    return "pending" in commit_required.text.lower()
