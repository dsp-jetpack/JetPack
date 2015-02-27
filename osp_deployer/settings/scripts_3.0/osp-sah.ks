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
text
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
SubscriptionManagerPool="CHANGEME"
SubscriptionManagerProxy=""
SubscriptionManagerProxyPort=""
SubscriptionManagerProxyUser=""
SubscriptionManagerProxyPassword=""


# Network configuration
Gateway="10.148.44.254"
NameServers="10.148.44.11"
NTPServers="clock.bos.redhat.com"
TimeZone="UTC"

# Installation interface configuration
# Format is "ip/netmask interface"
anaconda_interface="10.148.44.211/255.255.255.0 em2"

# Bonding and Bridge configuration. These variables are bash associative arrays and take the form of array[key]="value".
# Specifying a key more than once will overwrite the first key. For example:
#
# Define the bonds
# Bond1 (Public)
public_bond_name="bond1"
public_boot_opts="onboot none"
public_bond_opts="mode=active-backup miimon=100"
public_ifaces="em2 p1p2"
#
# Bond0 (Private)
private_bond_name="bond0"
private_boot_opts="onboot none"
private_bond_opts="mode=active-backup miimon=100"
private_ifaces="em1 p1p1"
#
# Provision
provision_bond_name="bond0.120"
provision_boot_opts="onboot none vlan"
#
# Storage
storage_bond_name="bond0.170"
storage_boot_opts="onboot none vlan"
#
# Define the bridges
# Public Bridge
public_bridge_boot_opts="onboot static 10.148.44.41/255.255.255.0"
#
# Provision Bridge
provision_bridge_boot_opts="onboot static 192.168.120.41/255.255.255.0"
#
# Storage Bridge
storage_bridge_boot_opts="onboot static 192.168.170.41/255.255.255.0"
################### END of CHANGEME

# Create the files that will be used by the installation environment and %post environment
read -a itmp <<< $( tr '/' ' ' <<< ${anaconda_interface} )

echo "network --activate --onboot=true --noipv6 --device=${itmp[2]} --bootproto=static --ip=${itmp[0]}" \
     " --netmask=${itmp[1]} --hostname=${HostName} --gateway=${Gateway} --nameserver=${NameServers}" \
     >> /tmp/ks_include.txt

echo "rootpw ${SystemPassword}" >> /tmp/ks_include.txt
echo "timezone ${TimeZone} --utc" >> /tmp/ks_include.txt

#Post_include Environment 
echo "HostName=\"${HostName}\"" >> /tmp/ks_post_include.txt
echo "Gateway=\"${Gateway}\"" >> /tmp/ks_post_include.txt
echo "NameServers=\"${NameServers}\"" >> /tmp/ks_post_include.txt
echo "NTPServers=\"${NTPServers}\"" >> /tmp/ks_post_include.txt

echo "declare -A bonds" >> /tmp/ks_post_include.txt
echo "declare -A bond_opts" >> /tmp/ks_post_include.txt
echo "declare -A bond_ifaces" >> /tmp/ks_post_include.txt 
echo "declare -A bridges" >> /tmp/ks_post_include.txt
echo "declare -A bridge_iface" >> /tmp/ks_post_include.txt

echo "bonds[${public_bond_name}]=\"${public_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bond_opts[${public_bond_name}]=\"${public_bond_opts}\"" >> /tmp/ks_post_include.txt
echo "bond_ifaces[${public_bond_name}]=\"${public_ifaces}\"" >> /tmp/ks_post_include.txt

echo "bonds[${private_bond_name}]=\"${private_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bond_opts[${private_bond_name}]=\"${private_bond_opts}\"" >> /tmp/ks_post_include.txt
echo "bond_ifaces[${private_bond_name}]=\"${private_ifaces}\"" >> /tmp/ks_post_include.txt

echo "bonds[${provision_bond_name}]=\"${provision_boot_opts}\"" >> /tmp/ks_post_include.txt

echo "bonds[${storage_bond_name}]=\"${storage_boot_opts}\"" >> /tmp/ks_post_include.txt

echo "bridges[public]=\"${public_bridge_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bridge_iface[public]=\"${public_bond_name}\"" >> /tmp/ks_post_include.txt

echo "bridges[provision]=\"${provision_bridge_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bridge_iface[provision]=\"${provision_bond_name}\"" >> /tmp/ks_post_include.txt

echo "bridges[storage]=\"${storage_bridge_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bridge_iface[storage]=\"${storage_bond_name}\"" >> /tmp/ks_post_include.txt

echo "SMUser=\"${SubscriptionManagerUser}\"" >> /tmp/ks_post_include.txt
echo "SMPassword=\"${SubscriptionManagerPassword}\"" >> /tmp/ks_post_include.txt
echo "SMPool=\"${SubscriptionManagerPool}\"" >> /tmp/ks_post_include.txt

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


