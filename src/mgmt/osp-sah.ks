# (c) 2014-2019 Dell
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
dhcp
ntp
ntpdate
-chrony
-firewalld
system-config-firewall-base
%end



%pre --log /tmp/sah-pre.log

################### CHANGEME
# The variables that need to be changed for the environment are preceeded with:
# CHANGEME.
# Those with examples are preceeded with: CHANGEME e.g.
# (in this case, the entire string including the example should be replaced)

# FQDN of server
HostName="CHANGEME e.g. sah.example.org"

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

# Satellite credential/details (if using)
SatelliteHostname="CHANGEME"
SatelliteIp="CHANGEME"
SatelliteOrganization="CHANGEME"
SatelliteActivationKey="CHANGEME"


# Network configuration
Gateway="CHANGEME e.g. 10.148.44.254"
NameServers="CHANGEME e.g. 10.148.44.11"
NTPServers="0.centos.pool.ntp.org"
TimeZone="UTC"

# Installation interface configuration
# Format is "ip/netmask interface no"
anaconda_interface="CHANGEME e.g. 10.148.44.211/255.255.255.0 em4 no"

# Bonding and Bridge configuration. These variables are bash associative arrays and take the form of array[key]="value".
# Specifying a key more than once will overwrite the first key. For example:

# Define the bonds
# Bond to handle external traffic
extern_bond_name="CHANGEME e.g. bond1"
extern_boot_opts="onboot none"
extern_bond_opts="mode=802.3ad miimon=100 xmit_hash_policy=layer3+4 lacp_rate=1"
extern_ifaces="CHANGEME e.g. em2 p1p2"
extern_bond_mtu="CHANGEME e.g. 9000"

# Bond to handle internal traffic
internal_bond_name="CHANGEME e.g. bond0"
internal_boot_opts="onboot none"
internal_bond_opts="mode=802.3ad miimon=100 xmit_hash_policy=layer3+4 lacp_rate=1"
internal_ifaces="CHANGEME e.g. em1 p1p1"
internal_bond_mtu="CHANGEME e.g. 9000"

# Management
mgmt_bond_name="CHANGEME e.g. bond0.110"
mgmt_boot_opts="onboot none vlan"
mgmt_bond_mtu= "1500"

# Provisioning
prov_bond_name="CHANGEME e.g. bond0.120"
prov_boot_opts="onboot none vlan"
prov_bond_mtu="1500"

# Storage
stor_bond_name="CHANGEME e.g. bond0.170"
stor_boot_opts="onboot none vlan"
stor_bond_mtu="CHANGEME e.g. 9000"

# Public API
pub_api_bond_name="CHANGEME e.g. bond1.190"
pub_api_boot_opts="onboot none vlan"
pub_api_bond_mtu="CHANGEME e.g. 9000"

# Private API
priv_api_bond_name="CHANGEME e.g. bond0.140"
priv_api_boot_opts="onboot none vlan"
priv_api_bond_mtu="CHANGEME e.g. 9000"

# Define the bridges
# Management bridge options
br_mgmt_boot_opts="CHANGEME onboot static 192.168.110.12/255.255.255.0"
br_mgmt_mtu="1500"

# Provisioning bridge options
br_prov_boot_opts="CHANGEME e.g. onboot static 192.168.120.12/255.255.255.0"
br_prov_mtu="1500"

# Storage bridge options
br_stor_boot_opts="CHANGEME e.g. onboot static 192.168.170.12/255.255.255.0"
br_stor_mtu="CHANGEME e.g. 9000"

# Public API bridge options
br_pub_api_boot_opts="CHANGEME e.g. onboot static 192.168.190.12/255.255.255.0"
br_pub_api_mtu="CHANGEME e.g. 9000"

# Private API bridge options
br_priv_api_boot_opts="CHANGEME e.g. onboot static 192.168.140.12/255.255.255.0"
br_priv_api_mtu="CHANGEME e.g. 9000"

# Provisioning Network for NTP settings
prov_network="CHANGEME e.g 192.168.120.0"
prov_netmask="CHANGEME e.g 255.255.255.0"


