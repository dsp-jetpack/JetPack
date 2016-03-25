#!/usr/bin/env python

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


from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys

import time

SEL = None


# noinspection PyClassHasNoInit
class UIManager():

    @staticmethod
    def driver():
        global SEL
        SEL = SEL or webdriver.Firefox()
        return SEL


# noinspection PyProtectedMember
class Widget():

    def __init__(self, locator):
        self.locator = locator

    def click(self):
        self.wait_for(10)
        element = UIManager.driver().find_element_by_xpath(self.locator)
        # force in focus
        element.send_keys(Keys.NULL)
        element.click()

    def exists(self):
        # noinspection PyBroadException
        try:
            element = UIManager.driver().find_element_by_xpath(self.locator)
            visible = element.is_displayed()
            si_o_no = visible
        except:
            si_o_no = False
        return si_o_no

    def mouse_over(self):
        UIManager.driver()._info("mouse over " + self.locator)
        UIManager.driver().mouse_down(self.locator)
        UIManager.driver().mouse_up(self.locator)

    def get_text(self):
        self.wait_for(10)
        element = UIManager.driver().find_element_by_xpath(self.locator)
        return element.text

    def get_input_text(self):
        element = UIManager.driver().find_element_by_xpath(self.locator)
        return element.get_attribute('value')

    def set_text(self, text_to_set, clear_before=True):
        self.wait_for(10)
        element = UIManager.driver().find_element_by_xpath(self.locator)
        if clear_before:
            element.clear()
        element.send_keys(text_to_set)

    def send_key(self, keys):
        UIManager.driver().focus(self.locator)
        element = UIManager.driver().find_element_by_xpath(self.locator)
        element.send_keys(keys)

    def get_attribute(self, attribute):
        element = UIManager.driver().find_element_by_xpath(self.locator)
        return element.get_attribute(attribute)

    def select(self, label_value):
        element = Select(
            UIManager.driver().find_element_by_xpath(self.locator))
        element.select_by_visible_text(label_value)

    def select_by_value(self, value):
        element = UIManager.driver()._get_select_list(self.locator)
        element.select_by_value(value)

    def select_by_index(self, index):
        element = UIManager.driver()._get_select_list(self.locator)
        element.select_by_index(index)

    def get_selected_value(self):
        element = UIManager.driver()._get_select_list(self.locator)
        return element.first_selected_option.get_attribute('value')

    def wait_for(self, timeout_seconds):
        inc = 0
        while inc < timeout_seconds:
            if self.exists():
                return
            else:
                time.sleep(2)
                inc += 2
        raise AssertionError(self.locator + " not found in " +
                             str(timeout_seconds) + " seconds")
