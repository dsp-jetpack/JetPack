#version=RHEL7

install
cdrom
reboot

# Partitioning
ignoredisk --only-use=sda
zerombr
bootloader --boot-drive=sda

clearpart --all --initlabel 

part biosboot --ondisk=sda --size=2
part /boot --fstype=ext4 --size=1024
part pv.01 --size=79872
part pv.02 --size=1024 --grow

volgroup VolGroup --pesize=4096 pv.01
volgroup vg_vms   --pesize=4096 pv.02

logvol / --fstype=ext4    --name=lv_root --vgname=VolGroup --size 30720
logvol /tmp --fstype=ext4 --name=lv_tmp  --vgname=VolGroup --size 10240
logvol /var --fstype=ext4 --name=lv_var  --vgname=VolGroup --size 20480
logvol swap               --name=lv_swap --vgname=VolGroup --size 16384

logvol /store/data --fstype=ext4 --name=data --vgname=vg_vms --size 1 --grow

keyboard --vckeymap=us --xlayouts='us'
lang en_US.UTF-8

auth --enableshadow --passalgo=sha512

%include /tmp/ks_include.txt

skipx
firstboot --disable
eula --agreed

%packages
@gnome-desktop
@internet-browser
@x11
@dns-server
@ftp-server
@file-server
@network-file-system-client
@performance
@remote-desktop-clients
@remote-system-management
@virtualization-client
@virtualization-hypervisor
@virtualization-tools
ntp
ntpdate
-chrony
-firewalld
system-config-firewall-base
%end



%pre --log /tmp/sah-pre.log

################### CHANGEME
#  These are the variables that need changed for the environment

# FQDN of server
HostName="sah.example.org"

# Root password of server
SystemPassword="CHANGEME"

# Subscription Manager credentials and pool to connect to.
# If the pool is not specified, the kickstart will try to subscribe to
# the first subcription specified as "Red Hat Enterprise Linux Server"
SubscriptionManagerUser="CHANGEME"
SubscriptionManagerPassword="CHANGEME"
SubscriptionManagerPool="8j45445948fg908090fs5681d2243969"
SubscriptionManagerProxy=""
SubscriptionManagerProxyPort=""
SubscriptionManagerProxyUser=""
SubscriptionManagerProxyPassword=""

# Network configuration
Gateway="10.19.143.254"
NameServers="10.19.143.247,10.19.143.248"
NTPServers="CHANGEME.CHANGEME"
TimeZone="America/Chicago"

# bridge and bonding configuration. The format of the value is
# a space seperated list containing:
# Bridge_Name Bond_Name Bridge_IP Bridge_Mask Slave_Interface1 Slave_Interface2 SlaveInterface3 ...
# The network configuration specified for the public_bond will be used by the installation environment as well.
public_bond="public bond0 10.19.139.60 255.255.248.0 em1 em3"
provision_bond="provision bond1 172.44.139.60 255.255.255.0 em2 em4"

################### END of CHANGEME

# Create the files that will be used by the installation environment and %post environment
read -a itmp <<< ${public_bond}

echo "network --activate --onboot=true --noipv6 --device=${itmp[4]} --bootproto=static --ip=${itmp[2]}" \
     " --netmask=${itmp[3]} --hostname=${HostName} --gateway=${Gateway} --nameserver=${NameServers}" \
     >> /tmp/ks_include.txt

echo "rootpw ${SystemPassword}" >> /tmp/ks_include.txt
echo "timezone ${TimeZone} --utc" >> /tmp/ks_include.txt

echo "HostName=\"${HostName}\"" >> /tmp/ks_post_include.txt
echo "Gateway=\"${Gateway}\"" >> /tmp/ks_post_include.txt
echo "NameServers=\"${NameServers}\"" >> /tmp/ks_post_include.txt
echo "NTPServers=\"${NTPServers}\"" >> /tmp/ks_post_include.txt

echo "public_bond=\"${public_bond}\"" >> /tmp/ks_post_include.txt
echo "provision_bond=\"${provision_bond}\"" >> /tmp/ks_post_include.txt
echo "SMUser=${SubscriptionManagerUser}" >> /tmp/ks_post_include.txt
echo "SMPassword=${SubscriptionManagerPassword}" >> /tmp/ks_post_include.txt
echo "SMPool=${SubscriptionManagerPool}" >> /tmp/ks_post_include.txt

[[ ${SubscriptionManagerProxy} ]] && {
  echo "SMProxy=\"${SubscriptionManagerProxy}\"" >> /tmp/ks_post_include.txt
  echo "SMProxyPort=\"${SubscriptionManagerProxyPort}\"" >> /tmp/ks_post_include.txt
  echo "SMProxyUser=\"${SubscriptionManagerProxyUser}\"" >> /tmp/ks_post_include.txt
  echo "SMProxyPassword=\"${SubscriptionManagerProxyPassword}\"" >> /tmp/ks_post_include.txt
  }

