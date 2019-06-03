#!/usr/bin/python

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

from __future__ import absolute_import
from __future__ import print_function

import argparse
from collections import namedtuple
from exceptions import ValueError
import json
import logging
import os.path
import sys

import dracclient.exceptions
import dracclient.utils
import netaddr
import requests.packages

import discover_nodes.dracclient.client as discover_nodes_dracclient

# Suppress InsecureRequestWarning: Unverified HTTPS request is being
# made. See
# https://urllib3.readthedocs.org/en/latest/security.html#disabling-warnings.
# It emanates from the urllib3 instance inside of the requests package.
requests.packages.urllib3.disable_warnings()

# Perform basic configuration of the logging system, which configures
# the root logger. A StreamHandler that directs log messages to stderr
# is created. The format argument is used to create a formatter that is
# applied to that handler. Finally, the handler is added to the root
# logger.
#
# This configuration applies to the log messages emitted by both this
# script and the modules in the python-dracclient package that it uses.
# Their log messages are output to stderr.
logging.basicConfig(
    format='%(asctime)-15s %(name)-48s %(levelname)-8s %(message)s',
    level=logging.WARNING)

# Create and configure this script's logging. Logs emitted from this
# script include the IP address of the Dell Integrated Dell Remote
# Access Controller (iDRAC).


class CustomLoggerAdapter(logging.LoggerAdapter):
    """Prepend an iDRAC's IP address to log messages.
    """

    def __init__(self, logger, extra):
        """Construct a CustomLoggerAdapter object.

        Initialize the adapter with a logger and a dict-like object
        which provides contextual information.

        :param logger: Logger instance to which to delegate calls to
                       logging methods
        :param extra: dict-like object which provides contextual
                      information
        """
        super(CustomLoggerAdapter, self).__init__(logger, extra)

    # TODO: Add docstring comments to this class's public methods.
    def process(self, msg, kwargs):
        if 'idracip' in self.extra:
            return '%s %s' % (self.extra['idracip'], msg), kwargs
        else:
            return msg, kwargs

    def set_idrac_ip_address(self, ip_address):
        self.extra['idracip'] = ip_address


logger = logging.getLogger(__name__)
LOG = CustomLoggerAdapter(logger, {})

PROGRAM_NAME = os.path.splitext(os.path.basename(sys.argv[0]))[0]

DCIM_iDRACCardView = ('http://schemas.dell.com/wbem/wscim/1/cim-schema/2/'
                      'DCIM_iDRACCardView')

IDRAC_FACTORY_ADMIN_USER_CREDENTIALS = {
    'user_name': 'root',
    'password': 'calvin'}

# Constants used to specify the formatting of JavaScript Object Notation
# (JSON).
JSON_FORMAT_INDENT_LEVEL = 2
JSON_FORMAT_SEPARATORS = (',', ': ')

# Red Hat OpenStack Platform (OSP) Director node definition template
# attributes. They are documented in the "Red Hat OpenStack Platform Director
# Installation and Usage" document. Search for "instackenv.json".
#
# The abbreviation 'PM' represents "platform management" or "power
# management".
OSPD_NODE_TEMPLATE_ATTRIBUTE_NODES = 'nodes'
OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_ADDR = 'pm_addr'
OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_PASSWORD = 'pm_password'
OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_TYPE = 'pm_type'
OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_USER = 'pm_user'

# The following attributes are not supported by OSP Director, but
# are provided to allow the user to determine which node is which
# in the case where the nodes are using DHCP.

NODE_TEMPLATE_ATTRIBUTE_MODEL = 'model'
NODE_TEMPLATE_ATTRIBUTE_SERVICE_TAG = 'service_tag'

OSPD_NODE_TEMPLATE_VALUE_PM_TYPE_PXE_IDRAC = 'pxe_drac'
OSPD_NODE_TEMPLATE_VALUE_PM_TYPE_PXE_IPMI = 'pxe_ipmitool'
OSPD_NODE_TEMPLATE_VALUE_USER_INTERVENTION_REQUIRED = \
    'FIXME and rerun ' + PROGRAM_NAME


