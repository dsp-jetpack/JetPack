#!/usr/bin/env python

# Copyright (c) 2017-2019 Dell Inc. or its subsidiaries.
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

import argparse
import os
import shutil
import subprocess
import sys


def parse_arguments():
    """ Parses the input argments
    """

    parser = argparse.ArgumentParser(
        description="Deploys the Dashboard VM.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("cfg_filename",
                        help="Dashboard configuration file",
                        metavar="CFG-FILE")
    parser.add_argument("rhel_iso",
                        help="RHEL ISO file",
                        metavar="RHEL-ISO")

    return parser.parse_args()


def create_kickstart(ks_filename, cfg_filename):
    """ Creates the kickstart file for the Dashboard VM

    The kickstart file consists of 3 parts, two of which are fixed text. The
    middle section (part 2) is dynamically generated using the contents of the
    specified configuration file.

    NOTE:

    The fixed text (ks_part_1 and ks_part_3 variables) has '\' characters at
    the end of some lines. Sometimes there is one of them and sometimes there
    are two, and the distinction is important.

    - When a line ends in a single '\', Python will merge that line and the one
      that follows into a single long line of text. No '\' will appear at the
      end of the line in the kickstart file.

    - When a line ends in a double "\\", the back-slash is escaped in Python,
      and a single '\' will be appended to the line in the kickstart file.
    """

    ks_part_1 = """
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

%pre --log /tmp/dashboard-pre.log

"""

    ks_part_3 = """
%end

%post --nochroot --logfile /root/dashboard-post.log
# Copy the files created during the %pre section to /root of the
# installed system for later use.
  cp -v /tmp/dashboard-pre.log /mnt/sysimage/root
  cp -v /tmp/ks_include.txt /mnt/sysimage/root
  cp -v /tmp/ks_post_include.txt /mnt/sysimage/root
  mkdir -p /mnt/sysimage/root/dashboard-ks-logs
  cp -v /tmp/dashboard-pre.log /mnt/sysimage/root/dashboard-ks-logs
  cp -v /tmp/ks_include.txt /mnt/sysimage/root/dashboard-ks-logs
  cp -v /tmp/ks_post_include.txt /mnt/sysimage/root/dashboard-ks-logs
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
  echo "MTU=${eth0_mtu}" >> /etc/sysconfig/network-scripts/ifcfg-eth0
  echo "MTU=${eth1_mtu}" >> /etc/sysconfig/network-scripts/ifcfg-eth1

  sed -i -e '/^DNS/d' -e '/^GATEWAY/d' \
/etc/sysconfig/network-scripts/ifcfg-eth0
  sed -i -e '/^DNS/d' -e '/^GATEWAY/d' \
/etc/sysconfig/network-scripts/ifcfg-eth1

  echo "$( ip addr show dev eth0 | awk '/inet / { print $2 }' | \
sed 's/\/.*//' )  ${HostName}" >> /etc/hosts

  echo "----------------------"
  ip addr
  echo "subscription-manager register --username ${SMUser} --password ********"
  echo "----------------------"

  # Register the system using Subscription Manager
  [[ ${SMProxy} ]] && {
    ProxyInfo="--proxy ${SMProxy}"

    [[ ${SMProxyUser} ]] && ProxyInfo+=" --proxyuser ${SMProxyUser}"
    [[ ${SMProxyPassword} ]] && ProxyInfo+=" --proxypassword \
${SMProxyPassword}"

    Proxy_Creds=""
    [[ ${SMProxyUser} && ${SMProxyPassword} ]] && \\
      Proxy_Creds="${SMProxyUser}:${SMProxyPassword}@"

    HTTP_Proxy="http://${Proxy_Creds}${SMProxy}"
    ip_addresses=$(ip addr | grep -Po 'inet \K[\d.]+')
    no_proxy_list=$(echo $ip_addresses | tr ' ' ',')

    export no_proxy=$no_proxy_list
    export http_proxy=${HTTP_Proxy}
    export https_proxy=${HTTP_Proxy}

    }
  
if [[ -z ${SA_ip} ]]
  then
      subscription-manager register --username ${SMUser} --password ${SMPassword} ${ProxyInfo}
  else
      echo "$SA_ip    $SA_host" >> /etc/hosts
      rpm -Uvh http://$SA_host/pub/katello-ca-consumer-latest.noarch.rpm
      subscription-manager register --org=$SA_org --activationkey="$SA_key"
fi

  [[ x${SMPool} = x ]] \\
    && SMPool=$( subscription-manager list --available ${ProxyInfo} \
| awk '/Red Hat Enterprise Linux Server/,/Pool/ {pool = $3} END {print pool}' )

  [[ -n ${SMPool} ]] \\
    && subscription-manager attach --pool ${SMPool} ${ProxyInfo} \\
    || ( echo "Could not find a Red Hat Enterprise Linux Server pool to \
attach to. - Auto-attaching to any pool." ; \\
         subscription-manager attach --auto ${ProxyInfo}
         )

  subscription-manager repos ${ProxyInfo} --disable=* \\
    --enable=rhel-7-server-rpms \\
    --enable=rhel-7-server-extras-rpms \\
    --enable=rhel-7-server-rh-common-rpms \\
    --enable=rhel-7-server-rhceph-3-tools-rpms

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
-A INPUT -m state --state NEW -m tcp -p tcp --dport 2004 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 3000 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 7002 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 4505 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 4506 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 6789 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 8002 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 8080 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 8181 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 10080 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 10443 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp-host-prohibited
-A FORWARD -j REJECT --reject-with icmp-host-prohibited
COMMIT
EOIP

  systemctl enable iptables

  # To configure SELINUX to permissive, uncomment the following line
  #sed -i -e "s/^SELINUX=.*/SELINUX=permissive/" /etc/selinux/config

  # Configure the ntp daemon
  systemctl enable ntpd
  sed -i -e "/^server /d" /etc/ntp.conf

  for ntps in ${NTPServers//,/ }
  do
    echo "server ${ntps}" >> /etc/ntp.conf
  done

  # Add heat user for remote/manual installation steps of integrating
  # Dashboard to RDO based OSP
  /usr/sbin/groupadd -g 1000 heat-admin
  /usr/sbin/useradd -d /home/heat-admin -s /bin/bash -u 1000 -g 1000 heat-admin

  # Add heat-admin to sudoers
  echo "heat-admin ALL = (root) NOPASSWD:ALL" > /etc/sudoers.d/heat-admin
  echo "Defaults:heat-admin !requiretty" >> /etc/sudoers.d/heat-admin

  /usr/bin/yum install -y cephmetrics-ansible libselinux-python

  mkdir /tmp/mnt
  mount /dev/fd0 /tmp/mnt
  [[ -e /tmp/mnt/versionlock.list ]] && {
    cp /tmp/mnt/versionlock.list /etc/yum/pluginconf.d
    chmod 644 /etc/yum/pluginconf.d/versionlock.list
    }

  yum -y update

) 2>&1 | /usr/bin/tee -a /root/dashboard-post.log

chvt 6

%end
"""
    with open(ks_filename, "w") as ks:
        # Write part 1
        ks.write(ks_part_1)

        # Part 2 is dynamically created from the configuration file

        cfg_lines = []
        with open(cfg_filename, "r") as cfg_file:
            cfg_lines = [line.strip("\n") for line in cfg_file.readlines()]

        ks_include = "/tmp/ks_include.txt"
        ks_post_include = "/tmp/ks_post_include.txt"
        hostname = ""
        nameservers = ""
        gateway = ""

        for line in cfg_lines:
            if line.startswith("#") or line.startswith(";") or len(line) == 0:
                continue
            tokens = line.split()

            if tokens[0] == "rootpassword":
                ks.write("echo rootpw '{}' >> {}\n".
                         format(tokens[1], ks_include))

            elif tokens[0] == "timezone":
                ks.write("echo timezone '{}' --utc >> {}\n".
                         format(tokens[1], ks_include))

            elif tokens[0] == "hostname":
                hostname = tokens[1]
                ks.write("echo HostName='{}' >> {}\n".
                         format(hostname, ks_post_include))

            elif tokens[0] == "nameserver":
                nameservers = tokens[1]
                ks.write("echo NameServers='{}' >> {}\n".
                         format(nameservers, ks_post_include))

            elif tokens[0] == "gateway":
                gateway = tokens[1]
                ks.write("echo Gateway='{}' >> {}\n".
                         format(gateway, ks_post_include))

            elif tokens[0] == "ntpserver":
                ks.write("echo NTPServers='{}' >> {}\n".
                         format(tokens[1], ks_post_include))

            elif tokens[0] == "smuser":
                ks.write("echo SMUser='{}' >> {}\n".
                         format(tokens[1], ks_post_include))

            elif tokens[0] == "smpassword":
                ks.write("echo SMPassword='{}' >> {}\n".
                         format(tokens[1], ks_post_include))

            elif tokens[0] == "smpool":
                ks.write("echo SMPool='{}' >> {}\n".
                         format(tokens[1], ks_post_include))

            elif tokens[0] == "satellite_ip":
                ks.write("echo SA_ip='{}' >> {}\n".
                         format(tokens[1], ks_post_include))

            elif tokens[0] == "satellite_hostname":
                ks.write("echo SA_host='{}' >> {}\n".
                         format(tokens[1], ks_post_include))

            elif tokens[0] == "satellite_org":
                ks.write("echo SA_org='{}' >> {}\n".
                         format(tokens[1], ks_post_include))

            elif tokens[0] == "satellite_activation_key":
                ks.write("echo SA_key='{}' >> {}\n".
                         format(tokens[1], ks_post_include))

            elif tokens[0] == "smproxy":
                ks.write("echo SMProxy='{}' >> {}\n".
                         format(tokens[1], ks_post_include))

            elif tokens[0] == "smproxyuser":
                ks.write("echo SMProxyUser='{}' >> {}\n".
                         format(tokens[1], ks_post_include))

            elif tokens[0] == "smproxypassword":
                ks.write("echo SMProxyPassword='{}' >> {}\n".
                         format(tokens[1], ks_post_include))

            elif tokens[0] == "eth0":
                ks.write("echo network --activate --onboot=true --noipv6"
                         " --device='{}' --bootproto=static --ip='{}'"
                         " --netmask='{}' --hostname='{}'"
                         " --gateway='{}' --nameserver='{}' --mtu='{}'>> {}\n".
                         format(
                             tokens[0],
                             tokens[1],
                             tokens[2],
                             hostname,
                             gateway,
                             nameservers,
                             tokens[3],
                             ks_include))
                ks.write("echo eth0_mtu='{}' >> {}\n".
                         format(tokens[3], ks_post_include))

            elif tokens[0] == "eth1":
                ks.write("echo network --activate --onboot=true --noipv6"
                         " --device='{}' --bootproto=static --ip='{}'"
                         " --netmask='{}' --gateway='{}' --nodefroute "
                         "--mtu='{}' >> {}\n".
                         format(
                             tokens[0],
                             tokens[1],
                             tokens[2],
                             gateway,
                             tokens[3],
                             ks_include))
                ks.write("echo eth1_mtu='{}' >> {}\n".
                         format(tokens[3], ks_post_include))

        # Write part 3, and we're done
        ks.write(ks_part_3)


