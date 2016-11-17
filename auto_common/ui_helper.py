#!/usr/bin/env python

# Copyright (c) 2015-2016 Dell Inc. or its subsidiaries.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from auto_common import UIManager
import time


# noinspection PyClassHasNoInit,PyUnresolvedReferences,PyProtectedMember
class UIHelper():
    @staticmethod
    def verify_new_window_opened(page_title):
        """
        Verifies the right page (given its title), opened
        raise exception if it didn't
        """
        time.sleep(1)
        driver = UIManager.sel()._current_browser()
        windows = driver.window_handles
        if len(windows) != 2:
            raise AssertionError("Only one window opened")
        driver.switch_to_window(windows[1])
        if driver.title == page_title:
            driver.switch_to_window(windows[1])
            return
        else:
            raise AssertionError(
                "Wrong window opened, expected [" + page_title +
                "], got [" + driver.title + "]")

    @staticmethod
    def switch_to_window(window_title):
        time.sleep(1)
        driver = UIManager.sel()._current_browser()
        windows = driver.window_handles
        if len(windows) != 2:
            raise AssertionError("Only one window opened")
        driver.switch_to_window(windows[1])
        if driver.title == window_title:
            return
        else:
            raise AssertionError(
                "Wrong window found cannot switch to it, expected [" +
                window_title + "], got [" + driver.title + "]")