class NotSupported(BaseException):
    pass


# Create a factory function for creating tuple-like objects that contain
# the information needed to generate an OSP Director node template. The
# generated template is in JavaScript Object Notation (JSON) format.
#
# The article
# http://stackoverflow.com/questions/35988/c-like-structures-in-python
# describes the use of collections.namedtuple to implement C-like
# structures in Python.
NodeInfo = namedtuple('NodeInfo',
                      [OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_ADDR,
                       OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_PASSWORD,
                       OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_TYPE,
                       OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_USER,
                       NODE_TEMPLATE_ATTRIBUTE_MODEL,
                       NODE_TEMPLATE_ATTRIBUTE_SERVICE_TAG
                       ])

# Create a factory function for creating tuple-like objects that contain
# the information needed to log into an iDRAC, as well as a description
# of the node's provisioning network interface.
ScanInfo = namedtuple('ScanInfo',
                      ['ip_address',
                       'user_name',
                       'password',
                       'provisioning_nics',
                       ])


def main():
    # Parse the command line arguments.
    parser = argparse.ArgumentParser(
        description='Discover nodes.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('idrac',
                        nargs='+',
                        help="""White space separated list of IP address
                                specifications to scan for iDRACs. Each
                                specification may be an IP address,
                                range of IP addresses, or IP network
                                address. A range's start and end IP
                                addresses are separated by a hyphen. An
                                IP network address may contain a CIDR,
                                netmask, or hostmask. The addresses that
                                can be assigned to hosts are scanned.
                                Only IPv4 addresses are supported.""")
    parser.add_argument(
        '-u',
        '--username',
        default=IDRAC_FACTORY_ADMIN_USER_CREDENTIALS['user_name'],
        help='username for accessing the iDRACs')
    parser.add_argument(
        '-p',
        '--password',
        default=IDRAC_FACTORY_ADMIN_USER_CREDENTIALS['password'],
        help='password for accessing the iDRACs')
    parser.add_argument(
        '-n',
        '--nics',
        default=1,
        type=int,
        choices=[1, 10, 25, 40, 50, 100],
        help='link speed of provisioning network interfaces in gigabits '
        'per second (Gbps)')

    args = parser.parse_args()

    try:
        # Create a set of IP addresses from the idrac command line
        # arguments.
        ip_set = parse_idrac_arguments(idrac_list=args.idrac)
    except (NotSupported, ValueError, netaddr.AddrFormatError) as e:
        # Print this script's usage message, information about the error
        # detected in the command line argument, and exit
        # unsuccessfully.
        parser.print_usage(file=sys.stderr)
        print(sys.argv[0],
              ': error: argument idrac:',
              e.message,
              file=sys.stderr)
        sys.exit(1)

    nodes = {
        OSPD_NODE_TEMPLATE_ATTRIBUTE_NODES: scan(
            ip_set,
            user_name=args.username,
            password=args.password,
            provisioning_nics=args.nics)}

    print(json.dumps(nodes,
                     allow_nan=False,
                     indent=JSON_FORMAT_INDENT_LEVEL,
                     separators=JSON_FORMAT_SEPARATORS,
                     sort_keys=True))


def parse_idrac_arguments(idrac_list):
    ip_set = netaddr.IPSet()

    for idrac in idrac_list:
        ip_set = ip_set.union(ip_set_from_idrac(idrac))

    return ip_set


def ip_set_from_idrac(idrac):
    range_bounds = idrac.split('-')

    if len(range_bounds) == 2:
        start, end = range_bounds
        ip_set = ip_set_from_address_range(start, end)
    elif len(range_bounds) == 1:
        ip_set = ip_set_from_address(range_bounds[0])
    else:
        # String contains more than one (1) dash.
        raise ValueError(
            ('invalid IP range: %(idrac)s (contains more than one hyphen)') % {
                'idrac': idrac})

    return ip_set


