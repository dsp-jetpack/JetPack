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

from . import uris
from .. import utils_additional
from dracclient import utils
from dracclient import wsman

LOG = logging.getLogger(__name__)


class iDRACCardConfiguration(object):

    def __init__(self, client):
        """Creates iDRACCardManagement object

        :param client: an instance of WSManClient
        """
        self.client = client

    def list_idrac_settings(self, by_name=True):
        """List the iDRACCard configuration settings

        :param by_name: Controls whether returned dictionary uses iDRAC
                        attribute name or instance_id as key.
        :returns: a dictionary with the iDRACCard settings using its name as
                  the key. The attributes are either
                  iDRACCardEnumerableAttribute, iDRACCardStringAttribute
                  or iDRACCardIntegerAttribute objects.
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the DRAC
                 interface
        """
        result = {}
        namespaces = [(uris.DCIM_iDRACCardEnumeration,
                       iDRACCardEnumerableAttribute),
                      (uris.DCIM_iDRACCardString, iDRACCardStringAttribute),
                      (uris.DCIM_iDRACCardInteger, iDRACCardIntegerAttribute)]
        for (namespace, attr_cls) in namespaces:
            attribs = self._get_config(namespace, attr_cls, by_name)
            result.update(attribs)
        return result

    def _get_config(self, resource, attr_cls, by_name):
        result = {}
        doc = self.client.enumerate(resource)

        items = doc.find('.//{%s}Items' % wsman.NS_WSMAN)

        if items is not None:
            for item in items:
                attribute = attr_cls.parse(item)
                if by_name:
                    # Attribute names are made unique by prefixing them
                    # with "group_id#"
                    name = "{}#{}".format(attribute.group_id, attribute.name)
                    result[name] = attribute
                else:
                    result[attribute.instance_id] = attribute
        return result

    def set_idrac_settings(self, idrac_fqdd, new_settings):
        """Set the iDRACCard configuration settings

        To be more precise, it sets the pending_value parameter for each of the
        attributes passed in. For the values to be applied, a config job must
        be created and the node must be rebooted.

        :param idrac_fqdd: the FQDD of the iDRAC.
        :param new_settings: a dictionary containing the proposed values, with
                             each key being the name of attribute and the
                             value being the proposed value.
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
        return utils_additional.set_settings(self.client,
                                             self.list_idrac_settings,
                                             new_settings,
                                             uris.DCIM_iDRACCardService,
                                             "DCIM_iDRACCardService",
                                             "DCIM:iDRACCardService",
                                             idrac_fqdd)

    def reset_idrac(self, force=False):
        """Resets the iDRAC

        :param force: does a force reset when True and a graceful reset when
               False.
        :returns: True on success and False on failure.
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        selectors = {'CreationClassName': "DCIM_iDRACCardService",
                     'Name': "DCIM:iDRACCardService",
                     'SystemCreationClassName': 'DCIM_ComputerSystem',
                     'SystemName': 'DCIM:ComputerSystem'}

        properties = {'Force': "1" if force else "0"}

        doc = self.client.invoke(uris.DCIM_iDRACCardService,
                                 'iDRACReset',
                                 selectors,
                                 properties,
                                 check_return_value=False)

        message_id = utils.find_xml(doc,
                                      'MessageID',
                                      uris.DCIM_iDRACCardService).text
        return "RAC064" == message_id


