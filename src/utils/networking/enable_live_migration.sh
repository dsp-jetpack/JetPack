#!/bin/bash


### Enable live migration within libvirt ###
#Modify /etc/sysconfig/libvirtd to listen for incoming request
sed -i.bak 's/^#LIBVIRTD_ARGS="--listen"/LIBVIRTD_ARGS="--listen"/g' /etc/sysconfig/libvirtd

#Modify /etc/libvirt/libvirtd.conf to accept tcp connections
sed -i.bak 's/^#listen_tls = 0/listen_tls = 0/g' /etc/libvirt/libvirtd.conf
sed -i 's/^#listen_tcp = 1/listen_tcp = 1/g' /etc/libvirt/libvirtd.conf
sed -i 's/^#auth_tcp = "sasl"/auth_tcp = "none"/g' /etc/libvirt/libvirtd.conf

#Restart libvirtd process
systemctl restart libvirtd


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
