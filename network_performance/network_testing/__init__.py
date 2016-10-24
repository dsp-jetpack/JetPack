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

import netvaltest
#import netperftest


__version__ = '1.0.1b1'

def run_netvaltest():
    """ entry point for network validation tool """    
    netvaltest.Main()

# XXX(mikeyp) disable since netperftest depends on importlib, which is not in 
# Python 2.6
#def run_netperftest():
#    """ entry point for network performance tool """    
#    netperftest.Main()