class iDRACCardAttribute(object):
    """Generic iDRACCard attribute class"""

    def __init__(self, name, instance_id, current_value, pending_value,
                 read_only, fqdd, group_id):
        """Creates iDRACCardAttribute object

        :param name: name of the iDRACCard attribute
        :param instance_id: InstanceID of the iDRACCard attribute
        :param current_value: current value of the iDRACCard attribute
        :param pending_value: pending value of the iDRACCard attribute,
                reflecting an unprocessed change (eg. config job not completed)
        :param read_only: indicates whether this iDRACCard attribute can be
                changed
        :param fqdd: Fully Qualified Device Description of the iDRACCard
                Attribute
        :param group_id: GroupID of the iDRACCard Attribute
        """
        self.name = name
        self.instance_id = instance_id
        self.current_value = current_value
        self.pending_value = pending_value
        self.read_only = read_only
        self.fqdd = fqdd
        self.group_id = group_id

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @classmethod
    def parse(cls, namespace, idrac_attr_xml):
        """Parses XML and creates iDRACCardAttribute object"""

        name = utils.get_wsman_resource_attr(
            idrac_attr_xml, namespace, 'AttributeName')
        instance_id = utils.get_wsman_resource_attr(
            idrac_attr_xml, namespace, 'InstanceID')
        current_value = utils.get_wsman_resource_attr(
            idrac_attr_xml, namespace, 'CurrentValue', nullable=True)
        pending_value = utils.get_wsman_resource_attr(
            idrac_attr_xml, namespace, 'PendingValue', nullable=True)
        read_only = utils.get_wsman_resource_attr(
            idrac_attr_xml, namespace, 'IsReadOnly').lower()
        fqdd = utils.get_wsman_resource_attr(
            idrac_attr_xml, namespace, 'FQDD')
        group_id = utils.get_wsman_resource_attr(
            idrac_attr_xml, namespace, 'GroupID')

        return cls(name, instance_id, current_value, pending_value,
                   (read_only == 'true'), fqdd, group_id)


class iDRACCardEnumerableAttribute(iDRACCardAttribute):
    """Enumerable iDRACCard attribute class"""

    namespace = uris.DCIM_iDRACCardEnumeration

    def __init__(self, name, instance_id, current_value, pending_value,
                 read_only, fqdd, group_id, possible_values):
        """Creates iDRACCardEnumerableAttribute object

        :param name: name of the iDRACCard attribute
        :param instance_id: InstanceID of the iDRACCard attribute
        :param current_value: current value of the iDRACCard attribute
        :param pending_value: pending value of the iDRACCard attribute,
                reflecting an unprocessed change (eg. config job not completed)
        :param read_only: indicates whether this iDRACCard attribute can be
                changed
        :param fqdd: Fully Qualified Device Description of the iDRACCard
                Attribute
        :param group_id: GroupID of the iDRACCard Attribute
        :param possible_values: list containing the allowed values for the
                                iDRACCard attribute
        """
        super(iDRACCardEnumerableAttribute, self).__init__(name, instance_id,
                                                           current_value,
                                                           pending_value,
                                                           read_only, fqdd,
                                                           group_id)
        self.possible_values = possible_values

    @classmethod
    def parse(cls, idrac_attr_xml):
        """Parses XML and creates iDRACCardEnumerableAttribute object"""

        idrac_attr = iDRACCardAttribute.parse(cls.namespace, idrac_attr_xml)
        possible_values = [attr.text for attr
                           in utils.find_xml(idrac_attr_xml, 'PossibleValues',
                                             cls.namespace, find_all=True)]

        return cls(idrac_attr.name, idrac_attr.instance_id,
                   idrac_attr.current_value, idrac_attr.pending_value,
                   idrac_attr.read_only, idrac_attr.fqdd, idrac_attr.group_id,
                   possible_values)

    def validate(self, new_value):
        """Validates new value"""

        if str(new_value) not in self.possible_values:
            msg = ("Attribute '%(attr)s' cannot be set to value '%(val)s'."
                   " It must be in %(possible_values)r.") % {
                       'attr': self.name,
                       'val': new_value,
                       'possible_values': self.possible_values}
            return msg


