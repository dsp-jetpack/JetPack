# (c) 2014-2021 Dell Inc. or its subsidiaries.
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
# version=RHEL8

cdrom
reboot

# Partitioning
ignoredisk --only-use=sda
zerombr
bootloader --boot-drive=sda

clearpart --all --initlabel

part /boot/efi --fstype=efi --ondisk=sda --size=2
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

user --name=ansible --password=Dell0SS!
%include /tmp/ks_include.txt

skipx
text
firstboot --disable
eula --agreed

%packages
@standard
@python36
@gnome-desktop
@internet-browser
@network-server
@ftp-server
@file-server
@network-file-system-client
@performance
@remote-desktop-clients
@remote-system-management
@virtualization-client
@virtualization-hypervisor
@virtualization-tools
dhcp-server
tmux
python3-jinja2
%end



%pre --log /tmp/sah-pre.log

################### CHANGEME
# The variables that need to be changed for the environment are preceeded with:
# CHANGEME.
# Those with examples are preceeded with: CHANGEME e.g.
# (in this case, the entire string including the example should be replaced)

# FQDN of server
HostName="CHANGEME"

# Root password of server
SystemPassword="CHANGEME"

# Password for Ansible user
AnsiblePassword="CHANGEME"

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
Gateway="CHANGEME"
NameServers="CHANGEME"
NTPServers="0.centos.pool.ntp.org"
TimeZone="UTC"

# Installation interface configuration
# Format is "ip/netmask interface no"
anaconda_interface="CHANGEME e.g. 100.67.87.190/255.255.255.192 ens1f0 no"

# Bonding and Bridge configuration. These variables are bash associative arrays and take the form of array[key]="value".
# Specifying a key more than once will overwrite the first key. For example:

# Define the bond
# Bond to handle external traffic
extern_bond_name="CHANGEME e.g. bond0"
extern_boot_opts="onboot"
extern_bond_opts="mode=802.3ad,miimon=100,xmit_hash_policy=layer3+4,lacp_rate=1"
extern_ifaces="CHANGEME e.g. ens1f0,ens2f0"
extern_bond_mtu="1500"


# Define the bridge
# bridge options
bridge_name="br0"
bridge_bond_name="CHANGEME e.g. bond0"
bridge_boot_opts="CHANGEME e.g. onboot static 100.67.87.183/255.255.255.192"
bridge_mtu="1500"



################### END of CHANGEME

# Create the files that will be used by the installation environment and %post environment
read -a itmp <<< $( tr '/' ' ' <<< ${anaconda_interface} )

anaconda_if_name=${itmp[2]}
IFS='.' read anaconda_name anaconda_vlanid <<< "$anaconda_if_name"

anaconda_vlanid_opt=""
if [ -n "$anaconda_vlanid" ]; then
    anaconda_vlanid_opt="--vlanid=${anaconda_vlanid}"
fi

echo "network --noipv6 --device=${anaconda_name} ${anaconda_vlanid_opt} --bootproto=static --ip=${itmp[0]}" \
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

echo "bridges[br0]=\"${bridge_boot_opts}\"" >> /tmp/ks_post_include.txt
echo "bridge_iface[br0]=\"${bridge_bond_name}\"" >> /tmp/ks_post_include.txt
echo "bridges_mtu[br0]=\"${bridge_mtu}\"" >> /tmp/ks_post_include.txt

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

echo "AnsiblePassword=\"${AnsiblePassword}\"" >> /tmp/ks_post_include.txt

# Source variables for network config
. /tmp/ks_post_include.txt

# Configure Bonding and Slaves
#
for bond in ${!bonds[@]}
do
  read parms <<< $( tr -d '\r' <<< ${bonds[$bond]} )

  unset bond_info
  declare -A bond_info=(  \
                         [ONBOOT]="no"      \
                         )

  for parm in ${parms}
  do
    case $parm in
          onboot ) bond_info[ONBOOT]="yes"
                   ;;
    esac
  done

echo "network --noipv6 --noipv4 --no-activate --device=${bond} --interfacename=${bond} --mtu=${bonds_mtu[$bond]}" \
" --bondslaves=${bond_ifaces[$bond]} --bondopts=${bond_opts[$bond]} --onboot=yes" >> /tmp/ks_include.txt

done

