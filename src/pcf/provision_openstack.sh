#!/bin/bash - 

# Copyright (c) 2017 Dell Inc. or its subsidiaries.
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

#title :provision_openstack.sh 
#description :This script will provision the Openstack Infrastructure for installing PCF 1.11.5 on Openstack 10. 
#author :Rachita Gupta
#date :07/24/2017
#version :1.0 
#usage	:./provision_openstack.sh
#notes : Please make sure that the pre requisites are met before running this script.

#color coding
NC='\033[0m' 
RED='\033[0;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'

#Provisioning the Openstack Infrastructure
echo -e "${GREEN}*********************************************${NC}\n"
echo -e "${GREEN}* Provisioning the Openstack Infrastructure *${NC}\n"
echo -e "${GREEN}*********************************************${NC}\n"

#Fetching Overcloud Stack Name
source stackrc
OVERCLOUD=$(openstack stack list | sed '4!d' | awk '{print $4 "rc"}')
echo $OVERCLOUD > overcloud.txt

#Logging into Overcloud
echo -e "${YELLOW}***Logging into the Overcloud Stack on the Director Node***${NC}\n"
source $OVERCLOUD

#Deleting old OpsManager Instance
INSTANCE=$(openstack server list | grep -oP 'OpsManager')
if [ -z $INSTANCE ];
then 
echo -e "${YELLOW}***No existing instance with name OpsManager***${NC}\n"
else 
echo -e "${YELLOW}***Deleting the existing instance with name OpsManager***${NC}\n"
nova delete OpsManager
fi

#Creating Key Pair for PCF
KEYPAIR=$(nova keypair-list | grep -oP 'pcf')
if [ -z $KEYPAIR ];
then 
echo -e "${YELLOW}***Creating a key pair with name PCF***${NC}\n"
openstack keypair create pcf > pcf.pem
else 
echo -e "${YELLOW}***Deleting the existing keypair and Creating a key pair with name PCF***${NC}\n"
nova keypair-delete pcf
openstack keypair create pcf >pcf.pem
fi

#Creating Security Group for PCF 
SECURITY=$(nova secgroup-list | grep -oP 'pcf')
if [ -z $SECURITY ];
then 
echo -e "${YELLOW}***Creating a security group with name PCF***${NC}\n"
openstack security group create pcf --description pcf
else 
echo -e "${YELLOW}***Deleting the existing security group and Creating a security group with name PCF***${NC}\n"
nova secgroup-delete pcf
openstack security group create pcf --description pcf
fi

#Managing rule for the security group created in previous step
echo -e "${YELLOW}***Managing rules for the security group***${NC}\n"
openstack security group rule create pcf --protocol tcp --ingress --dst-port 22
openstack security group rule create pcf --protocol tcp --ingress --dst-port 80
openstack security group rule create pcf --protocol tcp --ingress --dst-port 443
openstack security group rule create pcf --protocol tcp --ingress --dst-port 25555
openstack security group rule create pcf --protocol tcp --ingress --dst-port 1:65535 --src-group pcf
openstack security group rule create pcf --protocol udp --ingress --dst-port 1:65535 --src-group pcf

#Downloading Pivotal Cloud Foundry Operations Manager for Openstack Version 1.11.5 (Note: To change the version please update the verssion details in this section)
echo -e "${YELLOW}***Downloading Image File for Pivotal Cloud Foundry Operations Manager for Openstack***${NC}\n"
curl -i -H "Accept: application/json" -H "Content-Type: application/json" -H "Authorization: Token 6K8ySzrmSedjfr7ALpw8" -X POST https://network.pivotal.io/api/v2/products/ops-manager/releases/6070/eula_acceptance
wget -O "pcf-openstack-1.11.5.raw" --header="Authorization: Token 6K8ySzrmSedjfr7ALpw8" https://network.pivotal.io/api/v2/products/ops-manager/releases/6070/product_files/24695/download

#Creating Image from the file downloaded in previous step
IMAGE=$(openstack image list | grep -oP 'pcf')
if [ -z $IMAGE ];
then 
echo -e "${YELLOW}***Creating an image with name PCF***${NC}\n"
openstack image create pcf --protected --private --disk-format raw --min-disk 40 --min-ram 8192 --file pcf-openstack-1.11.5.raw 
else 
echo -e "${YELLOW}***Deleting the existing image and Creating an image with name PCF***${NC}\n"
openstack image set --unprotected pcf
openstack image delete pcf
openstack image create pcf --protected --private --disk-format raw --min-disk 40 --min-ram 8192 --file pcf-openstack-1.11.5.raw 
fi

