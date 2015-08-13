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
RADOSGW_PUBLIC_VIP=${1}
RADOSGW_PRIVATE_VIP=${2}
CONTROLLER01_SNAME=${3}
CONTROLLER01_IP=${4}
CONTROLLER02_SNAME=${5}
CONTROLLER02_IP=${6}
CONTROLLER03_SNAME=${7}
CONTROLLER03_IP=${8}

####################
# Function usage
####################
usage( ) {
cat <<EOF
Usage: $0 <RADOSGW_PUBLIC_VIP> <RADOSGW_PRIVATE_VIP> <CONTROLLER01_SNAME> <CONTROLLER01_IP> <CONTROLLER02_SNAME> <CONTROLLER02_IP> <CONTROLLER03_SNAME> <CONTROLLER03_IP>
EOF
exit -1
}


####################
# Main
####################
[[ $# -lt 8 ]] && usage

if [ ! -f /etc/haproxy/radosgw.cfg ]
then
cat << EOF > /etc/haproxy/radosgw.cfg
listen ceph-radosgw
  bind ${RADOSGW_PUBLIC_VIP}:8087
  bind ${RADOSGW_PRIVATE_VIP}:8087
  mode tcp
  option tcplog
  server ${CONTROLLER01_SNAME} ${CONTROLLER01_IP}:7480 check inter 1s
  server ${CONTROLLER02_SNAME} ${CONTROLLER02_IP}:7480 check inter 1s
  server ${CONTROLLER03_SNAME} ${CONTROLLER03_IP}:7480 check inter 1s
EOF
fi 

EXISTING_LINE=`iptables -nL | grep "8087,7480"`
if [ ! "$EXISTING_LINE" ]
then 
  # Add iptables rule
  LINE_NUM=$((`iptables -nL --line-numbers| grep "80,443" | cut -f1 -d " "` + 1))
  iptables -I INPUT ${LINE_NUM} -p tcp -m multiport --dports 8087,7480 -m comment --comment "001 civet incoming" -j ACCEPT
  service iptables save
  systemctl restart iptables
fi

#Stop haproxy
pcs resource disable haproxy
sleep 1

EXISTING_LINE=`cat /usr/lib/systemd/system/haproxy.service | grep radosgw.cfg`
if [ ! "$EXISTING_LINE" ]
then
  #Add radosgw to HA Proxy serivce 
  systemctl stop haproxy
  echo `systemctl status haproxy` > /tmp/haproxy.status
  sed -i 's/haproxy.cfg/haproxy.cfg -f \/etc\/haproxy\/radosgw.cfg/' /usr/lib/systemd/system/haproxy.service
  systemctl daemon-reload
fi



if  [ ! "`pcs status | grep ip-radosgw`" ] 
then
  #Create VIPS 
  pcs resource create ip-radosgw-prv-${RADOSGW_PRIVATE_VIP} ocf:heartbeat:IPaddr2 ip=${RADOSGW_PRIVATE_VIP} cidr_netmask=32 op monitor interval=10s 
  pcs resource create ip-radosgw-pub-${RADOSGW_PUBLIC_VIP} ocf:heartbeat:IPaddr2 ip=${RADOSGW_PUBLIC_VIP} cidr_netmask=32 op monitor interval=10s 
fi 

#Start haproxy
pcs resource enable haproxy

#Give service time to start -- automation gets to the next step too quiclkly
sleep 5