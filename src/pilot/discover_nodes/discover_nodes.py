#!/usr/bin/python

from __future__ import absolute_import
from __future__ import print_function

import argparse
from collections import namedtuple
import json
import logging
import os.path
import sys
from time import sleep

import netaddr
import requests.packages

import discover_nodes.dracclient.client as discover_nodes_dracclient
from exceptions import ValueError

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

IDRAC_FACTORY_ADMIN_USER_CREDENTIALS = {
    'user_name': 'root',
    'password': 'calvin'}

# Constants used to specify the formatting of JavaScript Object Notation
# (JSON).
JSON_FORMAT_INDENT_LEVEL = 2
JSON_FORMAT_SEPARATORS = (',', ': ')

# Dictionary that maps integral link speeds in gigabits per second
# (Gbps) to the textual representations returned by dracclient.
LINK_SPEEDS = {
    1: discover_nodes_dracclient.LINK_SPEED_1_GBPS,
    10: discover_nodes_dracclient.LINK_SPEED_10_GBPS,
    25: discover_nodes_dracclient.LINK_SPEED_25_GBPS,
    40: discover_nodes_dracclient.LINK_SPEED_40_GBPS,
    50: discover_nodes_dracclient.LINK_SPEED_50_GBPS,
    100: discover_nodes_dracclient.LINK_SPEED_100_GBPS,
}

# Red Hat Enterprise Linux OpenStack Platform (OSP) Director node
# definition template attributes. They are documented in "Red Hat
# Enterprise Linux OpenStack Platform 7 Director Installation and Usage"
# (https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux_OpenStack_Platform/7/html/Director_Installation_and_Usage),
# section 6.1.1, "Registering Nodes for the Basic Overcloud". Search for
# "instackenv.json".
#
# The abbreviation 'PM' represents "platform management" or "power
# management".
OSPD_NODE_TEMPLATE_ATTRIBUTE_ARCHITECTURE = 'arch'
OSPD_NODE_TEMPLATE_ATTRIBUTE_CPU = 'cpu'
OSPD_NODE_TEMPLATE_ATTRIBUTE_DISK = 'disk'
OSPD_NODE_TEMPLATE_ATTRIBUTE_MAC = 'mac'
OSPD_NODE_TEMPLATE_ATTRIBUTE_MEMORY = 'memory'
OSPD_NODE_TEMPLATE_ATTRIBUTE_NODES = 'nodes'
OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_ADDR = 'pm_addr'
OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_PASSWORD = 'pm_password'
OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_TYPE = 'pm_type'
OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_USER = 'pm_user'

OSPD_NODE_TEMPLATE_VALUE_MAC_USER_INTERVENTION_REQUIRED = \
    'FIXME and rerun ' + PROGRAM_NAME
