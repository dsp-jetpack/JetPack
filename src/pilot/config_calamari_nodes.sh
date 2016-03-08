#!/bin/bash
 
############
# Usage 
############
ceph_node_ip="$1"
root_password="$2"
if [ -z "${ceph_node_ip}" ]
then
  echo "Usage: $0 <ceph_node_ip> [root_password]"
  exit 1
fi


############
# Copy Director root keys to Ceph node
############
printf "[INFO] Pushing ssh-keys to Ceph node...\n"
if [ -n "${root_password}" ]
then
  sudo yum -y install sshpass --enablerepo "rhel-7-server-rhceph-1.3-calamari-rpms" 1>&2> /dev/null
  tmp_root_file=`mktemp`
  echo ${root_password} >> ${tmp_root_file}
  /bin/sshpass -f ${tmp_root_file} ssh-copy-id -oStrictHostKeyChecking=no root@${ceph_node_ip} 1>&2> /dev/null
  rm ${tmp_root_file} 
  sleep 3
else
  ssh-copy-id -oStrictHostKeyChecking=no root@${ceph_node_ip} 1>&2> /dev/null
fi

############
# Create Host file for Ceph VM Storage Node
############
printf "\n[INFO] Gathering Calamari MONs and OSDs host data..."
tmp_hostfile=`mktemp`
echo "" > ${tmp_hostfile}
echo "#Entries below generated with Calamari installation." >> ${tmp_hostfile}

calamari_host_clients=`nova list | awk -F'[|=]' '/2/ {print $8 $3}' | awk '/controller|storage/ {print $1}'`
 
for host in ${calamari_host_clients}
do 
  printf "\n[INFO] - gathering host data for client: ${host}..." 
  storage_net_cidr=`grep StorageNetCidr ~/pilot/templates/network-environment.yaml | awk '{print $2}' | sed -e "s/0\//\*\//"`
  storage_net_ip=`ssh -oStrictHostKeyChecking=no heat-admin@${host} "/usr/sbin/ip a | grep ${storage_net_cidr}" | awk -F'[/ ]' '{print $6}'`
  short_name=`ssh heat-admin@${host} 'hostname -s'`
  echo $storage_net_ip $short_name >> ${tmp_hostfile}
done


############
# Prep Ceph VM Storage Node
############
printf "\n[INFO] Pushing Calamari host entries to Ceph node..."
scp -oStrictHostKeyChecking=no ${tmp_hostfile} root@${ceph_node_ip}:/tmp/host_addins &>/dev/null
ssh root@${ceph_node_ip} 'bash -s' <<'ENDSSH'
calamari_hosts=`grep "#Entries below generated with Calamari" /etc/hosts`
if [ -z "${calamari_hosts}" ]
then
   cat /tmp/host_addins >> /etc/hosts
fi
ENDSSH
rm ${tmp_hostfile}


############
# Gather Ceph VM data 
############
printf "\n[INFO] Gathering Ceph VM data..."
ceph_hostname=`ssh root@${ceph_node_ip} 'hostname -s'`
storage_net_cidr=`grep StorageNetCidr ~/pilot/templates/network-environment.yaml | awk '{print $2}' | sed -e "s/0\//\*\//"`
ceph_storage_net_ip=`ssh -oStrictHostKeyChecking=no root@${ceph_node_ip} "/usr/sbin/ip a | grep ${storage_net_cidr}" | awk -F'[/ ]' '{print $6}'`


############
# Prep Ceph Calamari Storage client nodes 
############
printf "\n[INFO] Configuring Calamari clients... "
if [ -n "${calamari_host_clients}" ] 
then
  for host in ${calamari_host_clients}
  do 
    printf "\n[INFO] - configuring client: ${host}..." 
    client_hostname=`ssh heat-admin@${host} 'hostname -s'`

    configured=`ssh heat-admin@${host} "grep '#Entries below generated with Calamari' /etc/hosts"`
    if [ -z "${configured}" ]
    then
       ssh heat-admin@${host} "sudo bash -c $(printf '%q' "echo '#Entries below generated with Calamari installation.' >> /etc/hosts")"
       ssh heat-admin@${host} "sudo bash -c $(printf '%q' "echo '$ceph_storage_net_ip  ${ceph_hostname}' >> /etc/hosts")"
       ssh heat-admin@${host} 'sudo mkdir -p /etc/salt/minion.d'
       ssh heat-admin@${host} "sudo bash -c $(printf '%q' "[[ ! -f /etc/salt/minion.d/calamari.conf ]] && echo 'master: ${ceph_hostname}' > /etc/salt/minion.d/calamari.conf ")"

       if [[ "${client_hostname}" =~ "controller" ]]
       then 
         ssh heat-admin@${host} "sudo /usr/sbin/iptables -I INPUT 1 -p tcp -m multiport --dport 6800:7300 -j ACCEPT"
         ssh heat-admin@${host} "sudo service iptables save" 1>&2> /dev/null
       fi

       if [[ "${client_hostname}" =~ "storage" ]]
       then 
         ssh heat-admin@${host} "sudo /usr/sbin/iptables -I INPUT 1 -p tcp --dport 6879 -j ACCEPT"
         ssh heat-admin@${host} "sudo service iptables save" 1>&2> /dev/null
       fi
       ssh heat-admin@${host} 'sudo systemctl start salt-minion'
    else
       ssh heat-admin@${host} 'sudo systemctl restart salt-minion'
    fi
  done
fi


############
# Restart the salt-master services on the Ceph VM node
############
printf "\n[INFO] Restarting salt services... "
ssh root@${ceph_node_ip} 'bash -s' <<'ENDSSH'
/bin/systemctl stop salt-master
/bin/systemctl start salt-master
/usr/bin/salt-key -y -q -A 1>&2> /dev/null
ENDSSH


############
# Prompt the user to take final steps on the Ceph VM node to finish the installation or Initialize Calamari.
############
printf "\n[INFO] Calamari configuration steps are complete.\n"
if [ -z "${root_password}" ]
then
  printf "\nLogon to the Ceph Admin Node as root and run 'calamari-ctl initialize'.\n\n"
else
  printf "[INFO] Final Steps -- Initializing Calamari...\n"
  local_hostname=`ssh root@${ceph_node_ip} "hostname"`
  ssh root@${ceph_node_ip} "calamari-ctl initialize --admin-username root --admin-password ${root_password} --admin-email root@${local_hostname}"
fi