def ip_set_from_address_range(start, end):
    try:
        start_ip_address = ip_address_from_address(start)
        end_ip_address = ip_address_from_address(end)
    except (NotSupported, ValueError) as e:
        raise ValueError(
            ('invalid IP range: %(start)s-%(end)s (%(message)s)') %
            {
                'start': start,
                'end': end,
                'message': e.message})
    except netaddr.AddrFormatError as e:
        raise ValueError(
            ("invalid IP range: '%(start)s-%(end)s' (%(message)s)") %
            {
                'start': start,
                'end': end,
                'message': e.message})

    if start_ip_address > end_ip_address:
        raise ValueError(
            ('invalid IP range: %(start)s-%(end)s (lower bound IP greater than'
             ' upper bound)') %
            {
                'start': start,
                'end': end})

    ip_range = netaddr.IPRange(start_ip_address, end_ip_address)

    return netaddr.IPSet(ip_range)


def ip_set_from_address(address):
    ip_set = netaddr.IPSet()

    try:
        ip_address = ip_address_from_address(address)
        ip_set.add(ip_address)
    except ValueError:
        ip_network = ip_network_from_address(address)
        ip_set.update(ip_network.iter_hosts())

    return ip_set


def ip_address_from_address(address):
    try:
        ip_address = netaddr.IPAddress(address)
    except ValueError as e:
        # address contains a CIDR prefix, netmask, or hostmask.
        e.message = ('invalid IP address: %(address)s (detected CIDR, netmask,'
                     ' hostmask, or subnet)') % {'address': address}
        raise
    except netaddr.AddrFormatError as e:
        # address is not an IP address represented in an accepted string
        # format.
        e.message = ("invalid IP address: '%(address)s' (failed to detect a"
                     " valid IP address)") % {'address': address}
        raise

    if ip_address.version == 4:
        return ip_address
    else:
        raise NotSupported(
            ('invalid IP address: %(address)s (Internet Protocol version'
             ' %(version)s is not supported)') % {
                'address': address,
                'version': ip_address.version})


def ip_network_from_address(address):
    try:
        ip_network = netaddr.IPNetwork(address)
    except netaddr.AddrFormatError as e:
        # address is not an IP address represented in an accepted string
        # format.
        e.message = ("invalid IP network: '%(address)s' (failed to detect a"
                     " valid IP network)") % {
            'address': address}
        raise

    if ip_network.version == 4:
        return ip_network
    else:
        raise NotSupported(
            ('invalid IP network: %(address)s (Internet Protocol version'
             ' %(version)s is not supported)') % {
                'address': address,
                'version': ip_network.version})


def scan(ip_set, user_name, password, provisioning_nics):
    # Scan each iDRAC.
    nodes = []

    for ip_address in ip_set:
        node = scan_one(ScanInfo(str(ip_address),
                                 user_name,
                                 password,
                                 provisioning_nics))

        if node is not None:
            nodes.append(node._asdict())

    return nodes


