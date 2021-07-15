#!/usr/bin/env python3

# Copyright (c) 2015-2021 Dell Inc. or its subsidiaries.
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


from auto_common import Ssh
import yaml
from ipmi import Ipmi 
import logging, sys, os 
import dracclient
from discover_nodes.dracclient.client import DRACClient
import subprocess, time
import requests, json, argparse
from ocp_deployer.settings.ocp_config import OCP_Settings
from ocp_deployer.csah import CSah
logger = logging.getLogger("ocp_deployer")

def setup_logging():
    import logging.config
    path = '/auto_results'
    if not os.path.exists(path):
        os.makedirs(path)
    logging.config.fileConfig('logging_ocp.conf')

def load_settings():
    parser = argparse.ArgumentParser(
        description='JetPack 16.x deployer')
    parser.add_argument('-s', '--settings',
                        help='ini settings file, e.g settings/acme.ini',
                        required=True)
    args, unknown = parser.parse_known_args()
    if len(unknown) > 0:
        parser.print_help()
        msg = "Invalid argument(s) :"
        for each in unknown:
            msg += " " + each + ";"
        raise AssertionError(msg)

    logger.info("Loading settings file: " + args.settings)
    settings = OCP_Settings(args.settings)
    return settings, args


def set_node_to_pxe(idrac_ip, idrac_user, idrac_password):
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1' % idrac_ip
    payload = {"Boot":{"BootSourceOverrideTarget":"Pxe"}}
    headers = {'content-type': 'application/json'}

    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_user, idrac_password))
    data = response.json()
    statusCode = response.status_code
    if statusCode == 200:
        logger.info("Node set to Pxe on next boot")
    else:
        logger.info("\n- Failed to set node to Pxe boot, errror code is %s" % statusCode)
        detail_message=str(response.__dict__)
        logger.info(detail_message)

def get_settings():
    parser = argparse.ArgumentParser(
        description='JetPack 16.x deployer')
    parser.add_argument('-s', '--settings',
                        help='ini settings file, e.g settings/acme.ini',
                        required=True)
    args, unknown = parser.parse_known_args()
    if len(unknown) > 0:
        parser.print_help()
        msg = "Invalid argument(s) :"
        for each in unknown:
            msg += " " + each + ";"
        raise AssertionError(msg)

    logger.info("Loading settings file: " + args.settings)
    settings = OCP_Settings(args.settings)
    return settings, args        


def deploy():
    logger.debug("=================================")
    logger.info("=== Starting up ...")
    logger.debug("=================================")

    settings, args = get_settings()

    settings = load_settings()

    csah = CSah()
    # CSah healthChecks

    # Add step : [root@csah-pri ~]# nmcli connection modify bridge-br0 ipv4.dns <IP address> & resolv.conf
    csah.cleanup_sah()
    csah.delete_bootstrap_vm()

    csah.generate_inventory_file()

    csah.discover_nodes()
    csah.configure_idracs()
    csah.power_off_cluster_nodes()

    csah.run_playbooks()
    csah.create_bootstrap_vm()
    csah.wait_for_bootstrap_ready()

    csah.pxe_boot_controllers()    
    csah.wait_for_controllers_ready()

    csah.complete_bootstrap_process()
    csah.pxe_boot_computes()
    csah.wait_for_operators_ready()
    csah.complete_cluster_setup()

    csah.delete_bootstrap_vm()

    csah.configure_ntp()
    csah.wait_for_operators_ready()


    logger.info("- Done")
    # .. /openshift-install --dir=openshift wait-for install-complete

    # oc get nodes .. all in



def main():
    setup_logging()
    deploy()
        

if __name__ == "__main__":
    main()




