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

from selenium.webdriver import ActionChains
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys

import time

SEL = None

class UI_Manager():
    
    
    @staticmethod
    def driver():
        global SEL
        SEL = SEL or webdriver.Firefox()
        return SEL


class Widget():
    
    def __init__(self, locator):
        self.locator = locator
        
    def click(self):
        self.waitFor(10)
         
        element = UI_Manager.driver().find_element_by_xpath(self.locator)
        element.send_keys(Keys.NULL) # force in focus
        element.click()
        
        
    def exists(self):
        #UI_Manager.driver()._info( "exists ? " + self.locator)
        try:
            element = UI_Manager.driver().find_element_by_xpath(self.locator)
            visible = element.is_displayed()
            siOno =  visible
        except:
            siOno = False
        #UI_Manager.driver()._info( "     exists " + str(siOno) + " visible "+ str(visible))
        return siOno
    
    def mouse_over(self):
        UI_Manager.driver()._info( "mouse over " + self.locator)
        UI_Manager.driver().mouse_down(self.locator)
        UI_Manager.driver().mouse_up(self.locator)
        
    def getText(self):
        #UI_Manager.sel._info( "getting text of " + self.locator)
        self.waitFor(10)
        element = UI_Manager.driver().find_element_by_xpath(self.locator)
        #UI_Manager.sel._info(( ".. " + element.get_attribute('.'))
        return element.text
    
    def getInputText(self):
        #UI_Manager.sel._info( "getting text of " + self.locator)
        element = UI_Manager.driver().find_element_by_xpath(self.locator)
        return element.get_attribute('value')
    
    def setText(self, textToSet, bclearBefore=True):
        #UI_Manager.driver()._info( "setting text of " + self.locator)
        self.waitFor(10)
        #UI_Manager.driver().focus(self.locator)
        element = UI_Manager.driver().find_element_by_xpath(self.locator)
        if bclearBefore == True:
            element.clear()
        element.send_keys(textToSet)
        
    def sendKey(self, keys):
        #UI_Manager.driver()._info( "setting text of " + self.locator)
        UI_Manager.driver().focus(self.locator)
        element = UI_Manager.driver().find_element_by_xpath(self.locator)
        element.send_keys(keys)        
   
    def getAttribute(self, attribute):
        element = UI_Manager.driver().find_element_by_xpath(self.locator)
        return element.get_attribute(attribute)
         
    def select(self, labelValue):
        element = Select(UI_Manager.driver().find_element_by_xpath(self.locator))
        element.select_by_visible_text(labelValue)
    
    def selectByValue(self, value):
        element = UI_Manager.driver()._get_select_list(self.locator)
        element.select_by_value(value)
        
    def selectByIndex(self, index):
        element = UI_Manager.driver()._get_select_list(self.locator)
        element.select_by_index(index)
        
    def getSelectedValue(self):
        element = UI_Manager.driver()._get_select_list(self.locator)
        return element.first_selected_option.get_attribute('value')
    
    def waitFor(self, timeoutSeconds):
        inc = 0
        while inc < timeoutSeconds:
            if self.exists() :
                return
            else:
                time.sleep(2)
                inc = inc + 2
        raise AssertionError(self.locator + " not found in " + str(timeoutSeconds) + " seconds") 
    
    
   
    
        
