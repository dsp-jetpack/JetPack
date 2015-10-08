#! /bin/bash
#
# OpenStack - A set of software tools for building and managing cloud computing
# platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.
#

[[ ${#@} != 2 ]] && echo "This script requires two parameters, a configuration file as the first parameter and the location of the installation ISO as the second parameter." && exit

cfg_file=$1
location=$2

cat <<'EOFKS' > /tmp/ceph.ks

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
ntp
ntpdate
-chrony
-firewalld
-NetworkManager
-NetworkManager-*
system-config-firewall-base
iptables
iptables-services
yum-plugin-versionlock
yum-utils
%end

%pre --log /tmp/ceph-pre.log
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

  [[ ${iface} == ntpserver ]] && echo "echo NTPServers=${ip} >> /tmp/ks_post_include.txt"
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
} >> /tmp/ceph.ks

cat <<'EOFKS' >> /tmp/ceph.ks
%end

%post --nochroot --logfile /root/ceph-post.log
# Copy the files created during the %pre section to /root of the installed system for later use.
  cp -v /tmp/ceph-pre.log /mnt/sysimage/root
  cp -v /tmp/ks_include.txt /mnt/sysimage/root
  cp -v /tmp/ks_post_include.txt /mnt/sysimage/root
  mkdir -p /mnt/sysimage/root/ceph-ks-logs
  cp -v /tmp/ceph-pre.log /mnt/sysimage/root/ceph-ks-logs
  cp -v /tmp/ks_include.txt /mnt/sysimage/root/ceph-ks-logs
  cp -v /tmp/ks_post_include.txt /mnt/sysimage/root/ceph-ks-logs  
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
  echo "subscription-manager register --username ${SMUser} --password *********"
  echo "----------------------"

# Register the system using Subscription Manager
  [[ ${SMProxy} ]] && {
    ProxyInfo="--proxy ${SMProxy}"

    [[ ${SMProxyUser} ]] && ProxyInfo+=" --proxyuser ${SMProxyUser}"
    [[ ${SMProxyPassword} ]] && ProxyInfo+=" --proxypassword ${SMProxyPassword}"
    }

  subscription-manager register --username ${SMUser} --password ${SMPassword} ${ProxyInfo}

  [[ x${SMPool} = x ]] \
    && SMPool=$( subscription-manager list --available | awk '/Red Hat Enterprise Linux Server/,/Pool/ {pool = $3} END {print pool}' )

  [[ -n ${SMPool} ]] \
    && subscription-manager attach --pool ${SMPool} \
    || ( echo "Could not find a Red Hat Enterprise Linux Server pool to attach to. - Auto-attaching to any pool." \
         subscription-manager attach --auto
         )

  subscription-manager repos --disable=*
  subscription-manager repos --enable=rhel-7-server-rpms 
  subscription-manager repos --enable=rhel-7-server-rhceph-1.3-calamari-rpms 
  subscription-manager repos --enable=rhel-7-server-rhceph-1.3-installer-rpms 
  subscription-manager repos --enable=rhel-7-server-rhceph-1.3-mon-rpms 
  subscription-manager repos --enable=rhel-7-server-rhceph-1.3-osd-rpms

  cat <<EOIP > /etc/sysconfig/iptables
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT
-A INPUT -p icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -p tcp -m state --state NEW -m tcp --dport 22 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 443 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 2003 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 4505 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 4506 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp-host-prohibited
-A FORWARD -j REJECT --reject-with icmp-host-prohibited
COMMIT
EOIP

  systemctl enable iptables


  sed -i -e "s/^SELINUX=.*/SELINUX=permissive/" /etc/selinux/config

  # Configure the ntp daemon
  systemctl enable ntpd
  sed -i -e "/^server /d" /etc/ntp.conf

  for ntps in ${NTPServers//,/ }
  do
    echo "server ${ntps}" >> /etc/ntp.conf
  done

  mkdir /tmp/mnt
  mount /dev/fd0 /tmp/mnt
  [[ -e /tmp/mnt/versionlock.list ]] && {
    cp /tmp/mnt/versionlock.list /etc/yum/pluginconf.d
    chmod 644 /etc/yum/pluginconf.d/versionlock.list
    }

  yum -y update

  systemctl disable NetworkManager
  systemctl disable firewalld
  systemctl disable chronyd


) 2>&1 | /usr/bin/tee -a /root/ceph-post.log

chvt 6

%end

EOFKS


[[ ! -e /store/data/images ]] && mkdir -p /store/data/images

[[ -e ceph_vm.vlock ]] && {

  [[ -e /tmp/floppy-ceph.img ]] && rm -rf /tmp/floppy-ceph.img
  mkfs.vfat -C /tmp/floppy-ceph.img 1440
  mkdir /tmp/mnt-ceph
  mount -o loop /tmp/floppy-ceph.img /tmp/mnt-ceph
  cp ceph_vm.vlock /tmp/mnt-ceph/versionlock.list
  sync
  umount /tmp/mnt-ceph
  rmdir /tmp/mnt-ceph

  virt-install --name ceph \
    --ram 1024 \
    --vcpus 1 \
    --hvm \
    --os-type linux \
    --os-variant rhel6 \
    --disk /store/data/images/ceph.img,bus=virtio,size=16 \
    --disk /tmp/floppy-ceph.img,device=floppy \
    --network bridge=public \
    --network bridge=storage \
    --initrd-inject /tmp/ceph.ks \
    --extra-args "ks=file:/ceph.ks" \
    --noautoconsole \
    --graphics spice \
    --autostart \
    --location ${location}
  } || {

virt-install --name ceph \
  --ram 1024 \
  --vcpus 1 \
  --hvm \
  --os-type linux \
  --os-variant rhel6 \
  --disk /store/data/images/ceph.img,bus=virtio,size=16 \
  --network bridge=public \
  --network bridge=storage \
  --initrd-inject /tmp/ceph.ks \
  --extra-args "ks=file:/ceph.ks" \
  --noautoconsole \
  --graphics spice \
  --autostart \
  --location ${location}
  }
