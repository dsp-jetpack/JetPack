#!/usr/bin/python

import argparse
import json
import os
from ironicclient import client
from subprocess import check_output
from credential_helper import CredentialHelper


def main():
  os_auth_url, os_tenant_name, os_username, os_password = \
    CredentialHelper.get_undercloud_creds()

  kwargs = {'os_username': os_username,
            'os_password': os_password,
            'os_auth_url': os_auth_url,
            'os_tenant_name': os_tenant_name}
  ironic = client.get_client(1, **kwargs)

  for node in ironic.node.list(detail=True):
    ip, username, password = CredentialHelper.get_drac_creds_from_node(node)

    # Power off the node
    cmd="ipmitool -H {} -I lanplus -U {} -P '{}' chassis power off".format(
      ip, username, password)
    print cmd
    os.system(cmd)

    # Set the first boot device to PXE
    cmd="ipmitool -H {} -I lanplus -U {} -P '{}' chassis bootdev pxe options=persistent".format(
      ip, username, password)
    print cmd
    os.system(cmd)


if __name__ == "__main__":
  main()
