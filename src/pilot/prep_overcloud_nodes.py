#!/usr/bin/python

import argparse
import netaddr
import os
import sys


def main():

  parser = argparse.ArgumentParser()
  parser.add_argument("-u", dest="user",
    required=True, help="The user ID of the iDRAC")
  parser.add_argument("-p", dest="password",
    required=True, help="The password of the iDRAC nodes")
  parser.add_argument("-r", dest="ip_range",
    required=True, help="The IP address range of the iDRACs in 1.2.3.4-5.6.7.8 format")
  args = parser.parse_args()

  if args.ip_range.find("-") == -1:
    print "Error: IP range must be in the format of <start_ip>-<end_ip>"
    sys.exit(1)

  start_ip_str, end_ip_str = args.ip_range.split("-",2)
  if not netaddr.valid_ipv4(start_ip_str):
    print "Error: The starting IP is invalid"
    sys.exit(1)

  if not netaddr.valid_ipv4(end_ip_str):
    print "Error: The ending IP is invalid"
    sys.exit(1)

  for current_ip in netaddr.IPRange(start_ip_str, end_ip_str):
    # Power off the node
    cmd="ipmitool -H {} -I lanplus -U {} -P '{}' chassis power off".format(
      str(current_ip),
      args.user,
      args.password)
    print cmd
    os.system(cmd)

    # Set the first boot device to PXE
    cmd="ipmitool -H {} -I lanplus -U {} -P '{}' chassis bootdev pxe options=persistent".format(
      str(current_ip),
      args.user,
      args.password)
    print cmd
    os.system(cmd)


if __name__ == "__main__":
  main()
