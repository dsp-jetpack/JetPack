#!/usr/bin/python

import argparse
import os
import sys

from ironicclient import client
from oslo_config import cfg
from subprocess import call
from subprocess import check_output

CONF = cfg.CONF


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
  parser.add_argument("mac", help="The MAC address of the node")
  parser.add_argument("role",
                      help="The role that the node will play (valid values " +
                           "are \"controller\", \"compute\", and " +
                           "\"storage\")")
  args = parser.parse_args()

  get_creds()

  # Get the UUID of the node
  kwargs = {'os_username': os_username,
            'os_password': os_password,
            'os_auth_url': os_auth_url,
            'os_tenant_name': os_tenant_name}
  ironic = client.get_client(1, **kwargs)

  port = ironic.port.get_by_address(args.mac)
  node_uuid = port.node_uuid

  # Assign the role to the node
  DEVNULL = open(os.devnull, 'w')

  print "Setting role for {} to {}".format(args.mac, args.role)
  props = "properties/capabilities=profile:{},boot_option:local".format(
    args.role)
  return_code = call(["ironic", "node-update", node_uuid, "add", props],
                     stdout=DEVNULL)
  if return_code != 0:
    print "Unable to set the profile to {} on the node.".format(args.role)
    sys.exit(return_code)

  # Configure the BIOS settings for the node in Ironic
  #db = cmdb.load_cmdb(CONF.edeploy.configdir, args.role)
  #bios_settings = db[0]['bios_settings']

  #return_code = call(["ironic", "node-update", node_uuid, "add",
                      #"extra/bios_settings={}"], stdout=DEVNULL)
  #if return_code != 0:
    #sys.exit(return_code)

  #print "Loading {} BIOS settings for {}:".format(args.role, args.mac)
  #for setting, val in iter(sorted(bios_settings.items())):
    #print "  Setting {}={}".format(setting, val)
    #return_code = call(["ironic", "node-update", node_uuid, "add",
                        #"extra/bios_settings/{}={}".format(setting, val)],
                        #stdout=DEVNULL)
    #if return_code != 0:
      #sys.exit(return_code)

  # Configure the RAID settings for the node in Ironic
  # TODO

if __name__ == "__main__":
  main()
