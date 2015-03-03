#!/bin/bash
# Copyright 2014, Dell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Rajini Ram
# Version: 0.1
#
#exit on failure
#set -e 

shopt -s nullglob

NETWORK_CONFIG_DIR=/etc/sysconfig/network-scripts


# Logging levels
FATAL=0
ERROR=1
WARN=2
INFO=3
DEBUG=4

# Default logging level
LOG_LEVEL=$INFO

# Logging functions
log() { echo -e "$(date '+%F %T'): $@" >&2; }
fatal() { log "FATAL: $@" >&2; exit 1; }
error() { [[ $ERROR -le $LOG_LEVEL ]] && log "ERROR: $@"; }
warn() { [[ $WARN -le $LOG_LEVEL ]] && log "WARN: $@"; }
info() { [[ $INFO -le $LOG_LEVEL ]] && log "INFO: $@"; }
debug() { [[ $DEBUG -le $LOG_LEVEL ]] && log "DEBUG: $@"; }


######## Functions ############
read_config(){
	set -e
	info "Reading config...." 	
        tr -d '\r' < ./config.cfg > ./config.in
	source ./config.in
	if [ $? -ne 0 ]; then
            echo "command failed"
	    exit 1
	fi
	set +e	
}

subscription_manager() {
	info "### Register with Subscription manager and Yum update ###"

	subscription-manager repos --list

	subscription-manager register --username dellcloudsol --password cr0wBar!

	# the pool id out to a parameter
	subscription-manager attach --pool=$pool_id
}

os_update() {
	yum -y update
}

tftp_setup(){
	info "### Installing tftp server ###"	

	yum install -y dhcp tftp tftp-server syslinux wget vsftpd
	mkdir -p /var/lib/tftpboot
	chmod 777 /var/lib/tftpboot
	cp -v /usr/share/syslinux/pxelinux.0 /var/lib/tftpboot
	cp -v /usr/share/syslinux/menu.c32 /var/lib/tftpboot
	cp -v /usr/share/syslinux/memdisk /var/lib/tftpboot
	cp -v /usr/share/syslinux/mboot.c32 /var/lib/tftpboot
	cp -v /usr/share/syslinux/chain.c32 /var/lib/tftpboot
	mkdir /var/lib/tftpboot/pxelinux.cfg
	mkdir -p /var/lib/tftpboot/netboot/

    TFTP_FILE="/var/lib/tftpboot/pxelinux.cfg/default"

cat > $TFTP_FILE << EOF	
default menu.c32
prompt 0
timeout 30
MENU TITLE unixme.com PXE Menu
LABEL RHEL7_x64
MENU LABEL RHEL 7 X64
KERNEL /netboot/vmlinuz
APPEND initrd=/netboot/initrd.img inst.repo=http://192.168.120.188/pub ks=http://192.168.120.188/ks.cfg
EOF

TFTP_CONF_FILE="/etc/xinetd.d/tftp"

cat > $TFTP_CONF_FILE << EOF	
# default: off
# description: The tftp server serves files using the trivial file transfer \
#       protocol.  The tftp protocol is often used to boot diskless \
#       workstations, download configuration files to network-aware printers, \
#       and to start the installation process for some operating systems.
service tftp
{
        socket_type             = dgram
        protocol                = udp
        wait                    = yes
        user                    = root
        server                  = /usr/sbin/in.tftpd
        server_args             = -s /var/lib/tftpboot
        disable                 = no
        per_source              = 11
        cps                     = 100 2
        flags                   = IPv4
}
EOF

service xinetd restart

}

dhcp_setup(){

DHCP_CONFIG_FILE="/etc/dhcp/dhcpd.conf"

cat > $DHCP_CONFIG_FILE << EOF
#
# DHCP Server Configuration file.\
# see /usr/share/doc/dhcp*/dhcpd.conf.example
# see dhcpd.conf(5) man page
ddns-update-style interim;
ignore client-updates;
authoritative;
allow booting;
allow bootp;
allow unknown-clients;
# A slightly different configuration for an internal subnet.
subnet 192.168.120.0 netmask 255.255.255.0 {
range 192.168.120.190 192.168.120.210;
option domain-name-servers $pxe_server_ip;
default-lease-time 600;
max-lease-time 7200;
# PXE SERVER IP
next-server $pxe_server_ip; 
filename "pxelinux.0";
}
EOF

}