################### END of CHANGEME

# Create the files that will be used by the installation environment and %post environment
read -a itmp <<< $( tr '/' ' ' <<< ${anaconda_interface} )

anaconda_if_name=${itmp[2]}
IFS='.' read anaconda_name anaconda_vlanid <<< "$anaconda_if_name"

anaconda_vlanid_opt=""
if [ -n "$anaconda_vlanid" ]; then
    anaconda_vlanid_opt="--vlanid=${anaconda_vlanid}"
fi

echo "network --activate --noipv6 --device=${anaconda_name} ${anaconda_vlanid_opt} --bootproto=static --ip=${itmp[0]}" \
     " --netmask=${itmp[1]} --hostname=${HostName} --gateway=${Gateway} --nameserver=${NameServers}" \
     >> /tmp/ks_include.txt

echo "rootpw ${SystemPassword}" >> /tmp/ks_include.txt
echo "timezone ${TimeZone} --utc" >> /tmp/ks_include.txt

[[ ${anaconda_if_name} ]] && { 
  echo "AnacondaIface_device=\"${anaconda_if_name}\"" >> /tmp/ks_post_include.txt 
  }

[[ ${itmp[3]} = no ]] && { 
  echo "AnacondaIface_noboot=\"${itmp[3]}\"" >> /tmp/ks_post_include.txt 
  }


#Post_include Environment 
echo "HostName=\"${HostName}\"" >> /tmp/ks_post_include.txt
echo "Gateway=\"${Gateway}\"" >> /tmp/ks_post_include.txt
echo "NameServers=\"${NameServers}\"" >> /tmp/ks_post_include.txt
echo "NTPServers=\"${NTPServers}\"" >> /tmp/ks_post_include.txt
echo "NTPSettings=\"${prov_network} netmask ${prov_netmask}\"" >> /tmp/ks_post_include.txt


echo "declare -A bonds" >> /tmp/ks_post_include.txt
echo "declare -A bond_opts" >> /tmp/ks_post_include.txt
echo "declare -A bond_ifaces" >> /tmp/ks_post_include.txt 
echo "declare -A bridges" >> /tmp/ks_post_include.txt
echo "declare -A bridge_iface" >> /tmp/ks_post_include.txt
echo "declare -A bridges_mtu" >> /tmp/ks_post_include.txt
echo "declare -A bonds_mtu" >> /tmp/ks_post_include.txt


echo "bonds[${extern_bond_name}]=\"${extern_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bond_opts[${extern_bond_name}]=\"${extern_bond_opts}\"" >> /tmp/ks_post_include.txt
echo "bonds_mtu[${extern_bond_name}]=\"${extern_bond_mtu}\"" >> /tmp/ks_post_include.txt
echo "bond_ifaces[${extern_bond_name}]=\"${extern_ifaces}\"" >> /tmp/ks_post_include.txt


echo "bonds[${internal_bond_name}]=\"${internal_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bond_opts[${internal_bond_name}]=\"${internal_bond_opts}\"" >> /tmp/ks_post_include.txt
echo "bonds_mtu[${internal_bond_name}]=\"${internal_bond_mtu}\"" >> /tmp/ks_post_include.txt
echo "bond_ifaces[${internal_bond_name}]=\"${internal_ifaces}\"" >> /tmp/ks_post_include.txt



echo "bonds[${mgmt_bond_name}]=\"${mgmt_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bonds_mtu[${mgmt_bond_name}]=\"${mgmt_bond_mtu}\"" >> /tmp/ks_post_include.txt

echo "bonds[${prov_bond_name}]=\"${prov_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bonds_mtu[${prov_bond_name}]=\"${prov_bond_mtu}\"" >> /tmp/ks_post_include.txt

echo "bonds[${stor_bond_name}]=\"${stor_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bonds_mtu[${stor_bond_name}]=\"${stor_bond_mtu}\"" >> /tmp/ks_post_include.txt

