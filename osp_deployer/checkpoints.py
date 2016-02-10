import sys, getopt, time, subprocess, paramiko,logging, traceback, os.path, urllib2, shutil, socket
from osp_deployer.ceph import Ceph
from auto_common import Ipmi, Ssh, FileHelper, Scp, UI_Manager
from osp_deployer import Settings
from osp_deployer import Settings, Deployer_sanity
logger = logging.getLogger("osp_deployer")



class Checkpoints():
    '''
    '''


    def __init__(self):
        self.settings = Settings.settings
        self.ping_success = "packets transmitted, 3 received"

    def verify_deployer_settings(self):
        logger.info("==== Running environment sanity tests")
        checks = Deployer_sanity()
        checks.check_network_settings()
        checks.check_files()
        checks.check_ipmi_to_nodes()

    def verify_subscription_status(self, external_ip, user, password, retries):
        i = 0
        subscriptionStatus = Ssh.execute_command(external_ip, user, password, "subscription-manager status")[0]
        while("Current" not in subscriptionStatus and i < retries):
            if "Unknown" in subscriptionStatus:
                return subscriptionStatus
            logger.debug("...")
            time.sleep(60)
            subscriptionStatus = Ssh.execute_command(external_ip, user, password, "subscription-manager status")[0]
            i += 1;
        return subscriptionStatus


    def ping_host(self, external_ip, user, passwd, targetHost):
        subscriptionStatus = Ssh.execute_command(external_ip, user, passwd, "ping " + targetHost + " -c 3 -w 30 ")[0]
        return subscriptionStatus

    def sah_health_check(self):
        settings = Settings.settings
        logger.info("SAH node health check")
        logger.debug("*** Verify the SAH node registered properly ***")
        subscriptionStatus = self.verify_subscription_status(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, self.settings.subscription_check_retries)
        if "Current" not in subscriptionStatus:
            raise AssertionError("SAH did not register properly : " + subscriptionStatus)

        logger.debug("*** Verify the SAH can ping its public gateway")
        test = self.ping_host(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, self.settings.external_gateway)
        if self.ping_success not in test:
            raise AssertionError("SAH cannot ping its public gateway : " + test)

        logger.debug("*** Verify the SAH can ping the outside world (ip)")
        test = self.ping_host(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "8.8.8.8")
        if self.ping_success not in test:
            raise AssertionError("SAH cannot ping the outside world (ip) : " + test)

        logger.debug("*** Verify the SAH can ping the outside world (dns)")
        test = self.ping_host(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, "google.com")
        if self.ping_success not in test:
            raise AssertionError("SAH cannot ping the outside world (dns) : " + test)

        logger.debug("*** Verify the SAH can ping the idrac network")
        test = self.ping_host(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, self.settings.controller_nodes[0].idrac_ip)
        if self.ping_success not in test:
            raise AssertionError("SAH cannot ping idrac networkn (ip) : " + test)

        logger.debug("*** Verify the SAH has KVM enabled *** ")
        cmd = 'ls -al /dev/kvm'
        if "No such file" in Ssh.execute_command(self.settings.sah_node.external_ip, "root", self.settings.sah_node.root_password, cmd)[1]:
            raise AssertionError("KVM Not running on the SAH node - make sure the node has been DTK'ed/Virtualization enabled in the Bios")

    def director_vm_health_check(self):
        logger.info("Director VM health checks")
        logger.debug("*** Verify the Director VM registered properly ***")
        subscriptionStatus = self.verify_subscription_status(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password, self.settings.subscription_check_retries)
        if "Current" not in subscriptionStatus:
            raise AssertionError("Director VM did not register properly : " + subscriptionStatus)

        logger.debug("*** Verify the Director VM can ping its public gateway")
        test = self.ping_host(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password, self.settings.external_gateway)
        if self.ping_success not in test:
            raise AssertionError("Director VM cannot ping its public gateway : " + test)

        logger.debug("*** Verify the Director VM can ping the outside world (ip)")
        test = self.ping_host(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password, "8.8.8.8")
        if self.ping_success not in test:
            raise AssertionError("Director VM cannot ping the outside world (ip) : " + test)

        logger.debug("*** Verify the Director VM can ping the outside world (dns)")
        test = self.ping_host(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password, "google.com")
        if self.ping_success not in test:
            raise AssertionError("Director VM cannot ping the outside world (dns) : " + test)

        logger.debug("*** Verify the Director VM can ping the SAH node through the provisioning network")
        test = self.ping_host(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password, self.settings.sah_node.provisioning_ip)
        if self.ping_success not in test:
            raise AssertionError("Director VM cannot ping the SAH node through the provisioning network : " + test)

        logger.debug("*** Verify the Director VM can ping the SAH node through the public network")
        test = self.ping_host(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password, self.settings.sah_node.external_ip)
        if self.ping_success not in test:
            raise AssertionError("Director VM cannot ping the SAH node through the provisioning network : " + test)

        logger.debug("*** Verify the Director VM can ping the idrac network")
        test = self.ping_host(self.settings.director_node.external_ip, "root", self.settings.director_node.root_password, self.settings.controller_nodes[0].idrac_ip)
        if self.ping_success not in test:
            raise AssertionError("Director VM cannot ping idrac network (ip) : " + test)

    def ceph_vm_health_check(self):
        logger.info("Ceph VM health checks")
        logger.debug("*** Verify the Ceph VM registered properly ***")
        subscriptionStatus = self.verify_subscription_status(self.settings.ceph_node.external_ip, "root", self.settings.ceph_node.root_password, self.settings.subscription_check_retries)
        if "Current" not in subscriptionStatus:
            raise AssertionError("Ceph VM did not register properly : " + subscriptionStatus)

        logger.debug("*** Verify the Ceph VM can ping its public gateway")
        test = self.ping_host(self.settings.ceph_node.external_ip, "root", self.settings.ceph_node.root_password, self.settings.public_gateway)
        if self.ping_success not in test:
            raise AssertionError("Ceph VM cannot ping its public gateway : " + test)

        logger.debug("*** Verify the Ceph VM can ping the outside world (ip)")
        test = self.ping_host(self.settings.ceph_node.external_ip, "root", self.settings.ceph_node.root_password, "8.8.8.8")
        if self.ping_success not in test:
            raise AssertionError("Ceph VM cannot ping the outside world (ip) : " + test)

        logger.debug("*** Verify the Ceph VM can ping the outside world (dns)")
        test = self.ping_host(self.settings.ceph_node.external_ip, "root", self.settings.ceph_node.root_password, "google.com")
        if self.ping_success not in test:
            raise AssertionError("Ceph VM cannot ping the outside world (dns) : " + test)

        logger.debug("*** Verify the Ceph VM can ping the SAH node through the storage network")
        test = self.ping_host(self.settings.ceph_node.external_ip, "root", self.settings.ceph_node.root_password, self.settings.sah_node.storage_ip)
        if self.ping_success not in test:
            raise AssertionError("Ceph VM cannot ping the SAH node through the storage network : " + test)

        logger.debug("*** Verify the Ceph VM can ping the SAH node through the public network")
        test = self.ping_host(self.settings.ceph_node.external_ip, "root", self.settings.ceph_node.root_password, self.settings.sah_node.external_ip)
        if self.ping_success not in test:
            raise AssertionError("Ceph VM cannot ping the SAH node through the public network : " + test)

        logger.debug("*** Verify the Ceph VM can ping the Director VM through the public network")
        test = self.ping_host(self.settings.ceph_node.external_ip, "root", self.settings.ceph_node.root_password, self.settings.director_node.external_ip)
        if self.ping_success not in test:
            raise AssertionError("Ceph VM cannot ping the Director VM through the provisioning network : " + test)

    def verify_nodes_registered_in_ironic(self):
        logger.debug("Verify the expected amount of nodes imported in ironic")
        cmd = "source ~/stackrc;ironic node-list | grep None"
        re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
        list = re[0].split("\n")
        list.pop()
        expected_nodes = len(self.settings.controller_nodes) + len(self.settings.compute_nodes) + len(self.settings.ceph_nodes)
        if len(list) != expected_nodes:
            raise AssertionError("Expected amount of nodes registered in Ironic does not add up " + str(len(list)) + "/" + str(expected_nodes))

    def verify_introspection_sucessfull(self):
        logger.debug("Verify the introspection did not encounter any errors")
        cmd = "source ~/stackrc;ironic node-list | grep None"
        re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
        list = re[0].split("\n")
        list.pop()
        for node in list:
            state = node.split("|")[5]
            if "available" not in state:
                raise AssertionError("Node state not available post bulk introspection" + "\n " +re[0])

    def verify_undercloud_installed(self):
        logger.debug("Verify the undercloud installed properly")
        cmd = "stat ~/stackrc"
        re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
        if "No such file or directory" in re[0]:
            raise AssertionError("Director & Undercloud did not install properly, check /pilot/install-director.log for details")
        cmd = " grep \"Undercloud install complete\" ~/pilot/install-director.log"
        re = Ssh.execute_command_tty(self.settings.director_node.external_ip, self.settings.director_install_account_user, self.settings.director_install_account_pwd,cmd)
        if not "Undercloud install complete." in re[0]:
            raise AssertionError("Director & Undercloud did not install properly, check /pilot/install-director.log for details")


