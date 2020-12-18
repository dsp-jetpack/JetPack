#!/usr/bin/env python3

# Copyright (c) 2021 Dell Inc. or its subsidiaries.
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

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import yaml
from osp_deployer.settings.config import Settings
from infra_host import InfraHost
from infra_host import directory_check
from auto_common import Scp
from director import Director

logger = logging.getLogger("osp_deployer")

class Powerflexgw(InfraHost):


    def __init__(self):

        self.settings = Settings.settings
        logger.info("Settings.settings: %s", str(Settings.settings))
        self.ip = self.settings.powerflexgw_vm.public_api_ip
        self.root_pwd = self.settings.powerflexgw_vm.root_password
        self.rpm_dir = "/root/rpms"
        self.certs_dir = "/root/certs"
        self.lia_cert = "/opt/emc/scaleio/lia/cfg/lia_certificate.pem"
        self.mdm_cert = "/opt/emc/scaleio/mdm/cfg/mdm_management_certificate.pem"
        self.gateway_dir = "/opt/emc/scaleio/gateway/webapps/ROOT/WEB-INF/classes"
        self.gateway_conf = self.gateway_dir + "/gatewayUser.properties"
        self.keystore = self.gateway_dir + "/certificates/truststore.jks"
        self.keystore_pwd = "changeit"
        self.controller_vip = self.settings.provisioning_vip
        self.director_user = self.settings.director_install_account_user
        self.home_dir = "/home/" + self.director_user 
        self.source_overcloudrc = "source " + self.home_dir + "/" + self.settings.overcloud_name + "rc; " 
        self.pilot_dir = self.settings.foreman_configuration_scripts + "/pilot"
        self.powerflex_dir = self.pilot_dir + "/powerflex"

        self.director = Director()


    def upload_rpm(self):

        cmd = "mkdir -p " + self.rpm_dir
        self.run_as_root(cmd)
        
        logger.debug("Uploading powerflex gateway rpm")
        source_file = self.powerflex_dir + "/rpms/" + \
                      self.settings.powerflex_gateway_rpm
        self.upload_file(source_file,
                         self.rpm_dir + "/" + \
                         self.settings.powerflex_gateway_rpm)


    def install_gateway(self):
  
        logger.debug("Installing the gateway")
        powerflexgw_ip = self.settings.powerflexgw_vm.public_api_ip
        cmd = "GATEWAY_ADMIN_PASSWORD=" + \
              self.settings.powerflex_password + \
              " rpm -ivh " + \
              self.rpm_dir + \
              "/" + \
              self.settings.powerflex_gateway_rpm
        self.run_as_root(cmd)


    def configure_gateway(self):

        logger.debug("Retrieving MDM IPs")

        mdm_ips = []

        stor_ = self.settings.storage_network.rsplit(".", 1)[0]
        stor_.replace(".", '\.')

        re = self.director.run_as_root("cat /var/lib/mistral/" +
                                  self.settings.overcloud_name + 
                                  "/powerflex-ansible/inventory.yml " +
                                  "| sed -n '/mdms/,/tbs/{//!p}'")
        mdm_nodes = re[0].split("\n")
        mdm_nodes.pop()

        for each in mdm_nodes:
            provisioning_ip = each.split(" ")[0]
            ssh_opts = (
                " -o StrictHostKeyChecking=no "
                " -o UserKnownHostsFile=/dev/null "
                " -o KbdInteractiveDevices=no")

            cmd = ("ssh " + ssh_opts + " heat-admin@" +
                   provisioning_ip +
                   " /sbin/ifconfig | grep inet.*" +
                   stor_ +
                   " | awk '{print $2}'")
            re = self.director.run_tty(cmd)

            mdm_ip = re[0].split("\n")[1]
            mdm_ips.append(mdm_ip.strip())

        logger.debug("Updating gatewayUser.properties")

        cmd = ('sed -i "s|^mdm.ip.addresses=*|' +
               'mdm.ip.addresses=' +
               mdm_ips[0] +
               ',' +
               mdm_ips[1] +
               '|" ' +
               self.gateway_conf)

        self.run_as_root(cmd)


    def get_ssl_certificates(self):

        cmd = "mkdir -p " + self.certs_dir
        self.run_as_root(cmd)

        logger.debug("Retrieving all nodes IPs")

        cmd = "grep " + self.ip + " ~./ssh/known_hosts"
        re = self.director.run(cmd)
        if self.ip not in re:
            logger.debug("Authenticating the powerflex gateway vm")
            cmd = "ssh-keyscan -t ecdsa " + self.ip + " >> ~/.ssh/known_hosts"
            re = self.director.run(cmd)

        re = self.director.run_as_root("cat /var/lib/mistral/" +
                                  self.settings.overcloud_name +
                                  "/powerflex-ansible/inventory.yml " +
                                  "| sed -n '/mdms/,/tbs/{//!p}'")
        mdm_nodes = re[0].split("\n")
        mdm_nodes.pop()

        ssh_opts = (
        " -o StrictHostKeyChecking=no "
        " -o UserKnownHostsFile=/dev/null "
        " -o KbdInteractiveDevices=no"
        " -o LogLevel=ERROR")

        re = self.director.run(self.director.source_stackrc +
                              "openstack server list -f value")
        nodes = re[0].split("\n")
        nodes.pop()

        for each in nodes:
            hostname = each.split(" ")[1]
            ip = each.split(" ")[3].split("=")[1]
            if ip in str(mdm_nodes):
                logger.debug("MDM detected on host {}, capturing MDM and LIA certificates".format(hostname))
                cmds = [
                    "ssh " + ssh_opts + " heat-admin@" +
                    ip + " sudo cat " + self.mdm_cert +
                    " | sshpass -p " + self.root_pwd +
                    " ssh root@" + self.ip +
                    ' " cat > ' + self.certs_dir + "/" + hostname + '.mdm.cer"',
                    "ssh " + ssh_opts + " heat-admin@" +
                    ip + " sudo cat " + self.lia_cert +
                    " | sshpass -p " + self.root_pwd +
                    " ssh root@" + self.ip +
                    ' " cat > ' + self.certs_dir + "/" + hostname + '.lia.cer"']
                for cmd in cmds:
                    re = self.director.run(cmd)
            else:
                logger.debug("Capturing LIA certificate on host {}".format(hostname))
                cmd = ("ssh " + ssh_opts + " heat-admin@" +
                       ip +
                       " sudo cat " + self.lia_cert +
                       " | sshpass -p " + self.root_pwd +
                       " ssh root@" + self.ip +
                       ' " cat > ' + self.certs_dir + "/" + hostname + '.lia.cer"')
                re = self.director.run(cmd)

 
    def inject_ssl_certificates(self):
    
        certs_file_count = 0
        
        cmd = (" ls " + self.certs_dir)
        re = self.run_as_root(cmd)
        certs = re[0].split("\n") 
        certs.pop()
 
        for cert_file in certs:
            certs_file_count += 1
            alias = cert_file.rsplit(".", 1)[0]
            cmds = [
               "sed -ni '/CERTIFICATE/,/CERTIFICATE/p' " + 
               self.certs_dir + "/" + cert_file,
               "keytool -import -trustcacerts -noprompt -storepass " +
               self.keystore_pwd + " -alias " +
               alias + " -file " + self.certs_dir + "/" + cert_file +
               " -keystore " + self.keystore]
            logger.debug("Importing certificate for host {} as alias {}".format(alias.split(".")[0], alias))
            for cmd in cmds:
               re = self.run_as_root(cmd) 

        cmd = ("keytool -noprompt -storepass " +
               self.keystore_pwd + " -list -keystore " +
               self.keystore + " | grep trusted")
        re = self.run_as_root(cmd)
        certs_count = re[0].split("\n") 
        certs_count.pop()
        if len(certs_count) == certs_file_count:
            logger.debug("All certificates have been successfully imported")


    def restart_gateway(self):
      
        logger.debug("Restarting gateway service")
        cmd = ("systemctl restart scaleio-gateway")

        self.run_as_root(cmd)


    def restart_cinder_volume(self):

        ssh_opts = (
        " -o StrictHostKeyChecking=no "
        " -o UserKnownHostsFile=/dev/null "
        " -o KbdInteractiveDevices=no"
        " -o LogLevel=ERROR")

        logger.debug("Restarting cinder-volume service")
        cmd = ("ssh " + ssh_opts + " heat-admin@" +
               self.controller_vip + " sudo pcs resource restart openstack-cinder-volume")
        self.director.run(cmd)

        re = self.director.run(self.source_overcloudrc +
                          "openstack volume service list | grep " +
                          "tripleo_dellemc_powerflex")
        status = re[0].split("\n")
        status.pop()
        status = status[0].split("|")[5]
        if ' up' in status:
            logger.debug("PowerFlex backend is now up and running")
