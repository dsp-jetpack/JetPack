
# OpenStack - A set of software tools for building and managing cloud computing
# platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.


import unittest, time
from auto_common import Ipmi, Power_State

class Test(unittest.TestCase):
    '''
    test ipmi lib
    '''
    
    def __init__(self, *args, **kwargs):
        self.target_idrac_ip = "10.21.246.114"
        self.target_ipmi_user = "ipmi"
        self.target_ipmi_password = "QaCl0ud"
        self.cygWinloc = "c:\\temp"
        self.ipmi = Ipmi(self.cygWinloc, self.target_ipmi_user, self.target_ipmi_password, self.target_idrac_ip)
        super(Test, self).__init__(*args, **kwargs)
         
    def test_ipmi_power_off(self):
        self.ipmi.power_off( )
        assert self.ipmi.get_power_state() == Power_State.POWER_OFF
        
    def test_ipmi_power_on(self):
        self.ipmi.power_on()
        assert self.ipmi.get_power_state() == Power_State.POWER_ON
    
    
    def test_ipmi_power_set_pxe(self):
        self.ipmi.set_boot_to_pxe()
        pass
    
    def test_ipmi_power_set_disk(self):
        self.ipmi.set_boot_to_disk()
        pass
    
    def test_turn_back_off(self):
        self.ipmi.power_off()
        pass

if __name__ == "__main__":
    
    
    unittest.main()