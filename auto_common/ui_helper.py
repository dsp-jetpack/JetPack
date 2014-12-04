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
            
    