class iDRACCardStringAttribute(iDRACCardAttribute):
    """String iDRACCard attribute class"""

    namespace = uris.DCIM_iDRACCardString

    def __init__(self, name, instance_id, current_value, pending_value,
                 read_only, fqdd, group_id, min_length, max_length):
        """Creates iDRACCardStringAttribute object

        :param name: name of the iDRACCard attribute
        :param instance_id: InstanceID of the iDRACCard attribute
        :param current_value: current value of the iDRACCard attribute
        :param pending_value: pending value of the iDRACCard attribute,
                reflecting an unprocessed change (eg. config job not completed)
        :param read_only: indicates whether this iDRACCard attribute can be
                changed
        :param fqdd: Fully Qualified Device Description of the iDRACCard
                Attribute
        :param group_id: GroupID of the iDRACCard Attribute
        :param min_length: minimum length of the string
        :param max_length: maximum length of the string
        """
        super(iDRACCardStringAttribute, self).__init__(name, instance_id,
                                                       current_value,
                                                       pending_value,
                                                       read_only, fqdd,
                                                       group_id)
        self.min_length = min_length
        self.max_length = max_length

    @classmethod
    def parse(cls, idrac_attr_xml):
        """Parses XML and creates iDRACCardStringAttribute object"""

        idrac_attr = iDRACCardAttribute.parse(cls.namespace, idrac_attr_xml)
        min_length = int(utils.get_wsman_resource_attr(
            idrac_attr_xml, cls.namespace, 'MinLength'))
        max_length = int(utils.get_wsman_resource_attr(
            idrac_attr_xml, cls.namespace, 'MaxLength'))

        return cls(idrac_attr.name, idrac_attr.instance_id,
                   idrac_attr.current_value, idrac_attr.pending_value,
                   idrac_attr.read_only, idrac_attr.fqdd, idrac_attr.group_id,
                   min_length, max_length)

    def validate(self, new_value):
        """Validates new value"""

        val_len = len(new_value)
        if val_len < self.min_length or val_len > self.max_length:
            msg = ('Attribute %(attr)s cannot be set to value %(val)d. It '
                   'must have a length between %(lower)d and %(upper)d.') % {
                       'attr': self.name,
                       'val': new_value,
                       'lower': self.min_length,
                       'upper': self.max_length}
            return msg


class iDRACCardIntegerAttribute(iDRACCardAttribute):
    """Integer iDRACCard attribute class"""

    namespace = uris.DCIM_iDRACCardInteger

    def __init__(self, name, instance_id, current_value, pending_value,
                 read_only, fqdd, group_id, lower_bound, upper_bound):
        """Creates iDRACCardIntegerAttribute object

        :param name: name of the iDRACCard attribute
        :param instance_id: InstanceID of the iDRACCard attribute
        :param current_value: current value of the iDRACCard attribute
        :param pending_value: pending value of the iDRACCard attribute,
                reflecting an unprocessed change (eg. config job not completed)
        :param read_only: indicates whether this iDRACCard attribute can be
                changed
        :param fqdd: Fully Qualified Device Description of the iDRACCard
                Attribute
        :param group_id: GroupID of the iDRACCard Attribute
        :param lower_bound: minimum value for the iDRACCard attribute
        :param upper_bound: maximum value for the iDRACCard attribute
        """
        super(iDRACCardIntegerAttribute, self).__init__(name, instance_id,
                                                        current_value,
                                                        pending_value,
                                                        read_only, fqdd,
                                                        group_id)
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    @classmethod
    def parse(cls, idrac_attr_xml):
        """Parses XML and creates iDRACCardIntegerAttribute object"""

        idrac_attr = iDRACCardAttribute.parse(cls.namespace, idrac_attr_xml)
        lower_bound = utils.get_wsman_resource_attr(
            idrac_attr_xml, cls.namespace, 'LowerBound')
        upper_bound = utils.get_wsman_resource_attr(
            idrac_attr_xml, cls.namespace, 'UpperBound')

        if idrac_attr.current_value:
            idrac_attr.current_value = int(idrac_attr.current_value)
        if idrac_attr.pending_value:
            idrac_attr.pending_value = int(idrac_attr.pending_value)

        return cls(idrac_attr.name, idrac_attr.instance_id,
                   idrac_attr.current_value, idrac_attr.pending_value,
                   idrac_attr.read_only, idrac_attr.fqdd, idrac_attr.group_id,
                   int(lower_bound), int(upper_bound))

    def validate(self, new_value):
        """Validates new value"""

        val = int(new_value)
        if val < self.lower_bound or val > self.upper_bound:
            msg = ('Attribute %(attr)s cannot be set to value %(val)d.'
                   ' It must be between %(lower)d and %(upper)d.') % {
                       'attr': self.name,
                       'val': new_value,
                       'lower': self.lower_bound,
                       'upper': self.upper_bound}
            return msg
