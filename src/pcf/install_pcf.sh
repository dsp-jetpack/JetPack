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

#title :install_pcf.sh 
#description :This script will install Ops Manager Director and Pivotal Elastic Runtime 1.11.5 on Openstack 10. 
#author :Rachita Gupta
#date :07/24/2017
#version :1.0 
#usage	:./install_pcf.sh
#notes : Please make sure that provision_optack.sh script is executed successfully before running this script.

#color coding
NC='\033[0m' 
RED='\033[0;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m' 

# Configuring the Ops Manager Director
echo -e "${GREEN}********************************************************${NC}\n"
echo -e "${GREEN}* Configuring the Ops Manager Director (Bosh Director) *${NC}\n"
echo -e "${GREEN}********************************************************${NC}\n"

# Cheching if the dependencies are installed for Ops Manager
echo -e "${YELLOW}***Checking Dependencies on OpsManager***${NC}\n"
if  which ruby  2>/dev/null; then
    echo -e "${YELLOW}***Ruby is already installed***${NC}\n"
else
    echo -e "${YELLOW}***Please install Ruby***${NC}"
fi

# Fetching the details from Openstack overcloud such as Openstack Project Name, Username, Password, Authentication URL
echo -e "${YELLOW}***Fetching the Overcloud Details***${NC}\n"
OVERCLOUD=$(cat overcloud.txt)
PROJECTNAME=$(cat $OVERCLOUD | grep -oP '(?<=OS_PROJECT_NAME=).*')
if [ -z $PROJECTNAME ]; 
	then TENANT=$(cat $OVERCLOUD | grep -oP '(?<=OS_TENANT_NAME=).*')
	else TENANT=$(cat $OVERCLOUD | grep -oP '(?<=OS_PROJECT_NAME=).*')
fi
USERNAME=$(cat $OVERCLOUD | grep -oP '(?<=OS_USERNAME=).*')
PASSWORD=$(cat $OVERCLOUD | grep -oP '(?<=OS_PASSWORD=).*')
AUTHURL=$(cat $OVERCLOUD | grep -oP '(?<=OS_AUTH_URL=).*')

# Fetching the value of Fully Qualified Domain Name for OpsManager entered in previous script
OPSMANAGERFQDN=$(cat fqdn.txt)

# UserInput for the Private Tenant Network ID
echo -e "${RED}***Please enter the Tenant NetworkID you used to provision OpenStack***${NC}\n"
read NETWORKID

# UserInput for the Private Tenant Network CIDR
echo -e "${RED}***Please enter the Tenant Network CIDR***${NC}\n"
read CIDR

# UserInput for the Private Tenant Network Reserved IPs. Please keep the first 50 IPs of your network as reserved
echo -e "${RED}***Please enter a Range of Reserved IPs. Ops Manager will not deploy VMs to any IP in this range***${NC}\n"
read RESERVEDIP

# UserInput for the Private Tenant Network DNS Name Server
echo -e "${RED}***Please enter the DNS Name Server for your Network***${NC}\n"
read DNSSERVER

# UserInput for the Private Tenant Network Gateway
echo -e "${RED}***Please enter the Gateway for your Network***${NC}\n"
read GATEWAY

# Deleting old access token file
if [ -f accesstoken.txt ];
then
echo -e "${YELLOW}***Deleting the existing Aceess Token File***${NC}\n"
rm accesstoken.txt
fi

# Installing Ruby gem for UAAC
echo -e "${YELLOW}***Installing ruby gem for User Account and Authentication CLI***${NC}\n"
sudo gem install cf-uaac

# Targetting the UAA for OpsManager FQDN
echo -e "${YELLOW}***Targetting the User Account and Authentication for OpsManager FQDN***${NC}\n"
uaac target https://$OPSMANAGERFQDN/uaa --skip-ssl-validation

