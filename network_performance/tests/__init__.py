"""Unit Tests for network performance and validation tool"""
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


import unittest

#import unittests_netval
import test_iperf3
import test_netlog

def test_all():
    """return a suite of all tests for the network_testing package

    This is the entry point for tests run from distutils, and is specified
    in setup.py   Each test module should define a suite attribute that
    is a unittest.TestSuite() instance including all tests to be run in
    that module.

    """

    suite = unittest.TestSuite()
    #suite.addTest(unittests_netval.suite)
    suite.addTest(test_iperf3.suite)
    suite.addTest(test_netlog.suite)

    return suite
