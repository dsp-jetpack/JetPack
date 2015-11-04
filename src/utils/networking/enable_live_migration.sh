#!/bin/bash
#
# OpenStack - A set of software tools for building and managing cloud
# computing platforms for public and private clouds.
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


### Enable live migration within libvirt ###
### This script requires execution on each compute to enable compute nodes
### to communicate with each other

# Modify nova.conf to enable live BLOCK mirgration CES-3985
sed -i.bak 's/^#block_migration_flag.*$/block_migration_flag=VIR_MIGRATE_UNDEFINE_SOURCE, VIR_MIGRATE_PEER2PEER, VIR_MIGRATE_LIVE, VIR_MIGRATE_NON_SHARED_INC/' /etc/nova/nova.conf

#Modify /etc/sysconfig/libvirtd to listen for incoming request
sed -i.bak 's/^#LIBVIRTD_ARGS="--listen"/LIBVIRTD_ARGS="--listen"/g' /etc/sysconfig/libvirtd

#Modify /etc/libvirt/libvirtd.conf to accept tcp connections
sed -i.bak 's/^#listen_tls = 0/listen_tls = 0/g' /etc/libvirt/libvirtd.conf
sed -i 's/^#listen_tcp = 1/listen_tcp = 1/g' /etc/libvirt/libvirtd.conf
sed -i 's/^#auth_tcp = "sasl"/auth_tcp = "none"/g' /etc/libvirt/libvirtd.conf

#Restart libvirtd process
systemctl restart libvirtd

#Restart nova compute services
systemctl restart openstack-nova-compute


### Open iptables ports to allow tcp pconnections for libvirtd"
EXISTING_LINE=`iptables -nL | grep "16509"`
if [ ! "$EXISTING_LINE" ]
then
  # Add iptables rule
  LINE_NUM=$((`iptables -nL --line-numbers| grep "port 22" | cut -f1 -d " "` + 1))
  iptables -I INPUT ${LINE_NUM} -p tcp -m multiport --ports 16509 -m comment --comment "libvirt" -j ACCEPT
  iptables -I INPUT ${LINE_NUM} -p tcp -m multiport --ports 49152:49216 -m comment --comment "migration" -j ACCEPT
  service iptables save
  systemctl restart iptables
fi
