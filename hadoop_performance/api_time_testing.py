import threading
import time
import time, calendar, re, uuid,  importlib, datetime,  subprocess, paramiko, sys, os, requests, logging
from cm_api.api_client import ApiResource
import dateutil.parser
from datetime import timedelta
from perftest2 import getJobStartFinishTimes, run_tpc_benchmark, get_datanode_cores

offset = datetime.timedelta(minutes=0)
offset2 = datetime.timedelta(minutes=60)
job_id = {'job_1460938781401_0043', 'job_1460938781401_0044', 'job_1460938781401_0045'}
job_id = 'job_1470948030861_0023'
#start_time = '2016-04-19 16:29:38.755000'
#start_time = datetime.datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S.%fZ')
start_time = datetime.datetime.now() + offset
print 'S: ' + str(start_time)
time.sleep(3)
#end_time = '2016-04-19 16:30:08.881000'
#end_time = datetime.datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S.%fZ')
end_time = datetime.datetime.now() + offset2

print 'e: ' + str(end_time)

# for each in job_id:
    # print 'each: ' + str(each)
job_name, start, finish = getJobStartFinishTimes(job_id, start_time, end_time)
print job_name
print start
print finish
print '--------------'

#job_ids, job_names, start_times, finish_times = run_tpc_benchmark('1')

print '----------------'
edge_node_ip = "172.16.14.156"
session = ApiResource(edge_node_ip,  7180, "admin", "admin", version=6)

'''
id = 'job_201504160841_0028'
id = 'job_201504160841_0033'
id = 'job_201504160841_0092'
id = 'job_201504160841_0169'
id = 'job_201504160841_0193'
id = 'job_1460032860833_0062'
id = 'job_1460938781401_0043'
id = 'job_1460938781401_0044'
id = 'job_1464878633740_0028'
'''
date = time.strftime('%Y/%m/%d')
print date
#tsquery = 'select cpu_user_rate / 32 *100 where hostname = "r2s1xd4.rcbd.lab" and category= Host'
#tsquery = 'select cpu_user_rate  / 56 * 100 where hostname = "r3s1xd8.ignition.dell.com" and category= Host'
tsquery = 'select physical_memory_used where hostname = "r3s1xd8.ignition.dell.com" and category= Host'

offset = datetime.timedelta(minutes=240)
#start_time = datetime.datetime.now()-offset 
#end_time = datetime.datetime.now()#+offset

start_time = start - offset
end_time = finish - offset

cm_api_ip = "172.16.14.156" 
hostname = "r3s1xd8.ignition.dell.com"
clustername = "Cluster 1"

cores = get_datanode_cores(cm_api_ip, clustername, hostname)

print 'CORES ' + str(cores)

'''
cdh4 = None
for c in session.get_all_clusters():
    print str(c.version)
    if c.version == "CDH5":
        cdh4 = c 
for s in cdh4.get_all_services():
    print s.name
    if s.name == "yarn":
        mapreduce = s
    #elif s.name == "mapreduce":
    #    mapreduce = s
        ac =  s.get_yarn_applications(start_time, end_time)
        for job in ac.applications:
            print 'Job: ' + str(job)
            if id == str(job.applicationId):
                ob = job
                print 'ob scope1: ' + str(ob)
            # print 'ob scope2: ' + str(ob)
        print 'ob scope3: ' + str(ob)
        start = ob.startTime
        finish = ob.endTime
        job_name = ob.name
    
        print 'job name: ' + str(job.name)
        print 'start: ' + str(job.startTime)
        print 'finish: ' + str(job.endTime)
        print finish
        print job_name
'''
# ac = mapreduce.get_activity(id)
# print str(ac.name)
# print "stats with NO offset"
# print str(ac.startTime)
# print str(ac.finishTime)

# time_start = datetime.datetime.strptime(ac.startTime, '%Y-%m-%dT%H:%M:%S.%fZ')
# time_finish = datetime.datetime.strptime(ac.finishTime, '%Y-%m-%dT%H:%M:%S.%fZ')
# offset = datetime.timedelta(minutes=300)

# time_start = start - offset
# time_finish = datetime.datetime.now() #finish + offset

# #offset = datetime.timedelta(hours=24)

time_start = start_time
time_finish = end_time

print time_start
print time_finish
print '-----------------------------'
hostRes = session.query_timeseries(tsquery, time_start, time_finish)
print hostRes
for rez in hostRes[0].timeSeries:
    #print rez
    for point in rez.data:
        #print "point.value: " + str(point.value)
        #print "timestamp: " + str(point.timestamp)
        if point.value > 5:
            print "point.value: " + str(point.value)
            print "timestamp: " + str(point.timestamp)



# print "\nStats WITH offset"
# offset = datetime.timedelta(hours=5)
# offset2 = datetime.timedelta(hours=5)
# #Rolling back both start and end times by 5 hours
# time_start = time_start-offset2
# time_finish = time_finish-offset

# print str(time_start)
# print str(time_finish)

# hostRes = session.query_timeseries(tsquery, time_start, time_finish)

# for rez in hostRes[0].timeSeries:
    # for point in rez.data:
        # print "point.value: " + str(point.value)
        # print "timestamp: " + str(point.timestamp)
        # #if point.value > 1:
            # #print "point.value: " + str(point.value)
            # #print "timestamp: " + str(point.timestamp)
        
# #t = (2009, 2, 17, 17, 3, 38, 1, 48, 0)
# #t = datetime.datetime.now()
# #secs = time.mktime( t )
# #print "time.mktime(t) : %f" %  secs
# #time_start = datetime.datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')
# #print "asctime(localtime(secs)): %s" % time.asctime(time_start)
# t = time.localtime()
# #print t
# t = time.mktime(t)
# #print t
# #print "time.asctime(t): %s " % time.asctime(t)
 
# #rrdtool fetch /var/lib/ganglia/rrds/13g Performance\ Stamp/r3s1xd8/bytes_out.rrd AVERAGE -s 1430369792 -e 1430369820

                