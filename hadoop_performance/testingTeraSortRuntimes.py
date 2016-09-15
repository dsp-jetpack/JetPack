# This tests the repeatability of Teragen - compare runtimes of each teragen run.
from perftest2 import getJobStartFinishTimes, teragen, terasort_output_folder
import time


folderName = ['teragenSF3_672', 'teragenSF3_672', 'teragenSF3_672', 'teragenSF3_672']
outFolder = ['teragenSF3_outi', 'teragenSF3_outj', 'teragenSF3_outk', 'teragenSF3_outl']

for each in folderName:

    out, err = terasort_output_folder(each, outFolder[folderName.index(each)])
    print out
    time.sleep(15)  