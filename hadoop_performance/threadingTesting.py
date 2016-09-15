import threading
import time
import time, calendar, re, uuid,  importlib, datetime,  subprocess, paramiko, sys, os, requests, logging
from cm_api.api_client import ApiResource
import dateutil.parser
from datetime import timedelta

def ssh_emulator():
    print threading.currentThread().getName(), ' Starting Long'
    time.sleep(1)
    print threading.currentThread().getName(), ' Exiting Long'

def get_stats():
    print threading.currentThread().getName(), 'Starting'
    time.sleep(1)
    print threading.currentThread().getName(), 'Exiting'

ssh = threading.Thread(name='Ssh_emulator', target=ssh_emulator)
get_stats1 = threading.Thread(name='Get_stats', target=get_stats)
get_stats2 = threading.Thread(name='Get_stats', target=get_stats) # use default name
get_stats3 = threading.Thread(name='Get_stats', target=get_stats) # use default name

jobIDs = {'1','2','3','4','5'}
#ssh.start()
#get_stats1.start()
#get_stats2.start()
#get_stats3.start()


for each in range(6):
    print each%3
    
edge_node_ip = "172.16.11.143"
session = ApiResource(edge_node_ip,  7180, "admin", "admin", version=6)
    #log('jobIds = ' + str(jobIDs))
    #log(str(id))
id = 'job_201504160841_0028'
    #for id in jobIDs:
        # Get the MapReduce job runtime from the job id
cdh4 = None
for c in session.get_all_clusters():
    print str(c.version)
    if c.version == "CDH5":
        cdh4 = c 
for s in cdh4.get_all_services():
    print s.name
    ############
    if s.name == "yarn":
        mapreduce = s
    elif s.name == "mapreduce":
        mapreduce = s
                
    
    
ac = mapreduce.get_activity(id)
#print jobIDs
print str(ac.startTime)
print str(ac.finishTime)

time_start = datetime.datetime.strptime(ac.startTime, '%Y-%m-%dT%H:%M:%S.%fZ')
time_finish = datetime.datetime.strptime(ac.finishTime, '%Y-%m-%dT%H:%M:%S.%fZ')

time_start = time_start-datetime.timedelta(hours=5)
time_finish = time_finish-datetime.timedelta(hours=5)

tsquery = 'select cpu_user_rate / 32 *100 where hostname = "r2s1xd1.rcbd.lab" and category= Host'
#tsquery = "select "+stat+" / "+str(numCores)+" * 100 where hostname = \""+ host +"\" and category = Host"
        #log(str(tsquery))
print str(time_start)
print str(time_finish)

hostRes = session.query_timeseries(tsquery, time_start, time_finish)
print hostRes
for rez in hostRes[0].timeSeries:
    for point in rez.data:
        print "point.value: " + str(point.value)
        print "timestamp: " + str(point.timestamp)
        #if point.value > 0:
        #    print "point.value: " + str(point.value)
        #    print "timestamp: " + str(point.timestamp)
        
        
                