http_setup(){
	info "### Installing http server ###"

	yum install -y httpd
	service httpd restart
	service httpd status

	systemctl disable firewalld
        systemctl stop iptables
        service httpd restart
}

ipmi(){

	info "### Setting up ipmi ###"
	yum install -y ipmitool
}

python_setup(){
	info "Configuring python ####"

	yum groupinstall -y "Development Tools"
	yum groupinstall -y "Development Libraries"
	yum install python-devel
	#yum install -y pip 

	#You need to install a few extra modules, to do this run the following commands in a command prompt :

	easy_install decorator
	easy_install paramiko
	easy_install pysphere
	easy_install pyyaml
	easy_install wxpython 
	easy_install selenium
	easy_install cm_api

	### Setup PATHs

	info "Before  PATH = $PATH"
	info "Before PYTHONPATH = $PYTHONPATH"


	if [ -z "$PYTHONPATH" ]; then
		info "Need to set PYTHON_PATH and PATH"
		echo 'export PYTHONPATH=/usr/bin/python:/lib/python2.7:/lib/python2.7/site-packages:~/deploy-auto' >> ~/.bashrc
	fi


	echo $PATH | grep "deploy-auto"
	if [ $? -eq 0 ]; then
	  echo 'export PATH=$PATH:~/deploy-auto' >> ~/.bashrc
	fi	
       

	info "After: PYTHONPATH = $PYTHONPATH"
	info "After: PATH = $PATH"

}

git_setup() {
	info "### GIT Setup ####"

	yum install -y git

	#parameterized
	git config --global user.name $git_user_name
	git config --global user.email $git_user_email

	cd ~/

	git clone https://$git_user_name:$git_user_password@github.com/dell-esg/deploy-auto.git
}

file_setup(){
	mkdir /var/www/html/RH7
	cd /var/www/html/RH7

	# are we in Nashua ? if so go grab the iso's somewhere local
	ip_add=$(ip addr show)
	
	#paramterized
	if [ ! -f /var/www/html/RH7/$rhel7_iso_file ]; then
	    if [[ $ip_add == *10.152* ]]
			then
				wget --no-check-certificate --user "mht1\Script_User" --password "New2Day!" -O $rhel7_iso_file "https://10.152.248.11/folder/ISOs/RHEL-7.0-20140507.0-Server-x86_64-dvd1.iso?dcPath=Cloud%2520Bastion%2520Physical%2520Stamps&dsName=Data2%252dStorage"
		else
			wget $rhel7_iso
		fi
	else
		echo "File Already exists $rhel7_iso_file" 
	fi

	if [ ! -f /var/www/html/RH7/$rhel6_iso_file ]; then
			if [[ $ip_add == *10.152* ]]
				then
					wget --no-check-certificate --user "mht1\Script_User" --password "New2Day!" -O $rhel6_iso_file "https://10.152.248.11/folder/ISOs/RHEL6.5-20131111.0-Server-x86_64-DVD1.iso?dcPath=Cloud%2520Bastion%2520Physical%2520Stamps&dsName=Data2%252dStorage"
			else	
               wget $rhel6_iso
			 fi
	else
		echo "File Already exists $rhel6_iso_file" 
	fi

        mkdir /var/www/html/pub
        mount /var/www/html/RH7/$rhel7_iso_file /var/www/html/pu
		#finish tftp setup
        cp /var/www/html/pub/isolinux/vmlinuz /var/lib/tftpboot/netboot/
        cp /var/www/html/pub/isolinux/initrd.img /var/lib/tftpboot/netboot/
        systemctl start tftp.socket
        service tftp restart
}

ui_setup(){
info "ui setup"
yum -y groupinstall 'X Windows System' 'GNOME'
systemctl enable graphical.target --force
gnome-shell --version
yum -y install firefox
}
################################



####################################################
info "##### Setting up Auto Linux Node #####"
info "##### Starting setup #####"

# Setup Nics

info "###Setting up Nics - TODO ###"

### Read configs
read_config

### Register with subscription manager
subscription_manager

os_update
### Install tftp server ###
dhcp_setup

### Install dhcp server ###
tftp_setup


### Install http server ###
http_setup

### Install ipmi

#ipmi

### Setup python env ###

python_setup

### Setting up GIT ####

git_setup

### Setup other files

file_setup

## ui setup
ui_setup
### DONE
service httpd restart
info "##### Done #####"

bash
