#!/usr/bin/python

import ironicclient
from novaclient import client as novaclient
from os import path
from subprocess import check_output


def get_openstack_creds():
    creds_file = open(path.join(path.expanduser('~'), 'stackrc'), 'r')

    for line in creds_file:
        prefix = "export"
        if line.startswith(prefix):
            line = line[len(prefix):]

        line = line.strip()
        key, val = line.split('=', 2)
        key = key.lower()

        if key == 'os_username':
            os_username = val
        elif key == 'os_auth_url':
            os_auth_url = val
        elif key == 'os_tenant_name':
            os_tenant_name = val

    os_password = check_output(['sudo', 'hiera', 'admin_password']).strip()

    return os_auth_url, os_tenant_name, os_username, os_password


def main():
    os_auth_url, os_tenant_name, os_username, os_password = \
        get_openstack_creds()

    kwargs = {'os_username': os_username,
              'os_password': os_password,
              'os_auth_url': os_auth_url,
              'os_tenant_name': os_tenant_name}
    ironic = ironicclient.client.get_client(1, **kwargs)
    nodes = ironic.node.list(detail=True)

    nova = novaclient.Client('2',  # API version
                             os_username,
                             os_password,
                             os_tenant_name,
                             os_auth_url)

    # Slightly odd syntax for declaring 'banner' reduces the line length
    banner = (
        "+-----------------+---------------------------+-----------------+"
    )
    nodeinfo = "| {:<15} | {:<25} | {:<15} |"
    print banner
    print nodeinfo.format('iDRAC Addr', 'Node Name', 'Provision Addr')
    print banner
    # Display the list ordered by the iDRAC address
    for n in sorted(nodes, key=lambda x: x.driver_info['ipmi_address']):
        idrac_addr = n.driver_info['ipmi_address']

        if 'display_name' in n.instance_info:
            node_name = n.instance_info['display_name']
        else:
            node_name = 'None'

        prov_addr = 'None'
        if n.instance_uuid:
            nova_ips = nova.servers.ips(n.instance_uuid)
            if nova_ips and 'ctlplane' in nova_ips:
                prov_addr = nova_ips['ctlplane'][0]['addr']

        print nodeinfo.format(idrac_addr, node_name, prov_addr)
    print banner


if __name__ == "__main__":
    main()
