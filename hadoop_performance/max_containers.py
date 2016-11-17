# get max number of containers
import time, datetime
import dateutil.parser

from datetime import timedelta
from cm_api.api_client import ApiResource

cm_api_ip = "172.16.14.156" 

session = ApiResource(cm_api_ip,  7180, "admin", "admin", version=6)

offset = datetime.timedelta(minutes=150)
start_offset = datetime.timedelta(minutes=60)

start_time = datetime.datetime.now()
end_time = datetime.datetime.now()

start_time = start_time + start_offset
end_time = end_time + offset

print start_time
print end_time

hostname = "r3s1xd8.ignition.dell.com"
clustername = "Cluster 1"

tsquery = 'SELECT total_containers_running_across_nodemanagers WHERE entityName = "yarn" AND category = SERVICE'

hostRes = session.query_timeseries(tsquery, start_time, end_time)
print hostRes
data = []
for rez in hostRes[0].timeSeries:
    #print rez
	
    for point in rez.data:
        #print "point.value: " + str(point.value)
        #print "timestamp: " + str(point.timestamp)
        data.append(point.value)
	
highestValue = 0.00
highestValue = sorted(data, key=float, reverse=True)[0]
    
print highestValue