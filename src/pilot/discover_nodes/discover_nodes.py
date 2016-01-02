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

# Create and configure this script's logging.  Logs emitted from this
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
    parser.add_argument('idrac', nargs='+', help='IP addresses of iDRACs')
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

    nodes = {
        OSPD_NODE_TEMPLATE_ATTRIBUTE_NODES: scan(
            ip_addresses=args.idrac,
            user_name=args.username,
            password=args.password,
            provisioning_nics=args.nics)}

    print(json.dumps(nodes,
                     allow_nan=False,
                     indent=JSON_FORMAT_INDENT_LEVEL,
                     separators=JSON_FORMAT_SEPARATORS,
                     sort_keys=True))


def scan(ip_addresses, user_name, password, provisioning_nics):
    nodes = []

    # Scan each iDRAC.
    for ip in ip_addresses:
        node = scan_one(ScanInfo(ip, user_name, password, provisioning_nics))

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
