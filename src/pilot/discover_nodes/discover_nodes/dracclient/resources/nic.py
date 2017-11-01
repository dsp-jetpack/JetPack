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

import collections
import logging
import re

import dracclient.exceptions as ironic_exceptions
import dracclient.utils as utils
import dracclient.wsman as wsman

from .. import exceptions
from .. import utils_additional
from . import uris

LOG = logging.getLogger(__name__)

# Defining these constants to have the same value effectively disables
# retries of WS_Man Enumerate operation requests by
# NICManagement._list_nics_common(). This helps us more quickly iterate
# while working to identify the root cause of the bug that the retry
# behavior attempts to work around.
ENUMERATE_WITH_FILTER_ATTEMPTS_MIN = 1
ENUMERATE_WITH_FILTER_ATTEMPTS_MAX = 1

LINK_SPEED_UNKNOWN = 'unknown'
LINK_SPEED_10_MBPS = '10 Mbps'
LINK_SPEED_100_MBPS = '100 Mbps'
LINK_SPEED_1_GBPS = '1000 Mbps'
LINK_SPEED_2_5_GBPS = '2.5 Gbps'
LINK_SPEED_10_GBPS = '10 Gbps'
LINK_SPEED_20_GBPS = '20 Gbps'
LINK_SPEED_25_GBPS = '25 Gbps'
LINK_SPEED_40_GBPS = '40 Gbps'
LINK_SPEED_50_GBPS = '50 Gbps'
LINK_SPEED_100_GBPS = '100 Gbps'

LINK_SPEEDS = {
    '0': LINK_SPEED_UNKNOWN,
    '1': LINK_SPEED_10_MBPS,
    '2': LINK_SPEED_100_MBPS,
    '3': LINK_SPEED_1_GBPS,
    '4': LINK_SPEED_2_5_GBPS,
    '5': LINK_SPEED_10_GBPS,
    '6': LINK_SPEED_20_GBPS,
    '7': LINK_SPEED_40_GBPS,
    '8': LINK_SPEED_100_GBPS,
    '9': LINK_SPEED_25_GBPS,
    '10': LINK_SPEED_50_GBPS,
}

LINK_STATUSES = {
    '0': 'unknown',
    '1': 'up',
    '3': 'down',
}

NIC = collections.namedtuple(
    'NIC',
    ['id',
     'description',
     'manufacturer',
     'model',
     'firmware_version',
     'is_integrated',
     'mac_address',
     'link_speed'
     ])

NICStatistics = collections.namedtuple('NICStatistics', ['id', 'link_status'])


