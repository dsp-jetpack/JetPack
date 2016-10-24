#
# Copyright (c) 2015-2016 Dell Inc. or its subsidiaries.
#
# This file is free software:  you can redistribute it and or modify
# it under the terms of the GNU General Public License, as published
# by the Free Software Foundation, version 3 of the license or any
# later version.
#
# This file is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

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

