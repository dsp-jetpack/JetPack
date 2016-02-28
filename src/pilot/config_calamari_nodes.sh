#!/bin/bash

ceph_node_ip="$1"
if [ -z "${ceph_node_ip}" ];
then
  echo "Usage: $0 <ceph_node_ip>"
  exit 1
fi

#Create Host file for Ceph VM Storage Node
tmp_hostfile=/tmp/$(tr -dc 'A-Z0-9' < /dev/urandom | head -c8)
echo "" > $tmp_hostfile
echo "Entries below generated with Calamari installation." >> $tmp_hostfile

calamari_host_clients=`nova list | awk -F'[|=]' '/2/ {print $8 $3}' | awk '/controller|storage/' | awk '{print $1}'`
 
printf "[INFO] Gathering Calamari MONs and OSDs node information: "
for host in $calamari_host_clients
do 
  printf "."
  storage_net_ip=`ssh -oStrictHostKeyChecking=no heat-admin@$host '/usr/sbin/ip a | grep 170.*\/24' | awk -F'[/ ]' '{print $6}'`
  printf "."
  short_name=`ssh heat-admin@$host 'hostname -s'`
  echo $storage_net_ip $short_name >> $tmp_hostfile
done


#Prep Ceph VM Storage Node
printf "\n[INFO] Pushing ssh-keys to Ceph node."
cmd="if [ ! -d ~heat-admin/.ssh ]; then mkdir ~heat-admin/.ssh; cd ~heat-admin/.ssh; cp ~root/.ssh/authorized_keys .; chown -R heat-admin:heat-admin ~heat-admin/.ssh; chmod 700 ~heat-admin/.ssh; fi"
ssh root@${ceph_node_ip} $cmd 

printf "\n[INFO] Pushing Calamari host entries to Ceph node."
scp -oStrictHostKeyChecking=no $tmp_hostfile root@${ceph_node_ip}:/tmp/host_addins
ssh root@${ceph_node_ip} 'bash -s' <<'ENDSSH'
calamari_hosts=`grep "Entries below generated with Calamari" /etc/hosts`
if [ -z "$calamari_hosts" ]
then
   cat /tmp/host_addins >> /etc/hosts
fi
ENDSSH

printf "[INFO] Configuring Calamari clients: "
ceph_hostname=`ssh root@${ceph_node_ip} 'hostname -s'`
ceph_storage_net_ip=`ssh -oStrictHostKeyChecking=no heat-admin@${ceph_node_ip} '/usr/sbin/ip a | grep 170.*\/24' | awk -F'[/ ]' '{print $6}'`

if [ -n "$calamari_host_clients" ] 
then
  for host in $calamari_host_clients
  do 
    ssh heat-admin@$host "sudo bash -c $(printf '%q' "echo '$ceph_storage_net_ip  $ceph_hostname' >> /etc/hosts")"
    ssh -oStrictHostKeyChecking=no heat-admin@$host 'sudo mkdir -p /etc/salt/minion.d'
    ssh heat-admin@$host "bash -c $(printf '%q' "[[ ! -f /etc/salt/minion.d/calamari.conf ]] && echo 'master: $ceph_hostname' > /etc/salt/minion.d/calamari.conf ")"

    if [[ "$host" =~ "controller" ]]
    then 
      ssh heat-admin@$host 'sudo /usr/sbin/iptables -I INPUT 1 -p tcp -m multiport --dports 6800:7300 -j ACCEPT'
      ssh heat-admin@$host 'sudo service iptables save'
    fi

    if [[ "$host" =~ "storage" ]]
    then 
      ssh heat-admin@$host 'sudo /usr/sbin/iptables -I INPUT 1 -p tcp --dports 6879 -j ACCEPT'
      ssh heat-admin@$host 'sudo service iptables save'
    fi
    ssh heat-admin@$host 'sudo systemctl start salt-minion'
    printf "."
  done
fi

ssh root@${ceph_node_ip} 'bash -s' <<'ENDSSH2'
/bin/systemctl stop salt-master
/bin/systemctl start salt-master
printf "\n[INFO] Calamari configuration steps are complete."
printf "\n\nLogon to the Ceph Admin Node as root and run 'calamari-ctl initialize'."
printf "\nWhen the initialization is complete, login to Calamari via a web browser and accept the OSD and MON nodes.\n\n"
ENDSSH2
