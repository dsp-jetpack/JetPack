#
# Copyright (c) 2015-2016 Dell Inc. or its subsidiaries.
#
# This file is free software:  you can redistribute it and or modify
# it under the terms of the GNU General Public License, as published
# by the Free Software Foundation, version 3 of the license or any
# later version.
#
# This file is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

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

def error(msg, *args, **kwargs):
    log.error(msg, *args, **kwargs) 

def critical(msg, *args, **kwargs):
    log.critical(msg, *args, **kwargs) 
