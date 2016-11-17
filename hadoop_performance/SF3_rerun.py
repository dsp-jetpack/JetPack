# This tests the repeatability of Teragen - compare runtimes of each teragen run.
from perftest2 import getJobStartFinishTimes, teragen, terasort_output_folder
import time


folderName = ['955c0ad4-fada-472d-92a5-e99f504e7254', '955c0ad4-fada-472d-92a5-e99f504e7254']
outFolder = ['SF10_out1', 'SF10_out2']

for each in folderName:

    out, err = terasort_output_folder(each, outFolder[folderName.index(each)])
    print out
    time.sleep(5)  