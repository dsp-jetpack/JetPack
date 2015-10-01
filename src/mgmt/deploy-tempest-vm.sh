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

cat <<'EOFKS' > /tmp/tempest.ks

install
text
cdrom
reboot

# Partitioning
ignoredisk --only-use=vda
# If zerombr is specified, any disks whose formatting is unrecognized are initialized. This will destroy all of the contents of disks with invalid partition tables or other formatting 
# unrecognizable to the installer. It is useful so that the installation program does not ask if it should initialize the disk label if installing to a brand new hard drive.
zerombr
# Specifies which drive the bootloader should be written to and thus, which drive the computer will boot from.
bootloader --boot-drive=vda
# Erases all partitions from the system.
clearpart --all

part /boot --fstype=ext4 --size=500
part pv.01 --size=8192 --grow

volgroup VolGroup --pesize=4096 pv.01

logvol / --fstype=ext4 --name=lv_root --vgname=VolGroup --grow --size=1024
logvol swap --name=lv_swap --vgname=VolGroup --size=1024

keyboard --vckeymap=us --xlayouts='us'
lang en_US.UTF-8

auth --enableshadow --passalgo=sha512

%include /tmp/tempest_ks_include.txt

skipx
firstboot --disable
eula --agreed

%packages
@base
@core
@development
ntp
ntpdate
-chrony
-firewalld
system-config-firewall-base
iptables
iptables-services
yum-plugin-versionlock
yum-utils
%end

%pre --log /tmp/tempest-pre.log
EOFKS


{ 
ntp=""

while read iface ip mask bridge
do
  flag=""

  [[ ${iface} == rootpassword ]] && echo "echo rootpw ${ip} >> /tmp/tempest_ks_include.txt"
  [[ ${iface} == timezone ]] && echo "echo timezone ${ip} --utc >> /tmp/tempest_ks_include.txt"

  [[ ${iface} == hostname ]] && {
    HostName=${ip} 
    echo "echo HostName=${ip} >> /tmp/tempest_ks_post_include.txt"
    }

  [[ ${iface} == nameserver ]] && {
    NameServers=${ip} 
    echo "echo NameServers=${ip} >> /tmp/tempest_ks_post_include.txt"
    }

  [[ ${iface} == gateway ]] && {
    Gateway=${ip} 
    echo "echo Gateway=${ip} >> /tmp/tempest_ks_post_include.txt"
    }

  [[ ${iface} == ntpserver ]] && echo "echo NTPServers=${ip} >> /tmp/tempest_ks_post_include.txt"
  [[ ${iface} == smuser ]] && echo "echo SMUser=${ip} >> /tmp/tempest_ks_post_include.txt"
  [[ ${iface} == smpassword ]] && echo "echo SMPassword=\'${ip}\' >> /tmp/tempest_ks_post_include.txt"
  [[ ${iface} == smpool ]] && echo "echo SMPool=${ip} >> /tmp/tempest_ks_post_include.txt"

  [[ ${iface} == smproxy ]] && echo "echo SMProxy=${ip} >> /tmp/tempest_ks_post_include.txt"
  [[ ${iface} == smproxyuser ]] && echo "echo SMProxyUser=${ip} >> /tmp/tempest_ks_post_include.txt"
  [[ ${iface} == smproxypassword ]] && echo "echo SMProxyPassword=${ip} >> /tmp/tempest_ks_post_include.txt"
  
  [[ ${iface} == tempestcommit ]] && echo "echo TempestCommit=${ip} >> /tmp/tempest_ks_post_include.txt"

  [[ ${iface} == eth0 ]] && { 
    echo "echo network --activate --onboot=true --noipv6 --device=${iface} --bootproto=static --ip=${ip} --netmask=${mask} --hostname=${HostName} --gateway=${Gateway} --nameserver=${NameServers} >> /tmp/tempest_ks_include.txt"
    }

  [[ ${iface} == eth1 ]] && { 
    echo "echo network --activate --onboot=true --noipv6 --device=${iface} --bootproto=static --ip=${ip} --netmask=${mask} --gateway=${Gateway} >> /tmp/tempest_ks_include.txt"
    }

  [[ ${iface} == eth2 ]] && {
    echo "echo network --activate --onboot=true --noipv6 --device=${iface} --bootproto=static --ip=${ip} --netmask=${mask} --gateway=${Gateway} >> /tmp/tempest_ks_include.txt"
    }

done <<< "$( grep -Ev "^#|^;|^\s*$" ${cfg_file} )"
} >> /tmp/tempest.ks

cat <<'EOFKS' >> /tmp/tempest.ks
%end

%post --nochroot --logfile /root/tempest-post.log
# Copy the files created during the %pre section to /root of the installed system for later use.
  cp -v /tmp/tempest-pre.log /mnt/sysimage/root
  cp -v /tmp/tempest_ks_include.txt /mnt/sysimage/root
  cp -v /tmp/tempest_ks_post_include.txt /mnt/sysimage/root
%end


%post

exec < /dev/tty8 > /dev/tty8
chvt 8

