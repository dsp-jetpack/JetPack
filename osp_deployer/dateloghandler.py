import logging
from datetime import datetime


class Dateloghandler(logging.FileHandler):

    def __init__(self, filename, mode):

        path = '/auto_results/'
        fname = datetime.now().strftime(".%Y.%m.%d-%H.%M")
        super(Dateloghandler, self).__init__(path + filename + fname, mode)

