import logging 

LOGGER_NAME = 'netlog'

log = logging.getLogger(LOGGER_NAME)

def getLogger():
    return log

def init():
    "configure logging"
    # set up console logging
    log = logging.getLogger(LOGGER_NAME)

    log.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    # davids format
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    log.addHandler(console_handler)

def enable_log_file(logfile=None):
    "turn on logging to a file"
    log = logging.getLogger(LOGGER_NAME)

    if not logfile:
        logfile = 'netval.log'
    fh = logging.FileHandler(logfile)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    log.addHandler(fh)
    msg = "Enabled logging to file: " + logfile
    log.info(msg)

def enable_debug():
    "Turn on debug level logging"
    log = logging.getLogger(LOGGER_NAME)
    log.setLevel(logging.DEBUG)
    msg = "Enabled verbose logging."
    log.debug(msg)   

def debug(msg, *args, **kwargs):

    log.debug(msg, *args, **kwargs) 

def info(msg, *args, **kwargs):

    log.info(msg, *args, **kwargs)


