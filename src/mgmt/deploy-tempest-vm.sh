#! /bin/bash

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
  

  [[ ${iface} == ens3 ]] && { 
    echo "echo network --activate --onboot=true --noipv6 --device=${iface} --bootproto=static --ip=${ip} --netmask=${mask} --hostname=${HostName} --gateway=${Gateway} --nameserver=${NameServers} >> /tmp/tempest_ks_include.txt"
    }

  [[ ${iface} == ens4 ]] && { 
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

  sed -i -e '/^DNS/d' -e '/^GATEWAY/d' /etc/sysconfig/network-scripts/ifcfg-ens3
  sed -i -e '/^DNS/d' -e '/^GATEWAY/d' /etc/sysconfig/network-scripts/ifcfg-ens4

  echo "$( ip addr show dev ens3 | awk '/inet / { print $2 }' | sed 's/\/.*//' )  ${HostName}" >> /etc/hosts

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


  SMPool=""

  [[ x${SMPool} = x ]] \
    && SMPool=$( subscription-manager list --available | awk '/Red Hat Enterprise Linux Server/,/Pool/ {pool = $3} END {print pool}' )

  [[ -n ${SMPool} ]] \
    && subscription-manager attach --pool ${SMPool} \
    || ( echo "Could not find a Red Hat Enterprise Linux Server pool to attach to. - Auto-attaching to any pool." \
         subscription-manager attach --auto
         )

  # Disable all enabled repositories
  for repo in $( yum repolist all | awk '/enabled:/ { print $1}' )
  do
    yum-config-manager --disable ${repo} | grep -E "^\[|^enabled"
  done

  yum-config-manager --enable rhel-7-server-rpms rhel-7-server-optional-rpms rhel-7-server-extras-rpms
	  
  cd /tmp
  wget https://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
  ls *.rpm
  yum -y install epel-release-7-5.noarch.rpm

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

  yum -y install python-devel python-pip python-crypto.x86_64 libxslt-devel libxml2-devel libffi-devel

  cd ~/ 
  git clone https://github.com/redhat-openstack/tempest.git
  cd tempest
  pip install unittest2 discover Babel pbr
  python ./setup.py install
  


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
    --ram 4096 \
    --vcpus 2 \
    --hvm \
    --os-type linux \
    --os-variant rhel7 \
    --disk /store/data/images/tempest.img,bus=virtio,size=16 \
    --disk /tmp/floppy-tempest.img,device=floppy \
    --network bridge=public \
    --network bridge=provision \
    --initrd-inject /tmp/tempest.ks \
    --extra-args "ks=file:/tempest.ks" \
    --noautoconsole \
    --graphics spice \
    --autostart \
    --location ${location}
  } || {

virt-install --name tempest \
  --ram 4096 \
  --vcpus 2 \
  --hvm \
  --os-type linux \
  --os-variant rhel7 \
  --disk /store/data/images/tempest.img,bus=virtio,size=16 \
  --network bridge=public \
  --network bridge=provision \
  --initrd-inject /tmp/tempest.ks \
  --extra-args "ks=file:/tempest.ks" \
  --noautoconsole \
  --graphics spice \
  --autostart \
  --location ${location}
  }

