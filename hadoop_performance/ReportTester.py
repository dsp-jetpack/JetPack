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
 
tpc_size = '30TB'
report_job_id = 'job_1460938781401_0284'
results_file = 'Results-100GB T26.log'
scale_factor = '100GB'#convertToSF(tpc_size)

print report_job_id
print results_file
print scale_factor

bob.createReport(report_job_id, results_file, scale_factor)