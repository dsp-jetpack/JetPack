#!/usr/bin/python

import argparse
import distutils.dir_util
import os
import re
import subprocess
import sys
import time

from subprocess import check_output

# Dell utilities
from identify_nodes import main as identify_nodes
from update_ssh_config import main as update_ssh_config

home_dir = os.path.expanduser('~')


def get_creds():
  global os_username
  global os_password
  global os_auth_url
  global os_tenant_name

  creds_file = open(home_dir + '/stackrc', 'r')

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


def subst_home(relative_path):
  in_file_name = os.path.join(home_dir, relative_path)
  out_file_name = in_file_name + '.out'

  in_file = open(in_file_name, 'r')
  out_file = open(out_file_name, 'w')

  for line in in_file:
    line = re.sub("HOME", home_dir, line)
    out_file.write(line)

  in_file.close()
  out_file.close()

  os.rename(in_file_name, in_file_name + '.bak')
  os.rename(out_file_name, in_file_name)

def create_volume_types(types):
    for type in types:
        cmd = "source $HOME/overcloudrc && " \
              "cinder type-create {} && " \
              "cinder type-key {} set volume_backend_name={}" \
              "".format(type[0], type[0], type[1])
        os.system(cmd)

    os.system('source $HOME/overcloudrc && cinder extra-specs-list')


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
    default="120", help="The amount of time in minutes to allow the overcloud to deploy")
  parser.add_argument('--enable_eqlx', action='store_true', default=False, 
    help="Enable cinder Dell Eqlx backend")
  parser.add_argument('--enable_dellsc', action='store_true', default=False,
    help="Enable cinder Dell Storage Center backend")
  parser.add_argument('--static_ips', action='store_true', default=False,
    help="Specify the IPs and VIPs on the controller nodes")
  args = parser.parse_args()
  p = re.compile('\d+:\d+')
  if not p.match(args.vlan_range):
    print("Error: The VLAN range must be a number followed by a colon, followed by another number")
    sys.exit(1)
  get_creds()

  # Replace HOME with the actual home directory in a few files
  subst_home('pilot/templates/dell-environment.yaml')
  subst_home('pilot/templates/static-ip-environment.yaml')
  subst_home('pilot/templates/network-environment.yaml')
  subst_home('pilot/templates/dell-dellsc-environment.yaml')
  subst_home('pilot/templates/dell-eqlx-environment.yaml')


  # Recursively copy pilot/templates/overrides to pilot/templates/overcloud
  overrides_dir = os.path.join(home_dir, 'pilot/templates/overrides')
  overcloud_dir = os.path.join(home_dir, 'pilot/templates/overcloud')
  distutils.dir_util.copy_tree(overrides_dir, overcloud_dir)

  # Launch the deployment

  # The order of the environment files is important as a later inclusion
  # overrides resources defined in prior inclusions.

  # The network-environment.yaml must be included after the network-isolation.yaml
  env_opts = "-e ~/pilot/templates/overcloud/environments/network-isolation.yaml" \
             " -e ~/pilot/templates/network-environment.yaml"

  # The static-ip-environment.yaml must be included after the network-environment.yaml
  if args.static_ips:
    env_opts += " -e ~/pilot/templates/static-ip-environment.yaml"

  # The dell-environment.yaml must be included after the storage-environment.yaml
  env_opts += " -e ~/pilot/templates/overcloud/environments/storage-environment.yaml" \
              " -e ~/pilot/templates/dell-environment.yaml" \
              " -e /usr/share/openstack-tripleo-heat-templates/environments/puppet-pacemaker.yaml"

  if args.enable_dellsc | args.enable_eqlx:
    env_opts += " -e ~/pilot/templates/dell-cinder-backends.yaml"

  cmd = "cd ; openstack overcloud deploy" \
        " --debug" \
        " --log-file ~/pilot/overcloud_deployment.log" \
        " -t {}" \
        " --templates ~/pilot/templates/overcloud" \
        " {}" \
        " --control-flavor control" \
        " --compute-flavor compute" \
        " --ceph-storage-flavor ceph-storage" \
        " --swift-storage-flavor swift-storage" \
        " --block-storage-flavor block-storage" \
        " --neutron-public-interface bond1" \
        " --neutron-network-type vlan" \
        " --neutron-disable-tunneling" \
        " --os-auth-url {}" \
        " --os-project-name {}" \
        " --os-user-id {}" \
        " --os-password {}" \
        " --control-scale {}" \
        " --compute-scale {}" \
        " --ceph-storage-scale {}" \
        " --ntp-server {}" \
        " --neutron-network-vlan-ranges physint:{},physext" \
        " --neutron-bridge-mappings physint:br-tenant,physext:br-ex" \
        "".format (args.timeout,
                   env_opts,
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
  start = time.time()
  os.system(cmd)
  end = time.time()
  print '\nExecution time: {} (hh:mm:ss)'.format(time.strftime('%H:%M:%S', time.gmtime(end - start)))
  print 'Creating cinder volume types ...'
  types = [["rbd_backend","tripleo_ceph"]]
  if args.enable_eqlx:
      types.append(["eql_backend","tripleo_eqlx"])
  if args.enable_dellsc:
      types.append(["dellsc_backend","tripleo_dellsc"])
  create_volume_types(types)
  print 'Fetching SSH keys...'
  update_ssh_config()
  print 'Overcloud nodes:'
  identify_nodes()

  try:
    # Data will look like this: '"http://192.168.190.127:5000/v2.0"\n'
    data = subprocess.check_output('heat output-show overcloud KeystoneURL'.split())
    keystone_url = data.translate(None, '"\n')
    # Form the Dashboard URL by trimming everything after the trailing ':'
    print '\nHorizon Dashboard URL: {}\n'.format(keystone_url[:keystone_url.rfind(':'):])
  except:
    # In case the overcloud failed to deploy
    pass

if __name__ == "__main__":
  main()
