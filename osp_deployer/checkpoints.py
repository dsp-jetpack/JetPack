# (c) 2015-2016 Dell
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
from osp_deployer import Settings, DeployerSanity
import time
import logging
logger = logging.getLogger("osp_deployer")


class Checkpoints():
    def __init__(self):
        self.settings = Settings.settings
        self.ping_success = "packets transmitted, 1 received"

    @staticmethod
    def verify_deployer_settings():
        logger.info("==== Running environment sanity tests")
        checks = DeployerSanity()
        checks.check_network_settings()
        checks.check_files()
        checks.check_ipmi_to_nodes()
        checks.check_network_overlaps()
        checks.check_duplicate_ips()

    @staticmethod
    def verify_subscription_status(external_ip, user, password, retries):
        i = 0
        subscription_status = Ssh.execute_command(
            external_ip,
            user,
            password,
            "subscription-manager status")[0]

        while "Current" not in subscription_status and i < retries:
            if "Unknown" in subscription_status:
                return subscription_status
            time.sleep(60)
            subscription_status = \
                Ssh.execute_command(external_ip,
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
        logger.debug("*** Verify the SAH node registered properly ***")
        subscription_status = self.verify_subscription_status(
            self.settings.sah_node.external_ip,
            "root",
            self.settings.sah_node.root_password,
            self.settings.subscription_check_retries)
        if "Current" not in subscription_status:
            raise AssertionError(
                "SAH did not register properly : " + subscription_status)

        logger.debug("*** Verify the SAH can ping its public gateway")
        test = self.ping_host(self.settings.sah_node.external_ip,
                              "root",
                              self.settings.sah_node.root_password,
                              self.settings.external_gateway)
        if self.ping_success not in test:
            raise AssertionError(
                "SAH cannot ping its public gateway : " + test)

        logger.debug("*** Verify the SAH can ping the outside world (ip)")
        test = self.ping_host(self.settings.sah_node.external_ip,
                              "root",
                              self.settings.sah_node.root_password,
                              "8.8.8.8")
        if self.ping_success not in test:
            raise AssertionError(
                "SAH cannot ping the outside world (ip) : " + test)

        logger.debug("*** Verify the SAH can ping the outside world (dns)")
        test = self.ping_host(self.settings.sah_node.external_ip,
                              "root",
                              self.settings.sah_node.root_password,
                              "google.com")
        if self.ping_success not in test:
            raise AssertionError(
                "SAH cannot ping the outside world (dns) : " + test)

        logger.debug("*** Verify the SAH can ping the idrac network")
        test = self.ping_host(self.settings.sah_node.external_ip,
                              "root",
                              self.settings.sah_node.root_password,
                              self.settings.controller_nodes[0].idrac_ip)
        if self.ping_success not in test:
            raise AssertionError(
                "SAH cannot ping idrac networkn (ip) : " + test)

        logger.debug("*** Verify the SAH has KVM enabled *** ")
        cmd = 'ls -al /dev/kvm'
        if "No such file" in \
                Ssh.execute_command(self.settings.sah_node.external_ip,
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
        logger.debug("*** Verify the Director VM registered properly ***")
        subscription_status = self.verify_subscription_status(
            setts.director_node.external_ip,
            "root",
            setts.director_node.root_password,
            setts.subscription_check_retries)
        if "Current" not in subscription_status:
            raise AssertionError(
                "Director VM did not register properly : " +
                subscription_status)

        logger.debug(
            "*** Verify all pools registered & repositories subscribed ***")
        if self.verify_pools_attached(setts.director_node.external_ip,
                                      "root",
                                      setts.director_node.root_password,
                                      "/root/" + setts.director_node.hostname +
                                      "-posts.log") is False:
            raise AssertionError(
                "Director vm did not subscribe/attach "
                "repos properly, see log.")

        logger.debug("*** Verify the Director VM can ping its public gateway")
        test = self.ping_host(setts.director_node.external_ip,
                              "root",
                              setts.director_node.root_password,
                              setts.public_api_gateway)
        if self.ping_success not in test:
            raise AssertionError(
                "Director VM cannot ping its public gateway : " + test)

        logger.debug(
            "*** Verify the Director VM can ping the outside world (ip)")
        test = self.ping_host(setts.director_node.external_ip,
                              "root",
                              setts.director_node.root_password,
                              "8.8.8.8")
        if self.ping_success not in test:
            raise AssertionError(
                "Director VM cannot ping the outside world (ip) : " + test)

        logger.debug(
            "*** Verify the Director VM can ping the outside world (dns)")
        test = self.ping_host(setts.director_node.external_ip,
                              "root",
                              setts.director_node.root_password,
                              "google.com")
        if self.ping_success not in test:
            raise AssertionError(
                "Director VM cannot ping the outside world (dns) : " + test)

        logger.debug(
            "*** Verify the Director VM can ping the SAH node "
            "through the provisioning network")
        test = self.ping_host(setts.director_node.external_ip,
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
        test = self.ping_host(setts.director_node.external_ip,
                              "root",
                              setts.director_node.root_password,
                              setts.sah_node.external_ip)
        if self.ping_success not in test:
            raise AssertionError(
                "Director VM cannot ping the SAH node through "
                "the provisioning network : " + test)

        logger.debug("*** Verify the Director VM can ping the idrac network")
        test = self.ping_host(setts.director_node.external_ip,
                              "root",
                              setts.director_node.root_password,
                              setts.controller_nodes[0].idrac_ip)
        if self.ping_success not in test:
            raise AssertionError(
                "Director VM cannot ping idrac network (ip) : " + test)

    def ceph_vm_health_check(self):
        logger.info("Ceph VM health checks")
        logger.debug("*** Verify the Ceph VM registered properly ***")
        subscription_status = self.verify_subscription_status(
            self.settings.ceph_node.external_ip,
            "root",
            self.settings.ceph_node.root_password,
            self.settings.subscription_check_retries)
        if "Current" not in subscription_status:
            raise AssertionError(
                "Ceph VM did not register properly : " + subscription_status)

        logger.debug("*** Verify the Ceph VM can ping its public gateway")
        test = self.ping_host(self.settings.ceph_node.external_ip,
                              "root",
                              self.settings.ceph_node.root_password,
                              self.settings.external_gateway)
        if self.ping_success not in test:
            raise AssertionError(
                "Ceph VM cannot ping its public gateway : " + test)

        logger.debug("*** Verify the Ceph VM can ping the outside world (ip)")
        test = self.ping_host(self.settings.ceph_node.external_ip,
                              "root",
                              self.settings.ceph_node.root_password,
                              "8.8.8.8")
        if self.ping_success not in test:
            raise AssertionError(
                "Ceph VM cannot ping the outside world (ip) : " + test)

        logger.debug("*** Verify the Ceph VM can ping the outside world (dns)")
        test = self.ping_host(self.settings.ceph_node.external_ip,
                              "root",
                              self.settings.ceph_node.root_password,
                              "google.com")
        if self.ping_success not in test:
            raise AssertionError(
                "Ceph VM cannot ping the outside world (dns) : " + test)

        logger.debug(
            "*** Verify the Ceph VM can ping the SAH node "
            "through the storage network")
        test = self.ping_host(self.settings.ceph_node.external_ip,
                              "root",
                              self.settings.ceph_node.root_password,
                              self.settings.sah_node.storage_ip)
        if self.ping_success not in test:
            raise AssertionError(
                "Ceph VM cannot ping the SAH node "
                "through the storage network : " + test)

        logger.debug(
            "*** Verify the Ceph VM can ping the SAH "
            "node through the public network")
        test = self.ping_host(self.settings.ceph_node.external_ip,
                              "root",
                              self.settings.ceph_node.root_password,
                              self.settings.sah_node.external_ip)
        if self.ping_success not in test:
            raise AssertionError(
                "Ceph VM cannot ping the SAH node through "
                "the public network : " + test)

        logger.debug(
            "*** Verify the Ceph VM can ping the Director VM "
            "through the public network")
        test = self.ping_host(self.settings.ceph_node.external_ip,
                              "root",
                              self.settings.ceph_node.root_password,
                              self.settings.director_node.external_ip)
        if self.ping_success not in test:
            raise AssertionError(
                "Ceph VM cannot ping the Director VM through "
                "the provisioning network : " + test)

    def verify_nodes_registered_in_ironic(self):
        logger.debug("Verify the expected amount of nodes imported in ironic")
        cmd = "source ~/stackrc;ironic node-list | grep None"
        setts = self.settings
        re = Ssh.execute_command_tty(setts.director_node.external_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        ls_nodes = re[0].split("\n")
        ls_nodes.pop()
        expected_nodes = len(self.settings.controller_nodes) + len(
            self.settings.compute_nodes) + len(
            self.settings.ceph_nodes)
        if len(ls_nodes) != expected_nodes:
            raise AssertionError(
                "Expected amount of nodes registered in Ironic "
                "does not add up " +
                str(len(list)) + "/" + str(expected_nodes))

    def verify_introspection_sucessfull(self):
        logger.debug("Verify the introspection did not encounter any errors")
        cmd = "source ~/stackrc;ironic node-list | grep None"
        setts = self.settings
        re = Ssh.execute_command_tty(setts.director_node.external_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        #TODO :: i fnode failed introspection - set to to PXE - reboot
        ls_nodes = re[0].split("\n")
        ls_nodes.pop()
        for node in ls_nodes:
            state = node.split("|")[5]
            if "available" not in state:
                raise AssertionError(
                    "Node state not available post bulk introspection" +
                    "\n " + re[0])

    def verify_undercloud_installed(self):
        logger.debug("Verify the undercloud installed properly")
        cmd = "stat ~/stackrc"
        setts = self.settings
        re = Ssh.execute_command_tty(setts.director_node.external_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        if "No such file or directory" in re[0]:
            raise AssertionError(
                "Director & Undercloud did not install properly, "
                "check /pilot/install-director.log for details")
        cmd = " grep \"Undercloud install complete\" " \
              "~/pilot/install-director.log"
        setts = self.settings
        re = Ssh.execute_command_tty(setts.director_node.external_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        if "Undercloud install complete." not in re[0]:
            raise AssertionError(
                "Director & Undercloud did not install properly,"
                " check /pilot/install-director.log for details")

        cmd = "cat "\
              "~/pilot/install-director.log"
        re = Ssh.execute_command_tty(setts.director_node.external_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        if "There are no enabled repos" in re[0]:
            raise AssertionError(
                "Unable to attach to pool ID while updating the overcloud image")

    def verify_computes_virtualization_enabled(self):
        logger.debug("*** Verify the Compute nodes have KVM enabled *** ")
        cmd = "source ~/stackrc;nova list | grep compute"
        setts = self.settings
        re = Ssh.execute_command_tty(setts.director_node.external_ip,
                                     setts.director_install_account_user,
                                     setts.director_install_account_pwd,
                                     cmd)
        computes = re[0].split("\n")
        computes.pop()
        for each in computes:
            provisioning_ip = each.split("|")[6].split("=")[1]
            cmd = "ssh heat-admin@" + provisioning_ip + " \"ls -al /dev/kvm\""
            re = Ssh.execute_command_tty(
                self.settings.director_node.external_ip,
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
        logger.info("Retreiving switch(es) configuration")
        for each in self.settings.switches:
            logger.info(
                "Retreiving configuration for switch " + each.switch_name)
            logger.info(
                self.execute_as_shell(each.ip, each.user, each.password,
                                      'show version'))
            logger.info(
                self.execute_as_shell(each.ip,
                                      each.user,
                                      each.password,
                                      'copy running-config scp://' +
                                      self.settings.bastion_host_user + ':' +
                                      self.settings.bastion_host_password +
                                      '@' + self.settings.bastion_host_ip +
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
        if self.settings.enable_dellsc_backend or self.settings.enable_eqlx_backend:
            setts = self.settings
            cmd = "source ~/stackrc;nova list | grep compute"
            re = Ssh.execute_command_tty(setts.director_node.external_ip,
                                         setts.director_install_account_user,
                                         setts.director_install_account_pwd,
                                         cmd)
            ls =  re[0].split("\n")
            ls.pop()
            compute_node_ip = ls[0].split("|")[6].split("=")[1]

            cmd = "source ~/stackrc;nova list | grep controller"
            re = Ssh.execute_command_tty(setts.director_node.external_ip,
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
                  " ping " + self.settings.dellsc_san_ip  +\
                  " -c 1 -w 30 "
            re = Ssh.execute_command_tty(setts.director_node.external_ip,
                                        setts.director_install_account_user,
                                         setts.director_install_account_pwd,
                                         cmd)
            if self.ping_success not in re[0]:
                raise AssertionError(controller_node_ip +
                                     " cannot ping the dellsc san ip " +
                                     self.settings.dellsc_san_ip)

            logger.debug("Verify Make sure ISCSI access work from Compute & Controller nodes")
            for each in compute_node_ip, controller_node_ip :
                cmd = "ssh heat-admin@" + each +\
                      " sudo iscsiadm -m discovery -t sendtargets -p " +\
                      self.settings.dellsc_iscsi_ip_address +\
                      ":" + self.settings.dellsc_iscsi_port
                re = Ssh.execute_command_tty(setts.director_node.external_ip,
                                        setts.director_install_account_user,
                                         setts.director_install_account_pwd,
                                         cmd)
                if "com.compellent" not in re[0]:
                   raise AssertionError(each +
                                        " not able to validate ISCSI access to " +
                                        self.settings.dellsc_iscsi_ip_address +
                                        ":" + self.settings.dellsc_iscsi_port)

        if self.settings.enable_eqlx_backend:
            logger.debug("Verifying eql backend connectivity")

            logger.debug("Verify ssh access to the san ip from Compute & Controller nodes")

            for each in compute_node_ip, controller_node_ip :
                cmd = "ssh heat-admin@" + each +\
                      " sshpass -p " + self.settings.eqlx_san_password +\
                      " ssh -o StrictHostKeyChecking=no " + self.settings.eqlx_san_login + "@" +\
                      self.settings.eqlx_san_ip + " 'uname -a'"
                re = Ssh.execute_command_tty(setts.director_node.external_ip,
                                            setts.director_install_account_user,
                                             setts.director_install_account_pwd,
                                             cmd)
                if "NetBSD" not in re[0]:
                    raise AssertionError(each +
                                         " not able to ssh to EQL san ip " +
                                         self.settings.eqlx_san_ip)