# UserInput for OpsManager Client ID, Username and Password. Please use "opsman" for Client ID and leave Client Secret as blank.
echo -e "${YELLOW}***Please enter the Client ID, Username and Password for OpsManager***${NC}\n"
uaac token owner get

# Retrieving the Access Token for OpsManager
echo -e "${YELLOW}***Retrieving the Access Token for OpsManager***${NC}\n"
uaac context > accesstoken.txt 
ACCESSTOKEN=$(grep -o 'access_token:[^,]*' accesstoken.txt | awk '{print $2}')

Retrieving the private key from pem file created while provisioning openstack
echo -e "${YELLOW}***Retrieving the private key from pem file***${NC}\n"
PRIVATEKEY=$(sed ':a;N;$!ba;s/\n/\\n/g' pcf.pem)

# Updating the director, IaaS and security peoperties for Ops Manager Director
echo -e "${YELLOW}***Updating the director, IaaS and security peoperties for Ops Manager Director***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/director/properties" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"iaas_configuration": {"identity_endpoint":"'"$AUTHURL"'","username":"'"$USERNAME"'","password":"'"$PASSWORD"'","tenant":"'"$TENANT"'","security_group": "pcf","key_pair_name": "pcf","ssh_private_key": "'"$PRIVATEKEY"'","region": "regionOne","ignore_server_availability_zone":false,"disable_dhcp":true},"director_configuration": {"ntp_servers_string": "0.amazon.pool.ntp.org, 1.amazon.pool.ntp.org","metrics_ip": null,"resurrector_enabled": true,"max_threads": null,"database_type": "internal","blobstore_type": "local"},"security_configuration": {"trusted_certificates": null,"generate_vm_passwords": true}}' 

# Updating the Openstack Config & Avialability Zones for Ops Manager Director
echo -e "${YELLOW}***Updating the Openstack Config & Avialability Zones for Ops Manager Director***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/director/availability_zones" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"availability_zones": [{ "name": "nova", "guid": "existing-guid" }]}'

# Updating the Network configuration for Ops Manager Director
echo -e "${YELLOW}***Updating the Network configuration for Ops Manager Director***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/director/networks" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"icmp_checks_enabled": true,"networks": [{"name": "PCFnetwork","service_network": false,"subnets": [{"iaas_identifier": "'"$NETWORKID"'","cidr": "'"$CIDR"'","reserved_ip_ranges": "'"$RESERVEDIP"'","dns": "'"$DNSSERVER"'","gateway": "'"$GATEWAY"'","availability_zone_names": ["nova"]}]}]}'

# Assigning the Network and Avialability Zone
echo -e "${YELLOW}***Assigning the Network and Avialability Zone***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/director/network_and_az" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"network_and_az": {"network": {"name": "PCFnetwork"},"singleton_availability_zone": {"name": "nova"}}}'

# Installing OpsManager Director. Please ignore ICMP Error messages as PCF Security blocks ICMP
echo -e "${YELLOW}***Installing OpsManager Director. Please ignore ICMP Error messages as PCF Security blocks ICMP***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/installations" -k -X POST -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"ignore_warnings": true}'

# Deleting old status file for OpsManager Director
if [ -f status1.txt ];
then
echo -e "${YELLOW}***Deleting the existing Status File for OpsManager Director***${NC}\n"
rm status1.txt
fi

