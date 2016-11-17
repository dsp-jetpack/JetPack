# This tests the repeatability of Teragen - compare runtimes of each teragen run.
from perftest2 import getJobStartFinishTimes, teragen_cmd
import time

#rowNumber = 10000000000

#rowNumber = 1000000000000
rowNumber = 30000000000
folderName = ['teragenSF3_']#, 'teragenSF3_PATj_', 'teragenSF3_PATk_', 'teragenSF3_PATl_']
maps = 672

for each in folderName:
    each = each + str(maps)
    print maps
    #cmd = 'cd /opt/cloudera/parcels/CDH-5.6.0-1.cdh5.6.0.p0.45/lib/hadoop-mapreduce/;sudo -u hdfs hadoop jar hadoop-mapreduce-examples-2.6.0-cdh5.6.0.jar teragen -D mapreduce.job.maps=480 -D mapreduce.job.reduces=240 ' + str(rowNumber) +' '+ str(each)
    #cmd = 'cd /opt/cloudera/parcels/CDH-5.6.1-1.cdh5.6.1.p0.3/lib/hadoop-mapreduce/;sudo -u hdfs hadoop jar hadoop-mapreduce-examples-2.6.0-cdh5.6.1.jar teragen -D mapreduce.terasort.output.replication=3 -D mapreduce.job.maps=480 -D mapreduce.job.reduces=240 ' + str(rowNumber) +' '+ str(each)
    cmd = 'cd /opt/cloudera/parcels/CDH-5.6.0-1.cdh5.6.0.p0.45/lib/hadoop-mapreduce/;sudo -u hdfs hadoop jar hadoop-mapreduce-examples-2.6.0-cdh5.6.0.jar teragen -D mapreduce.job.maps='+str(maps) +' ' + str(rowNumber) +' '+ str(each)
    #maps = maps + maps
    print cmd
    out, err = teragen_cmd(rowNumber, cmd)
    print out
    time.sleep(15)
    
    
    