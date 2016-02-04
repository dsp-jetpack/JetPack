#!/usr/bin/python

import argparse
import os
import re
import sys

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


def main():

  parser = argparse.ArgumentParser()
  parser.add_argument("--controllers", dest="num_controllers", type=int,
    default=3, help="The number of controller nodes")
  parser.add_argument("--computes", dest="num_computes", type=int,
    required=True, help="The number of compute nodes")
  parser.add_argument("--storage", dest="num_storage", type=int,
    required=True, help="The number of storage nodes")
  parser.add_argument("--vlans", dest="vlan_range", required=True,
    help="The VLAN range to use for Neutron in xxx:yyy format")
  parser.add_argument("--ntp", dest="ntp_server_fqdn",
    default="0.centos.pool.ntp.org", help="The FQDN of the ntp server to use")
  parser.add_argument("--timeout",
    default="90", help="The amount of time in minutes to allow the overcloud to deploy")
  args = parser.parse_args()

  p = re.compile('\d+:\d+')
  if not p.match(args.vlan_range):
    print("Error: The VLAN range must be a number followed by a colon, followed by another number")
    sys.exit(1)

  get_creds()

  # Launch the deployment
  cmd="cd;openstack overcloud deploy -t {} --templates ~/pilot/templates/overcloud -e ~/pilot/templates/network-environment.yaml -e ~/pilot/templates/overcloud/environments/storage-environment.yaml -e /usr/share/openstack-tripleo-heat-templates/environments/puppet-pacemaker.yaml --control-flavor controller --compute-flavor compute --ceph-storage-flavor storage --swift-storage-flavor storage --block-storage-flavor storage --neutron-public-interface bond1 --neutron-network-type vlan --neutron-disable-tunneling --os-auth-url {} --os-project-name {} --os-user-id {} --os-password {} --control-scale {} --compute-scale {} --ceph-storage-scale {} --ntp-server {} --neutron-network-vlan-ranges datacentre:{}".format(
    args.timeout,
    os_auth_url,
    os_tenant_name,
    os_username,
    os_password,
    args.num_controllers,
    args.num_computes,
    args.num_storage,
    args.ntp_server_fqdn,
    args.vlan_range)

  print cmd
  os.system(cmd)


if __name__ == "__main__":
  main()
