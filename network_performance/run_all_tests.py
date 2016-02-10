""" comand line hook to run all unit tests manually 

Intended for use from the command line during development or qa
automation, since tests aren't installed with the final package.

This hook accomplishes the same thing as 'setup.py test'

"""
import unittest

import tests

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(tests.test_all())