# Fetching the status for OpsManager Director installation
curl "https://$OPSMANAGERFQDN/api/v0/installations/1" -k -X GET -H "Authorization: Bearer $ACCESSTOKEN" > status1.txt
STATUS1=$(grep -c 'running' status1.txt)
if [ $STATUS1 -eq 1 ];
then 
echo -e "${YELLOW}***The installation for OpsManager Director is running***${NC}\n"
fi
while true; do
    curl "https://$OPSMANAGERFQDN/api/v0/installations/1" -k -X GET -H "Authorization: Bearer $ACCESSTOKEN" > status1.txt
    SUCCESS1=$(grep -c 'succeeded' status1.txt)
    FAILURE1=$(grep -c 'failed' status1.txt)
    if [ $SUCCESS1 -eq 1 ]; then
        echo -e "${GREEN}*******************************************************************************${NC}\n"
		echo -e "${GREEN}* Configuring the Ops Manager Director (Bosh Director) Completed Successfully *${NC}\n"
		echo -e "${GREEN}*******************************************************************************${NC}\n"
        break
    elif [ $FAILURE1 -eq 1 ]; then
        echo -e "${YELLOW}***The installation for OpsManager Director has failed***${NC}\n"
        break
    fi
    echo -e "${YELLOW}***The installation for OpsManager Director is still running***${NC}\n"
    sleep 120
done

# Installing the Pivotal Cloud Foundry Elastic Runtime Version 1.11.5
echo -e "${GREEN}***********************************************************************${NC}\n"
echo -e "${GREEN}* Installing the Pivotal Cloud Foundry Elastic Runtime Version 1.11.5 *${NC}\n"
echo -e "${GREEN}***********************************************************************${NC}\n"

# Downloading the Pivotal Elastic Runtime version 1.11.5 from Pivotal Network
echo -e "${YELLOW}***Downlaoding the Pivotal Elastic Runtime 1.11.5 from Pivotal Network***${NC}\n"
wget -O "cf-1.11.5-build.2.pivotal" --header="Authorization: Token 6K8ySzrmSedjfr7ALpw8" https://network.pivotal.io/api/v2/products/elastic-runtime/releases/6213/product_files/25540/download

# Adding Pivotal Cloud Foundry Elastic Runtime to available products on Installation Dashboard
echo -e "${YELLOW}***Adding Pivotal Cloud Foundry Elastic Runtime to available products on Installation Dashboard***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/available_products" -k -X POST -H "Authorization: Bearer $ACCESSTOKEN" -F 'product[file]=@/home/ubuntu/cf-1.11.5-build.2.pivotal'

# Staging Pivotal Cloud Foundry Elastic Runtime on Installation Dashboard
echo -e "${YELLOW}***Staging Pivotal Cloud Foundry Elastic Runtime on Installation Dashboard***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/products" -k -X POST -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"name": "cf", "product_version": "1.11.5"}'

# Fetching a Floating IP Address for HAProxy Load Balancer and TCP Router
echo -e "${YELLOW}***Fetching a Floating IP Address for HAProxy Load Balancer and TCP Router***${NC}\n"
HAPROXY=$(cat haproxy.txt)
TCPROUTER=$(cat tcprouter.txt)

# User needs to create a wildcard DNS record for HAProxy load balancer using the IP address generated in previous step
echo -e "${YELLOW}***Please create a wildcard DNS record for HAProxy load balancer $HAPROXY***${NC}\n"

# UserInput for FQDN created for HAProxy load balancer created in previous step
echo -e "${RED}***Please enter the Fully Qualified Domain Name created for HAProxy load balancer***${NC}\n"
read LOADFQDN

# Fetching System and Application Domians using the HAProxy FQDN created in previous step
SYSDOMAIN=$(sed 's/^\s*./system/g' <<< "$LOADFQDN")
APPSDOMAIN=$(sed 's/^\s*./system/g' <<< "$LOADFQDN")

# Deleting existing GUID for Pivotal Elastic Runtime
if [ -f productguid.txt ];
then
echo -e "${YELLOW}***Deleting the existing Product GUI File***${NC}\n"
rm productguid.txt
fi

# Fetching the GUID for Pivotal Elastic Runtime
echo -e "${YELLOW}***Fetching the GUID for Pivotal Elastic Runtime***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/products" -k -X GET -H "Authorization: Bearer $ACCESSTOKEN" > productguid.txt
PRODGUID=$(grep -o 'cf-*[^"]\+' productguid.txt | sort | uniq)

