#!/usr/bin/python

import argparse
import dracclient.wsman
import lxml

# Suppress InsecureRequestWarning: Unverified HTTPS request is being made.
# See
# https://urllib3.readthedocs.org/en/latest/security.html#disabling-warnings.
# It emanates from the urllib3 instance inside of the requests package.
import requests
requests.packages.urllib3.disable_warnings()


def main():
    # Parse the command line arguments.
    parser = argparse.ArgumentParser(description='Probe iDRACs.')
    parser.add_argument("idrac", nargs='+', help='IP addresses of iDRACs')
    parser.add_argument(
        "-l",
        "--login-name",
        default='',
        help='user to login as')
    parser.add_argument("-p", "--password", default='', help='password')

    args = parser.parse_args()

    # List of Dell Common Information Models (DCIM) to enumerate.
    #
    # The Dell Common Information Model (DCIM) Extensions Library Managed
    # Object Format (MOF) Collection is available at
    # http://en.community.dell.com/techcenter/systems-management/w/wiki/1840.
    dcims = [
        'DCIM_SystemView',
        'DCIM_PhysicalDiskView',
        'DCIM_VirtualDiskView',
        'DCIM_CPUView',
        'DCIM_NICView',
        'DCIM_NICStatistics',
    ]

    # Probe each iDRAC specified on the command line.
    for i in args.idrac:
        # Identify the iDRAC.
        print i + ':'

        # Create client for talking to the iDRAC over the WSMan protocol.
        client = dracclient.wsman.Client(i, args.login_name, args.password)

        # Enumerate and pretty print each DCIM in the list.
        for d in dcims:
            response = client.enumerate(
                'http://schemas.dell.com/wbem/wscim/1/cim-schema/2/' + d)
            print lxml.etree.tostring(response, pretty_print=True)

if __name__ == "__main__":
    main()
