import logging
import random
import os, datetime, sys
from datetime import datetime

class dateLogHandler(logging.FileHandler):

    def __init__(self,fileName,mode):
        isLinux = False
        if sys.platform.startswith('linux'):
                isLinux = True
        path = '/auto_results/'
        fname = datetime.now().strftime(".%Y.%m.%d-%H.%M")
        super(dateLogHandler,self).__init__(path + fileName + fname,mode)

