"""Unit Tests for network performance and validation tool"""

# Copyright 2014-2016 Dell, Inc. or it's subsidiaries.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#  http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
