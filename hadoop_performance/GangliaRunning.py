# check gmond is running on all nodes
from perftest2 import checkGangliaStatus, get_datanode_entityname, getAllNodeObjects
import time

test_name = 'Checking Ganglia running on datanodes.'
ganglia_ip = "172.16.14.97"
clustername = 'Cluster 1'
cm_api_ip = "172.16.14.156"

objs = getAllNodeObjects(cm_api_ip, clustername)

is_passing = True

for each in objs:
    entity = get_datanode_entityname(cm_api_ip, clustername, each.ipAddress)
    for role in each.roleRefs:
        if 'DATANODE' in role.roleName:
            # print role.roleName
            print entity
            out, err = checkGangliaStatus(each.ipAddress)
            print out
            if 'is running' not in out:
                is_passing = False

print test_name
if is_passing == True:
    print 'Test Passed'
else:
    print 'Test Failed'