echo "bonds[${priv_api_bond_name}]=\"${priv_api_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bonds_mtu[${priv_api_bond_name}]=\"${priv_api_bond_mtu}\"" >> /tmp/ks_post_include.txt


echo "bonds[${pub_api_bond_name}]=\"${pub_api_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bonds_mtu[${pub_api_bond_name}]=\"${pub_api_bond_mtu}\"" >> /tmp/ks_post_include.txt

echo "bridges[br-mgmt]=\"${br_mgmt_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bridge_iface[br-mgmt]=\"${mgmt_bond_name}\"" >> /tmp/ks_post_include.txt
echo "bridges_mtu[br-mgmt]=\"${br_mgmt_mtu}\"" >> /tmp/ks_post_include.txt

echo "bridges[br-prov]=\"${br_prov_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bridge_iface[br-prov]=\"${prov_bond_name}\"" >> /tmp/ks_post_include.txt
echo "bridges_mtu[br-prov]=\"${br_prov_mtu}\"" >> /tmp/ks_post_include.txt

echo "bridges[br-stor]=\"${br_stor_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bridge_iface[br-stor]=\"${stor_bond_name}\"" >> /tmp/ks_post_include.txt
echo "bridges_mtu[br-stor]=\"${br_stor_mtu}\"" >> /tmp/ks_post_include.txt

echo "bridges[br-priv-api]=\"${br_priv_api_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bridge_iface[br-priv-api]=\"${priv_api_bond_name}\"" >> /tmp/ks_post_include.txt
echo "bridges_mtu[br-priv-api]=\"${br_priv_api_mtu}\"" >> /tmp/ks_post_include.txt

echo "bridges[br-pub-api]=\"${br_pub_api_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bridge_iface[br-pub-api]=\"${pub_api_bond_name}\"" >> /tmp/ks_post_include.txt
echo "bridges_mtu[br-pub-api]=\"${br_pub_api_mtu}\"" >> /tmp/ks_post_include.txt


echo "SMUser=\"${SubscriptionManagerUser}\"" >> /tmp/ks_post_include.txt
echo "SMPassword=\"${SubscriptionManagerPassword}\"" >> /tmp/ks_post_include.txt
echo "SMPool=\"${SubscriptionManagerPool}\"" >> /tmp/ks_post_include.txt

echo "SA_ip=\"${SatelliteIp}\"" >> /tmp/ks_post_include.txt
echo "SA_host=\"${SatelliteHostname}\"" >> /tmp/ks_post_include.txt
echo "SA_org=\"${SatelliteOrganization}\"" >> /tmp/ks_post_include.txt
echo "SA_key=\"${SatelliteActivationKey}\"" >> /tmp/ks_post_include.txt


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
  mkdir -p /mnt/sysimage/root/osp-sah-ks-logs
  cp -v /tmp/sah-pre.log /mnt/sysimage/root/osp-sah-ks-logs
  cp -v /tmp/ks_include.txt /mnt/sysimage/root/osp-sah-ks-logs
  cp -v /tmp/ks_post_include.txt /mnt/sysimage/root/osp-sah-ks-logs  
%end


%post --log=/root/sah-post-ks.log

# exec < /dev/tty8 > /dev/tty8
# chvt 8

# Source the variables from the %pre section
. /root/ks_post_include.txt


sed -i -e "s/^SELINUX=.*/SELINUX=permissive/" /etc/selinux/config

# Configure the system files
echo "POST: Configure the system files..."
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


echo "restrict ${NTPSettings} nomodify notrap" >> /etc/ntp.conf
echo "server  127.127.1.0 # local clock" >> /etc/ntp.conf


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

  [[ ${bonds_mtu[${bond}]} ]] && cat << EOB >> /etc/sysconfig/network-scripts/ifcfg-${bond}
MTU="$( tr -d '\r' <<< ${bonds_mtu[$bond]} )"
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

  [[ ${bonds_mtu[${bond}]} ]] && cat << EOB >> /etc/sysconfig/network-scripts/ifcfg-${iface}
