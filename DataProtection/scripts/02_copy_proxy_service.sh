#!/bin/sh

CONTROLLERS=`openstack server list --name "controller" -f value -c Name -c Networks | awk -F= '{print $2}'`
PACKAGE="../rpms/epel-release-latest-7.noarch.rpm ../rpms/CENTOS7_64/dpe-proxy-service-19.2.0.89-1.noarch.rpm"

for ip in $CONTROLLERS
do
  for rpm in $PACKAGE
  do
     echo "Copying $rpm to Controller with IP $ip..."
     scp -oStrictHostKeyChecking=no $rpm heat-admin@${ip}:~/
  done
done

