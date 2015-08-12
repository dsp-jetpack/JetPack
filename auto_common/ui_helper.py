
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

from auto_common import UI_Manager, Widget
import time

class UI_Helper:
    
    @staticmethod
    def verify_new_window_opened(pageTitle):
        '''
        Verifies the right page (given its title), opened
        raise exception if it didn't
        '''
        time.sleep(1)
        driver = UI_Manager.sel()._current_browser()
        windows = driver.window_handles
        if len(windows) != 2:
            raise AssertionError("Only one window opened")
        driver.switch_to_window(windows[1])
        if driver.title == pageTitle:
                driver.switch_to_window(windows[1])
                return
        else:
            raise AssertionError("Wrong window opened, expected [" + pageTitle + "], got [" + driver.title + "]")
            
                
    @staticmethod
    def switch_to_window( windowTitle):
        time.sleep(1)
        driver = UI_Manager.sel()._current_browser()
        windows = driver.window_handles
        if len(windows) != 2:
            raise AssertionError("Only one window opened")
        driver.switch_to_window(windows[1])
        if driver.title == windowTitle:
                return
        else:
            raise AssertionError("Wrong window found cannot switch to it, expected [" + windowTitle + "], got [" + driver.title + "]")
            
    