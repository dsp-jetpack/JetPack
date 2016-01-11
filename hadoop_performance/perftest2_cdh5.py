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


def edit_file(target, new_value, file):
    config = importlib.import_module('config_cdh5') 
    tpc_node_ip = config.tpc_node_ip
    myScp = Scp()
    usr = 'root'
    pwd = 'Ignition01'

    cmd = 'sed -i.bak s/'"^"+target+'=.*/'+target+'='+str(new_value)+'/g '+file

    #print "running: " + cmd
    Ssh.execute_command(tpc_node_ip, usr, pwd, cmd)


def get_other_cpu_stats(timestamp, host):
    config = importlib.import_module('config_cdh5')
    cm_api_ip = config.cm_api_ip
    clustername = config.cluster_name

    cpu_stats = ('cpu_soft_irq_rate',
                 'cpu_iowait_rate',
                 'cpu_irq_rate',
                 'cpu_system_rate'
                 )

    session = ApiResource(cm_api_ip,  7180, "admin", "admin", version=5)
    data = []
    cpu_total = []

    numCores = get_datanode_cores(cm_api_ip, clustername, host)

    sec = timedelta(seconds=10)

    time_start = timestamp-sec   # GMT +1
    time_end = timestamp+sec

    time_start = time_start-datetime.timedelta(hours=6)
    time_end = time_end-datetime.timedelta(hours=6)

    for stat in cpu_stats:
        tsquery = "select "+stat+" / "+str(numCores)+" * 100 where hostname = \""+ str(host) +"\" and category = Host"
        hostRes = session.query_timeseries(tsquery, time_start, time_end)

        for rez in hostRes[0].timeSeries:
            for point in rez.data:
                cpu_total.append(point.value)
                data.append(dict({stat:point.value}))
                timestamp = point.timestamp
    total = 0
    for value in cpu_total:
        total = total+value

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
    cmd = 'cd ' + teragen_jar_location + '/;sudo -u hdfs hadoop jar ' + teragen_jar_filename + ' teragen ' + teragen_parameters + ' ' + str(rowNumber) +' '+ str(folderName)
    print "running " + cmd
    cl_stdoutd, cl_stderrd = Ssh.execute_command(hadoop_ip, usr, pwd, cmd)    
    print cl_stdoutd
    print cl_stderrd
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
    
    print "running " + cmd 
    cl_stdoutd, cl_stderrd = Ssh.execute_command(hadoop_ip, usr, pwd, cmd)
    print cl_stdoutd
    print cl_stderrd
    return cl_stdoutd, cl_stderrd


def tpc_benchmark(tpc_size):
    config = importlib.import_module('config_cdh5') 
    tpc_node_ip = config.tpc_node_ip
    tpc_location = config.tpc_location
    print 'running TPC Benchmark'
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

def log(entry, printOutput=True):
    if printOutput:
        print entry
    f = open('Results.log','a')
    f.write(entry + "\n")
    f.close()


def get_cloudera_dataNodesAverage(cm_api_ip, dataNodes, stat, time_start, time_end, cluster_name):
    session = ApiResource(cm_api_ip, 7180, "admin", "admin", version=6)
    avg = 0.00
    DataNodesCount = 0
    
    highests = []
    highestCPU = 0
    cpu_avgs = 0
    timeAdj = datetime.timedelta(hours=6)
    time_start = time_start-timeAdj
    time_end = time_end-timeAdj
    # add 60 seconds to the end time to allow for collecting stats for post-job processing that affects CPU usage.
    time_end = time_end + datetime.timedelta(seconds=60)

    for host in dataNodes:
        host = get_datanode_entityname(cm_api_ip, cluster_name, host)
        numCores = get_datanode_cores(cm_api_ip, cluster_name, host)
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
            if highestValue != 0.00:
                highests.append(dict({host:highestValue}))
                DataNodesCount += 1
            else:
                timestamp = 0
                highests.append(dict({host:'0'}))
        else:
            highests.append(dict({host:'0'}))

        if stat == 'cpu_user_rate':
            other_cpu_stats, full_total = get_other_cpu_stats(timestamps[0], host)
            #log(str(timestamps[0]))
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
    offset = time_offset*60*60
    start = start - offset
    end = end - offset
    usr = 'root'
    pwd = 'DellCloud'
    cmd = 'rrdtool fetch '+location + '' + str(host) + '/' + metric +'.rrd AVERAGE -s '+ str(start) +' -e ' + str(end) 
    #log(str(cmd))
    cl_stdoutd, cl_stderrd = Ssh.execute_command(crowbar_admin_ip, usr, pwd, cmd)
    return cl_stdoutd, cl_stderrd

