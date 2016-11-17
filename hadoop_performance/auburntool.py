#!/usr/bin/env python

# OpenStack - A set of software tools for building and managing cloud computing
# platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.

import time, calendar, re, uuid,  importlib, datetime, subprocess, paramiko, sys, os, requests, logging
import fileinput
from cm_api.api_client import ApiResource
import dateutil.parser
from datetime import timedelta
from auto_common import *
from sandbox import ConfigStamp, ReportBuilder
from shutil import copyfile

def checkGangliaProcess(ganglia_ip):
    print 'Checking Ganglia Process'
    usr = 'root'
    pwd = 'Ignition01'
    cmd = 'ps -ef | grep -v grep | grep gm'

    cl_stdoutd, cl_stderrd = Ssh.execute_command(ganglia_ip, usr, pwd, cmd)

    return cl_stdoutd, cl_stderrd

def checkGangliaPorts(ganglia_ip):
    print 'Checking Ganglia ports'
    usr = 'root'
    pwd = 'Ignition01'
    cmd = "netstat -plane | egrep 'gmon|gme'"

    cl_stdoutd, cl_stderrd = Ssh.execute_command(ganglia_ip, usr, pwd, cmd)

    return cl_stdoutd, cl_stderrd

def checkGangliaStatusAll(ganglia_ip):
    print 'Checking Ganglia status'
    usr = 'root'
    pwd = 'Ignition01'
    cmd = "clush -a service gmond status"

    cl_stdoutd, cl_stderrd = Ssh.execute_command(ganglia_ip, usr, pwd, cmd)

    return cl_stdoutd, cl_stderrd


def checkGangliaStatus(node_ip):
    print 'Checking Ganglia status'
    usr = 'root'
    pwd = 'Ignition01'
    cmd = "service gmond status"

    cl_stdoutd, cl_stderrd = Ssh.execute_command(node_ip, usr, pwd, cmd)

    return cl_stdoutd, cl_stderrd

    
def startGmondDaemon(ganglia_ip):
    print 'Starting gmond daemons'
    usr = 'root'
    pwd = 'Ignition01'
    cmd = "clush -a service gmetad start"

    cl_stdoutd, cl_stderrd = Ssh.execute_command(ganglia_ip, usr, pwd, cmd)

    cmd = "service gmond start"
    cl_stdoutd, cl_stderrd = Ssh.execute_command(ganglia_ip, usr, pwd, cmd)
    
    return cl_stdoutd, cl_stderrd

def getWebServerStatus(ganglia_ip):
    print 'Getting webserver status'
    usr = 'root'
    pwd = 'DellCloud'
    cmd = "service httpd status"

    cl_stdoutd, cl_stderrd = Ssh.execute_command(ganglia_ip, usr, pwd, cmd)

    return cl_stdoutd, cl_stderrd


def startApacheWebServer(ganglia_ip):
    print 'Starting Apache webserver'
    usr = 'root'
    pwd = 'DellCloud'
    cmd = "apachectl start"

    cl_stdoutd, cl_stderrd = Ssh.execute_command(ganglia_ip, usr, pwd, cmd)
    
    return cl_stdoutd, cl_stderrd
    
def getGmetaDaemonStatus():
    print 'Checking Ganglia status'
    usr = 'root'
    pwd = 'DellCloud'
    cmd = "service gmetad status"

    cl_stdoutd, cl_stderrd = Ssh.execute_command(ganglia_ip, usr, pwd, cmd)

    return cl_stdoutd, cl_stderrd


def startGmetaDaemon():
    print 'Checking Ganglia status'
    usr = 'root'
    pwd = 'Ignition01'
    cmd = "service gmetad start"

    cl_stdoutd, cl_stderrd = Ssh.execute_command(ganglia_ip, usr, pwd, cmd)

    return cl_stdoutd, cl_stderrd

def getEpochServerTime(ip_address):
    
    usr = 'root'
    pwd = 'Ignition01'
    cmd = "date %s"

    epoch_time, cl_stderrd = Ssh.execute_command(ip_address, usr, pwd, cmd)
    
    return epoch_time
    

def edit_file(target, new_value, file):

    config = importlib.import_module('config_cdh5') 
    tpc_node_ip = config.tpc_node_ip
    usr = 'root'
    pwd = 'Ignition01'
    cmd = 'sed -i.bak s/'"^"+target+'=.*/'+target+'='+str(new_value)+'/g '+file

    #print "running: " + cmd
    Ssh.execute_command(tpc_node_ip, usr, pwd, cmd)


def check_disks(clean_up_ip):

    print 'Checking disks'
    usr = 'root'
    pwd = 'Ignition01'
    cmd = 'sudo -u hdfs hadoop fs -ls hdfs:///user/hdfs'

    cl_stdoutd, cl_stderrd = Ssh.execute_command(clean_up_ip, usr, pwd, cmd)
    if cl_stderrd != '':
        print 'Check disk error: ' +str(cl_stderrd)
        sys.exit()
    if cl_stdoutd == '':
        print 'No files to delete'

        return 0

    else:
        print 'Files found by disk check: ' + str(cl_stdoutd)

        return 1


