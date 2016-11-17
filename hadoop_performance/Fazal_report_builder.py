import time, calendar, re, uuid,  importlib, datetime, subprocess, paramiko, sys, os, requests, logging
import fileinput
from cm_api.api_client import ApiResource
import dateutil.parser
from datetime import timedelta
from auto_common import *
from sandbox import ConfigStamp, ReportBuilder
from shutil import copyfile

def convertToSF(tpc_size):

    if tpc_size == '1':
        tpc_size = '100GB'
    elif tpc_size == '2':
        tpc_size = '300GB'
    elif tpc_size == '3':
        tpc_size = '1TB'
    elif tpc_size == '4':
        tpc_size = '3TB'
    elif tpc_size == '5':
        tpc_size = '10TB'
    elif tpc_size == '6':
        tpc_size = '30TB'
    elif tpc_size == '7':
        tpc_size = '100TB'
    elif tpc_size == '8':
        tpc_size = '300TB'
    elif tpc_size == '9':
        tpc_size = '1PB'

    return tpc_size

# generate a report based on the output from the job run above.
bob = ReportBuilder()
report_job_id = 'job_1460938781401_0023'
results_file = 'Results-300000000000 T7.log'
scale_factor = convertToSF(tpc_size)

print report_job_id
print results_file
print scale_factor

bob.createReport(report_job_id, results_file, scale_factor)