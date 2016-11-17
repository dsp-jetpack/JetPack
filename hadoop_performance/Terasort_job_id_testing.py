# This tests the repeatability of Teragen - compare runtimes of each teragen run.
from perftest2 import getJobStartFinishTimes, teragen, terasort_output_folder, run_terasort_job
import time


folderName = ['teragenDDD672']

for each in folderName:

    job_id, job_name, start, finish = run_terasort_job(each)

    print job_id
    print job_name
    print start
    print finish
    time.sleep(5)  