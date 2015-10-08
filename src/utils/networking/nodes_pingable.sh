#!/bin/bash
#
# OpenStack - A set of software tools for building and managing cloud computing
# platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.
#

# This script just tests to see if the nodes are pingable across the RA VLANs from
# the Foreman VM Host.  This script should be executed on the Foreman node.
# Note this script only validates ping connectivity,
#
# In some instances, the nodes will not be pingable as not all VLANs are connected
# to all hosts.
#
# Our current RA calls for the following VLANs
#   120=provisioner, 140=private API, 170=storage, 180=ceph cluster, 190=nova public

PUBLIC_NET_PREFIX="10.149.44"
PRIVATE_NET_PREFIX="10.149"
PRIVATE_NET_VLANS="120 140 170 180 190"
NODE_IPS="74 75 76 77 78 79 80 81 83"

#The following tests that the VLANs are pingable
for vlan in `echo $PRIVATE_NET_VLANS`
do
  if find /etc/sysconfig/network-scripts/*.$vlan >&/dev/null
  then
     echo "Found VLAN: $vlan -- Testing IPs $NODE_IPS are pingable."
     for ip in `echo $NODE_IPS`
     do
       ping -c 1 ${PRIVATE_NET_PREFIX}.$vlan.$ip
     done
     echo ""
  else
    echo "VLAN $vlan not defined."
  fi
echo ""
done


#The following tests that the public IPs are pingable
echo ""
echo "Testing public IPs $NODE_IPS are pingable."
for ip in `echo $NODE_IPS`
do
  ping -c 1 ${PUBLIC_NET_PREFIX}.$ip
done