(
  # Source the variables from the %pre section
  . /root/tempest_ks_post_include.txt

  # Configure name resolution
  for ns in ${NameServers//,/ }
  do
    echo "nameserver ${ns}" >> /etc/resolv.conf
  done

  echo "GATEWAY=${Gateway}" >> /etc/sysconfig/network

  sed -i -e '/^DNS/d' -e '/^GATEWAY/d' /etc/sysconfig/network-scripts/ifcfg-eth0
  sed -i -e '/^DNS/d' -e '/^GATEWAY/d' /etc/sysconfig/network-scripts/ifcfg-eth1
  sed -i -e '/^DNS/d' -e '/^GATEWAY/d' /etc/sysconfig/network-scripts/ifcfg-eth2

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
  subscription-manager repos --enable=rhel-server-rhscl-7-rpms
  subscription-manager repos --enable=rhel-7-server-optional-rpms
  subscription-manager repos --enable=rhel-7-server-extras-rpms
  subscription-manager repos --enable=rhel-7-server-openstack-7.0-rpms

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

  yum -y install screen openstack-tempest.noarch python-tempest-lib-doc.noarch

  # get config script patch
  cd /tmp
  git clone https://github.com/redhat-openstack/tempest.git
  cd tempest
  git checkout ${TempestCommit}
  # Apply patch to package install tree
  cp -bf tools/config_tempest.py /usr/share/openstack-tempest-kilo/tools/
  cp -bf tempest/common/api_discovery.py /usr/share/openstack-tempest-kilo/tempest/common/
    
  # init tempest runtime dir
  cd /root 
  mkdir tempest
  cd tempest
  /usr/share/openstack-tempest-kilo/tools/configure-tempest-directory 
  # write base conf file to use in config script post install.  
  cat <<TBASE > etc/tempest.conf.base
[auth]
tempest_roles = _member_
allow_tenant_isolation = False

[compute]
image_ssh_user = cirros
image_ssh_password = cubswin:)
image_alt_ssh_user = cirros
image_alt_ssh_password = cubswin:)

# Does SSH use Floating IPs? (boolean value)
use_floatingip_for_ssh = True

[identity]
username = demo
tenant_name = demo
password = secrete
alt_username = alt_demo
alt_tenant_name = alt_demo
alt_password = secrete
admin_username = admin
admin_tenant_name = admin
disable_ssl_certificate_validation = false

[scenario]
img_dir = etc
# ssh username for the image file (string value)
ssh_user = cirros
ssh_password = cubswin:)

[volume-feature-enabled]
bootable = true
backup = False

[compute-feature-enabled]
live_migrate_paused_instances = True
preserve_ports = True

# Does the test environment support resizing? (boolean value)
resize = False

# Does the test environment have the ec2 api running? (boolean value)
ec2_api = False

[network-feature-enabled]
# Allow the execution of IPv6 tests (boolean value)
ipv6 = False
ipv6_subnet_attributes = False

[object-storage-feature-enabled]
discoverability = False
discoverable_apis = 

[service_available]
glance = True
cinder = True
swift = False
nova = True
neutron = True
trove = False
ceilometer = True
sahara = False
ironic = False
heat = True
zaqar = False
horizon = False
TBASE
  # delete patch checkout
  rm -rf /tmp/tempest


) 2>&1 | /usr/bin/tee -a /root/tempest-post.log

chvt 1

%end

EOFKS


[[ ! -e /store/data/images ]] && mkdir -p /store/data/images

[[ -e tempest_vm.vlock ]] && {

  [[ -e /tmp/floppy-tempest.img ]] && rm -rf /tmp/floppy-tempest.img
  mkfs.vfat -C /tmp/floppy-tempest.img 1440
  mkdir /tmp/mnt-tempest
  mount -o loop /tmp/floppy-tempest.img /tmp/mnt-tempest
  cp tempest_vm.vlock /tmp/mnt-tempest/versionlock.list
  sync
  umount /tmp/mnt-tempest
  rmdir /tmp/mnt-tempest

  virt-install --name tempest \
    --ram 12288 \
    --vcpus 12 \
    --hvm \
    --os-type linux \
    --os-variant rhel7 \
    --disk /store/data/images/tempest.img,bus=virtio,size=16 \
    --disk /tmp/floppy-tempest.img,device=floppy \
    --network bridge=public \
    --network bridge=external \
    --network bridge=private \
    --initrd-inject /tmp/tempest.ks \
    --extra-args "ks=file:/tempest.ks" \
    --noautoconsole \
    --graphics spice \
    --autostart \
    --location ${location}
  } || {

virt-install --name tempest \
  --ram 12288 \
  --vcpus 12 \
  --hvm \
  --os-type linux \
  --os-variant rhel7 \
  --disk /store/data/images/tempest.img,bus=virtio,size=16 \
  --network bridge=public \
  --network bridge=external \
  --network bridge=private \
  --initrd-inject /tmp/tempest.ks \
  --extra-args "ks=file:/tempest.ks" \
  --noautoconsole \
  --graphics spice \
  --autostart \
  --location ${location}
  }