def getYarnJobStartFinishTimes(job_id, start_time, end_time):
    # get the job id between the given time range.
    # return the start and end times for that job.

    config = importlib.import_module('config_cdh5') 
    cm_api_ip = config.cm_api_ip
    session = ApiResource(cm_api_ip,  7180, "admin", "admin", version=6)
        # Get the MapReduce2 job runtime from the job id
    cdh4 = None
    for c in session.get_all_clusters():
        if c.version == "CDH5":
            cdh4 = c
    for s in cdh4.get_all_services():
        #print "s = " + str(s)
        slist = []
        if s.name == "yarn":
            mapreduce = s
            ac =  mapreduce.get_yarn_applications(start_time, end_time)
            for job in ac.applications:
                if job_id == str(job.applicationId):
                    ob = job
            start = ob.startTime
            finish = ob.endTime
            job_name = ob.name

    return job_name, start, finish


def run_teragen_job(rowCount):
    randFolderName = str(uuid.uuid4())
    timeA = datetime.datetime.now()
    bla = teragen(rowCount, randFolderName)
    time.sleep(60)
    ls = bla[1].split('\r' );
    for line in ls:
        #print "line: "+str(line)
        #ma =  re.search("Job complete: (.+)", line)
        ma =  re.search("Job (.+) complete", line)
        #print ma
        if ma:
            job_id = ma.group(1) 

    timeB = datetime.datetime.now()
    job_name, start, finish = getYarnJobStartFinishTimes(job_id, timeA, timeB)

    return job_id, job_name, start, finish, randFolderName

def run_terasort_job(target_folder):
    timeA = datetime.datetime.now()
    bla = terasort(target_folder)
    time.sleep(60)
    ls = bla[1].split('\r' );
    for line in ls:
        print "line: "+str(line)
        #ma =  re.search("Job complete: (.+)", line)
        ma =  re.search("Job (.+) complete", line)
        #print ma
        if ma:
            job_id = ma.group(1) 

    timeB = datetime.datetime.now()

    job_name, start, finish = getYarnJobStartFinishTimes(job_id, timeA, timeB)

    return job_id, job_name, start, finish

def run_tpc_benchmark(tpc_size):
    job_ids = []
    start_times = []
    finish_times = []
    job_names = []

    time_start = datetime.datetime.now()
    out1, out2 = tpc_benchmark(tpc_size)
    time.sleep(80)
    time_end= datetime.datetime.now()

    #job_ids =  re.findall("Job complete: (.+)", out1)
    job_ids =  re.findall("Job (.+) completed", out1)
    print "job_ids " +str(job_ids)
    
    for job in job_ids:
        job_name, start, finish = getYarnJobStartFinishTimes(job, time_start, time_end)

        start_times.append(start)
        finish_times.append(finish)
        job_names.append(job_name)

    return job_ids, job_names, start_times, finish_times


