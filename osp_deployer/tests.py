import sys, time
from auto_common import Ipmi, Ssh, FileHelper, Scp, UI_Manager, Widget
from datetime import datetime
from osp_deployer import *
from selenium import webdriver
import paramiko, re
from osp_deployer.config import Settings
from auto_common import Ssh, Scp, UI_Manager, Widget
import time
import logging

logger = logging.getLogger(__name__)


if __name__ == '__main__':
   
    import logging.config
    logging.basicConfig(filename='c:/auto_results/deployer.log',
                    format="%(asctime)-15s:%(name)s:%(process)d:%(levelname)s:%(message)s",
                    filemode='w',
                    level=logging.INFO)
    
    settings = Settings('settings\settings.ini')  
    attrs = vars(settings)
    
    
    ceph = Ceph()
    ceph.copy_installer()
    ceph.install_ice()
    ceph.configure_monitor()
    
        

    