def scan_one(scan_info):
    LOG.set_idrac_ip_address(scan_info.ip_address)

    # Create client for managing a server's resources through its iDRAC.
    # It interacts with the iDRAC using the Distributed Management Task
    # Force, Inc.'s (DMTF) Web Services for Management (WS-Man)
    # protocol. See the DMTF's "Web Services for Management
    # (WS-Management) Specification"
    # (http://www.dmtf.org/sites/default/files/standards/documents/DSP0226_1.2.0.pdf).
    client = discover_nodes_dracclient.DRACClient(scan_info.ip_address,
                                                  scan_info.user_name,
                                                  scan_info.password)

    # Initialize the values of the attributes.
    pm_address = scan_info.ip_address
    pm_password = scan_info.password
    pm_type = OSPD_NODE_TEMPLATE_VALUE_PM_TYPE_PXE_IDRAC
    pm_user = scan_info.user_name
    model = ''
    service_tag = ''

    try:
        # Determine if the IP address is a WS-Man endpoint and an iDRAC.
        # If it is not, return None so that no entry is created for it
        # in the node definition template.
        if not is_idrac(client):
            LOG.info('IP address is not an iDRAC')
            return None

        model = client.get_system().model
        service_tag = client.get_system().service_tag
    except dracclient.exceptions.WSManInvalidResponse:
        # Most likely the user credentials are unauthorized.

        # Log an error level message, along with the exception, because
        # this is something that should be addressed and infrequently
        # encountered.
        LOG.exception('Could not determine if IP address is an iDRAC')

        # Create an entry in the node definition template for this IP
        # address that provides information about what needs to be
        # fixed.
        pm_user += ' '
        pm_user += OSPD_NODE_TEMPLATE_VALUE_USER_INTERVENTION_REQUIRED

        pm_password += ' '
        pm_password += OSPD_NODE_TEMPLATE_VALUE_USER_INTERVENTION_REQUIRED
    except Exception:
        # Handle all other exceptions so that the remaining addresses
        # can be scanned.

        # Log an error level message, along with the exception, because
        # this is something that should be addressed and infrequently
        # encountered.
        LOG.exception('Unexpected exception encountered while determining if'
                      ' IP address is an iDRAC')

        # Create an entry in the node definition template for this IP
        # address that provides information about what needs to be
        # fixed.
        pm_address += ' '
        pm_address += OSPD_NODE_TEMPLATE_VALUE_USER_INTERVENTION_REQUIRED

    kwargs = {
        OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_ADDR: pm_address,
        OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_PASSWORD: pm_password,
        OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_TYPE: pm_type,
        OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_USER: pm_user,
        NODE_TEMPLATE_ATTRIBUTE_MODEL: model,
        NODE_TEMPLATE_ATTRIBUTE_SERVICE_TAG: service_tag
    }
    return NodeInfo(**kwargs)


# TODO: CES-4471 Ensure IPv4 address is a WS-Man endpoint and iDRAC
#
#       When the Python python-dracclient package's simple WS-Man
#       client, class dracclient.Client, which is implemented in
#       dracclient/wsman.py, provides support for the WS-Man Identify
#       operation, change this function to use it. See the Distributed
#       Management Task Force, Inc.'s (DMTF) "Web Services for
#       Management (WS-Management) Specification"
#       (http://www.dmtf.org/sites/default/files/standards/documents/DSP0226_1.2.0.pdf),
#       section 11, "Metadata and Discovery", for the specification of
#       Identify.
def is_idrac(client):
    # This determines whether or not an IPv4 address is a WS-Man
    # endpoint and iDRAC.
    #
    # Since the GetRemoteAPIStatus call is vendor specific, if the
    # server responds then that is sufficient to determine that it's an iDRAC.
    # Squelch a couple of chatty libraries.
    dracclient_wsman_logger = logging.getLogger('dracclient.wsman')
    dracclient_wsman_logger.disabled = True
    requests_logger = logging.getLogger(
        'requests.packages.urllib3.connectionpool')
    requests_logger.disabled = True

    try:
        client.client.is_idrac_ready()
    except dracclient.exceptions.WSManInvalidResponse as e:
        # Most likely the user credentials are unauthorized.

        # Since it cannot be determined if the IP address is an iDRAC,
        # re-raise the exception so the calling function can handle it.
        raise
    except dracclient.exceptions.WSManRequestFailure as e:
        # Most likely the host does not exist, there is no route to it,
        # or the connection was refused.

        # Log a debug level message, because it is reasonable for this
        # to be encountered when the user specifies IP address ranges or
        # network addresses to scan on the command line. And a large
        # number of them can occur.
        LOG.debug(
            '%(message)s; host is not reachable or connection refused' % {
                'message': e.message})
        # Consider the IP address to not be an iDRAC.
        return False
    except Exception as e:
        # Since it cannot be determined if the IP address is an iDRAC,
        # re-raise the exception so the calling function can handle it.
        raise
    finally:
        # Ensure the libraries' loggers are re-enabled.
        requests_logger.disabled = False
        dracclient_wsman_logger.disabled = False
    return True


if __name__ == '__main__':
    main()
