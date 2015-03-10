#! /bin/bash

[[ ${#@} != 2 ]] && echo "This script requires two parameters, a configuration file as the first parameter and the location of the installation ISO as the second parameter." && exit

cfg_file=$1
location=$2

cat <<'EOFKS' > /tmp/foreman.ks

install
text
cdrom
reboot

# Partitioning
ignoredisk --only-use=vda
zerombr
bootloader --boot-drive=vda
clearpart --all

part /boot --fstype=ext4 --size=500
part pv.01 --size=8192 --grow

volgroup VolGroup --pesize=4096 pv.01

logvol / --fstype=ext4 --name=lv_root --vgname=VolGroup --grow --size=1024
logvol swap --name=lv_swap --vgname=VolGroup --size=1024

keyboard --vckeymap=us --xlayouts='us'
lang en_US.UTF-8

auth --enableshadow --passalgo=sha512

%include /tmp/ks_include.txt

skipx
firstboot --disable
eula --agreed

%packages
@core
-NetworkManager
-NetworkManager-*
ntp
ntpdate
-chrony
system-config-firewall-base
yum-plugin-versionlock
%end

%pre --log /tmp/foreman-pre.log
EOFKS


{ 
ntp=""

while read iface ip mask bridge
do
  flag=""

  [[ ${iface} == rootpassword ]] && echo "echo rootpw ${ip} >> /tmp/ks_include.txt"
  [[ ${iface} == timezone ]] && echo "echo timezone ${ip} --utc >> /tmp/ks_include.txt"

  [[ ${iface} == hostname ]] && {
    HostName=${ip} 
    echo "echo HostName=${ip} >> /tmp/ks_post_include.txt"
    }

  [[ ${iface} == nameserver ]] && {
    NameServers=${ip} 
    echo "echo NameServers=${ip} >> /tmp/ks_post_include.txt"
    }

  [[ ${iface} == gateway ]] && {
    Gateway=${ip} 
    echo "echo Gateway=${ip} >> /tmp/ks_post_include.txt"
    }

  [[ ${iface} == ntpserver ]] && echo "echo NTPServer=${ip} >> /tmp/ks_post_include.txt"
  [[ ${iface} == smuser ]] && echo "echo SMUser=${ip} >> /tmp/ks_post_include.txt"
  [[ ${iface} == smpassword ]] && echo "echo SMPassword=\'${ip}\' >> /tmp/ks_post_include.txt"
  [[ ${iface} == smpool ]] && echo "echo SMPool=${ip} >> /tmp/ks_post_include.txt"

  [[ ${iface} == smproxy ]] && echo "echo SMProxy=${ip} >> /tmp/ks_post_include.txt"
  [[ ${iface} == smproxyuser ]] && echo "echo SMProxyUser=${ip} >> /tmp/ks_post_include.txt"
  [[ ${iface} == smproxypassword ]] && echo "echo SMProxyPassword=${ip} >> /tmp/ks_post_include.txt"

  [[ ${iface} == eth0 ]] && { 
    echo "echo network --activate --onboot=true --noipv6 --device=${iface} --bootproto=static --ip=${ip} --netmask=${mask} --hostname=${HostName} --gateway=${Gateway} --nameserver=${NameServers} >> /tmp/ks_include.txt"
    }

  [[ ${iface} == eth1 ]] && { 
    echo "echo network --activate --onboot=true --noipv6 --device=${iface} --bootproto=static --ip=${ip} --netmask=${mask} --gateway=${Gateway} --nodefroute >> /tmp/ks_include.txt"
    }
done <<< "$( grep -Ev "^#|^;|^\s*$" ${cfg_file} )"
} >> /tmp/foreman.ks

cat <<'EOFKS' >> /tmp/foreman.ks
%end

%post --nochroot --logfile /root/foreman-post.log
# Copy the files created during the %pre section to /root of the installed system for later use.
  cp -v /tmp/foreman-pre.log /mnt/sysimage/root
  cp -v /tmp/ks_include.txt /mnt/sysimage/root
  cp -v /tmp/ks_post_include.txt /mnt/sysimage/root
%end


%post

exec < /dev/tty8 > /dev/tty8
chvt 8

(
  # Source the variables from the %pre section
  . /root/ks_post_include.txt

  # Configure name resolution
  for ns in ${NameServers//,/ }
  do
    echo "nameserver ${ns}" >> /etc/resolv.conf
  done

  echo "GATEWAY=${Gateway}" >> /etc/sysconfig/network

  sed -i -e '/^DNS/d' -e '/^GATEWAY/d' /etc/sysconfig/network-scripts/ifcfg-eth0
  sed -i -e '/^DNS/d' -e '/^GATEWAY/d' /etc/sysconfig/network-scripts/ifcfg-eth1

  echo "$( ip addr show dev eth0 | awk '/inet / { print $2 }' | sed 's/\/.*//' )  ${HostName}" >> /etc/hosts

  echo "----------------------"
  ip addr
  echo "subscription-manager register --username ${SMUser} --password ********"
  echo "----------------------"

# Register the system using Subscription Manager
  [[ ${SMProxy} ]] && {
    ProxyInfo="--proxy ${SMProxy}"

    [[ ${SMProxyUser} ]] && ProxyInfo+=" --proxyuser ${SMProxyUser}"
    [[ ${SMProxyPassword} ]] && ProxyInfo+=" --proxypassword ${SMProxyPassword}"
    }

  subscription-manager register --username ${SMUser} --password ${SMPassword} ${ProxyInfo}


  SMPool=""

  [[ x${SMPool} = x ]] \
    && SMPool=$( subscription-manager list --available | awk '/OpenStack/,/Pool/ {pool = $3} END {print pool}' )

  [[ -n ${SMPool} ]] \
    && subscription-manager attach --pool ${SMPool} \
    || ( echo "Could not find an OpenStack pool to attach to. - Auto-attaching to any pool." \
         subscription-manager attach --auto
         )


  subscription-manager repos --disable=*
  subscription-manager repos --enable=rhel-7-server-rpms
  subscription-manager repos --enable=rhel-server-rhscl-7-rpms
  subscription-manager repos --enable=rhel-7-server-openstack-6.0-installer-rpms
  subscription-manager repos --enable=rhel-7-server-openstack-6.0-rpms

  # When the ceph solution is refreshed, the following line can be removed
  # Workaround for broken vlock obsolete processing
  sed -i 's/^\[main\]/\[main\]\nexclude=python-rados python-rbd/' /etc/yum.conf

  mkdir /tmp/mnt
  mount /dev/fd0 /tmp/mnt
  [[ -e /tmp/mnt/versionlock.list ]] && {
    cp /tmp/mnt/versionlock.list /etc/yum/pluginconf.d
    chmod 644 /etc/yum/pluginconf.d/versionlock.list
    }
  umount /tmp/mnt

  yum -y install openstack-foreman-installer
  yum -y install ceph-common
  yum -y update

  # Firewall rules to allow traffic for the http, https, dns, and tftp services and tcp port 8140.
  # Also accept all traffic from eth1 to pass through to eth0 and become NAT'd on the way out of eth0.

  cat <<EOIP > /etc/sysconfig/iptables
*nat
:PREROUTING ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
:POSTROUTING ACCEPT [0:0]
-A POSTROUTING -o eth0 -j MASQUERADE
COMMIT
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -i eth1 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 22 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 443 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 53 -j ACCEPT
-A INPUT -m state --state NEW -m udp -p udp --dport 53 -j ACCEPT
-A INPUT -m state --state NEW -m udp -p udp --dport 69 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 8140 -j ACCEPT
-A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
-A FORWARD -p icmp -j ACCEPT
-A FORWARD -i lo -j ACCEPT
-A FORWARD -i eth1 -j ACCEPT
-A FORWARD -o eth0 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp-host-prohibited
-A FORWARD -j REJECT --reject-with icmp-host-prohibited
COMMIT
EOIP


  systemctl enable iptables

  sed -i -e "/^net.ipv4.ip_forward/d" /etc/sysctl.conf
  echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
  sysctl -p

  sed -i -e "s/^SELINUX=.*/SELINUX=permissive/" /etc/selinux/config

  # Configure the ntp daemon
  chkconfig ntpd on
  sed -i -e "/^server /d" /etc/ntp.conf

  for ntps in ${NTPServers//,/ }
  do
    echo "server ${ntps}" >> /etc/ntp.conf
  done


#  sed -i "/^class.*'foreman'.*/aconfigure_epel_repo => false," /usr/share/openstack-foreman-installer/bin/foreman_server.sh
#  sed -i '/read -p/d' /usr/share/openstack-foreman-installer/bin/foreman_server.sh

  systemctl disable NetworkManager
  systemctl disable firewalld

) 2>&1 | /usr/bin/tee -a /root/foreman-posts.log

chvt 1

%end

EOFKS


[[ ! -e /store/data/images ]] && mkdir -p /store/data/images


[[ -e foreman_vm.vlock ]] && {

  [[ -e /tmp/floppy-foreman.img ]] && rm -rf /tmp/floppy-foreman.img
  mkfs.vfat -C /tmp/floppy-foreman.img 1440
  mkdir /tmp/mnt-foreman
  mount -o loop /tmp/floppy-foreman.img /tmp/mnt-foreman
  cp foreman_vm.vlock /tmp/mnt-foreman/versionlock.list
  sync
  umount /tmp/mnt-foreman
  rmdir /tmp/mnt-foreman

  virt-install --name foreman \
    --ram 4096 \
    --vcpus 2 \
    --hvm \
    --os-type linux \
    --os-variant rhel6 \
    --disk /store/data/images/foreman.img,bus=virtio,size=16 \
    --disk /tmp/floppy-foreman.img,device=floppy \
    --network bridge=public \
    --network bridge=provision \
    --initrd-inject /tmp/foreman.ks \
    --extra-args "ks=file:/foreman.ks" \
    --noautoconsole \
    --graphics spice \
    --autostart \
    --location ${location} 
  } || {

virt-install --name foreman \
  --ram 4096 \
  --vcpus 2 \
  --hvm \
  --os-type linux \
  --os-variant rhel6 \
  --disk /store/data/images/foreman.img,bus=virtio,size=16 \
  --network bridge=public \
  --network bridge=provision \
  --initrd-inject /tmp/foreman.ks \
  --extra-args "ks=file:/foreman.ks" \
  --noautoconsole \
  --graphics spice \
  --autostart \
  --location ${location}
  }