def create_floppy_image(vlock_filename, floppy_image):
    """ Creates the floppy image used to install the vlock file
    """

    # Delete any existing image to start clean
    if os.access(floppy_image, os.R_OK):
        os.unlink(floppy_image)

    subprocess.check_call("mkfs.vfat -C {} 1440".format(floppy_image),
                          shell=True)

    floppy_mnt = "/tmp/mnt-dashboard"
    os.mkdir(floppy_mnt)

    subprocess.check_call("mount -o loop {} {}".format(floppy_image,
                                                       floppy_mnt),
                          shell=True)

    shutil.copy(vlock_filename, os.path.join(floppy_mnt, "versionlock.list"))

    subprocess.check_call("umount {}".format(floppy_mnt), shell=True)
    os.rmdir(floppy_mnt)


def main():
    args = parse_arguments()

    ks_filename = "dashboard.ks"
    ks_tmp_filename = os.path.join("/tmp", ks_filename)
    create_kickstart(ks_tmp_filename, args.cfg_filename)

    images_path = "/store/data/images"
    dashboard_image = os.path.join(images_path, "dashboard.img")
    floppy_image = os.path.join(images_path, "dashboard-floppy.img")

    # Ensure the images directory exists
    try:
        # This may fail, including when the directory already exists
        os.makedirs(images_path)
    except:
        pass
    finally:
        # Final check for whether the images directory is valid. We don't
        # care about the contents, but rely on an exception if the directory
        # doesn't exist. If no exception then we're good.
        os.listdir(images_path)

    if os.path.exists(dashboard_image):
        os.remove(dashboard_image)

    if os.path.exists(floppy_image):
        os.remove(floppy_image)

    virt_install_args = [
        "virt-install",
        "--name dashboard",
        "--memory 16384",
        "--vcpus 4",
        "--hvm",
        "--os-type linux",
        "--os-variant rhel7",
        "--disk {},bus=virtio,size=100".format(dashboard_image),
        "--network bridge=br-pub-api",
        "--network bridge=br-stor",
        "--initrd-inject {}".format(ks_tmp_filename),
        "--extra-args 'ks=file:/{}'".format(ks_filename),
        "--noautoconsole",
        "--graphics spice",
        "--autostart",
        "--location {}".format(args.rhel_iso)
    ]

    # If the vlock file exists then add it to the floppy image
    vlock_filename = "dashboard_vm.vlock"
    if os.access(vlock_filename, os.R_OK):
        create_floppy_image(vlock_filename, floppy_image)
        virt_install_args.append("--disk {},device=floppy".format(
            floppy_image))

    return subprocess.call(" ".join(virt_install_args), shell=True)


if __name__ == "__main__":
    sys.exit(main())