# Remove all existing LVM configuration before the installation begins
echo "Determining LVM PVs"
pvscan

echo "Determining LVM VGs"
vgscan

echo "Determining LVM LVs"
lvscan

lvchange -a n
vgchange -a n

echo "Erasing LVM PVs"
for pv in $( pvs -o pv_name | grep -v "^\s*PV\s*$" )
do
  pvremove --force --force --yes ${pv}
done

echo "Checking LVM PVs do not exist"
pvscan

echo "Checking LVM VGs do not exist"
vgscan

echo "Checking LVM LVs do not exist"
lvscan

%end

%post --nochroot --log=/root/sah-ks.log
# Copy the files created during the %pre section to /root of the installed system for later use.
  cp -v /tmp/sah-pre.log /mnt/sysimage/root
  cp -v /tmp/ks_include.txt /mnt/sysimage/root
  cp -v /tmp/ks_post_include.txt /mnt/sysimage/root
%end


%post --log=/root/sah-post-ks.log

exec < /dev/tty8 > /dev/tty8
chvt 8

# Source the variables from the %pre section
. /root/ks_post_include.txt


sed -i -e "s/^SELINUX=.*/SELINUX=permissive/" /etc/selinux/config

# Configure the system files
echo "HOSTNAME=${HostName}" >> /etc/sysconfig/network
echo "GATEWAY=${Gateway}" >> /etc/sysconfig/network

read -a htmp <<< ${public_bond}
echo "${htmp[2]}  ${HostName}" >> /etc/hosts

# Configure name resolution
for ns in ${NameServers//,/ }
do
  echo "nameserver ${ns}" >> /etc/resolv.conf
done

# Configure the ntp daemon
systemctl enable ntpd
sed -i -e "/^server /d" /etc/ntp.conf

for ntps in ${NTPServers//,/ }
do
  echo "server ${ntps}" >> /etc/ntp.conf
done


# Configure the interfaces, bonds, and bridges
for bond in "${public_bond}" "${provision_bond}"
do
  read -a itmp <<< ${bond}
  bridge=${itmp[0]}
  bname=${itmp[1]}
  ip=${itmp[2]}
  mask=${itmp[3]}

  itmp=${itmp[@]:4}

# Configure the interfaces
  for iface in ${itmp}
  do
    mac=$( ip addr sh dev ${iface} | awk '/link/ {print $2}' )

    cat <<EOBF > /etc/sysconfig/network-scripts/ifcfg-${iface}
NAME=${iface}
DEVICE=${iface}
TYPE=Ethernet
HWADDR=${mac}
NM_CONTROLLED=no
ONBOOT=yes
BOOTPROTO=none
SLAVE=yes
MASTER=${bname}
EOBF

  done

# Configure the bonds
  cat <<EOBF > /etc/sysconfig/network-scripts/ifcfg-${bname}
NAME=${bname}
DEVICE=${bname}
TYPE=Bond
NM_CONTROLLED=no
BOOTPROTO=none
ONBOOT=yes
BONDING_OPTS="mode=balance-tlb miimon=100"
BONDING_MASTER=yes
DEFROUTE=no
BRIDGE=${bridge}
EOBF

# Configure the bridges
  cat <<EOBF > /etc/sysconfig/network-scripts/ifcfg-${bridge}
NAME=${bridge}
DEVICE=${bridge}
TYPE=Bridge
NM_CONTROLLED=no
ONBOOT=yes
BOOTPROTO=static
IPADDR=${ip}
NETMASK=${mask}
EOBF

done

echo "--------------------------------"
ip addr
ip route


# Register the system using Subscription Manager

[[ "${SMProxy}" ]] && {
  ProxyCmd="--server.proxy_hostname ${SMProxy}"

  [[ "${SMProxyPort}" ]]     && ProxyCmd+=" --server.proxy_port ${SMProxyPort}"
  [[ "${SMProxyUser}" ]]     && ProxyCmd+=" --server.proxy_user ${SMProxyUser}"
  [[ "${SMProxyPassword}" ]] && ProxyCmd+=" --server.proxy_password ${SMProxyPassword}"

  subscription-manager config ${ProxyCmd}
  }

SMPool=""

[[ x${SMPool} = x ]] \
  && SMPool=$( subscription-manager list --available \
  | awk '/Red Hat Enterprise Linux Server/,/Pool/ {pool = $3} END {print pool}' )

[[ -n ${SMPool} ]] \
  && subscription-manager attach --pool ${SMPool} \
  || ( echo "Could not find an Red Hat Enterprise Linux pool to attach to. - Auto-attaching to any pool." \
       subscription-manager attach --auto
       )

yum -y update


systemctl disable NetworkManager
systemctl disable firewalld

mkdir -p /store/data/images
mkdir -p /store/data/iso

chvt 6

%end
