""" comand line hook to run all unit tests manually 

Intended for use from the command line during development or qa
automation, since tests aren't installed with the final package.

This hook accomplishes the same thing as 'setup.py test'

"""
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

import tests

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=3).run(tests.test_all())
