#!/usr/bin/python

import argparse
import json
import os
from ironicclient import client
from subprocess import check_output


def get_creds():
  global os_username
  global os_password
  global os_auth_url
  global os_tenant_name

  creds_file = open(os.environ['HOME']+ '/stackrc', 'r')

  for line in creds_file:
    prefix = "export"
    if line.startswith(prefix):
        line=line[len(prefix):]

    line = line.strip()
    key, val = line.split('=',2)
    key = key.lower()

    if key == 'os_username':
      os_username = val
    elif key == 'os_auth_url':
      os_auth_url = val
    elif key == 'os_tenant_name':
      os_tenant_name = val
  os_password = check_output(['sudo', 'hiera', 'admin_password']).strip()


def find_password(ip):
  for node in nodes:
    if node["pm_addr"] == ip:
      return node["pm_password"]


def main():
  get_creds()

  instackenv_file = open(os.environ['HOME']+ '/instackenv.json', 'r')
  instackenv = json.load(instackenv_file)

  global nodes
  nodes = instackenv["nodes"]

  kwargs = {'os_username': os_username,
            'os_password': os_password,
            'os_auth_url': os_auth_url,
            'os_tenant_name': os_tenant_name}
  ironic = client.get_client(1, **kwargs)

  for node in ironic.node.list(detail=True):
    if "drac_host" in node.driver_info:
      ip = node.driver_info["drac_host"]
      username = node.driver_info["drac_username"]
    else:
      ip = node.driver_info["ipmi_address"]
      username = node.driver_info["ipmi_username"]

    password = find_password(ip)

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
