"""Unit Tests for network performance and validation tool"""

import unittest

import unittests_netval

def test_all():
    """return a suite of all tests for the network_testing package

    This is the entry point for tests run from distutils, and is specified
    in setup.py   Each test module should define a suite attribute that
    is a unittest.TestSuite() instance including all tests to be run in
    that module.

    """

    suite = unittest.TestSuite()
    suite.addTest(unittests_netval.suite)

    return suite