# Updating the Domain properties for Elastic Runtime
echo -e "${YELLOW}***Updating the Domain properties for Elastic Runtime***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/products/$PRODGUID/properties" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"properties": {".cloud_controller.system_domain": {"type": "wildcard_domain","configurable": true,"credential": false,"value": "'"$SYSDOMAIN"'","optional": false},".cloud_controller.apps_domain": {"type": "wildcard_domain","configurable": true,"credential": false,"value": "'"$APPSDOMAIN"'","optional": false}}}'

# Deleting old root certificate file
if [ -f rootcertificate.txt ];
then
echo -e "${YELLOW}***Deleting the existing Root Certificate File***${NC}\n"
rm rootcertificate.txt
fi

# Generating RSA Certificate using the FQDN for wildcard entry
echo -e "${YELLOW}***Generating RSA Certificate***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/certificates/generate" -k -X POST -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{ "domains": ["*.oss.labs", "'"$LOADFQDN"'"] }' > rootcertificate.txt #check subdomain
PRIVATEPEM="-----BEGIN RSA PRIVATE KEY$(grep -o -P '(?<=-----BEGIN RSA PRIVATE KEY).*(?=END RSA PRIVATE KEY-----)' rootcertificate.txt)END RSA PRIVATE KEY-----\n"
CERTPEM="-----BEGIN CERTIFICATE$(grep -o -P '(?<=-----BEGIN CERTIFICATE).*(?=END CERTIFICATE-----)' rootcertificate.txt)END CERTIFICATE-----\n"

# Updating the Properties for Pivotal Elastic Runtime
echo -e "${YELLOW}***Updating the Properties Pivotal Elastic Runtime***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/products/$PRODGUID/properties" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"properties": {".properties.networking_point_of_entry.haproxy.ssl_rsa_certificate": {"type": "rsa_cert_credentials","configurable": true,"credential": true,"value": {"cert_pem": "'"$CERTPEM"'", "private_key_pem": "'"$PRIVATEPEM"'"},"optional": true}}}'
curl "https://$OPSMANAGERFQDN/api/v0/staged/products/$PRODGUID/properties" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"properties": {".ha_proxy.skip_cert_verify": {"type": "boolean","configurable": true,"credential": false,"value": true,"optional": false}}}'
curl "https://$OPSMANAGERFQDN/api/v0/staged/products/$PRODGUID/properties" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"properties": {".properties.tcp_routing": {"type": "selector","configurable": true,"credential": false,"value": "enable","optional": false},".properties.tcp_routing.enable.reservable_ports": {"type": "string","configurable": true,"credential": false,"value": "1024-1123","optional": false}}}'
curl "https://$OPSMANAGERFQDN/api/v0/staged/products/$PRODGUID/properties" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"properties": {".properties.security_acknowledgement": {"type": "string","configurable": true,"credential": false,"value": "x","optional": false}}}'
curl "https://$OPSMANAGERFQDN/api/v0/staged/products/$PRODGUID/properties" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"properties": {".uaa.service_provider_key_credentials": {"type": "rsa_cert_credentials","configurable": true,"credential": true,"value": {"cert_pem": "'"$CERTPEM"'", "private_key_pem": "'"$PRIVATEPEM"'"},"optional": false}}}'
curl "https://$OPSMANAGERFQDN/api/v0/staged/products/$PRODGUID/properties" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"properties": {".mysql_monitor.recipient_email": {"type": "string","configurable": true,"credential": false,"value": "rachita_gupta@dell.com","optional": false}}}'

# Adding HAProxy and TCPRouter Floating IP Address to Resource Config file
echo -e "${YELLOW}***Adding HAProxy Floating IP Address to Resource Config File***${NC}\n"
cd /home/tempest-web/tempest/web/scripts/