def clear_disks(clean_up_ip):

    usr = 'root'
    pwd = 'Ignition01'
    if check_disks(clean_up_ip):
        #log(arch_file, "Clearing Disks")
        #clean_up_ip = '172.16.11.141'
        cmd = 'sudo -u hdfs hadoop fs -rm -R -f -skipTrash /user/hdfs/*'
        print "Running " + cmd 
        cl_stdoutd, cl_stderrd = Ssh.execute_command(clean_up_ip, usr, pwd, cmd)        
        print cl_stdoutd
        print cl_stderrd

        if cl_stderrd != '':
            print cl_stderrd
            sys.exit()

        return cl_stdoutd, cl_stderrd

    else:
        print 'skipping clear disks'

        return '', ''

def clear_cache(clean_up_ip):

    #log(arch_file, "Clearing cache")
    #clean_up_ip = '172.16.11.141'
    usr = 'root'
    pwd = 'Ignition01'

    cmd = 'clush -w r3s1xd[1-10] "sync"'
    cmd2 = 'clush -w r3s1xd[1-12] "echo 3> /proc/sys/vm/drop_caches"'

    print "Running " + cmd 
    syncOut, syncError = Ssh.execute_command(clean_up_ip, usr, pwd, cmd)
    #print 'syncOut' + str(syncOut)
    #print 'syncError' + str(syncError)
    if syncError != '':
        print 'sync error: ' + str(syncError)
        sys.exit()
    
    print "Running " + cmd2
    cl_stdoutd, cl_stderrd = Ssh.execute_command(clean_up_ip, usr, pwd, cmd2)
    
    print cl_stdoutd
    #print cl_stderrd
    if cl_stderrd != '':
        print 'Cache clearing error: ' + str(cl_stderrd)
        sys.exit()

    if cl_stdoutd == '':
        print 'Cache not cleared'
        sys.exit()

    #output =  re.search("Deleted ", cl_stdoutd)
    #print 'line: ' + str(output)

    return cl_stdoutd, cl_stderrd


def get_other_cpu_stats(timestamp, host):

    config = importlib.import_module('config_cdh5')
    cm_api_ip = config.cm_api_ip
    clustername = config.cluster_name
    offset = config.time_offset
    offset = 4
    cpu_stats = ('cpu_soft_irq_rate',
                 'cpu_iowait_rate',
                 'cpu_irq_rate',
                 'cpu_system_rate'
                 )

    session = ApiResource(cm_api_ip,  7180, "admin", "admin", version=5)
    data = []
    cpu_total = []

    numCores = get_datanode_cores(cm_api_ip, clustername, host)

    sec = timedelta(seconds=31)
    
    print 'In - get_other_cpu_stats: timestamp: ' +str(timestamp)

    time_start = timestamp-sec   # GMT +1
    time_end = timestamp+sec
    
    print time_start
    print time_end
    time_start = time_start-datetime.timedelta(hours=offset)
    time_end = time_end-datetime.timedelta(hours=offset)
    print '----------------'
    print time_start
    print time_end
    
    
    for stat in cpu_stats:
        tsquery = "select "+stat+" / "+str(numCores)+" * 100 where hostname = \""+ str(host) +"\" and category = Host"
        hostRes = session.query_timeseries(tsquery, time_start, time_end)

        for rez in hostRes[0].timeSeries:
            print rez.data
            for point in rez.data:
                print point.value
                cpu_total.append(point.value)
                data.append(dict({stat:point.value}))
                timestamp = point.timestamp
                print 'point.timestamp: ' + str(point.timestamp)
    total = 0
    for value in cpu_total:
        total = total+value
    
    #system.exit()
    return data, total


