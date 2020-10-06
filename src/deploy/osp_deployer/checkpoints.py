#!/usr/bin/env python

# Copyright (c) 2015-2020 Dell Inc. or its subsidiaries.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreedgoo to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from auto_common import Ssh
from osp_deployer.settings.config import Settings
from osp_deployer.settings_sanity import DeployerSanity
import json
import time
import logging

logger = logging.getLogger("osp_deployer")


class Checkpoints:
    def __init__(self):
        self.settings = Settings.settings
        self.ping_success = "packets transmitted, 1 received"
        self.director_ip = self.settings.director_node.public_api_ip
        self.director_user = self.settings.director_install_account_user
        self.director_home_dir = "/home/" + self.director_user
        self.source_stackrc = 'source ' + self.director_home_dir + "/stackrc; "
        self.sah_ip = self.settings.sah_node.public_api_ip
        self.verify_rhsm_status = self.settings.verify_rhsm_status
        if self.settings.use_satellite is True:
            self.verify_rhsm_status = False

    @staticmethod
    def verify_deployer_settings():
        logger.info("==== Running environment sanity tests")
        checks = DeployerSanity()
        checks.check_os_volume_size()
        checks.check_network_settings()
        checks.validate_nic_configs()
        checks.check_files()
        checks.check_network_overlaps()
        checks.check_duplicate_ips()
        checks.verify_overcloud_name()
        checks.validate_profile()
        checks.verify_dpdk_dependencies()
        checks.verify_sriov_dependencies()
        checks.verify_hw_offload_dependencies()

    @staticmethod
    def verify_subscription_status(public_api_ip, user, password, retries):
        i = 0

        subscription_status = Ssh.execute_command(
            public_api_ip,
            user,
            password,
            "subscription-manager status")[0]

        while "Current" not in subscription_status and i < retries:
            if "Unknown" in subscription_status:
                return subscription_status
            time.sleep(60)
            subscription_status = \
                Ssh.execute_command(public_api_ip,
                                    user,
                                    password,
                                    "subscription-manager status")[0]
            i += 1
        return subscription_status

    @staticmethod
    def verify_pools_attached(ip_addr, user, password, logfile):
        # check the xxxxx-posts.log for pool id's/repo's related errors.
        log_out = \
            Ssh.execute_command(ip_addr, user, password, "cat " + logfile)[0]
        error1 = 'No subscriptions are available from the pool with'
        error2 = 'Removed temporarly as this error will show when ' \
                 'not pulling from the cdn but internal repos'
        error3 = 'Could not find an OpenStack pool to attach to'
        if error1 in log_out or error2 in log_out or error3 in log_out:
            logger.info("*** post install log ***")
            logger.info(log_out)
            return False
        return True

    def ping_host(self, external_ip, user, passwd, target_host):
        for i in range(1, 30):
            ping_status = Ssh.execute_command(external_ip,
                                              user,
                                              passwd,
                                              "ping " + target_host +
                                              " -c 1 -w 30 ")[0]
            if self.ping_success in ping_status:
                logger.debug(
                    "Ping {} successful on attempt #{}".format(target_host, i))
                break
        # noinspection PyUnboundLocalVariable
        return ping_status

    def sah_health_check(self):

        logger.info("SAH node health check")
        if self.verify_rhsm_status:
            logger.debug("*** Verify the SAH node registered properly ***")
            for _ in range(60):
                subscription_status = self.verify_subscription_status(
                    self.sah_ip,
                    "root",
                    self.settings.sah_node.root_password,
                    self.settings.subscription_check_retries)
                if "Current" in subscription_status:
                    break
                time.sleep(2)
            else:
                raise AssertionError(
                    "SAH did not register properly : " + subscription_status)

        logger.debug("*** Verify the SAH can ping its public gateway")
        gateway = self.settings.public_api_gateway
        test = self.ping_host(self.sah_ip,
                              "root",
                              self.settings.sah_node.root_password,
                              gateway)
        if self.ping_success not in test:
            raise AssertionError(
                "SAH cannot ping its public gateway : " + test)

        logger.debug("*** Verify the SAH can ping the outside world (ip)")
        test = self.ping_host(self.sah_ip,
                              "root",
                              self.settings.sah_node.root_password,
                              "8.8.8.8")
        if self.ping_success not in test:
            raise AssertionError(
                "SAH cannot ping the outside world (ip) : " + test)

        logger.debug("*** Verify the SAH can ping the outside world (dns)")
        test = self.ping_host(self.sah_ip,
                              "root",
                              self.settings.sah_node.root_password,
                              "redhat.com")
        if self.ping_success not in test:
            raise AssertionError(
                "SAH cannot ping the outside world (dns) : " + test)

        logger.debug("*** Verify the SAH can ping the idrac network")
        test = self.ping_host(self.sah_ip,
                              "root",
                              self.settings.sah_node.root_password,
                              self.settings.sah_node.idrac_ip)
        if self.ping_success not in test:
            raise AssertionError(
                "SAH cannot ping idrac networkn (ip) : " + test)

        logger.debug("*** Verify the SAH has KVM enabled *** ")
        cmd = 'ls -al /dev/kvm'
        if "No such file" in \
                Ssh.execute_command(self.sah_ip,
                                    "root",
                                    self.settings.sah_node.root_password,
                                    cmd)[1]:
            raise AssertionError(
                "KVM Not running on the SAH node - make sure "
                "the node has been DTK'ed/Virtualization enabled "
                "in the Bios")

    def director_vm_health_check(self):
        setts = self.settings
        logger.info("Director VM health checks")
        if self.verify_rhsm_status:
            logger.debug("*** Verify the Director VM registered properly ***")
            subscription_status = self.verify_subscription_status(
                self.director_ip,
                "root",
                setts.director_node.root_password,
                setts.subscription_check_retries)
            if "Current" not in subscription_status:
                raise AssertionError(
                    "Director VM did not register properly : " +
                    subscription_status)

        logger.debug(
            "*** Verify all pools registered & repositories subscribed ***")
        if self.verify_pools_attached(self.director_ip,
                                      "root",
                                      setts.director_node.root_password,
                                      "/root/" + setts.director_node.hostname +
                                      "-posts.log") is False:
            raise AssertionError(
                "Director vm did not subscribe/attach "
                "repos properly, see log.")

        logger.debug("*** Verify the Director VM can ping its public gateway")
        test = self.ping_host(self.director_ip,
                              "root",
                              setts.director_node.root_password,
                              setts.public_api_gateway)
        if self.ping_success not in test:
            raise AssertionError(
                "Director VM cannot ping its public gateway : " + test)

        logger.debug(
            "*** Verify the Director VM can ping the outside world (ip)")
        test = self.ping_host(self.director_ip,
                              "root",
                              setts.director_node.root_password,
                              "8.8.8.8")
        if self.ping_success not in test:
            raise AssertionError(
                "Director VM cannot ping the outside world (ip) : " + test)

        logger.debug(
            "*** Verify the Director VM can ping the outside world (dns)")
        test = self.ping_host(self.director_ip,
                              "root",
                              setts.director_node.root_password,
                              "redhat.com")
        if self.ping_success not in test:
            raise AssertionError(
                "Director VM cannot ping the outside world (dns) : " + test)

        logger.debug(
            "*** Verify the Director VM can ping the SAH node "
            "through the provisioning network")
        test = self.ping_host(self.director_ip,
                              "root",
                              setts.director_node.root_password,
                              setts.sah_node.provisioning_ip)
        if self.ping_success not in test:
            raise AssertionError(
                "Director VM cannot ping the SAH node through "
                "the provisioning network : " + test)

        logger.debug(
            "*** Verify the Director VM can ping the SAH node "
            "through the public network")
        test = self.ping_host(self.director_ip,
                              "root",
                              setts.director_node.root_password,
                              self.sah_ip)
        if self.ping_success not in test:
            raise AssertionError(
                "Director VM cannot ping the SAH node through "
                "the provisioning network : " + test)

        logger.debug("*** Verify the Director VM can ping the idrac network")
        test = self.ping_host(self.director_ip,
                              "root",
                              setts.director_node.root_password,
                              self.sah_ip)
        if self.ping_success not in test:
            raise AssertionError(
                "Director VM cannot ping idrac network (ip) : " + test)

    def verify_nodes_registered_in_ironic(self, node_type=None):
        logger.debug("Verify the expected nodes imported in ironic")

        cmd = ("source ~/stackrc; openstack baremetal node list "
               "--long -c UUID -c 'Driver Info' -f json")
        setts = self.settings
        re = Ssh.execute_command_tty(self.director_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        ls_nodes = json.loads(re[0])
        drac_addresses = list(map(lambda _n: _n["Driver Info"]["drac_address"],
                                  ls_nodes))

        missing = list(filter(lambda x: x.idrac_ip not in drac_addresses,
                              setts.all_overcloud_nodes))

        if missing:
            raise AssertionError(
                "The following {:d} overcloud nodes defined in the "
                ".properties were not found in the ironic "
                "database {}".format(len(missing), str(missing)))
        if node_type:
            self.verify_nodes_registered_in_ironic_edge(node_type)

    def verify_nodes_registered_in_ironic_edge(self, node_type):
        expected_node_type_count = len(self.settings.node_types_map[node_type])
        cmd = ("source ~/stackrc;openstack baremetal node list "
               "--fields properties -f json")
        setts = self.settings
        stdout, stderr, exit_status = Ssh.execute_command_tty(
            self.director_ip,
            setts.director_install_account_user,
            setts.director_install_account_pwd,
            cmd)
        nodes = json.loads(stdout)
        registered_node_type_count = 0
        for node in nodes:
            props = node["Properties"]
            if "node_type" in props and props["node_type"] == node_type:
                registered_node_type_count += 1
        if expected_node_type_count != registered_node_type_count:
            raise AssertionError(
                "Expected number of nodes registered in Ironic for node type: "
                "{}, does not match, expected: {}, "
                "imported: {}".format(node_type,
                                      str(expected_node_type_count),
                                      str(registered_node_type_count)))
        logger.info("Validated node type: %s, "
                    "has the correct number of nodes imported "
                    "into Ironic: %s", node_type, registered_node_type_count)

    def verify_introspection_sucessfull(self, node_type=None):
        logger.debug("Verify the introspection did not encounter any errors")
        if node_type:
            self.verify_introspection_sucessfull_edge(node_type)
        else:
            cmd = "source ~/stackrc;openstack baremetal node list | grep None"
            setts = self.settings
            re = Ssh.execute_command_tty(self.director_ip,
                                         setts.director_install_account_user,
                                         setts.director_install_account_pwd,
                                         cmd)
            # TODO :: i fnode failed introspection - set to to PXE - reboot
            ls_nodes = re[0].split("\n")
            ls_nodes.pop()
            for node in ls_nodes:
                state = node.split("|")[5]
                if "available" not in state:
                    raise AssertionError(
                        "Node state not available post bulk introspection"
                        + "\n " + re[0])

    def verify_introspection_sucessfull_edge(self, node_type):
        node_type_count = len(self.settings.node_types_map[node_type])
        cmd = ("source ~/stackrc;openstack baremetal node list "
               "--fields uuid properties provision_state -f json")
        setts = self.settings
        stdout, stderr, exit_status = Ssh.execute_command_tty(
            self.director_ip,
            setts.director_install_account_user,
            setts.director_install_account_pwd,
            cmd)
        nodes = json.loads(stdout)
        introspected_node_type_count = 0
        for node in nodes:
            props = node["Properties"]
            uuid = node["UUID"]
            state = node["Provisioning State"]
            if ("node_type" in props and props["node_type"] == node_type
                    and state == "available"):
                introspected_node_type_count += 1
        if node_type_count != introspected_node_type_count:
            raise AssertionError(
                "Expected number of nodes introspected for node type: "
                "{}, does not match, expected: {}, "
                "introspected: {}".format(node_type,
                                          str(node_type_count),
                                          str(introspected_node_type_count)))
        logger.info("Validated node type: %s, "
                    "has the correct number of nodes introspected: %s",
                    node_type, introspected_node_type_count)

    def verify_undercloud_installed(self):
        logger.debug("Verify the undercloud installed properly")
        setts = self.settings
        cmd = "stat ~/stackrc"
        re = Ssh.execute_command_tty(self.director_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        if "No such file or directory" in re[0]:
            _error = AssertionError("Director & Undercloud did not install "
                                    "properly, no ~/stackrc found, check "
                                    "/pilot/install-director.log "
                                    "for details")

            return True, _error

        cmd = ("grep \"The Undercloud has been successfully installed\" "
               + "~/pilot/install-director.log")

        re = Ssh.execute_command_tty(self.director_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        if "The Undercloud has been successfully installed" not in re[0]:
            _error = AssertionError("Director & Undercloud did not install "
                                    "properly, log does not indicate a "
                                    "successful director installation, check "
                                    "/pilot/install-director.log for details")
            return True, _error

        cmd = "cat "\
              "~/pilot/install-director.log"
        re = Ssh.execute_command_tty(self.director_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        if "There are no enabled repos" in re[0]:
            _error = AssertionError("Unable to attach to pool ID while "
                                    "updating the overcloud image")
            return True, _error

        cmd = "source ~/stackrc;glance image-list"
        re = Ssh.execute_command_tty(self.director_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        if "overcloud-full" not in re[0]:
            _error = AssertionError("Unable to find the overcloud image "
                                    "in glance - check the "
                                    "install-director.log for possible "
                                    "package download errors")
            return True, _error

        logger.info("Undercloud installed Successfully!")

        return False, None

    def provisioning_subnet_exists(self, subnet):
        logger.debug("Check if edge subnet {} already "
                     "exists or not".format(subnet))
        setts = self.settings
        user = setts.director_install_account_user
        ip = setts.director_node.public_api_ip
        pwd = setts.director_install_account_pwd
        is_subnet = False
        subnet_cmd = ("{} openstack subnet "
                      "show {} -c name "
                      "-f value".format(self.source_stackrc, subnet))
        sn_out = Ssh.execute_command(ip, user, pwd, subnet_cmd)[0]
        if sn_out.strip() == subnet:
            is_subnet = True
            logger.info("Subnet {} already exists".format(subnet))
        return is_subnet

    def verify_provisioning_subnets_created(self, subnets):
        for subnet in subnets:
            _is_subnet = self.provisioning_subnet_exists(subnet)
            if not _is_subnet:
                raise AssertionError(
                    "Provisioning subnet {} not found in "
                    "undercloud".format(subnet))

    def verify_overcloud_deployed(self):
        logger.debug("Verify the overcloud installed properly")
        setts = self.settings
        overcloud_name = setts.overcloud_name

        # Verify the overcloud RC file was created
        cmd = "test -f ~/" + overcloud_name + "rc; echo $?;"
        re = Ssh.execute_command_tty(self.director_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        # Have to strip non-printing chars as re[0] contains newline '\n'
        _resp = re[0].strip()
        # If director is turned off or not deployed
        # re[0] == "host not up", handle this case by checking len(re[0])
        is_conf = not bool(int(_resp)) if len(_resp) == 1 else False
        if is_conf is False:
            msg = ("Overcloud RC file missing, either the overcloud has not "
                   "been deployed yet or there was an issue during "
                   "the deployment, such as Director VM being down or a heat "
                   "stack deployment failure")
            logger.warning(msg)
            return True, AssertionError(msg)

        # Check log for successful deployment
        success = "Overcloud Deployed"
        cmd = "grep \"" + success + "\" " + "~/pilot/overcloud_deploy_out.log"
        re = Ssh.execute_command_tty(self.director_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        if success not in re[0]:
            msg = ("Overcloud did not install successfully, "
                   "check ~/pilot/overcloud_deploy_out.log")
            logger.warning(msg)
            return True, AssertionError(msg)

        else:
            logger.info("Overcloud install successful")
            return False, None

    def verify_computes_virtualization_enabled(self):
        logger.debug("*** Verify the Compute nodes have KVM enabled *** ")
        cmd = "source ~/stackrc;nova list | grep compute"
        ssh_opts = (
            "-o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=/dev/null "
            "-o KbdInteractiveDevices=no")
        setts = self.settings
        re = Ssh.execute_command_tty(self.director_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        computes = re[0].split("\n")
        computes.pop()
        for each in computes:
            provisioning_ip = each.split("|")[6].split("=")[1]
            cmd = "ssh %s heat-admin@%s 'ls -al /dev/kvm'" % (
                ssh_opts, provisioning_ip)
            re = Ssh.execute_command_tty(
                self.director_ip,
                self.settings.director_install_account_user,
                self.settings.director_install_account_pwd, cmd)
            if "No such file" in re[0]:
                raise AssertionError(
                    "KVM Not running on Compute node '{}' -"
                    " make sure the node has been DTK'ed/Virtualization "
                    "enabled in the Bios".format(
                        provisioning_ip))

    def retreive_switches_config(self):
        if self.settings.switches == 0:
            return
        logger.info("Retrieving switch(es) configuration")
        for each in self.settings.switches:
            logger.info(
                "Retrieving configuration for switch " + each.switch_name)
            logger.debug(
                self.execute_as_shell(each.ip, each.user, each.password,
                                      'show version'))
            logger.debug(
                self.execute_as_shell(each.ip,
                                      each.user,
                                      each.password,
                                      'copy running-config scp://' +
                                      "root" + ':' +
                                      self.settings.sah_node.root_password +
                                      '@' + self.settings.sah_node.public_api_ip +
                                      '//auto_results/switch-config-' +
                                      each.switch_name))

    @staticmethod
    def execute_as_shell(address, usr, pwd, command):
        import paramiko

        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(address, username=usr, password=pwd)
        channel = conn.invoke_shell(term='vt100', width=800, height=1000,
                                    width_pixels=0,
                                    height_pixels=0)
        time.sleep(1)
        channel.recv(9999)
        channel.send(command + "\n")
        buff = ''
        while not buff.endswith('#'):
            resp = channel.recv(9999)
            buff += resp

    def verify_backends_connectivity(self):
        dellsc_be = self.settings.enable_dellsc_backend
        if dellsc_be:
            setts = self.settings
            cmd = "source ~/stackrc;nova list | grep compute"
            re = Ssh.execute_command_tty(self.director_ip,
                                         setts.director_install_account_user,
                                         setts.director_install_account_pwd,
                                         cmd)
            ls = re[0].split("\n")
            ls.pop()
            compute_node_ip = ls[0].split("|")[6].split("=")[1]

            cmd = "source ~/stackrc;nova list | grep controller"
            re = Ssh.execute_command_tty(self.director_ip,
                                         setts.director_install_account_user,
                                         setts.director_install_account_pwd,
                                         cmd)
            ls = re[0].split("\n")
            ls.pop()
            controller_node_ip = ls[0].split("|")[6].split("=")[1]

        if self.settings.enable_dellsc_backend:
            logger.debug("Verifying dellsc backend connectivity")

            logger.debug("Verify Controller nodes can ping the san ip")
            cmd = "ssh heat-admin@" + controller_node_ip +\
                  " sudo ping " + self.settings.dellsc_san_ip +\
                  " -c 1 -w 30 "
            re = Ssh.execute_command_tty(self.director_ip,
                                         setts.director_install_account_user,
                                         setts.director_install_account_pwd,
                                         cmd)
            if self.ping_success not in re[0]:
                raise AssertionError(controller_node_ip +
                                     " cannot ping the dellsc san ip " +
                                     self.settings.dellsc_san_ip)

            logger.debug("Verify Make sure ISCSI access work from Compute \
                         & Controller nodes")
            for each in compute_node_ip, controller_node_ip:
                cmd = "ssh heat-admin@" + each +\
                      " sudo iscsiadm -m discovery -t sendtargets -p " +\
                      self.settings.dellsc_iscsi_ip_address +\
                      ":" + self.settings.dellsc_iscsi_port
                re = Ssh.execute_command_tty(
                                   self.director_ip,
                                   setts.director_install_account_user,
                                   setts.director_install_account_pwd,
                                   cmd)
                if "com.compellent" not in re[0]:
                    raise AssertionError(
                                   each +
                                   " not able to validate ISCSI access to " +
                                   self.settings.dellsc_iscsi_ip_address +
                                   ":" + self.settings.dellsc_iscsi_port)
