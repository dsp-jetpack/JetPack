#!/bin/sh

CONTROLLERS=`. ~/stackrc; openstack server list --name "controller" -f value -c Name -c Networks | awk -F= '{print $2}'`
FILE="../rpms/CENTOS7_64/dpe-horizon-plugin-19.2.0.89-1.tar.gz"

for ip in $CONTROLLERS
do
  echo "Copying Dell EMC dashboard to controller with IP $ip..."
  scp -oStrictHostKeyChecking=no $FILE heat-admin@${ip}:~/

  echo "Copying Dell EMC dashboard into horizon container on controller with IP $ip..."
  ssh -oStrictHostKeyChecking=no heat-admin@${ip} /bin/sh << EOF
    sudo docker cp /home/heat-admin/dpe-horizon-plugin-19.2.0.89-1.tar.gz horizon:/
EOF
done