# UserInput for setting the Decryption Passphrase for OpsManager to decrypt the installation file
echo -e "${YELLOW}***Please enter the Decryption Passphrase for OpsManager to decrypt the installation file***${NC}\n"
sudo -u tempest-web ./decrypt /var/tempest/workspaces/default/installation.yml /tmp/installation.yml
cd /tmp
sudo sed -ri 's/^(\s*)(installation_name\s*:\s*ha_proxy\s*$)/\1installation_name: ha_proxy\n    internet_connected: false\n    floating_ips: "'"$HAPROXY"'"/' installation.yml
sudo sed -ri 's/^(\s*)(installation_name\s*:\s*tcp_router\s*$)/\1installation_name: tcp_router\n    internet_connected: false\n    floating_ips: "'"$TCPROUTER"'"/' installation.yml

# UserInput for setting the Decryption Passphrase for OpsManager to encrypt the installation file
echo -e "${YELLOW}***Please enter the Decryption Passphrase for OpsManager to encrypt the installation file***${NC}\n"
sudo -u tempest-web RAILS_ENV=production /home/tempest-web/tempest/web/scripts/encrypt /tmp/installation.yml /var/tempest/workspaces/default/installation.yml
sudo service tempest-web stop && sudo service tempest-web start
sleep 30;
echo -e "${RED}***Please enter the Decryption Passphrase for OpsManager to decrypt OpsManger Applaince***${NC}\n"
read DECRYPTION
curl "https://$OPSMANAGERFQDN/api/v0/unlock" -k -X PUT -H "Content-Type: application/json" -d '{"passphrase": "'"$DECRYPTION"'"}'
echo -e "${YELLOW}***Authentication is starting up and will take a few minutes.***${NC}\n"
sleep 45;

# Installing Pivotal Elastic Runtime. Please ignore ICMP Error messages as PCF Security blocks ICMP.
echo -e "${YELLOW}***Installing Pivotal Elastic Runtime. Please ignore ICMP Error messages as PCF Security blocks ICMP.***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/installations" -k -X POST -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"ignore_warnings": true}'

# Deleting old status file for Elastic Runtime
if [ -f status2.txt ];
then
echo -e "${YELLOW}***Deleting the existing Status File for Pivotal Elastic Runtime***${NC}\n"
rm status2.txt
fi

# Fetching the status for Elastic Runtime installation
curl "https://$OPSMANAGERFQDN/api/v0/installations/2" -k -X GET -H "Authorization: Bearer $ACCESSTOKEN" > status2.txt
STATUS2=$(grep -c 'running' status2.txt)
if [ $STATUS2 -eq 1 ];
then 
echo -e "${YELLOW}***The installation for Pivotal Elastic Runtime is running***${NC}\n"
fi
while true; do
    curl "https://$OPSMANAGERFQDN/api/v0/installations/2" -k -X GET -H "Authorization: Bearer $ACCESSTOKEN" > status2.txt
    SUCCESS2=$(grep -c 'succeeded' status2.txt)
    FAILURE2=$(grep -c 'failed' status2.txt)
    if [ $SUCCESS2 -eq 1 ]; then
		echo -e "${GREEN}*******************************************************************************${NC}\n"
		echo -e "${GREEN}* Installing the Pivotal Cloud Foundry Elastic Runtime Completed Successfully *${NC}\n"
		echo -e "${GREEN}*******************************************************************************${NC}\n"
        break
    elif [ $FAILURE2 -eq 1 ]; then
        echo -e "${YELLOW}***The installation for Pivotal Elastic Runtime has failed***${NC}\n"
        break
    fi
    echo -e "${YELLOW}***The installation for Pivotal Elastic Runtime is still running***${NC}\n"
    sleep 120
done

#Installing the Pivotal JMX Bridge Version 1.9.1
echo -e "${GREEN}*******************************************${NC}\n"
echo -e "${GREEN}* Installing the JMX Bridge Version 1.9.1 *${NC}\n"
echo -e "${GREEN}*******************************************${NC}\n"

