import unittest, random
from osp_deployer import *
import sys, getopt, logging
from auto_common import Ssh
logger = logging.getLogger(__name__)

# TODO add logger
# TODO  Pass in settings as argument

class TestVersionLock(unittest.TestCase):
    '''
    Verify the VersionLock list is as expected on the stamp nodes : foreman vm, ceph vm, controller, compute & ceph nodes
    '''

    settings = ''
    version_lock_list_cmd = 'yum versionlock list'
    rpm_list_cmd = 'rpm -qa'

    def setUp(self):
        pass

    def compare_lists(self, remote_locks, expected):

        expressions = [
            "Loaded plugins:",
            "versionlock list done",
            'locks on'
        ]
        for ex in expressions:
            for item in remote_locks:
                if ex in item:
                    remote_locks.remove(item)
            for item in expected:
                if ex in item:
                    expected.remove(item)

        for item in remote_locks:
            if item == '\n':
                remote_locks.remove(item)
        for item in expected:
            if item == '\n':
                expected.remove(item)

        a =  list(set(remote_locks).difference(set(expected)))
        b =  list(set(expected).difference(set(remote_locks)))



        logger.info( "diff a " + str(a))
        logger.info( "diff b " + str(b))

        assert len(a) == 0
        assert len(b) == 0

    def test_foreman_node_lock_list(self):
        remoteLocks =  Ssh.execute_command_readlines(TestVersionLock.settings.foreman_node.public_ip, "root", TestVersionLock.settings.foreman_node.root_password,TestVersionLock.version_lock_list_cmd )[0]
        localLocks = TestVersionLock.settings.lock_files_dir + '\\foreman_vm.vlock'
        with open(localLocks, 'rU') as f:
            expected = f.readlines()

        logger.info( "Verifying foreman Node")

        self.compare_lists(remoteLocks, expected)

        pass

    def test_ceph_node_lock_list(self):
        remoteLocks =  Ssh.execute_command_readlines(TestVersionLock.settings.ceph_node.public_ip, "root", TestVersionLock.settings.ceph_node.root_password,TestVersionLock.version_lock_list_cmd )[0]
        localLocks = TestVersionLock.settings.lock_files_dir + '\\ceph_vm.vlock'
        with open(localLocks, 'rU') as f:
            expected = f.readlines()

        logger.info( "Verifying Ceph Node")
        self.compare_lists(remoteLocks, expected)

        pass

    def test_controller_nodes_lock_list(self):

        for node in TestVersionLock.settings.controller_nodes:
            remoteLocks =  Ssh.execute_command_readlines(node.provisioning_ip, "root", TestVersionLock.settings.nodes_root_password,TestVersionLock.version_lock_list_cmd )[0]
            localLocks = TestVersionLock.settings.lock_files_dir + '\\controller.vlock'
            with open(localLocks, 'rU') as f:
                expected = f.readlines()
            logger.info( "Verifying Controller Node " + node.hostname )
            self.compare_lists(remoteLocks, expected)

        pass

    def test_compute_nodes_lock_list(self):

        for node in TestVersionLock.settings.compute_nodes:
            remoteLocks =  Ssh.execute_command_readlines(node.provisioning_ip, "root", TestVersionLock.settings.nodes_root_password,TestVersionLock.version_lock_list_cmd )[0]
            localLocks = TestVersionLock.settings.lock_files_dir + '\\compute.vlock'
            with open(localLocks, 'rU') as f:
                expected = f.readlines()
            logger.info( "Verifying Compute Node " + node.hostname )
            self.compare_lists(remoteLocks, expected)

        pass

    def test_ceph_nodes_lock_list(self):

        for node in TestVersionLock.settings.ceph_nodes:
            remoteLocks =  Ssh.execute_command_readlines(node.provisioning_ip, "root", TestVersionLock.settings.nodes_root_password,TestVersionLock.version_lock_list_cmd )[0]
            localLocks = TestVersionLock.settings.lock_files_dir + '\\ceph.vlock'
            with open(localLocks, 'rU') as f:
                expected = f.readlines()
            logger.info( "Verifying Ceph  Node " + node.hostname)
            self.compare_lists(remoteLocks, expected)

        pass


if __name__ == "__main__":


    TestVersionLock.settings = Settings('C:\workspace\deploy-auto\osp_deployer\settings\settings_sample.ini')

    unittest.main()



