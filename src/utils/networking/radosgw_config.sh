#!/bin/bash
# Copyright 2015, Dell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Version: 1.0
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
else 
  echo "Nothing to do -- Iptables rule for ports 8087 and 7480 already exist"
fi


if  [ ! "`pcs status | grep ip-radosgw`" ] 
then
  #Stop haproxy
  pcs resource disable haproxy

  #Add radosgw to HA Proxy serivce 
  sed -i 's/haproxy.cfg/haproxy.cfg -f \/etc\/haproxy\/radosgw.cfg/' /usr/lib/systemd/system/haproxy.service
  systemctl daemon-reload

  #Create VIPS 
  pcs resource create ip-radosgw-prv-${RADOSGW_PRIVATE_VIP} ocf:heartbeat:IPaddr2 ip=${RADOSGW_PRIVATE_VIP} cidr_netmask=32 op monitor interval=10s 
  pcs resource create ip-radosgw-pub-${RADOSGW_PUBLIC_VIP} ocf:heartbeat:IPaddr2 ip=${RADOSGW_PUBLIC_VIP} cidr_netmask=32 op monitor interval=10s 
  pcs resource enable haproxy
else
  echo "Nothing to do -- PCS radosgw services already installed"
fi 