# Configure Bridges
#
echo "# Configuring Bridges" >> /tmp/ks_include.txt
for bridge in ${!bridges[@]}
do
  read parms <<< $( tr -d '\r' <<< ${bridges[$bridge]} )

  unset bridge_info
  declare -A bridge_info=(  \
                         [ONBOOT]="no"      \
                         )

  for parm in ${parms}
  do
    case $parm in
          onboot ) bridge_info[ONBOOT]="yes"
                   ;;

 *.*.*.*/*.*.*.* ) read IP NETMASK <<< $( tr '/' ' ' <<< ${parm} )
                   bridge_info[IP]="${IP}"
                   bridge_info[NETMASK]="${NETMASK}"
                   ;;
    esac
  done

echo "network --noipv6 --no-activate --device=${bridge} --interfacename=${bridge} --bridgeslaves=${bridge_iface[$bridge]} --bootproto=static --onboot=yes" \
" --mtu=${bridges_mtu[${bridge}]} --ip=${bridge_info[IP]} --netmask=${bridge_info[NETMASK]} --nameserver=${NameServers} --gateway=${Gateway}" >> /tmp/ks_include.txt

done


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
  mkdir -p /mnt/sysimage/root/ocp-sah-ks-logs
  cp -v /tmp/sah-pre.log /mnt/sysimage/root/ocp-sah-ks-logs
  cp -v /tmp/ks_include.txt /mnt/sysimage/root/ocp-sah-ks-logs
  cp -v /tmp/ks_post_include.txt /mnt/sysimage/root/ocp-sah-ks-logs
%end


%post --log=/root/sah-post-ks.log

# exec < /dev/tty8 > /dev/tty8
# chvt 8

# Source the variables from the %pre section
. /root/ks_post_include.txt

# Work around for bond not being enslaved
rm /etc/sysconfig/network-scripts/ifcfg-br0_slave_1
echo "BRIDGE=br0" >> /etc/sysconfig/network-scripts/ifcfg-${bridge_iface[br0]}

# Disable IPv6
echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf
echo "net.ipv6.conf.default.disable_ipv6 = 1" >> /etc/sysctl.conf


sed -i -e "s/^SELINUX=.*/SELINUX=permissive/" /etc/selinux/config

# Configure the system files
echo "POST: Configure the system files..."
echo "HOSTNAME=${HostName}" >> /etc/sysconfig/network

IFS='/ ' read -r -a htmp <<< ${bridges[br0]}
IP=${htmp[2]}
echo "${IP}  ${HostName}" >> /etc/hosts

# Configure name resolution
for ns in ${NameServers//,/ }
do
  echo "nameserver ${ns}" >> /etc/resolv.conf
done

# Configure the chrony daemon for ntp
systemctl enable chronyd
sed -i -e "s/rhel/centos/" /etc/chrony.conf
sed -i -e "/^server /d" /etc/chrony.conf
sed -i -e "/^pool /d" /etc/chrony.conf

for ntps in ${NTPServers//,/ }
do
  echo "pool ${ntps}" >> /etc/chrony.conf
done

echo "allow ${NTPSettings}" >> /etc/chrony.conf
echo "local stratum 10" >> /etc/chrony.conf


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

subscription-manager repos ${ProxyInfo} '--disable=*' --enable=ansible-2.9-for-rhel-8-x86_64-rpms --enable=rhel-8-server-extras-rpms --enable=rhocp-4.6-for-rhel-8-x86_64-rpms --enable=rhel-8-for-x86_64-baseos-rpms --enable=rhel-8-for-x86_64-appstream-rpms

echo "POST: upgrade setuptools"
pip3 install --upgrade pip
pip3 install --upgrade setuptools
pip3 install paramiko
pip3 install cryptography
pip3 install python-dracclient
pip3 install ironic --ignore-installed=PyYAML
pip3 install setuptools_rust
pip3 install python-heatclient

echo "POST: Install other required packages"
yum install -y gcc libffi-devel openssl-devel ipmitool tmux httpd rust-toolset python3-devel xinetd tftp
yum install -y git ansible python3-netaddr python38 python38-pyyaml python38-requests libguestfs-tools

echo "POST: Done installing extra packages"

# Create a new user for running ansible playbooks
useradd ansible
passwd -f ansible << EOFPW
${AnsiblePassword}
${AnsiblePassword}
EOFPW

# Give the user sudo permissions
echo "ansible ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ansible
chmod 0440 /etc/sudoers.d/ansible

# Set Passwordless authentication for ansible user
su - ansible -c "ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''"
su - ansible -c "cat /home/ansible/.ssh/id_rsa.pub >> /home/ansible/.ssh/authorized_keys"
echo -n "${HostName},${IP} " >> /home/ansible/.ssh/known_hosts
ssh-keygen -q -t ecdsa -f /etc/ssh/ssh_host_ecdsa_key -C '' -N '' <<< y
chmod 600 /etc/ssh/ssh_host_ecdsa_key
chmod 644 /etc/ssh/ssh_host_ecdsa_key.pub
restorecon /etc/ssh/ssh_host_ecdsa_key.pub
cat /etc/ssh/ssh_host_ecdsa_key.pub >> /home/ansible/.ssh/known_hosts
chmod 600 /home/ansible/.ssh/authorized_keys

# Set PYTHONPATH for ansible user
echo "export PYTHONPATH=/lib/python3.6:/usr/local/lib/python3.6/site-packages/:/home/ansible/JetPack/src/deploy:/home/ansible/JetPack/src/deploy/auto_common:/home/ansible/JetPack/src/pilot/discover_nodes://home/ansible/JetPack/src/deploy/osp_deployer:/home/ansible/openshift-bare-metal/python:/home/ansible/JetPack/src/common/" >> /home/ansible/.bashrc

# Fix permission issues for Ansible user
mkdir /auto_results
chown ansible:ansible /auto_results


# Remove ssh banners
rm -rf /etc/motd.d/

# chvt 1

%end