class NICManagement(object):
    """classdocs"""

    def __init__(self, client):
        """Construct a NICManagement object.

        :param client: an instance of WSManClient
        """
        self.client = client

    def get_nic_link_status(self, nic_id):
        """Obtain the link status, up or down, of a NIC.

        :param nic_id: id of the network interface controller (NIC)
        :returns: link status
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: NotFound when no statistics for NIC found
        """
        return self.get_nic_statistics(nic_id).link_status

    def get_nic_statistics(self, nic_id):
        """Obtain the statistics of a NIC.

        :param nic_id: id of the network interface controller (NIC)
        :returns: NICStatistics object on successful query, None
                  otherwise
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: NotFound when no statistics for NIC found
        """
        filter_query = ('select * '
                        'from DCIM_NICStatistics '
                        'where InstanceID = "%(fqdd)s"') % {'fqdd': nic_id}
        doc = self.client.enumerate(uris.DCIM_NICStatistics,
                                    filter_query=filter_query)

        drac_nic_statistics = utils.find_xml(doc,
                                             'DCIM_NICStatistics',
                                             uris.DCIM_NICStatistics)

        # Were no statistics found?
        if drac_nic_statistics is None:
            raise exceptions.NotFound(
                what=('statistics for NIC %(nic)s') % {
                    'nic': nic_id})

        return self._parse_drac_nic_statistics(drac_nic_statistics)

    def is_nic_link_up(self, nic_id):
        """Return true if the link status of a NIC is up, false otherwise.

        :param nic_id: id of the network interface controller (NIC)
        :returns: boolean indicating whether or not the link is up
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: NotFound when no statistics for NIC found
        """
        return self.get_nic_statistics(nic_id).link_status == 'up'

    def list_integrated_nics(self, sort=False):
        """Return the list of integrated NICs.

        :param sort: indication of whether to sort the returned list by
                     network interface controller (NIC) id
        :returns: list of NIC objects for the integrated NICs
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        filter_query = ('select * '
                        'from DCIM_NICView '
                        'where InstanceID like "NIC.Integrated.%"')

        # _list_nics_common() may raise a WSManRequestFailure
        # exception. It is believed that is caused by a bug that is
        # triggered by the use of the Common Information Model (CIM)
        # Query Language (CQL) filter_query above.
        #
        # When that occurs, this works around it by enumerating all of
        # the DCIM_NICView instances. XPath is used to find the elements
        # in the returned document that are for the integrated NICs.
        #
        # Note that this is in addition to the retry logic that
        # _list_nics_common() implements for the same bug.
        try:
            nics = self._list_nics_common(filter_query, sort)
        except ironic_exceptions.WSManRequestFailure:
            doc = self.client.enumerate(uris.DCIM_NICView)

            name_spaces = {'n1': uris.DCIM_NICView}
            query = (
                './/n1:%(item)s/n1:InstanceID[contains(., '
                '"NIC.Integrated.")]/..' %
                {
                    'item': 'DCIM_NICView'})
            drac_integrated_nics = doc.xpath(query, namespaces=name_spaces)

            nics = [self._parse_drac_nic(nic) for nic in drac_integrated_nics]

            if sort:
                nics.sort(key=lambda nic: nic.id)

        return nics

    def list_nics(self, sort=False):
        """Return the list of NICs.

        :param sort: indication of whether to sort the returned list by
                     network interface controller (NIC) id
        :returns: list of NIC objects
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        """
        return self._list_nics_common(sort=sort)

    def _get_nic_property(self, drac_nic, property_name, nullable=False):
        return utils.get_wsman_resource_attr(drac_nic,
                                             uris.DCIM_NICView,
                                             property_name,
                                             nullable=nullable)

    def _get_nic_statistics_property(self, drac_nic_statistics, property_name):
        return utils.get_wsman_resource_attr(drac_nic_statistics,
                                             uris.DCIM_NICStatistics,
                                             property_name)

    def _list_nics_common(self, filter_query=None, sort=False):
        # This retry logic attempts to work around a bug that causes
        # this method to encounter a WSManRequestFailure exception. That
        # exception is raised by the Ironic python-dracclient's simple
        # WS-Man client. It has occurred when a filter_query argument is
        # passed to this function. That in turn is included in the
        # Enumerate request sent to the iDRAC. It has never been seen
        # when filter_query is None. python-dracclient's simple WS-Man
        # client is implemented by class dracclient.wsman.Client,
        # defined in dracclient/wsman.py.
        #
        # It has been reported that the bug can be worked around by
        # simply reissuing the same Enumerate request.
        #
        # Since the bug has only been encountered when DCIM_NICView
        # objects are enumerated, this is implemented here, instead of
        # more generally in the simple WS-Man client's enumerate()
        # method.
        if filter_query is None:
            max_attempts = ENUMERATE_WITH_FILTER_ATTEMPTS_MIN
        else:
            max_attempts = ENUMERATE_WITH_FILTER_ATTEMPTS_MAX

        for attempt in range(max_attempts):
            try:
                doc = self.client.enumerate(uris.DCIM_NICView,
                                            filter_query=filter_query)
            except ironic_exceptions.WSManRequestFailure:
                if attempt == max_attempts - 1:
                    LOG.debug('All %d enumerate attempts failed', attempt + 1)
                    raise
            else:
                if attempt >= ENUMERATE_WITH_FILTER_ATTEMPTS_MIN:
                    LOG.debug('Had to enumerate %d times, instead of just %d',
                              attempt + 1,
                              ENUMERATE_WITH_FILTER_ATTEMPTS_MIN)

                break

        drac_nics = utils.find_xml(doc,
                                   'DCIM_NICView',
                                   uris.DCIM_NICView,
                                   find_all=True)
        nics = [self._parse_drac_nic(nic) for nic in drac_nics]

        if sort:
            nics.sort(key=lambda nic: nic.id)

        return nics

    def _parse_drac_nic(self, drac_nic):
        drac_instance_id = self._get_nic_property(drac_nic, 'InstanceID')
        drac_link_speed = self._get_nic_property(drac_nic, 'LinkSpeed')

        return NIC(id=drac_instance_id,
                   description=self._get_nic_property(drac_nic,
                                                      'DeviceDescription'),
                   manufacturer=self._get_nic_property(drac_nic,
                                                       'PCIVendorID'),
                   model=self._get_nic_property(drac_nic, 'ProductName'),
                   firmware_version=self._get_nic_property(drac_nic,
                                                           'FamilyVersion',
                                                           nullable=True),
                   is_integrated=(
                       drac_instance_id.find('NIC.Integrated.') == 0),
                   mac_address=self._get_nic_property(drac_nic,
                                                      'CurrentMACAddress'),
                   link_speed=LINK_SPEEDS[drac_link_speed])

    def _parse_drac_nic_statistics(self, drac_nic_statistics):
        drac_link_status = self._get_nic_statistics_property(
            drac_nic_statistics,
            'LinkStatus')

        return NICStatistics(
            id=self._get_nic_statistics_property(
                drac_nic_statistics,
                'InstanceID'),
            link_status=LINK_STATUSES[drac_link_status])


class NICAttribute(object):
    """Generic NIC attribute class"""

    def __init__(self, name, current_value, pending_value, read_only):
        """Construct a NICAttribute object.

        :param name: name of the NIC attribute
        :param current_value: current value of the NIC attribute
        :param pending_value: pending value of the NIC attribute, reflecting
                an unprocessed change (eg. config job not completed)
        :param read_only: indicates whether this NIC attribute can be changed
        """
        self.name = name
        self.current_value = current_value
        self.pending_value = pending_value
        self.read_only = read_only

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @classmethod
    def parse(cls, namespace, nic_attr_xml):
        """Parses XML and creates a NICAttribute object."""

        name = utils.get_wsman_resource_attr(nic_attr_xml,
                                             namespace,
                                             'AttributeName')
        current_value = utils.get_wsman_resource_attr(nic_attr_xml,
                                                      namespace,
                                                      'CurrentValue',
                                                      nullable=True)
        pending_value = utils.get_wsman_resource_attr(nic_attr_xml,
                                                      namespace,
                                                      'PendingValue',
                                                      nullable=True)
        read_only = utils.get_wsman_resource_attr(nic_attr_xml,
                                                  namespace,
                                                  'IsReadOnly')

        return cls(name, current_value, pending_value, (read_only == 'true'))


class NICEnumerationAttribute(NICAttribute):
    """Enumeration NIC attribute class"""

    namespace = uris.DCIM_NICEnumeration

    def __init__(self,
                 name,
                 current_value,
                 pending_value,
                 read_only,
                 possible_values):
        """Construct a NICEnumerationAttribute object.

        :param name: name of the NIC attribute
        :param current_value: current value of the NIC attribute
        :param pending_value: pending value of the NIC attribute, reflecting
                an unprocessed change (eg. config job not completed)
        :param read_only: indicates whether this NIC attribute can be changed
        :param possible_values: list containing the allowed values for the NIC
                                attribute
        """
        super(NICEnumerationAttribute, self).__init__(name,
                                                      current_value,
                                                      pending_value,
                                                      read_only)
        self.possible_values = possible_values

    @classmethod
    def parse(cls, nic_attr_xml):
        """Parse XML and create a NICEnumerationAttribute object."""

        nic_attr = NICAttribute.parse(cls.namespace, nic_attr_xml)
        possible_values = [attr.text for attr
                           in utils.find_xml(nic_attr_xml,
                                             'PossibleValues',
                                             cls.namespace,
                                             find_all=True)]

        return cls(nic_attr.name,
                   nic_attr.current_value,
                   nic_attr.pending_value,
                   nic_attr.read_only,
                   possible_values)

    def validate(self, value):
        """Validate new value."""

        if str(value) not in self.possible_values:
            msg = ("Attribute '%(attr)s' cannot be set to value '%(val)s'."
                   " It must be in %(possible_values)r.") % {
                       'attr': self.name,
                       'val': value,
                       'possible_values': self.possible_values}
            return msg

        return None


class NICStringAttribute(NICAttribute):
    """String NIC attribute class."""

    namespace = uris.DCIM_NICString

    def __init__(self,
                 name,
                 current_value,
                 pending_value,
                 read_only,
                 min_length,
                 max_length,
                 pcre_regex):
        """Construct a NICStringAttribute object.

        :param name: name of the NIC attribute
        :param current_value: current value of the NIC attribute
        :param pending_value: pending value of the NIC attribute, reflecting
                an unprocessed change (eg. config job not completed)
        :param read_only: indicates whether this NIC attribute can be changed
        :param min_length: minimum length of the string
        :param max_length: maximum length of the string
        :param pcre_regex: is a PCRE compatible regular expression that the
                           string must match
        """
        super(NICStringAttribute, self).__init__(name,
                                                 current_value,
                                                 pending_value,
                                                 read_only)
        self.min_length = min_length
        self.max_length = max_length
        self.pcre_regex = pcre_regex

    @classmethod
    def parse(cls, nic_attr_xml):
        """Parse XML and create a NICStringAttribute object."""

        nic_attr = NICAttribute.parse(cls.namespace, nic_attr_xml)
        min_length = int(utils.get_wsman_resource_attr(nic_attr_xml,
                                                       cls.namespace,
                                                       'MinLength'))
        max_length = int(utils.get_wsman_resource_attr(nic_attr_xml,
                                                       cls.namespace,
                                                       'MaxLength'))
        pcre_regex = utils.get_wsman_resource_attr(nic_attr_xml,
                                                   cls.namespace,
                                                   'ValueExpression',
                                                   nullable=True)

        return cls(nic_attr.name,
                   nic_attr.current_value,
                   nic_attr.pending_value,
                   nic_attr.read_only,
                   min_length,
                   max_length,
                   pcre_regex)

    def validate(self, value):
        """Validate new value."""

        if self.pcre_regex is not None:
            regex = re.compile(self.pcre_regex)

            if regex.search(str(value)) is None:
                msg = ("Attribute '%(attr)s' cannot be set to value '%(val)s.'"
                       " It must match regex '%(re)s'.") % {
                           'attr': self.name,
                           'val': value,
                           're': self.pcre_regex}
                return msg

        return None


class NICIntegerAttribute(NICAttribute):
    """Integer NIC attribute class."""

    namespace = uris.DCIM_NICInteger

    def __init__(self,
                 name,
                 current_value,
                 pending_value,
                 read_only,
                 lower_bound,
                 upper_bound):
        """Construct a NICIntegerAttribute object.

        :param name: name of the NIC attribute
        :param current_value: current value of the NIC attribute
        :param pending_value: pending value of the NIC attribute, reflecting
                an unprocessed change (eg. config job not completed)
        :param read_only: indicates whether this NIC attribute can be changed
        :param lower_bound: minimum value for the NIC attribute
        :param upper_bound: maximum value for the NIC attribute
        """
        super(NICIntegerAttribute, self).__init__(name,
                                                  current_value,
                                                  pending_value,
                                                  read_only)
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    @classmethod
    def parse(cls, nic_attr_xml):
        """Parse XML and create a NICIntegerAttribute object."""

        nic_attr = NICAttribute.parse(cls.namespace, nic_attr_xml)
        lower_bound = utils.get_wsman_resource_attr(nic_attr_xml,
                                                    cls.namespace,
                                                    'LowerBound')
        upper_bound = utils.get_wsman_resource_attr(nic_attr_xml,
                                                    cls.namespace,
                                                    'UpperBound')

        if nic_attr.current_value:
            nic_attr.current_value = int(nic_attr.current_value)

        if nic_attr.pending_value:
            nic_attr.pending_value = int(nic_attr.pending_value)

        return cls(nic_attr.name,
                   nic_attr.current_value,
                   nic_attr.pending_value,
                   nic_attr.read_only,
                   int(lower_bound),
                   int(upper_bound))

    def validate(self, value):
        """Validate new value."""

        val = int(value)

        if val < self.lower_bound or val > self.upper_bound:
            msg = ('Attribute %(attr)s cannot be set to value %(val)d.'
                   ' It must be between %(lower)d and %(upper)d.') % {
                       'attr': self.name,
                       'val': value,
                       'lower': self.lower_bound,
                       'upper': self.upper_bound}
            return msg

        return None


class NICConfiguration(object):

    def __init__(self, client):
        """Construct a NICConfiguration object.

        :param client: an instance of WSManClient
        """
        self.client = client

    def get_nic_legacy_boot_protocol(self, nic_id):
        """Obtain the legacy, non-UEFI, boot protocol of a NIC.

        :param nic_id: id of the network interface controller (NIC)
        :returns: legacy boot protocol
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: NotFound when no settings for NIC found
        """
        return self.get_nic_setting(nic_id, 'LegacyBootProto')

    def get_nic_link_status(self, nic_id):
        """Obtain the link status, connected or disconnected, of a NIC.

        :param nic_id: id of the network interface controller (NIC)
        :returns: link status
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: NotFound when no settings for NIC found
        """
        return self.get_nic_setting(nic_id, 'LinkStatus')

    def get_nic_setting(self, nic_id, attribute_name):
        """Obtain a setting of a NIC.

        :param nic_id: id of the network interface controller (NIC)
        :param attribute_name: name of the setting
        :returns: value of the attribute on successful query, None
                  otherwise
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: NotFound when no settings for NIC found
        """
        selection_expression = ('InstanceID = '
                                '"%(fqdd)s:%(attribute_name)s"') % {
            'fqdd': nic_id,
            'attribute_name': attribute_name}
        settings = self._list_nic_settings(selection_expression)

        # Were no settings found?
        if not settings:
            raise exceptions.NotFound(
                what=('settings for NIC %(nic)s') % {
                    'nic': nic_id})

        # Do the settings include the attribute?
        if attribute_name not in settings:
            return None

        return settings[attribute_name]

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
        :raises: NotFound when no settings for NIC found
        """
        return self.get_nic_legacy_boot_protocol(
            nic_id).current_value == 'NONE'

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
        :raises: NotFound when no settings for NIC found
        """
        return self.get_nic_legacy_boot_protocol(nic_id).current_value == 'PXE'

    def is_nic_link_connected(self, nic_id):
        """Return true if the link status of a NIC is connected, false otherwise.

        :param nic_id: id of the network interface controller (NIC)
        :returns: boolean indicating whether or not the link is connected
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: NotFound when no settings for NIC found
        """
        return self.get_nic_link_status(nic_id).current_value == 'Connected'

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
        selection_expression = ('FQDD = "%(fqdd)s"') % {'fqdd': nic_id}
        return self._list_nic_settings(selection_expression)

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
        return self.set_nic_setting(nic_id, 'LegacyBootProto', value)

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
        settings = {attribute_name: value}
        return self.set_nic_settings(nic_id, settings)

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
                  must be created for the new settings to be applied and
                  also containing a 'reboot_required' key with a boolean
                  value indicating whether or not a reboot is required
        :raises: WSManRequestFailure on request failures
        :raises: WSManInvalidResponse when receiving invalid response
        :raises: DRACOperationFailed on error reported back by the iDRAC
                 interface
        :raises: InvalidParameterValue on invalid NIC attribute
        """
        current_settings = self.list_nic_settings(nic_id)
        unknown_keys = set(settings) - set(current_settings)

        if unknown_keys:
            msg = ('Unknown NIC attributes found: %(unknown_keys)r' %
                   {'unknown_keys': unknown_keys})
            raise ironic_exceptions.InvalidParameterValue(reason=msg)

        read_only_keys = []
        unchanged_attribs = []
        invalid_attribs_msgs = []
        attrib_names = []
        candidates = set(settings)

        for attr in candidates:
            if str(settings[attr]) == str(
                    current_settings[attr].current_value):
                unchanged_attribs.append(attr)
            elif current_settings[attr].read_only:
                read_only_keys.append(attr)
            else:
                validation_msg = current_settings[attr].validate(
                    settings[attr])

                if validation_msg is None:
                    attrib_names.append(attr)
                else:
                    invalid_attribs_msgs.append(validation_msg)

        if unchanged_attribs:
            LOG.warning('Ignoring unchanged NIC attributes: %r' %
                        unchanged_attribs)

        if invalid_attribs_msgs or read_only_keys:
            if read_only_keys:
                read_only_msg = ['Cannot set read-only NIC attributes: %r.'
                                 % read_only_keys]
            else:
                read_only_msg = []

            drac_messages = '\n'.join(invalid_attribs_msgs + read_only_msg)
            raise ironic_exceptions.DRACOperationFailed(
                drac_messages=drac_messages)

        if not attrib_names:
            return {'commit_required': False}

        selectors = {'CreationClassName': 'DCIM_NICService',
                     'Name': 'DCIM:NICService',
                     'SystemCreationClassName': 'DCIM_ComputerSystem',
                     'SystemName': 'DCIM:ComputerSystem'}
        properties = {'Target': nic_id,
                      'AttributeName': attrib_names,
                      'AttributeValue': [settings[attr] for attr
                                         in attrib_names]}
        doc = self.client.invoke(uris.DCIM_NICService,
                                 'SetAttributes',
                                 selectors,
                                 properties)

        return {'reboot_required': utils.is_reboot_required(
            doc, uris.DCIM_NICService),
                'commit_required': utils_additional.is_commit_required(
            doc, uris.DCIM_NICService)}

    def _get_config(self,
                    resource,
                    class_name,
                    selection_expression,
                    attr_cls):
        filter_query = (
            'select * '
            'from %(class)s '
            'where %(selection_expression)s') % {
            'class': class_name, 'selection_expression': selection_expression}
        doc = self.client.enumerate(resource, filter_query=filter_query)

        result = {}
        items = doc.find('.//{%s}Items' % wsman.NS_WSMAN)

        for item in items:
            attribute = attr_cls.parse(item)
            result[attribute.name] = attribute

        return result

    def _list_nic_settings(self, selection_expression):
        result = {}
        configurable_attributes = [
            (uris.DCIM_NICEnumeration,
             'DCIM_NICEnumeration',
             NICEnumerationAttribute),
            (uris.DCIM_NICString,
             'DCIM_NICString',
             NICStringAttribute),
            (uris.DCIM_NICInteger,
             'DCIM_NICInteger',
             NICIntegerAttribute)]

        for (resource, class_name, attr_cls) in configurable_attributes:
            attribs = self._get_config(resource,
                                       class_name,
                                       selection_expression,
                                       attr_cls)

            if not set(result).isdisjoint(set(attribs)):
                raise ironic_exceptions.DRACOperationFailed(
                    drac_messages=('Colliding attributes %r' % (
                        set(result) & set(attribs))))

            result.update(attribs)

        return result