#Downloading the Pivotal JMX Bridge 1.9.1 from Pivotal Network
echo -e "${YELLOW}***Downlaoding the Pivotal JMX Bridge 1.9.1 from Pivotal Network***${NC}\n"
wget -O "p-metrics-1.9.1.pivotal" --header="Authorization: Token 6K8ySzrmSedjfr7ALpw8" https://network.pivotal.io/api/v2/products/p-metrics/releases/5624/product_files/21560/download

#Adding Pivotal JMX Bridge 1.9.1 to available products on Installation Dashboard
echo -e "${YELLOW}***Adding Pivotal JMX Bridge to available products on Installation Dashboard***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/available_products" -k -X POST -H "Authorization: Bearer $ACCESSTOKEN" -F 'product[file]=@/home/ubuntu/p-metrics-1.9.1.pivotal'

#Staging Pivotal JMX Bridge 1.9.1 on Installation Dashboard
echo -e "${YELLOW}***Staging Pivotal JMX Bridge on Installation Dashboard***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/products" -k -X POST -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"name": "p-metrics", "product_version": "1.9.1"}'

#Downloading the Steamcell 3363.24 for JMX Bridge 1.9.1
echo -e "${YELLOW}***Downlaoding the Steamcell 3363.24 for JMX Bridge 1.9.1***${NC}\n"
wget -O "bosh-stemcell-3363.24-openstack-kvm-ubuntu-trusty-go_agent-raw.tgz" --header="Authorization: Token 6K8ySzrmSedjfr7ALpw8" https://network.pivotal.io/api/v2/products/stemcells/releases/5560/product_files/21229/download

#Deleting existing GUID for Pivotal JMX Bridge
if [ -f jmxguid.txt ];
then
echo -e "${YELLOW}***Deleting the existing JMX GUI File***${NC}\n"
rm jmxguid.txt
fi

#Fetching the GUID for Pivotal JMX Bridge
echo -e "${YELLOW}***Fetching the GUID for Pivotal JMX Bridge***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/products" -k -X GET -H "Authorization: Bearer $ACCESSTOKEN" > jmxguid.txt
JMXGUID=$(grep -o 'p-metrics-*[^"]\+' jmxguid.txt | sort | uniq)

#UserInput for the JMX Bridge Username 
echo -e "${RED}***Please enter Username for JMX Bridge***${NC}\n"
read JMXUSER

#UserInput for the JMX Bridge Username 
echo -e "${RED}***Please enter Password for JMX Bridge***${NC}\n"
read JMXPASS

#Updating the Domain properties for JMX Bridge
echo -e "${YELLOW}***Updating the properties for JMX Bridge***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/products/$JMXGUID/properties" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"properties": {".maximus.credentials": {"type": "simple_credentials","configurable": true,"credential": true,"value": {"identity": "'"$JMXUSER"'","password": "'"$JMXPASS"'"},"optional": false}}}'

#Importing Stemcell 3363.24 for JMX Bridge 1.9.1
curl "https://$OPSMANAGERFQDN/api/v0/stemcells" -k -X POST -H "Authorization: Bearer $ACCESSTOKEN" -F 'stemcell[file]=@/home/ubuntu/bosh-stemcell-3363.24-openstack-kvm-ubuntu-trusty-go_agent-raw.tgz'

#Installing JMX Bridge. Please ignore ICMP Error messages as PCF Security blocks ICMP.
echo -e "${YELLOW}***Installing Pivotal Elastic Runtime. Please ignore ICMP Error messages as PCF Security blocks ICMP.***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/installations" -k -X POST -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"ignore_warnings": true}'

#Deleting old status file for JMX Bridge
if [ -f status3.txt ];
then
echo -e "${YELLOW}***Deleting the existing Status File for Pivotal Elastic Runtime***${NC}\n"
rm status3.txt
fi

