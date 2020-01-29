#!/bin/sh

CONTROLLERS=`. ~/stackrc; openstack server list --name "controller" -f value -c Name -c Networks | awk -F= '{print $2}'`

for ip in $CONTROLLERS
do
    echo "Allowing trafic on port 1947 and 8443 on controller with IP $ip..."
    ssh -oStrictHostKeyChecking=no heat-admin@${ip} /bin/sh << EOF
      sudo iptables -I INPUT -p tcp --dport 1947 -j ACCEPT
      sudo iptables -I OUTPUT -p tcp --dport 1947 -j ACCEPT
      sudo iptables -I INPUT -p tcp --dport 8443 -j ACCEPT
      sudo iptables -I OUTPUT -p tcp --dport 8443 -j ACCEPT
      sudo service iptables save
EOF
done

