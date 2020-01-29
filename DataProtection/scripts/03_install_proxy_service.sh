#!/bin/sh

CONTROLLERS=`openstack server list --name "controller" -f value -c Name -c Networks | awk -F= '{print $2}'`
PACKAGE="epel-release-latest-7.noarch.rpm dpe-proxy-service-19.2.0.89-1.noarch.rpm"

for ip in $CONTROLLERS
do
  for rpm in $PACKAGE
  do
    echo "Installing $rpm on Controller with IP $ip..."
    ssh -oStrictHostKeyChecking=no heat-admin@${ip} "sudo yum install -y $rpm"
  done
  echo "Enabling dpe-proxy-service on Controller with IP $ip..."
  ssh -oStrictHostKeyChecking=no heat-admin@${ip} "sudo systemctl enable dpe-proxy-service"
done

