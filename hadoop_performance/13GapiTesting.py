import threading
import time
import time, calendar, re, uuid,  importlib, datetime,  subprocess, paramiko, sys, os, requests, logging
from cm_api.api_client import ApiResource
import dateutil.parser
from datetime import timedelta

edge_node_ip = "172.16.14.101"
session = ApiResource(edge_node_ip,  7180, "admin", "admin", version=6)

id = 'job_201504160841_0028'
id = 'job_201504160841_0033'
id = 'job_201504160841_0092'
id = 'job_201504160841_0169'
id = 'job_201504160841_0193'
id = 'job_1450127588408_0027'
#id = '1434992149266_0007'

#start = 2015-06-25 13:03:20.864000
#finish = 2015-06-25 13:03:49.316000
#time start: 2015-06-25 13:03:20.864000
#time end: 2015-06-25 13:03:49.316000

timeA = (2015, 12, 19, 11, 25, 13, 6, 61, 0)
timeB = (2015, 12, 21, 07, 34, 59, 7, 21, 0)

#timeA = datetime.datetime.now()-datetime.timedelta(hours=2)
#timeB = datetime.datetime.now()

#tsquery = 'select cpu_user_rate / 32 *100 where hostname = "r2s1xd4.rcbd.lab" and category= Host'
tsquery = 'select cpu_system_rate where hostname = "r3s1xd10.rcbd.lab" and category= Host'

 
cdh4 = None
for c in session.get_all_clusters():
    print str(c.version)
    if c.version == "CDH5":
        cdh4 = c 
for s in cdh4.get_all_services():
    print s.name
    if s.name == "yarn":
        mapreduce = s
    elif s.name == "mapreduce":
        mapreduce = s


#getting mapred jobs
ac = mapreduce.get_activity(id)
print str(ac.name)
print "stats with NO offset"
print str(ac.startTime)
print str(ac.finishTime)

time_start = datetime.datetime.strptime(ac.startTime, '%Y-%m-%dT%H:%M:%S.%fZ')
time_finish = datetime.datetime.strptime(ac.finishTime, '%Y-%m-%dT%H:%M:%S.%fZ')

print time_start.tzname
#wider_time = ob.startTime+datetime.timedelta(hours=5)

#for yarn
#hostRes = session.query_timeseries(tsquery, ob.startTime, ob.endTime)

#for mapred
hostRes = session.query_timeseries(tsquery, time_start, time_finish)
#hostRes = session.query_timeseries(tsquery, ac.startTime, ac.finishTime)

print str(hostRes)
for rez in hostRes[0].timeSeries:
    for point in rez.data:
        print "point.value: " + str(point.value)
        print "timestamp: " + str(point.timestamp)
        if point.value > 0:
            print "point.value: " + str(point.value)
            print "timestamp: " + str(point.timestamp)

print "\nStats WITH offset"
offset = datetime.timedelta(hours=5)
#time_start = ob.startTime
#time_finish = ob.endTime
#Rolling back both start and end times by 5 hours
time_start = time_start-offset
time_finish = time_finish-offset

print str(time_start)
print str(time_finish)

hostRes = session.query_timeseries(tsquery, time_start, time_finish)

for rez in hostRes[0].timeSeries:
    for point in rez.data:
        print "point.value: " + str(point.value)
        print "timestamp: " + str(point.timestamp)
        if point.value > 0:
            print "point.value: " + str(point.value)
            print "timestamp: " + str(point.timestamp)
        
#t = (2009, 2, 17, 17, 3, 38, 1, 48, 0)
#t = datetime.datetime.now()
#secs = time.mktime( t )
#print "time.mktime(t) : %f" %  secs
#time_start = datetime.datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')
#print "asctime(localtime(secs)): %s" % time.asctime(time_start)
print "----------------"
t = time.localtime()
print time.tzname
print t
t = time.mktime(t)

print "-------------------"
#print "time.asctime(t): %s " % time.asctime(t)
 
#rrdtool fetch /var/lib/ganglia/rrds/Performance\ Stamp/r2s1xd9/bytes_out.rrd AVERAGE -s 1430369792 -e 1430369820

#getting yarn jobs
#ac =  mapreduce.get_yarn_applications(timeA, timeB)
#for job in ac.applications:
#    print job
#    if id == str(job.applicationId):
#        print job.applicationId
#        ob = job
#        print ob.startTime
#        print ob.endTime



#ob = job         
#start = ob.startTime
#finish = ob.endTime                