# Configure Bonding and VLANS
#
for bond in ${!bonds[@]}
do
  read parms <<< $( tr -d '\r' <<< ${bonds[$bond]} )

  unset bond_info
  declare -A bond_info=(  \
                         [DEVICE]="${bond}" \
                         [PROTO]="dhcp" \
                         [ONBOOT]="no"      \
                         [NM_CONTROLLED]="no"      \
                         )

  for parm in ${parms}
  do
    case $parm in
          promisc ) bond_info[PROMISC]="yes"
                   ;;

          onboot ) bond_info[ONBOOT]="yes"
                   ;;

            none ) bond_info[PROTO]="none"
                   ;;

          static ) bond_info[PROTO]="static"
                   ;;

            dhcp ) bond_info[PROTO]="dhcp"
                   ;;

            vlan ) bond_info[VLAN]="yes"
                   ;;

 *.*.*.*/*.*.*.* ) read IP NETMASK <<< $( tr '/' ' ' <<< ${parm} )
                   bond_info[IP]="${IP}"
                   bond_info[NETMASK]="${NETMASK}"
                   ;;
    esac
  done

  cat << EOB > /etc/sysconfig/network-scripts/ifcfg-${bond}
NAME=${bond}
DEVICE=${bond}
TYPE=Bond
ONBOOT=${bond_info[ONBOOT]}
NM_CONTROLLED=${bond_info[NM_CONTROLLED]}
BOOTPROTO=${bond_info[PROTO]}
EOB

  [[ ${bond_opts[${bond}]} ]] && cat << EOB >> /etc/sysconfig/network-scripts/ifcfg-${bond}
BONDING_OPTS="$( tr -d '\r' <<< ${bond_opts[$bond]} )"
EOB

  [[ "${bond_info[PROTO]}" = "static" ]] && cat << EOB >> /etc/sysconfig/network-scripts/ifcfg-${bond}
IPADDR=${bond_info[IP]}
NETMASK=${bond_info[NETMASK]}
EOB

  [[ "${bond_info[PROMISC]}" = "yes" ]] && cat << EOB >> /etc/sysconfig/network-scripts/ifcfg-${bond}
PROMISC=${bond_info[PROMISC]}
EOB

  [[ "${bond_info[VLAN]}" = "yes" ]] && {
    cat << EOB >> /etc/sysconfig/network-scripts/ifcfg-${bond}
VLAN=${bond_info[VLAN]}
EOB
  } || {
    cat << EOB >> /etc/sysconfig/network-scripts/ifcfg-${bond}
BONDING_MASTER=yes
EOB
  }


for iface in $( tr -d '\r' <<< ${bond_ifaces[$bond]} )
do
  unset mac
  mac=$( ip addr sh dev ${iface} | awk '/link/ {print $2}' )

  cat << EOI > /etc/sysconfig/network-scripts/ifcfg-${iface}
NAME=${iface}
DEVICE=${iface}
TYPE=Ethernet
HWADDR=${mac}
BOOTPROTO=none
ONBOOT=${bond_info[ONBOOT]}
MASTER=${bond}
SLAVE=yes
NM_CONTROLLED=no
EOI
  done

done



# Configure Bridges
#
for bridge in ${!bridges[@]}
do
  read parms <<< $( tr -d '\r' <<< ${bridges[$bridge]} )

  unset bridge_info
  declare -A bridge_info=(  \
                         [DEVICE]="${bond}" \
                         [PROTO]="dhcp" \
                         [ONBOOT]="no"      \
                         [NM_CONTROLLED]="no"      \
                         )

  for parm in ${parms}
  do
    case $parm in
          onboot ) bridge_info[ONBOOT]="yes"
                   ;;

            none ) bridge_info[PROTO]="none"
                   ;;

          static ) bridge_info[PROTO]="static"
                   ;;

            dhcp ) bridge_info[PROTO]="dhcp"
                   ;;

 *.*.*.*/*.*.*.* ) read IP NETMASK <<< $( tr '/' ' ' <<< ${parm} )
                   bridge_info[IP]="${IP}"
                   bridge_info[NETMASK]="${NETMASK}"
                   ;;
    esac
  done



  cat << EOB > /etc/sysconfig/network-scripts/ifcfg-${bridge}
NAME=${bridge}
DEVICE=${bridge}
TYPE=Bridge
ONBOOT=${bridge_info[ONBOOT]}
NM_CONTROLLED=${bridge_info[NM_CONTROLLED]}
BOOTPROTO=${bridge_info[PROTO]}
EOB

  [[ "${bridge_info[PROTO]}" = "static" ]] && cat << EOB >> /etc/sysconfig/network-scripts/ifcfg-${bridge}
IPADDR=${bridge_info[IP]}
NETMASK=${bridge_info[NETMASK]}
EOB

  [[ "${bridge_iface[${bridge}]}" ]] && echo "BRIDGE=${bridge}" >> /etc/sysconfig/network-scripts/ifcfg-${bridge_iface[${bridge}]}


done




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