#Fetching the status for JMX Bridge installation
curl "https://$OPSMANAGERFQDN/api/v0/installations/3" -k -X GET -H "Authorization: Bearer $ACCESSTOKEN" > status3.txt
STATUS3=$(grep -c 'running' status3.txt)
if [ $STATUS3 -eq 1 ];
then 
echo -e "${YELLOW}***The installation for Pivotal JMX Bridge is running***${NC}\n"
fi
while true; do
    curl "https://$OPSMANAGERFQDN/api/v0/installations/3" -k -X GET -H "Authorization: Bearer $ACCESSTOKEN" > status3.txt
    SUCCESS3=$(grep -c 'succeeded' status3.txt)
    FAILURE3=$(grep -c 'failed' status3.txt)
    if [ $SUCCESS3 -eq 1 ]; then
		echo -e "${GREEN}************************************************************${NC}\n"
		echo -e "${GREEN}* Installing the Pivotal JMX Bridge Completed Successfully *${NC}\n"
		echo -e "${GREEN}************************************************************${NC}\n"
        break
    elif [ $FAILURE3 -eq 1 ]; then
        echo -e "${YELLOW}***The installation for Pivotal JMX Bridge has failed***${NC}\n"
        break
    fi
    echo -e "${YELLOW}***The installation for Pivotal JMX Bridge is still running***${NC}\n"
    sleep 120
done

#Fetching the IP Address for JMX Bridge
curl "https://$OPSMANAGERFQDN/api/v0/deployed/products/$JMXGUID/status" -k -X GET -H "Authorization: Bearer $ACCESSTOKEN" > jmx.txt
JMXIP=$(grep -E -o '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)' jmx.txt | head -1)

#Updating the director JMX IP Address on OpsManager Director
echo -e "${YELLOW}***Updating the director JMX IP Address on OpsManager Director***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/staged/director/properties" -k -X PUT -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"director_configuration": {"metrics_ip": "'"$JMXIP"'"}}' 

#Installing JMX Bridge. Please ignore ICMP Error messages as PCF Security blocks ICMP.
echo -e "${YELLOW}***Installing Pivotal Elastic Runtime. Please ignore ICMP Error messages as PCF Security blocks ICMP.***${NC}\n"
curl "https://$OPSMANAGERFQDN/api/v0/installations" -k -X POST -H "Authorization: Bearer $ACCESSTOKEN" -H "Content-Type: application/json" -d '{"ignore_warnings": true}'

#Deleting old status file
if [ -f status4.txt ];
then
echo -e "${YELLOW}***Deleting the existing Status File for Pivotal Cloud Foundry***${NC}\n"
rm status4.txt
fi

curl "https://$OPSMANAGERFQDN/api/v0/installations/4" -k -X GET -H "Authorization: Bearer $ACCESSTOKEN" > status4.txt
STATUS4=$(grep -c 'running' status4.txt)
if [ $STATUS4 -eq 1 ];
then 
echo -e "${YELLOW}***The installation for Pivotal Cloud Foundry is running***${NC}\n"
fi
while true; do
    curl "https://$OPSMANAGERFQDN/api/v0/installations/4" -k -X GET -H "Authorization: Bearer $ACCESSTOKEN" > status4.txt
    SUCCESS4=$(grep -c 'succeeded' status4.txt)
    FAILURE4=$(grep -c 'failed' status4.txt)
    if [ $SUCCESS4 -eq 1 ]; then
		echo -e "${GREEN}****************************************${NC}\n"
		echo -e "${GREEN}* Installing the Pivotal Cloud Foundry *${NC}\n"
		echo -e "${GREEN}****************************************${NC}\n"
        break
    elif [ $FAILURE4 -eq 1 ]; then
        echo -e "${YELLOW}***The installation for Pivotal Cloud Foundry has failed***${NC}\n"
        break
    fi
    echo -e "${YELLOW}***The installation for Pivotal Cloud Foundry still running***${NC}\n"
    sleep 120
done

