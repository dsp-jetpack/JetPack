import sys, time
from auto_common import Ipmi, Ssh, FileHelper, Scp, UI_Manager, Widget
from datetime import datetime
from osp_deployer import *
from selenium import webdriver
from osp_deployer.foreman_ui.login import Login
import paramiko, re
from osp_deployer.config import Settings
from auto_common import Ssh, Scp, UI_Manager, Widget
from osp_deployer.foreman_ui.login import Login
import time
import logging

logger = logging.getLogger(__name__)


if __name__ == '__main__':
   
    
    settings = Settings('settings\settings.ini')  
    attrs = vars(settings)
    print ('\r '.join("%s: %s" % item for item in attrs.items()))
    
    print " ...... 1 .... "
    
    print settings.stamp_storage
    #ceph = Ceph()
    #ceph.copy_installer()
    #ceph.install_ice()
    
    
        

    