OSPD_NODE_TEMPLATE_VALUE_PM_TYPE_PXE_IDRAC = 'pxe_drac'
OSPD_NODE_TEMPLATE_VALUE_PM_TYPE_PXE_IPMI = 'pxe_ipmitool'


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
                      [OSPD_NODE_TEMPLATE_ATTRIBUTE_ARCHITECTURE,
                       OSPD_NODE_TEMPLATE_ATTRIBUTE_CPU,
                       OSPD_NODE_TEMPLATE_ATTRIBUTE_DISK,
                       OSPD_NODE_TEMPLATE_ATTRIBUTE_MAC,
                       OSPD_NODE_TEMPLATE_ATTRIBUTE_MEMORY,
                       OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_ADDR,
                       OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_PASSWORD,
                       OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_TYPE,
                       OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_USER,
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

    # Create client for talking to the iDRAC over the WS-Man protocol.
    client = discover_nodes_dracclient.DRACClient(scan_info.ip_address,
                                                  scan_info.user_name,
                                                  scan_info.password)

    # The node is of interest only if it has an iDRAC. Ensure that the
    # IP address is a WS-Man endpoint and an iDRAC.
    if not has_idrac(client):
        return None

    # Testing determined that Ironic introspection fails for a node
    # definition template that does not contain the arch, cpu, disk, and
    # memory attributes. This contradicts the documentation, which
    # describes them as optional, as well as information received from
    # Red Hat engineers that they are not needed. Empty string values
    # for those attributes are sufficient.
    #
    # The documentation is identified at the beginning of this file.
    kwargs = {
        OSPD_NODE_TEMPLATE_ATTRIBUTE_ARCHITECTURE: '',
        OSPD_NODE_TEMPLATE_ATTRIBUTE_CPU: '',
        OSPD_NODE_TEMPLATE_ATTRIBUTE_DISK: '',
        OSPD_NODE_TEMPLATE_ATTRIBUTE_MAC: [
            get_mac(client, scan_info.provisioning_nics)],
        OSPD_NODE_TEMPLATE_ATTRIBUTE_MEMORY: '',
        OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_ADDR: scan_info.ip_address,
        OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_PASSWORD: scan_info.password,
        OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_TYPE:
            OSPD_NODE_TEMPLATE_VALUE_PM_TYPE_PXE_IPMI,
        OSPD_NODE_TEMPLATE_ATTRIBUTE_PM_USER: scan_info.user_name,
    }
    return NodeInfo(**kwargs)


# TODO: CES-4471 Ensure IPv4 address is a WS-Man endpoint and iDRAC
def has_idrac(client):
    return True


def get_mac(client, provisioning_nics):
    # The provisioning network interface must be on an integrated
    # network interface controller (NIC). Sort them so that they can be
    # considered below in lexicographical order.
    nics = client.list_integrated_nics(sort=True)

    if len(nics) == 0:
        LOG.warning('No integrated NIC found')
        return None

    provisioning_link_speed = LINK_SPEEDS[provisioning_nics]
    nic_to_use = None

    # Select the first interface whose link status is up and whose link
    # speed equals that specified by 'provisioning_nics'.
    for i, nic in enumerate(nics):
        if not client.is_nic_link_up(nic.id):
            if i == 0:
                LOG.warning('Link status of first integrated NIC %s is not up',
                            nic.id)
            continue

        if nic.link_speed != provisioning_link_speed:
            if i == 0:
                LOG.warning('Link speed of first integrated NIC %s is %s,'
                            ' instead of %s',
                            nic.id,
                            nic.link_speed,
                            provisioning_link_speed)
            else:
                LOG.info('Link speed of integrated NIC %s is %s, instead of'
                         ' %s',
                         nic.id,
                         nic.link_speed,
                         provisioning_link_speed)
            continue

        nic_to_use = nic
        break

    if nic_to_use is None:
        LOG.warning('No integrated NIC with link speed %s found',
                    provisioning_link_speed)
        return OSPD_NODE_TEMPLATE_VALUE_MAC_USER_INTERVENTION_REQUIRED

    # Ensure that the selected network interface is configured to PXE
    # boot.
    set_nic_to_pxe_boot(client, nic_to_use.id)

    return nic_to_use.mac_address


def set_nic_to_pxe_boot(client, nic_id):
    if client.is_nic_legacy_boot_protocol_pxe(nic_id):
        return

    result = client.set_nic_legacy_boot_protocol_pxe(nic_id)

    if not result['commit_required']:
        return

    job_id = client.commit_pending_nic_changes(nic_id, reboot=True)
    job_state = 'Unknown'

    LOG.info('Waiting for job %s to finish', job_id)

    # Poll for the job's final state.
    while not (job_state == 'Completed' or
               job_state == 'Completed with Errors' or
               job_state == 'Failed'):
        sleep(10)
        job_state = client.get_job(job_id).state

    if job_state == 'Completed':
        LOG.info('Job %s successful with final state %s', job_id, job_state)
    else:
        LOG.error('Job %s unsuccessful with final state %s', job_id, job_state)


if __name__ == '__main__':
    main()
