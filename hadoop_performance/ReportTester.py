import threading
import time
import time, calendar, re, uuid,  importlib, datetime,  subprocess, paramiko, sys, os, requests, logging
from cm_api.api_client import ApiResource
import dateutil.parser
from datetime import timedelta
from perftest2 import getJobStartFinishTimes, run_tpc_benchmark
from reportbuilder import ReportBuilder
#from ReportBuilder import convertToSF


bob = ReportBuilder()
 
tpc_size = '1TB'
#report_job_id = 'job_1475246076038_0050'
report_job_id = 'job_1475246076038_0083'

#results_file = 'Results-10000000000 T3.log'
#results_file = 'Results-SF1 T5.log'
#results_file = 'TPCx-HS-result-1TB.log'
results_file = 'Results-1TB T1.log'


scale_factor = '1TB'#convertToSF(tpc_size)

print report_job_id
print results_file
print scale_factor

bob.createReport(report_job_id, results_file, scale_factor)