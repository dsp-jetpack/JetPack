#/bin/sh

CONTROLLERS=`openstack server list --name "controller" -f value -c Name -c Networks | awk -F= '{print $2}'`

for ip in $CONTROLLERS
do
  echo "Connecting to controller with IP" $ip
  ssh -oStrictHostKeyChecking=no heat-admin@${ip} /bin/sh << EOF
    sudo crudini --set /var/lib/config-data/puppet-generated/nova/etc/nova/nova.conf DEFAULT metadata_host 192.168.140.201
    sudo docker restart nova_metadata
    sudo crudini --set /var/lib/config-data/puppet-generated/neutron/etc/neutron/dhcp_agent.ini DEFAULT enable_isolated_metadata true
    sudo crudini --set /var/lib/config-data/puppet-generated/neutron/etc/neutron/dhcp_agent.ini DEFAULT enable_metadata_network true
    sudo docker restart neutron_dhcp
EOF
done