#UserInput for the Private Tenant Network ID 
echo -e "${RED}***Please enter the Private Tenant NetworkID***${NC}\n"
read NETWORKID

#Launching OpsManager VM using the image, security group and keypair name created in previous steps 
echo -e "${YELLOW}***Launching the OpsManager VM with name OpsManager***${NC}\n"
openstack server create OpsManager --image pcf --flavor m1.large --security-group pcf --key-name pcf --nic net-id=$NETWORKID

#Associating a Floating IP with the OpsManager VM created in previous step
echo -e "${YELLOW}***Associating a Floating IP Address with the OpsManager VM***${NC}\n"
FLOATINGIP=$(openstack floating ip create public | sed '7!d' | awk '{print $4}')
openstack server add floating ip OpsManager $FLOATINGIP
openstack floating ip create public | sed '7!d' | awk '{print $4}' > haproxy.txt
openstack floating ip create public | sed '7!d' | awk '{print $4}' > tcprouter.txt

#User needs to create a FQDN for the OpsManager Floating IP created in previous step
echo -e "${YELLOW}***Please create a Fully Qualified Domain Name for OpsManager FLoating IP $FLOATINGIP***${NC}\n"

#Provisioning the Openstack Infrastructure
echo -e "${GREEN}********************************************************************${NC}\n"
echo -e "${GREEN}* Provisioning the Openstack Infrastructure Completed Successfully *${NC}\n"
echo -e "${GREEN}********************************************************************${NC}\n"

#UserInput for the FQDN created in previous step 
echo -e "${RED}***Please enter the Fully Qualified Domain Name created for Ops Manager***${NC}\n"
read OPSMANAGERFQDN
echo $OPSMANAGERFQDN > fqdn.txt

#UserInput for setting the OpsManager Username
echo -e "${RED}***Please enter a Username for Ops Manager***${NC}\n"
read USERNAME

#UserInput for setting the OpsManager Password
echo -e "${RED}***Please enter a Password for Ops Manager***${NC}\n"
read PASSWORD

#UserInput for setting the OpsManager Decryption Passphrase
echo -e "${RED}***Please enter a Decryption Passphrase for Ops Manager***${NC}\n"
read DECRYPTION

#Setting up OpsManager with the credentials from previous step
echo -e "${YELLOW}***Setting up the OpsManager with an internal Userstore***${NC}\n"
sleep 30;
curl "https://$OPSMANAGERFQDN/api/v0/setup" -k --insecure -X POST -H "Content-Type: application/json" -d '{ "setup": {"decryption_passphrase": "'"$DECRYPTION"'","decryption_passphrase_confirmation":"'"$DECRYPTION"'","eula_accepted": "true","identity_provider": "internal","admin_user_name": "'"$USERNAME"'","admin_password": "'"$PASSWORD"'","admin_password_confirmation": "'"$PASSWORD"'"}}'

#Secure copy files with details about overcloud, fqdn, haproxy, tcprouter, keypair and install_pcf script to OpsManager 
sudo scp -i pcf.pem overcloud.txt ubuntu@$FLOATINGIP:/home/ubuntu
sudo scp -i pcf.pem fqdn.txt ubuntu@$FLOATINGIP:/home/ubuntu
sudo scp -i pcf.pem haproxy.txt ubuntu@$FLOATINGIP:/home/ubuntu
sudo scp -i pcf.pem tcprouter.txt ubuntu@$FLOATINGIP:/home/ubuntu
sudo scp -i pcf.pem $OVERCLOUD ubuntu@$FLOATINGIP:/home/ubuntu
sudo scp -i pcf.pem install_pcf.sh ubuntu@$FLOATINGIP:/home/ubuntu
sudo scp -i pcf.pem pcf.pem ubuntu@$FLOATINGIP:/home/ubuntu

#SSH to the OpsManager
echo -e "${YELLOW}***Logging into the OpsManager***${NC}\n"
sudo ssh -i pcf.pem ubuntu@$FLOATINGIP