MTU="$( tr -d '\r' <<< ${bonds_mtu[$bond]} )"
EOB
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
  [[ ${bridges_mtu[${bridge}]} ]] && cat << EOB >> /etc/sysconfig/network-scripts/ifcfg-${bridge}
MTU="$( tr -d '\r' <<< ${bridges_mtu[$bridge]} )"
EOB
  [[ "${bridge_iface[${bridge}]}" ]] && echo "BRIDGE=${bridge}" >> /etc/sysconfig/network-scripts/ifcfg-${bridge_iface[${bridge}]}

done


[[ ${AnacondaIface_noboot} ]] && { 
  sed -i -e '/DEFROUTE=/d' /etc/sysconfig/network-scripts/ifcfg-${AnacondaIface_device} 
  sed -i -e '/ONBOOT=/d' /etc/sysconfig/network-scripts/ifcfg-${AnacondaIface_device} 
  echo "ONBOOT=no" >> /etc/sysconfig/network-scripts/ifcfg-${AnacondaIface_device} 
  }


echo "----------------------"
ip addr
echo "POST: subscription-manager register --username ${SMUser} --password *********"
echo "----------------------"

# Register the system using Subscription Manager
[[ ${SMProxy} ]] && {

    ProxyInfo="--proxy ${SMProxy}:${SMProxyPort}"

    [[ ${SMProxyUser} ]] && ProxyInfo+=" --proxyuser ${SMProxyUser}"
    [[ ${SMProxyPassword} ]] && ProxyInfo+=" --proxypassword ${SMProxyPassword}"

    Proxy_Creds=""
    [[ ${SMProxyUser} && ${SMProxyPassword} ]] && Proxy_Creds="${SMProxyUser}:${SMProxyPassword}@"

    HTTP_Proxy="http://${Proxy_Creds}${SMProxy}:${SMProxyPort}"
    ip_addresses=$(ip addr | grep -Po 'inet \K[\d.]+')
    no_proxy_list=$(echo $ip_addresses | tr ' ' ',')

    export no_proxy=$no_proxy_list
    export http_proxy=${HTTP_Proxy}
    export https_proxy=${HTTP_Proxy}

    }

if [[ ${SA_ip} == "CHANGEME" ]]
then
    subscription-manager register --username ${SMUser} --password ${SMPassword} ${ProxyInfo}
else
      echo "$SA_ip    $SA_host" >> /etc/hosts
      rpm -Uvh http://$SA_host/pub/katello-ca-consumer-latest.noarch.rpm
      subscription-manager register --org=$SA_org --activationkey="$SA_key"
fi
  [[ x${SMPool} = x ]] \
    && SMPool=$( subscription-manager list --available ${ProxyInfo} | awk '/Red Hat Enterprise Linux Server/,/Pool/ {pool = $3} END {print pool}' )

  [[ -n ${SMPool} ]] \
    && subscription-manager attach --pool ${SMPool} ${ProxyInfo} \
    || ( echo "POST: Could not find a Red Hat Enterprise Linux Server pool to attach to. - Auto-attaching to any pool." \
         subscription-manager attach --auto ${ProxyInfo}
         )

subscription-manager repos ${ProxyInfo} '--disable=*' --enable=rhel-7-server-rpms --enable=rhel-7-server-optional-rpms

systemctl disable NetworkManager
systemctl disable firewalld
systemctl disable chronyd

mkdir -p /store/data/images
mkdir -p /store/data/iso

echo "POST: Install other rerquired packages, paramiko, ..."
yum install -y gcc libffi-devel python-devel openssl-devel python-setuptools ipmitool tmux git

echo "POST: get and install pip"
curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
python get-pip.py
# temporary workaround for CES-7248 
echo "POST: upgrade setuptools"
pip install --upgrade setuptools
pip install paramiko
pip install selenium
pip install cryptography
echo "POST: Done installing extra packages"

echo 'export PYTHONPATH=/usr/bin/python:/lib/python2.7:/lib/python2.7/site-packages:/root/JetPack/src/deploy/' >> /root/.bashrc

# chvt 1

%end
