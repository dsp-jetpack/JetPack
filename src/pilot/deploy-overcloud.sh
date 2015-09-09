#!/bin/bash -x

openstack overcloud deploy \
  --templates ~/pilot/templates/overcloud \
  -e ~/pilot/templates/overcloud/environments/network-isolation.yaml \
  -e ~/pilot/templates/network-environment.yaml \
  --control-scale 3 \
  --compute-scale 3 \
  --ceph-storage-scale 3 \
  --control-flavor controller \
  --compute-flavor compute \
  --ceph-storage-flavor storage \
  --swift-storage-flavor storage \
  --block-storage-flavor storage \
  --ntp-server clock.redhat.com \
  --neutron-public-interface bond1 \
  --neutron-network-type vlan \
  --neutron-network-vlan-ranges datacentre:201:220 \
  --neutron-disable-tunneling
