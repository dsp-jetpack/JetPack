import unittest, random
from osp_deployer import *
import sys, getopt
from auto_common import Ssh

# TODO add logger
# TODO  Pass in settings as argument

class TestVersionLock(unittest.TestCase):

    settings = ''
    version_lock_list_cmd = 'yum versionlock list'
    rpm_list_cmd = 'rpm -qa'

    def setUp(self):
        pass

    def compare_lists(self, remote_locks, expected):

        for item in remote_locks:
            if "Loaded plugins:" in item:
                remote_locks.remove(item)
        for item in remote_locks:
            if "versionlock list done" in item:
                remote_locks.remove(item)
        for item in remote_locks:
            if 'locks on' in item:
                remote_locks.remove(item)
        for item in remote_locks:
            if item == '\n':
                remote_locks.remove(item)
        for item in expected:
            if "Loaded plugins:" in item:
                expected.remove(item)
        for item in expected:
            if "versionlock list done" in item:
                expected.remove(item)
        for item in expected:
            if 'locks on' in item:
                expected.remove(item)
        for item in expected:
            if item == '\n':
                expected.remove(item)

        a =  list(set(remote_locks).difference(set(expected)))
        b =  list(set(expected).difference(set(remote_locks)))



        print "diff a " + str(a)
        print "diff b " + str(b)

        assert len(a) == 0
        assert len(b) == 0

    def test_foreman_node(self):
        remoteLocks =  Ssh.execute_command_readlines(TestVersionLock.settings.foreman_node.public_ip, "root", TestVersionLock.settings.foreman_node.root_password,TestVersionLock.version_lock_list_cmd )[0]
        localLocks = TestVersionLock.settings.lock_files_dir + '\\foreman_vm.vlock'
        with open(localLocks, 'rU') as f:
            expected = f.readlines()

        print "Differences foreman Node"

        self.compare_lists(remoteLocks, expected)

        pass

    def test_ceph_node(self):
        remoteLocks =  Ssh.execute_command_readlines(TestVersionLock.settings.ceph_node.public_ip, "root", TestVersionLock.settings.ceph_node.root_password,TestVersionLock.version_lock_list_cmd )[0]
        localLocks = TestVersionLock.settings.lock_files_dir + '\\ceph_vm.vlock'
        with open(localLocks, 'rU') as f:
            expected = f.readlines()

        print "Differences Ceph Node"
        self.compare_lists(remoteLocks, expected)

        pass

    def test_controller_nodes(self):

        for node in TestVersionLock.settings.controller_nodes:
            remoteLocks =  Ssh.execute_command_readlines(node.provisioning_ip, "root", TestVersionLock.settings.nodes_root_password,TestVersionLock.version_lock_list_cmd )[0]
            localLocks = TestVersionLock.settings.lock_files_dir + '\\controller.vlock'
            with open(localLocks, 'rU') as f:
                expected = f.readlines()
            print "Differences Controller Node " + node.hostname
            self.compare_lists(remoteLocks, expected)

        pass

    def test_compute_nodes(self):

        for node in TestVersionLock.settings.controller_nodes:
            remoteLocks =  Ssh.execute_command_readlines(node.provisioning_ip, "root", TestVersionLock.settings.nodes_root_password,TestVersionLock.version_lock_list_cmd )[0]
            localLocks = TestVersionLock.settings.lock_files_dir + '\\compute.vlock'
            with open(localLocks, 'rU') as f:
                expected = f.readlines()
            print "Differences Compute Node " + node.hostname
            self.compare_lists(remoteLocks, expected)

        pass

    def test_ceph_nodes(self):

        for node in TestVersionLock.settings.controller_nodes:
            remoteLocks =  Ssh.execute_command_readlines(node.provisioning_ip, "root", TestVersionLock.settings.nodes_root_password,TestVersionLock.version_lock_list_cmd )[0]
            localLocks = TestVersionLock.settings.lock_files_dir + '\\ceph.vlock'
            with open(localLocks, 'rU') as f:
                expected = f.readlines()
            print "Differences Ceph  Node " + node.hostname
            self.compare_lists(remoteLocks, expected)

        pass


if __name__ == "__main__":


    TestVersionLock.settings = Settings('C:\workspace\deploy-auto\osp_deployer\settings\settings_sample.ini')
    print "starting tests "
    unittest.main()



