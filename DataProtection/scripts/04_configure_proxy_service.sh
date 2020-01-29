#!/bin/sh

CONTROLLERS=`. ~/stackrc; openstack server list --name "controller" -f value -c Name -c Networks | awk -F= '{print $2}'`
FILE="../templates/proxy-owner1.conf"

for ip in $CONTROLLERS
do
  echo "Copying DPE configuration file to controller with IP $ip..."
  scp -oStrictHostKeyChecking=no $FILE heat-admin@${ip}:~/

  ssh -oStrictHostKeyChecking=no heat-admin@${ip} /bin/sh << EOF
    sudo cp /home/heat-admin/proxy-owner1.conf /etc/avamar/
EOF

  echo "Patching nova configuration file on controller with IP $ip..."
  ssh -oStrictHostKeyChecking=no heat-admin@${ip} /bin/sh << EOF
    sudo chmod o+r /usr/share/nova/nova-dist.conf
    sudo rm -f /etc/nova/nova.conf
    sudo chmod o+r /var/lib/config-data/puppet-generated/nova/etc/nova/nova.conf
    sudo ln -s /var/lib/config-data/puppet-generated/nova/etc/nova/nova.conf /etc/nova/nova.conf
EOF
  echo "Starting dpe-proxy-service on controller with IP $ip..."
  ssh -oStrictHostKeyChecking=no heat-admin@${ip} 'sudo systemctl start dpe-proxy-service'
done


