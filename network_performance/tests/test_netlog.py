import logging
import os
import unittest

import network_testing.netlog as netlog

class TestLogging(unittest.TestCase):

    logfile_name = 'test_netlog.log'

    def setUp(self):
        try:
            os.remove(self.logfile_name)
        except OSError:
            pass

    def tearDown(self):
        try:
            os.remove(self.logfile_name)
        except OSError:
            pass

    def test_import(self):
        "Validate module properties"
        self.assertEqual(netlog.LOGGER_NAME, 'netlog')
        self.assertTrue(isinstance(netlog.log, logging.Logger))
        self.assertTrue(isinstance(netlog.getLogger(), logging.Logger))

    def test_file_logging(self):
        "test logging to a file"
        netlog.init()
        netlog.enable_log_file(self.logfile_name)
        netlog.info('something in the log')
        self.assertTrue(os.access(self.logfile_name, os.F_OK))

    def test_log_arguments(self):
        netlog.info("message argument %s", "hello")

# suite is all the test cases in this module

suite = unittest.TestSuite([
    unittest.TestLoader().loadTestsFromTestCase(TestLogging),
    ])