def logStats(job_type, data_nodes, start, finish, rowCount, start_epoch, finish_epoch):
    config = importlib.import_module('config_cdh5')
    datapointsToCheck = config.teragen_cloudera_stats
    ganglia_ip = config.ganglia_ip
    time_offset = config.time_offset
    cluster_name = config.cluster_name
    cm_api_ip = config.cm_api_ip

    for stat in datapointsToCheck:
        total_cpu_avg = 0

        cluster_highest_average_cm, individualHostsHighestPoints, timestamp, cpu_total = get_cloudera_dataNodesAverage(cm_api_ip, data_nodes, stat, start, finish, cluster_name)
        if stat == 'cpu_user_rate':
            log(job_type + " | " + str(rowCount) + " | average | CPU_Total | " + str(cpu_total) )

        log(job_type + " | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_cm) )
        
        for host in individualHostsHighestPoints:
            host_name = host.items()[0][0]
            stat_value = host.items()[0][1]

            if stat == 'cpu_user_rate':
                log(job_type + " | " + str(rowCount) + " | "+ str(host_name) +" | " + stat + " | " + str(stat_value) )
                #ResultsSummary.append([str(runId),
                #                       "terragen",
                #                       str(rowCount),
                #                       str(host.items()[0][0]),
                #                       str(stat),
                #                       str(host.items()[0][1])]
                #                      )

                other_cpu_stats, full_total = get_other_cpu_stats(timestamp, host_name)

                for each in other_cpu_stats:
                    cpu_stat = each.items()[0][0]
                    cpu_stat_value = each.items()[0][1]

                    log(job_type + " | " + str(rowCount) + " | "+ str(host_name) +" | " + str(cpu_stat) + " | " + str(cpu_stat_value))

                log(job_type + " | " + str(rowCount) + " | "+ str(host_name) +" | CPU Total | " + str(full_total + stat_value) )
                
            else:
                log(job_type + " | " + str(rowCount) + " | "+ str(host_name) +" | " + stat + " | " + str(stat_value) )
                #ResultsSummary.append([str(runId),
                #                       "terragen",
                #                       str(rowCount),
                #                       str(host.items()[0][0]),
                #                       str(stat),
                #                       str(host.items()[0][1])]
                #                      )
                #log("terragen | " + str(rowCount) + " | cpu_total | " + str(cpu_total) )

    ganglia_stats = config.teragen_ganglia_stats

    #print( "[Getting ganglia stats]")
    print "------ Ganglia Stats ! ------ "
    for stat in ganglia_stats:
        cluster_highest_average_ganglia, individualHostsHighestPoints = get_ganglia_datanodesAverage(data_nodes, stat, start_epoch, finish_epoch, ganglia_ip, time_offset)
       
        log(job_type + " | ganglia | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_ganglia) )
        #ResultsSummary.append([str(runId),
        #                       "terragen",
        #                      str(rowCount),
        #                      "average",
        #                      str(stat),
        #                      str(cluster_highest_average_ganglia)])
        for host in individualHostsHighestPoints:
            host_name = get_datanode_entityname(cm_api_ip, cluster_name, host.items()[0][0])
            stat_value = host.items()[0][1]
            log(job_type + " | ganglia | " + str(rowCount) + " | "+ str(host_name) +" | " + stat + " | " + str(stat_value) )
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
    log("------------[[["+str(run_id) + "]]]------------------------------")

    rowCountsBatchValues = config.teragen_row_counts
    datapointsToCheck = config.teragen_cloudera_stats
    teragen_params = config.teragen_parameters
    teragen_jar_location = config.teragen_jar_location
    teragen_jar_filename = config.teragen_jar_filename

    for rowCount in rowCountsBatchValues:
        log( "[[ Teragen Row Count Cycle  " + str(rowCount)   + "]]")
        ResultsSummary = []
        job_type = 'Teragen'
        
        jobID, job_name, start, finish, teragenFolder = run_teragen_job(rowCount)
        
        start_epoch = int(time.mktime(start.timetuple()))
        finish_epoch = int(time.mktime(finish.timetuple()))
        runTime = finish_epoch - start_epoch

        log("getting teragen stats for JobID: " + str(jobID))
        log(job_name + " | " + str(rowCount) + " | job | runtime | " + str(runTime ))
        logStats(job_type, data_nodes, start, finish, rowCount, start_epoch, finish_epoch)

        job_type = 'Terasort'
        log( "[[ Terasort Row Count Cycle  " + str(rowCount)   + "]]")

        jobID, job_name, start, finish = run_terasort_job(teragenFolder)
        log("getting terasort stats for JobID: " + str(jobID))

        start_epoch = int(time.mktime(start.timetuple()))
        finish_epoch = int(time.mktime(finish.timetuple()))

        runTime = finish_epoch - start_epoch
        log(job_name + " | " + str(rowCount) + " | job | runtime | " + str(runTime ))
        logStats(job_type, data_nodes, start, finish, rowCount, start_epoch, finish_epoch)

    job_type = 'TPC'
    tpc_size = config.tpc_size

    num_maps = config.NUM_MAPS
    num_reducers = config.NUM_REDUCERS
    hadoop_user = config.HADOOP_USER
    hdfs_user = config.HDFS_USER
    sleep_between_runs = config.SLEEP_BETWEEN_RUNS
    file = config.tpc_location +'/Benchmark_Parameters.sh'

    
    if config.tpc_flag == 'true':
        print 'updating config file'
        #print file

        edit_file('NUM_MAPS', num_maps, file)
        edit_file('NUM_REDUCERS', num_reducers, file)
        edit_file('HADOOP_USER', hadoop_user, file)
        edit_file('HDFS_USER', hdfs_user, file)
        edit_file('SLEEP_BETWEEN_RUNS', sleep_between_runs, file)

        #################### TPC Benchmark###########################
        log("[[[Running TPC Benchmark]]")


        job_ids, job_names, starts, finishs = run_tpc_benchmark(tpc_size)
        for job in job_ids:
            start = starts[job_ids.index(job)]
            finish = finishs[job_ids.index(job)]
            job_name = job_names[job_ids.index(job)]

            start_epoch = int(time.mktime(start.timetuple()))
            finish_epoch = int(time.mktime(finish.timetuple()))
            runTime = finish_epoch - start_epoch
            
            tpc_size = convertToSF(tpc_size)

            log("getting TPC stats for JobID: " + str(job))
            log('TPC- ' + job_name + " | " + str(tpc_size) + " | job | runtime | " + str(runTime ))
            logStats(job_name, data_nodes, start, finish, tpc_size, start_epoch, finish_epoch)

        print job_ids
        print "\nTPC RUN COMPLETE\n"
        print "TPC run complete, here is config info set for the run: "
        print "NUM_MAPS: "+ num_maps
        print "NUM_REDUCERS: "+ num_reducers
        print "HADOOP_USER: "+hadoop_user
        print "HDFS_USER: " +hdfs_user
        print "SLEEP_BETWEEN_RUNS: " +sleep_between_runs
    else:
        print "TPC not running, flag set to: " + config.tpc_flag


    log( "[[[ That's all folks ]]]"  )

if __name__ == '__main__':
    main()
    

    
