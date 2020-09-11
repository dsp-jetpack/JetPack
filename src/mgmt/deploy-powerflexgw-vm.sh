#! /bin/bash

# Copyright (c) 2020 Dell Inc. or its subsidiaries.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

[[ ${#@} != 2 ]] && echo "This script requires two parameters, a configuration file as the first parameter and the location of the installation ISO as the second parameter." && exit

cfg_file=$1
location=$2

cat <<'EOFKS' > /tmp/powerflexgw.ks

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
@standard
@python36
yum-plugin-versionlock
firewall-config
iptables-services
yum-utils
virt-who
tmux
%end

%pre --log /tmp/powerflexgw-pre.log
EOFKS


{ 
ntp=""
while read iface ip mask mtu
do
  flag=""
  [[ ${iface} == ntpserver ]] && echo "echo NTPServers=${ip} >> /tmp/ks_post_include.txt"
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


  [[ ${iface} == user ]] && echo "echo User=${ip} >> /tmp/ks_post_include.txt"
  [[ ${iface} == password ]] && echo "echo Password=${ip} >> /tmp/ks_post_include.txt"

  [[ ${iface} == smuser ]] && echo "echo SMUser=${ip} >> /tmp/ks_post_include.txt"
  [[ ${iface} == smpassword ]] && echo "echo SMPassword=\'${ip}\' >> /tmp/ks_post_include.txt"
  [[ ${iface} == smpool ]] && echo "echo SMPool=${ip} >> /tmp/ks_post_include.txt"

  [[ ${iface} == satellite_ip ]] && echo "echo SA_ip=${ip} >> /tmp/ks_post_include.txt"
  [[ ${iface} == satellite_hostname ]] && echo "echo SA_host=${ip} >> /tmp/ks_post_include.txt"
  [[ ${iface} == satellite_org ]] && echo "echo SA_org=${ip} >> /tmp/ks_post_include.txt"
  [[ ${iface} == satellite_activation_key ]] && echo "echo SA_key=${ip} >> /tmp/ks_post_include.txt"

  [[ ${iface} == smproxy ]] && echo "echo SMProxy=${ip} >> /tmp/ks_post_include.txt"
  [[ ${iface} == smproxyuser ]] && echo "echo SMProxyUser=${ip} >> /tmp/ks_post_include.txt"
  [[ ${iface} == smproxypassword ]] && echo "echo SMProxyPassword=${ip} >> /tmp/ks_post_include.txt"

  [[ ${iface} == enp1s0 ]] && {
    echo "echo network --activate --onboot=true --noipv6 --device=${iface} --bootproto=static --ip=${ip} --netmask=${mask} --hostname=${HostName} --gateway=${Gateway} --nameserver=${NameServers} --mtu=${mtu} >> /tmp/ks_include.txt"
    }

  [[ ${iface} == enp2s0 ]] && {
    echo "echo network --activate --onboot=true --noipv6 --device=${iface} --bootproto=static --ip=${ip} --netmask=${mask} --gateway=${Gateway} --nodefroute --mtu=${mtu} >> /tmp/ks_include.txt"
    }
    
done <<< "$( grep -Ev "^#|^;|^\s*$" ${cfg_file} )"
} >> /tmp/powerflexgw.ks

cat <<'EOFKS' >> /tmp/powerflexgw.ks
%end

%post --nochroot --logfile /root/powerflexgw-post.log
# Copy the files created during the %pre section to /root of the installed system for later use.
  cp -v /tmp/powerflexgw-pre.log /mnt/sysimage/root
  cp -v /tmp/ks_include.txt /mnt/sysimage/root
  cp -v /tmp/ks_post_include.txt /mnt/sysimage/root
  mkdir -p /mnt/sysimage/root/powerflexgw-ks-logs
  cp -v /tmp/powerflexgw-pre.log /mnt/sysimage/root/powerflexgw-ks-logs
  cp -v /tmp/ks_include.txt /mnt/sysimage/root/powerflexgw-ks-logs
  cp -v /tmp/ks_post_include.txt /mnt/sysimage/root/powerflexgw-ks-logs
%end


%post

exec < /dev/tty8 > /dev/tty8
chvt 8

(
  # Source the variables from the %pre section
  . /root/ks_post_include.txt

  #Configure Chrony
  sed -i -e "/^server /d" /etc/chrony.conf
  for ntps in ${NTPServers//,/ }
  do
    echo "server ${ntps}" >> /etc/chrony.conf
  done

  # Configure name resolution
  for ns in ${NameServers//,/ }
  do
    echo "nameserver ${ns}" >> /etc/resolv.conf
  done

  sed -i -e '/^DNS/d' -e '/^GATEWAY/d' /etc/sysconfig/network-scripts/ifcfg-enp2s0
  host=`hostname -s`
  sed -i "s/\(127.0.0.1\s\+\)/\1${HostName} ${host} /" /etc/hosts

  echo "----------------------"
  ip addr
  echo "subscription-manager register --username ${SMUser} --password ********"
  echo "----------------------"

# Register the system using Subscription Manager
[[ ${SMProxy} ]] && {

    ProxyInfo="--proxy ${SMProxy}"

    [[ ${SMProxyUser} ]] && ProxyInfo+=" --proxyuser ${SMProxyUser}"
    [[ ${SMProxyPassword} ]] && ProxyInfo+=" --proxypassword ${SMProxyPassword}"

    Proxy_Creds=""
    [[ ${SMProxyUser} && ${SMProxyPassword} ]] && Proxy_Creds="${SMProxyUser}:${SMProxyPassword}@"

    HTTP_Proxy="http://${Proxy_Creds}${SMProxy}"
    ip_addresses=$(ip addr | grep -Po 'inet \K[\d.]+')
    no_proxy_list=$(echo $ip_addresses | tr ' ' ',')

    export no_proxy=$no_proxy_list
    export http_proxy=${HTTP_Proxy}
    export https_proxy=${HTTP_Proxy}
	
    # Add file so proxy environment variables are maintaned with sudo commands
    echo 'Defaults env_keep += "http_proxy https_proxy no_proxy"' > /etc/sudoers.d/proxy
    chmod 0440 /etc/sudoers.d/proxy

    }
  if [[ -z ${SA_ip} ]]
  then
      subscription-manager register --username ${SMUser} --password ${SMPassword} ${ProxyInfo}
  else
      echo "$SA_ip    $SA_host" >> /etc/hosts
      rpm -Uvh http://$SA_host/pub/katello-ca-consumer-latest.noarch.rpm
      subscription-manager register --org=$SA_org --activationkey="$SA_key"
  fi

  [[ x${SMPool} = x ]] \
    && SMPool=$( subscription-manager list --available ${ProxyInfo} | awk '/OpenStack/,/Pool/ {pool = $3} END {print pool}' )

  [[ -n ${SMPool} ]] \
    && subscription-manager attach --pool ${SMPool} ${ProxyInfo} \
    || ( echo "Could not find an OpenStack pool to attach to. - Auto-attaching to any pool." \
         subscription-manager attach --auto ${ProxyInfo}
         )

  subscription-manager release --set=8.1

  subscription-manager repos ${ProxyInfo} '--disable=*' --enable=rhel-8-for-x86_64-baseos-eus-rpms --enable=rhel-8-for-x86_64-appstream-rpms --enable=rhel-8-for-x86_64-highavailability-eus-rpms --enable=ansible-2.8-for-rhel-8-x86_64-rpms --enable=fast-datapath-for-rhel-8-x86_64-rpms --enable=advanced-virt-for-rhel-8-x86_64-rpms --enable=satellite-tools-6.5-for-rhel-8-x86_64-rpms

  mkdir /tmp/mnt
  mount /dev/fd0 /tmp/mnt
  [[ -e /tmp/mnt/versionlock.list ]] && {
    cp /tmp/mnt/versionlock.list /etc/yum/pluginconf.d
    chmod 644 /etc/yum/pluginconf.d/versionlock.list
    }
  umount /tmp/mnt

  yum-config-manager --enable rhel-8-for-x86_64-baseos-eus-rpms --setopt="rhel-8-for-x86_64-baseos-eus-rpms.priority=1"
  yum-config-manager --enable rhel-8-for-x86_64-appstream-rpms --setopt="rhel-8-for-x86_64-appstream-rpms.priority=1"
  yum-config-manager --enable rhel-8-for-x86_64-highavailability-eus-rpms --setopt="rhel-8-for-x86_64-highavailability-eus-rpms.priority=1"
  
  dnf update -y

  dnf install java-1.8.0-openjdk -y

  # Firewall rules to allow traffic for the http, https, dns, and tftp services and tcp port 8140.

  cat <<EOIP > /etc/sysconfig/iptables
*nat
:PREROUTING ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
:POSTROUTING ACCEPT [0:0]
-A POSTROUTING -o enp1s0 -j MASQUERADE
COMMIT
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -i enp2s0 -j ACCEPT
-A INPUT -i enp3s0 -j ACCEPT
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
-A INPUT -j REJECT --reject-with icmp-host-prohibited
-A FORWARD -j REJECT --reject-with icmp-host-prohibited
COMMIT
EOIP


  systemctl enable iptables

  sed -i -e "/^net.ipv4.ip_forward/d" /etc/sysctl.conf
  echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
  sysctl -p

  systemctl disable firewalld

  # Put selinux into permissive mode
  sed -i -e "s/^SELINUX=.*/SELINUX=permissive/" /etc/selinux/config

) 2>&1 | /usr/bin/tee -a /root/powerflexgw-posts.log

# Remove ssh banners
rm -rf /etc/motd.d/

chvt 1

%end

EOFKS


[[ ! -e /store/data/images ]] && mkdir -p /store/data/images

[[ -e /store/data/images/floppy-powerflexgw.img ]] && rm -f /store/data/images/floppy-powerflexgw.img
rm -f /store/data/images/powerflexgw.img

[[ -e powerflexgw_vm.vlock ]] && {

  mkfs.vfat -C /store/data/images/floppy-powerflexgw.img 1440
  mkdir /tmp/mnt-powerflexgw
  mount -o loop /store/data/images/floppy-powerflexgw.img /tmp/mnt-powerflexgw
  cp powerflexgw_vm.vlock /tmp/mnt-powerflexgw/versionlock.list
  sync
  umount /tmp/mnt-powerflexgw
  rmdir /tmp/mnt-powerflexgw

  virt-install --name powerflexgw \
    --ram 32768 \
    --vcpus 8 \
    --hvm \
    --os-type linux \
    --os-variant rhel8.1 \
    --disk /store/data/images/powerflexgw.img,bus=virtio,size=120 \
    --disk /store/data/images/floppy-powerflexgw.img,device=floppy \
    --network bridge=br-pub-api \
    --network bridge=br-stor \
    --initrd-inject /tmp/powerflexgw.ks \
    --extra-args "ks=file:/powerflexgw.ks" \
    --noautoconsole \
    --graphics spice \
    --autostart \
    --location ${location} 

  } || {

virt-install --name powerflexgw \
  --ram 32768 \
  --vcpus 8 \
  --hvm \
  --os-type linux \
  --os-variant rhel8.1 \
  --disk /store/data/images/powerflexgw.img,bus=virtio,size=120 \
  --network bridge=br-pub-api \
  --network bridge=br-stor \
  --initrd-inject /tmp/powerflexgw.ks \
  --extra-args "ks=file:/powerflexgw.ks" \
  --noautoconsole \
  --graphics spice \
  --autostart \
  --location ${location}
  }