def getDataNodeHosts(cm_api_ip, clustername):

    hosts = []
    session = ApiResource(cm_api_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
       for each in host.roleRefs:
           if 'DATANODE' in  each.roleName :
               hosts.append(host.ipAddress)

    return hosts


def getDataNodeObjects(cm_api_ip, clustername):

    hosts = []
    objs = []
    session = ApiResource(cm_api_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
        for each in host.roleRefs:
            if 'DATANODE' in  each.roleName :
                hosts.append(host.ipAddress)
                objs.append(host)

    return objs, hosts


def getAllNodeObjects(cm_api_ip, clustername):

    objs = []
    session = ApiResource(cm_api_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
        objs.append(host)

    return objs


def getCPUCores(cm_api_ip, clustername):

    hostIPs = []
    cores = []
    objs = getAllNodeObjects(cm_api_ip, clustername)
    for each in objs:
        hostIPs.append(each.ipAddress)
        cores.append(each.numCores)

    return hostIPs, cores


def getAllNodeRoles(cm_api_ip, clustername):

    hosts = []
    objs = getAllNodeObjects(cm_api_ip, clustername)
    for each in objs:
        role_list = []
        for role in each.roleRefs:
            role_list.append(role.roleName)
        hosts.append({'host': each.ipAddress, 'role': role_list})

    return hosts


def get_datanode_entityname(cm_api_ip, clustername, ipAddress):

    hosts = []
    session = ApiResource(cm_api_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
        if ipAddress ==  host.ipAddress:
            return host.hostname

    return hosts    


def get_datanode_ip(cm_api_ip, clustername, hostname):

    hosts = []
    session = ApiResource(cm_api_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
        if hostname ==  host.hostname:
            return host.ipAddress

    return hosts   


def get_datanode_cores(cm_api_ip, clustername, hostname):

    hosts = []
    session = ApiResource(cm_api_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
        if host.hostname == hostname:
            return host.numCores

    return hosts

def prepare_cluster(name_node, secondary_nn):

    out1 = 'to-do'
    out2 = 'to-do'
    return out1, out2


def teragen_cmd(rowNumber, cmd):
    config = importlib.import_module('config_cdh5')
    hadoop_ip = config.hadoop_ip
    usr = 'root'
    pwd = 'Ignition01'
    cl_stdoutd, cl_stderrd = Ssh.execute_command(hadoop_ip, usr, pwd, cmd)
    #print cl_stdoutd
    #print cl_stderrd

    return cl_stdoutd, cl_stderrd

def teragen(rowNumber, folderName):
    '''
    note for this to work : 
    on the edge node : 
    bluepill chef-client stop
    sudo vi /etc/sudoers
    add :
    Defaults:root   !requiretty
    '''
    config = importlib.import_module('config_cdh5')
    hadoop_ip = config.hadoop_ip
    teragen_parameters = config.teragen_parameters
    teragen_jar_location = config.teragen_jar_location
    teragen_jar_filename = config.teragen_jar_filename

    usr = 'root'
    pwd = 'Ignition01'
    cmd = 'cd ' + teragen_jar_location + '/;sudo -u hdfs hadoop jar ' + teragen_jar_filename + ' teragen' + teragen_parameters + ' ' + str(rowNumber) +' '+ str(folderName)
    print "Running " + cmd
    debugLog(cmd)
    cl_stdoutd, cl_stderrd = Ssh.execute_command(hadoop_ip, usr, pwd, cmd)    
    #print cl_stdoutd
    #print cl_stderrd

    return cl_stdoutd, cl_stderrd

def terasort_output_folder(folderName, outFolder):

    destFolder = outFolder
    config = importlib.import_module('config_cdh5') 
    cm_api_ip = config.cm_api_ip
    terasort_parameters = config.terasort_parameters
    teragen_jar_location = config.teragen_jar_location
    teragen_jar_filename = config.teragen_jar_filename
    hadoop_ip = config.hadoop_ip
    usr = 'root'
    pwd = 'Ignition01'

    #cmd = 'cd /opt/cloudera/parcels/CDH-5.5.0-1.cdh5.5.0.p0.8/lib/hadoop-0.20-mapreduce/;sudo -u hdfs hadoop jar hadoop-examples-2.6.0-mr1-cdh5.5.0.jar terasort ' + terasort_params + ' '+ str(folderName) + ' ' + str(destFolder)
    cmd = 'cd ' + teragen_jar_location + '/;sudo -u hdfs hadoop jar ' + teragen_jar_filename + ' terasort ' + terasort_parameters + ' '+ str(folderName) + ' ' + str(destFolder)
    debugLog(cmd)
    print "Running " + cmd 
    cl_stdoutd, cl_stderrd = Ssh.execute_command(hadoop_ip, usr, pwd, cmd)
    #print cl_stdoutd
    #print cl_stderrd

    return cl_stdoutd, cl_stderrd

def terasort(folderName):

    destFolder = folderName + '_Sorted'
    config = importlib.import_module('config_cdh5') 
    cm_api_ip = config.cm_api_ip
    terasort_parameters = config.terasort_parameters
    teragen_jar_location = config.teragen_jar_location
    teragen_jar_filename = config.teragen_jar_filename
    hadoop_ip = config.hadoop_ip
    usr = 'root'
    pwd = 'Ignition01'

    #cmd = 'cd /opt/cloudera/parcels/CDH-5.5.0-1.cdh5.5.0.p0.8/lib/hadoop-0.20-mapreduce/;sudo -u hdfs hadoop jar hadoop-examples-2.6.0-mr1-cdh5.5.0.jar terasort ' + terasort_params + ' '+ str(folderName) + ' ' + str(destFolder)
    cmd = 'cd ' + teragen_jar_location + '/;sudo -u hdfs hadoop jar ' + teragen_jar_filename + ' terasort ' + terasort_parameters + ' '+ str(folderName) + ' ' + str(destFolder)
    debugLog(cmd)
    print "Running " + cmd 
    cl_stdoutd, cl_stderrd = Ssh.execute_command(hadoop_ip, usr, pwd, cmd)
    #print cl_stdoutd
    #print cl_stderrd

    return cl_stdoutd, cl_stderrd


def teravalidate(folderName):

    folderName = folderName + '_Sorted'
    destFolder = folderName + '_val'
    config = importlib.import_module('config_cdh5') 
    cm_api_ip = config.cm_api_ip
    teravalidate_parameters = config.teravalidate_parameters
    teragen_jar_location = config.teragen_jar_location
    teragen_jar_filename = config.teragen_jar_filename
    hadoop_ip = config.hadoop_ip
    usr = 'root'
    pwd = 'Ignition01'

    #cmd = 'cd /opt/cloudera/parcels/CDH-5.5.0-1.cdh5.5.0.p0.8/lib/hadoop-0.20-mapreduce/;sudo -u hdfs hadoop jar hadoop-examples-2.6.0-mr1-cdh5.5.0.jar terasort ' + terasort_params + ' '+ str(folderName) + ' ' + str(destFolder)
    cmd = 'cd ' + teragen_jar_location + '/;sudo -u hdfs hadoop jar ' + teragen_jar_filename + ' teravalidate ' + teravalidate_parameters + ' '+ str(folderName) + ' ' + str(destFolder)
    
    print "Running " + cmd 
    cl_stdoutd, cl_stderrd = Ssh.execute_command(hadoop_ip, usr, pwd, cmd)
    #print cl_stdoutd
    #print cl_stderrd

    return cl_stdoutd, cl_stderrd

def teravalidate_cmd(cmd):
    config = importlib.import_module('config_cdh5')
    hadoop_ip = config.hadoop_ip
    usr = 'root'
    pwd = 'Ignition01'
    cl_stdoutd, cl_stderrd = Ssh.execute_command(hadoop_ip, usr, pwd, cmd)
    #print cl_stdoutd
    #print cl_stderrd

    return cl_stdoutd, cl_stderrd

def tpc_benchmark(tpc_size):

    config = importlib.import_module('config_cdh5') 
    tpc_node_ip = config.tpc_node_ip
    tpc_location = config.tpc_location
    #print 'Running TPC Benchmark'
    cmd = 'cd '+str(tpc_location)+'; ./TPCx-HS-master.sh -g '+ tpc_size
    usr = 'root'
    pwd = 'Ignition01'
    cl_stdoutd, cl_stderrd = Ssh.execute_command(tpc_node_ip, usr, pwd, cmd)
    print cmd
    print 'TPC error: ' +str(cl_stderrd)
    print 'TPC output: ' + str(cl_stdoutd)

    return cl_stdoutd, cl_stderrd


def convertToSF(tpc_size):

    if tpc_size == '1':
        tpc_size = '100GB'
    elif tpc_size == '2':
        tpc_size = '300GB'
    elif tpc_size == '3':
        tpc_size = '1TB'
    elif tpc_size == '4':
        tpc_size = '3TB'
    elif tpc_size == '5':
        tpc_size = '10TB'
    elif tpc_size == '6':
        tpc_size = '30TB'
    elif tpc_size == '7':
        tpc_size = '100TB'
    elif tpc_size == '8':
        tpc_size = '300TB'
    elif tpc_size == '9':
        tpc_size = '1PB'

    return tpc_size

def jobLog(entry, printOutput=True):

    if printOutput:
        print entry
    f = open('jobLog.log','a')
    f.write(entry + "\n")
    f.close()

def debugLog(entry, printOutput=True):

    if printOutput:
        print entry
    f = open('debug.log','a')
    f.write(entry + "\n")
    f.close()

def log(file_name, entry, printOutput=True):

    if printOutput:
        print entry
    f = open('Results.log','a')
    f.write(entry + "\n")
    f.close()
    
    a = open(file_name, 'a')
    a.write(entry + "\n")
    a.close()
    return file_name

def createArch(file_name):
    file_name = 'ResultLogArch/Results_' + file_name + '_' + str(uuid.uuid4()) + '.log'
    a = open(file_name, 'w+')
    a.close()
    return file_name

def renameFile(old_name, new_name):
    print old_name
    print new_name
    old_name = old_name
    new_name = 'ResultLogArch/' + new_name
    os.rename(old_name, new_name)

def get_cloudera_dataNodesAverage(cm_api_ip, dataNodes, stat, time_start, time_end, cluster_name):
    config = importlib.import_module('config_cdh5')
    offset = config.time_offset
    offset = 4
    session = ApiResource(cm_api_ip, 7180, "admin", "admin", version=6)
    avg = 0.00
    DataNodesCount = 0
    
    highests = []
    highestCPU = 0
    cpu_avgs = 0
    timeAdj = datetime.timedelta(hours=offset)
    time_start = time_start-timeAdj
    #time_start = time_start-timeAdj
    time_end = time_end-timeAdj
    # add 60 seconds to the end time to allow for collecting stats for post-job processing that affects CPU usage.
    time_end = time_end + datetime.timedelta(seconds=30)

    for host in dataNodes:
        host = get_datanode_entityname(cm_api_ip, cluster_name, host)
        numCores = get_datanode_cores(cm_api_ip, cluster_name, host)
        #print numCores
        if stat == 'cpu_user_rate':
            tsquery = "select "+stat+" / "+str(numCores)+" *100 where hostname = \""+ host +"\" and category = Host"
        else:
            tsquery = "select "+stat+" where hostname = \""+ host +"\" and category = Host"
        data = []
        points = {}
        timestamps = []
        total = 0

        hostRes = session.query_timeseries(tsquery, time_start, time_end)
        for rez in hostRes[0].timeSeries:
            if (len(rez.data) > 0) :
                for point in rez.data:
                    data.append(point.value)
                    points.update(dict({point.value:point.timestamp}))          
            else :
                pass
        if len(data) > 0:
            highestValue = 0.00
            highestValue = sorted(data, key=float, reverse=True)[0]
            highestCPU = highestValue
            for key in sorted(points.iterkeys(), reverse=True):
                timestamps.append(points[key])
            avg = avg  + highestValue
            time.sleep(0)
            if highestValue != 0.00:
                highests.append(dict({host:highestValue}))
                DataNodesCount += 1
            else:
                timestamp = 0
                highests.append(dict({host:'0'}))
        else:
            highests.append(dict({host:'0'}))

        if stat == 'cpu_user_rate':
            print 'give me a break: ' + str(timestamps[0])
            time.sleep(0)
            other_cpu_stats, full_total = get_other_cpu_stats(timestamps[0], host)
            #log(arch_file, str(timestamps[0]))
            print timestamps
            cpu_total = full_total + highestCPU
            cpu_avgs = cpu_avgs + cpu_total
        else:
            cpu_avgs = 0

    if DataNodesCount == 0:
        return "0", [], [], 0
    return str(avg / DataNodesCount) , highests, timestamps[0], str(cpu_avgs/DataNodesCount)


def get_ganglia_datanodesAverage(dataNodes, stat, start_epoch, end_epoch, crowbar_admin_ip, time_offset):

        # Checking Ganglia stats
        DataNodesCount = 0
        avg = 0.00
        highests = []
	config = importlib.import_module('config_cdh5')
	edge_ip = config.edge_node_ip
	clustername = config.cluster_name
    #crowbar_admin_ip = "172.16.2.18"
        for host in dataNodes:
		entity = get_datanode_entityname(edge_ip, config.cluster_name, host)
                ganglia = rrdtoolXtract(start_epoch, end_epoch, stat, entity, edge_ip, time_offset)
                ls = ganglia[0].splitlines()
                bytes_in = []
                for each in ls:            
                    if ": " in each:
                        sp = each.split(': ')
                        f = float(str(sp[1]).strip())
                        bytes_in.append(f)
                if len(bytes_in) > 0:
                    highestValue = sorted(bytes_in, key=float, reverse=True)[0]
                    if f == 'nan':
                            highests.append(dict({host:'0'}))
                            continue
                    else:
                        DataNodesCount += 1
                        highests.append(dict({host:highestValue}))
                    avg = avg  + highestValue
                else:
                    highests.append(dict({host:'0'}))                   
        if DataNodesCount == 0:
            return "0", []
        return str(avg / DataNodesCount), highests


def rrdtoolXtract(start, end, metric, host, crowbar_admin_ip, time_offset):

    config = importlib.import_module('config_cdh5')
    location = config.ganglia_stat_locations
    time_offset = 5
    offset = time_offset*60*60
    start = start - offset
    end = end - offset
    usr = 'root'
    pwd = 'DellCloud'
    cmd = 'rrdtool fetch '+location + '' + str(host) + '/' + metric +'.rrd AVERAGE -s '+ str(start) +' -e ' + str(end)
    #print cmd
    #time.sleep(1)
    #log(arch_file, str(cmd))
    cl_stdoutd, cl_stderrd = Ssh.execute_command(crowbar_admin_ip, usr, pwd, cmd)
    return cl_stdoutd, cl_stderrd


def getJobStartFinishTimes(job_id, start_time, end_time):

    # get the job id between the given time range.
    # return the start and end times for that job.

    config = importlib.import_module('config_cdh5') 
    cm_api_ip = config.cm_api_ip
    session = ApiResource(cm_api_ip,  7180, "admin", "admin", version=6)
    
    #job_name = '' 
    #start = None
    #finish = None
    
    yarn_flag = False
    mapreduce_flag = False

    # Get the MapReduce2 job runtime from the job id
    cdh4 = None
    yarn_service = None
    mapreduce_service = None
    services = []

    for c in session.get_all_clusters():
        if c.version == "CDH5":
            cdh4 = c
    for s in cdh4.get_all_services():
        # print "s = " + str(s)
        if s.name == "yarn":
            yarn_flag = True
            services.append(dict({s.name:s}))
            yarn_service = s
            #service_list.append(s.name)
        if s.name == 'mapreduce':
            mapreduce_flag = True
            services.append(dict({s.name:s}))
            mapreduce_service = s
            #service_list.append(s.name)
        
    if (yarn_flag == True and mapreduce_flag == True) or (yarn_flag == True and mapreduce_flag == False):
        if yarn_flag == True and mapreduce_flag == True:
            print 'Mapreduce and Yarn both available, running YARN.'
        else:
            print 'Yarn available'
        ac =  yarn_service.get_yarn_applications(start_time, end_time)
        print start_time
        print end_time

        for job in ac.applications:
            print 'job_id: ' + str(job_id)
            print 'job_applicationID: ' + str(job.applicationId)
            if job_id == str(job.applicationId):
                ob = job
                print 'ob scope1: ' + str(ob)

                start = ob.startTime
                finish = ob.endTime
                job_name = ob.name

                jobLog(str(job_name) + ' ' +str(job_id) + ' ' + str(start) + ' ' + str(finish) )
                print job_name  
                print 'return'
                return job_name, start, finish

    elif yarn_flag == False and mapreduce_flag == True:
        print 'Run mapreduce - put mapreduce code here'

    else:
        print 'Neither Mapreduce or Yarn available'

        print '000000000000'
        #jobLog(str(job_name) + ' ' +str(job_id) + ' ' + str(start) + ' ' + str(finish) )

        return 0, 0, 0

def run_teragen_job(rowCount):

    randFolderName = str(uuid.uuid4())
    offset = datetime.timedelta(minutes=0)
    timeA = datetime.datetime.now()-offset
    bla = teragen(rowCount, randFolderName)
    time.sleep(90)
    ls = bla[1].split('\r' );
    for line in ls:
        #print "line: "+str(line)
        #ma =  re.search("Job complete: (.+)", line)
        ma =  re.search("Job (.+) complete", line)
        #print ma
        if ma:
            job_id = ma.group(1) 

    timeB = datetime.datetime.now()+offset
    job_name, start, finish = getJobStartFinishTimes(job_id, timeA, timeB)
    print job_name
    print start
    print finish
    return job_id, job_name, start, finish, randFolderName

def run_terasort_job(target_folder):
    offset = datetime.timedelta(minutes=0)
    timeA = datetime.datetime.now()-offset
    bla = terasort(target_folder)
    time.sleep(90)
    ls = bla[1].split('\r' );
    for line in ls:
        #print "line: "+str(line)
        #ma =  re.search("Job complete: (.+)", line)
        ma =  re.search("Job (.+) complete", line)
        #print ma
        if ma:
            job_id = ma.group(1) 

    timeB = datetime.datetime.now()+offset
    

    job_name, start, finish = getJobStartFinishTimes(job_id, timeA, timeB)

    return job_id, job_name, start, finish


def run_teravalidate_job(target_folder):

    offset = datetime.timedelta(minutes=0)
    timeA = datetime.datetime.now()-offset
    bla = teravalidate(target_folder)
    time.sleep(120)
    ls = bla[1].split('\r' );
    for line in ls:
        print "line: "+str(line)
        #ma =  re.search("Job complete: (.+)", line)
        ma =  re.search("Job (.+) completed successfully", line)
        #print ma
        if ma:
            job_id = ma.group(1) 
            result = str(job_id) + ' | Successfull.'
        else:
            result = ' | Error\n Teravalidate Output:\n' + str(ls)

    timeB = datetime.datetime.now()+offset

    job_name, start, finish = getJobStartFinishTimes(job_id, timeA, timeB)

    return result, job_id, job_name, start, finish


def run_tpc_benchmark(tpc_size):
    job_ids = []
    start_times = []
    finish_times = []
    job_names = []

    time_start = datetime.datetime.now()
    print time_start
    out1, out2 = tpc_benchmark(tpc_size)
    time.sleep(80)
    time_end = datetime.datetime.now()
    print time_end
    #job_ids =  re.findall("Job complete: (.+)", out1)
    job_ids =  re.findall("Job (.+) completed", out1)
    print "job_ids " +str(job_ids)
    #job_ids = {'job_1460938781401_0135'}
    for job in job_ids:
        print '&&&&' + str(job_ids)
        time_end = datetime.datetime.now()
        print time_end
        job_name, start, finish = getJobStartFinishTimes(job, time_start, time_end)
        print job_name
        print start
        print finish
        time.sleep(8)
        start_times.append(start)
        finish_times.append(finish)
        job_names.append(job_name)

    return job_ids, job_names, start_times, finish_times


def logStats(arch_file, job_type, data_nodes, start, finish, rowCount, start_epoch, finish_epoch):
    config = importlib.import_module('config_cdh5')
    datapointsToCheck = config.teragen_cloudera_stats
    ganglia_ip = config.ganglia_ip
    time_offset = config.time_offset
    cluster_name = config.cluster_name
    cm_api_ip = config.cm_api_ip

    
    for stat in datapointsToCheck:
        print 'getting ' + str(stat)
        total_cpu_avg = 0

        cluster_highest_average_cm, individualHostsHighestPoints, timestamp, cpu_total = get_cloudera_dataNodesAverage(cm_api_ip, data_nodes, stat, start, finish, cluster_name)
        print 'Timestamp from get_cloud_dnAverage(): ' + str(timestamp)
        if stat == 'cpu_user_rate':
            log(arch_file, job_type + " | Cloudera | " + str(rowCount) + " | average | CPU_Total | " + str(cpu_total) )

        log(arch_file, job_type + " | Cloudera | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_cm) )
        
        for host in individualHostsHighestPoints:
            host_name = host.items()[0][0]
            stat_value = host.items()[0][1]

            if stat == 'cpu_user_rate':
                log(arch_file, job_type + " | Cloudera | " + str(rowCount) + " | "+ str(host_name) +" | " + stat + " | " + str(stat_value) )
                #ResultsSummary.append([str(runId),
                #                       "terragen",
                #                       str(rowCount),
                #                       str(host.items()[0][0]),
                #                       str(stat),
                #                       str(host.items()[0][1])]
                #                      )
                print timestamp
                print host_name

                other_cpu_stats, full_total = get_other_cpu_stats(timestamp, host_name)
                print other_cpu_stats
                time.sleep(1)
                for each in other_cpu_stats:
                    cpu_stat = each.items()[0][0]
                    cpu_stat_value = each.items()[0][1]

                    log(arch_file, job_type + " | Cloudera | " + str(rowCount) + " | "+ str(host_name) +" | " + str(cpu_stat) + " | " + str(cpu_stat_value))

                log(arch_file, job_type + " | Cloudera | " + str(rowCount) + " | "+ str(host_name) +" | CPU Total | " + str(full_total + stat_value) )
                
            else:
                print 'logging stat: ' + str(stat)
                time.sleep(2)
                log(arch_file, job_type + " | Cloudera | " + str(rowCount) + " | "+ str(host_name) +" | " + stat + " | " + str(stat_value) )
                #ResultsSummary.append([str(runId),
                #                       "terragen",
                #                       str(rowCount),
                #                       str(host.items()[0][0]),
                #                       str(stat),
                #                       str(host.items()[0][1])]
                #                      )
                #log(arch_file, "terragen | " + str(rowCount) + " | cpu_total | " + str(cpu_total) )

    ganglia_stats = config.teragen_ganglia_stats

    #print( "[Getting ganglia stats]")
    print "------ Ganglia Stats ! ------ "
    for stat in ganglia_stats:
        cluster_highest_average_ganglia, individualHostsHighestPoints = get_ganglia_datanodesAverage(data_nodes, stat, start_epoch, finish_epoch, ganglia_ip, time_offset)
       
        log(arch_file, job_type + " | Ganglia  | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_ganglia) )
        #ResultsSummary.append([str(runId),
        #                       "terragen",
        #                      str(rowCount),
        #                      "average",
        #                      str(stat),
        #                      str(cluster_highest_average_ganglia)])
        for host in individualHostsHighestPoints:
            host_name = get_datanode_entityname(cm_api_ip, cluster_name, host.items()[0][0])
            stat_value = host.items()[0][1]
            log(arch_file, job_type + " | Ganglia  | " + str(rowCount) + " | "+ str(host_name) +" | " + stat + " | " + str(stat_value) )
        #    ResultsSummary.append([str(runId),
        #                           "terragen",
        #                          str(rowCount),
        #                          str(host.items()[0][0]),
        #                          str(stat),
        #                          str(host.items()[0][1])]                                      
        #                          )

def main():

    '''
    on the edge node : 
    sudo vi /etc/sudoers
    add :
    Defaults:root   !requiretty
    '''
    config = importlib.import_module('config_cdh5') 

    hadoop_ip = config.hadoop_ip
    run_id = config.run_id
    cm_api_ip = config.cm_api_ip
    clean_up_ip = config.clean_up_ip
    cluster_name = config.cluster_name

    ganglia_ip = config.ganglia_ip
    time_offset = config.time_offset


    data_nodes = getDataNodeHosts(cm_api_ip, cluster_name)
    hostObjs, dataHostIPs = getDataNodeObjects(cm_api_ip, cluster_name)
    hosts = getAllNodeRoles(cm_api_ip, cluster_name)

    runId = str(datetime.datetime.now()) + "__" + config.run_id
    file_name = convertToSF(config.tpc_size)
    arch_file = createArch(file_name)
    log(arch_file, "------------[[["+str(run_id) + "]]]------------------------------")


    rowCountsBatchValues = config.teragen_row_counts
    datapointsToCheck = config.teragen_cloudera_stats
    teragen_params = config.teragen_parameters
    teragen_jar_location = config.teragen_jar_location
    teragen_jar_filename = config.teragen_jar_filename

    #out1, out2 = clear_disks(clean_up_ip)
    #out1, out2 = clear_disks(clean_up_ip)
    #print out1
    #out1, out2 = clear_cache(clean_up_ip)
    #time.sleep(150)
    
    API = ApiResource(cm_api_ip,  7180, "admin", "admin", version=5)
    
    stamp = ConfigStamp()
    print "Connected to CM host on " + cm_api_ip

    CLUSTER = API.get_cluster(cluster_name)
    stamp.updateConfig(CLUSTER)
    stamp.restartCluster(CLUSTER)
    time.sleep(10)
    log(arch_file, "[[[ Teragen tests ]]]")

    for rowCount in rowCountsBatchValues:
        log(arch_file, "[[ Teragen Row Count Cycle  " + str(rowCount)   + "]]")
        ResultsSummary = []
        job_type = 'Teragen'
        
        jobID, job_name, start, finish, teragenFolder = run_teragen_job(rowCount)
        time.sleep(10)
        start_epoch = int(time.mktime(start.timetuple()))
        finish_epoch = int(time.mktime(finish.timetuple()))
        log(arch_file, str(start_epoch))
        log(arch_file, str(finish_epoch))

        runTime_epoch = finish_epoch - start_epoch
        run_time = finish - start

        runTime = (finish - start).total_seconds()
        '''
        secs = ''
        mins = ''
        hrs = ''

        if runTime > 3600:
            h = int(runTime/3600)
            m = int((runTime%3600)/60)
            s = m%60
            if s == 1:
                secs = 'second'
            else:
                secs = 'seconds'
            if m == 1:
                mins = 'minute'
            else:
                mins = 'minutes'
            if h == 1:
                hrs = 'hour'
            else:
                hrs = 'hours'
            r_time = str(h) + ':' + str(m) + ' ' + mins + ', ' + str(s) + ' ' + secs

        elif runTime > 60:
            m = (int(runTime)/60)
            s = runTime%60
            if s == 1:
                secs = 'second'
            else:
                secs = 'seconds'
            if m == 1:
                mins = 'minute'
            else:
                mins = 'minutes'
            
            r_time = str(m) + ' ' + mins + ', ' + str(s) + ' ' + secs
        else:
            if runTime == 1:
                secs = 'second'
            else:
                secs = 'seconds'
            r_time = str(runTime) + ' ' + secs

        '''
        log(arch_file, "Getting teragen stats for JobID: " + str(jobID))
        log(arch_file, job_name + " | Cloudera | " + str(rowCount) + " | job | runtime | " + str(run_time) + ' ('+ str(runTime) +' seconds)')
        logStats(arch_file, job_type, data_nodes, start, finish, rowCount, start_epoch, finish_epoch)
        
        job_type = 'Terasort'
        log(arch_file,  "[[ Terasort Row Count Cycle  " + str(rowCount)   + "]]")

        jobID, job_name, start, finish = run_terasort_job(teragenFolder)
        report_job_id = jobID
        log(arch_file, "Getting terasort stats for JobID: " + str(jobID))

        run_time = finish - start

        runTime = (finish - start).total_seconds()

        start_epoch = int(time.mktime(start.timetuple()))
        finish_epoch = int(time.mktime(finish.timetuple()))

        #runTime = finish_epoch - start_epoch
        log(arch_file, job_name + " | Cloudera | " + str(rowCount) + " | job | runtime | " + str(run_time) + ' ('+ str(runTime) +' seconds)')
        logStats(arch_file, job_type, data_nodes, start, finish, rowCount, start_epoch, finish_epoch)

        job_type = 'Teravalidate'
        log(arch_file,  "[[ Teravalidate Row Count Cycle  " + str(rowCount)   + "]]")
        result, jobID, job_name, start, finish = run_teravalidate_job(teragenFolder)
        log(arch_file, job_type + ' | result | ' + str(result))
        log(arch_file, "Getting teravalidate stats for JobID: " + str(jobID))
        
        run_time = finish - start

        runTime = (finish - start).total_seconds()

        start_epoch = int(time.mktime(start.timetuple()))
        finish_epoch = int(time.mktime(finish.timetuple()))

        log(arch_file, job_name + " | Cloudera | " + str(rowCount) + " | job | runtime | " + str(run_time) + ' ('+ str(runTime) +' seconds)')
        logStats(arch_file, job_type, data_nodes, start, finish, rowCount, start_epoch, finish_epoch)

    job_type = 'TPC'
    tpc_size = config.tpc_size

    num_maps = config.NUM_MAPS
    num_reducers = config.NUM_REDUCERS
    hadoop_user = config.HADOOP_USER
    hdfs_user = config.HDFS_USER
    sleep_between_runs = config.SLEEP_BETWEEN_RUNS
    file = config.tpc_location +'/Benchmark_Parameters.sh'

    
    if config.tpc_flag == 'true':
        print 'Updating TPC config file'
        #print file

        edit_file('NUM_MAPS', num_maps, file)
        edit_file('NUM_REDUCERS', num_reducers, file)
        edit_file('HADOOP_USER', hadoop_user, file)
        edit_file('HDFS_USER', hdfs_user, file)
        edit_file('SLEEP_BETWEEN_RUNS', sleep_between_runs, file)

        #################### TPC Benchmark###########################
        log(arch_file, "[[[Running TPC Benchmark]]")


        job_ids, job_names, starts, finishs = run_tpc_benchmark(tpc_size)
        print job_ids
        print '***********'
        for job in job_ids:
            start = starts[job_ids.index(job)]
            finish = finishs[job_ids.index(job)]
            job_name = 'TPC-' + str(job_names[job_ids.index(job)])

            start_epoch = int(time.mktime(start.timetuple()))
            finish_epoch = int(time.mktime(finish.timetuple()))
            #runTime = finish_epoch - start_epoch
            run_time = finish - start

            runTime = (finish - start).total_seconds()

            tpc_size = convertToSF(tpc_size)

            log(arch_file, 'Getting TPC-' + job_name + 'stats for JobID: ' + str(job))
            log(arch_file, job_name + " | Cloudera | " + str(tpc_size) + " | job | runtime | " + str(run_time) + ' ('+ str(runTime) +' seconds)')
            logStats(arch_file, job_name, data_nodes, start, finish, tpc_size, start_epoch, finish_epoch)

            if job_ids.index(job) == 2:
                log(arch_file, '**********  end of run one   ***********')

        print job_ids
        report_job_id = job_ids[1]
        print "\nTPC RUN COMPLETE\n"
        print "TPC run complete, here is config info set for the run: "
        print "NUM_MAPS: "+ num_maps
        print "NUM_REDUCERS: "+ num_reducers
        print "HADOOP_USER: "+hadoop_user
        print "HDFS_USER: " +hdfs_user
        print "SLEEP_BETWEEN_RUNS: " +sleep_between_runs
    else:
        print "TPC not running, flag set to: " + config.tpc_flag


    file_name = log(arch_file,  "[[[ That's all folks ]]]"  )

    if config.tpc_flag == 'true':
        scale_factor = convertToSF(tpc_size)
        # Rename and index the last Archive log for this run
        target_file = '-' + convertToSF(config.tpc_size)
        id_list = []
        for filename in os.listdir("ResultLogArch/."):
            if target_file in filename:
                file_id = re.search("Results" + target_file + " T(.+).log", filename)
                id_list.append(file_id.group(1))
            else:
                file_id = 0
                id_list.append(file_id)

        highestValue = 0
        highestValue = sorted(id_list, key=float, reverse=True)[0]
        new_id = int(highestValue) + 1
        new_file_name = "Results" + target_file + " T" + str(new_id) + ".log"
        renameFile(file_name, new_file_name)
    else:
        scale_factor = convertToSF(config.teragen_row_counts[0])
        # Rename and index the last Archive log for this run
        target_file = '-' + str(config.teragen_row_counts[0])
        id_list = []
        print target_file
        for filename in os.listdir("ResultLogArch/."):
            #print filename
            if target_file in filename:
                #print target_file
                #print filename
                file_id = re.search("Results" + target_file + " T(.+).log", filename)
                if file_id:
                    #print 'found: ' + str(file_id.group(1))
                    id_list.append(file_id.group(1))
                    #print id_list
            else:
                file_id = 0
                id_list.append(file_id)

        highestValue = 0
        highestValue = sorted(id_list, key=float, reverse=True)[0]
        new_id = int(highestValue) + 1
        new_file_name = "Results" + target_file + " T" + str(new_id) + ".log"
        renameFile(file_name, new_file_name)

    # create a copy of the renamed file from the archive and put it in the working directory.
    src = 'ResultLogArch/' + str(new_file_name)
    dst = new_file_name
    copyfile(src, dst)    
    #job_id = report_job_id
    results_file = new_file_name

    # generate a report based on the output from the job run above.
    bob = ReportBuilder()
    #report_job_id = 'job_1460938781401_0023'
    #results_file = 'Results-300000000000 T7.log'
    # scale_factor = convertToSF(tpc_size)
    
    print report_job_id
    print results_file
    print scale_factor

    bob.createReport(report_job_id, results_file, scale_factor)
    
if __name__ == '__main__':
    main()
    

    
