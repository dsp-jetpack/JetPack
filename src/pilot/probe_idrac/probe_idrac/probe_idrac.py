#!/usr/bin/python

import dracclient.wsman
import lxml

import requests
requests.packages.urllib3.disable_warnings()

def main():
  client = dracclient.wsman.Client('192.168.120.234', 'root', 'cr0wBar!')
  response = client.enumerate('http://schemas.dell.com/wbem/wscim/1/cim-schema/2/DCIM_SystemView')
  print lxml.etree.tostring(response, pretty_print=True)
  response = client.enumerate('http://schemas.dell.com/wbem/wscim/1/cim-schema/2/DCIM_VirtualDiskView')
  print lxml.etree.tostring(response, pretty_print=True)
  response = client.enumerate('http://schemas.dell.com/wbem/wscim/1/cim-schema/2/DCIM_CPUView')
  print lxml.etree.tostring(response, pretty_print=True)
  response = client.enumerate('http://schemas.dell.com/wbem/wscim/1/cim-schema/2/DCIM_NICView')
  print lxml.etree.tostring(response, pretty_print=True)

if __name__ == "__main__": 
  main() 
