import time, calendar, re, uuid,  importlib, datetime,  subprocess, paramiko, sys, os, requests, logging
from cm_api.api_client import ApiResource
import dateutil.parser
from datetime import timedelta
#from datetime import *
#from auto_common import shh
#from auto_common import *
class Scp():

    def __init(self):

        self.client = paramiko.SSHClient()

        self.client.load_system_host_keys()

        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def open_remote_file(self, address, file):
        output = []
        trans = paramiko.Transport((address, 22))
        trans.connect(username = 'root', password = 'cr0wBar!')
        sftp = paramiko.SFTPClient.from_transport(trans)
        remote_file = sftp.open(file)
        try:
          for line in remote_file:
            print line
            output.append(line)
                
        finally:
          remote_file.close()

        return output
        
    def put_file(self, address, localfile, remotefile):
        trans = paramiko.Transport((address, 22))

        trans.connect(username = 'root', password = 'cr0wBar!')

        sftp = paramiko.SFTPClient.from_transport(trans)
        sftp.put(localfile, remotefile)
        
        sftp.close()

        trans.close()

def edit_file(target, new_value, file):
    config = importlib.import_module('config_cdh5') 
    tpc_ip = config.tpc_ip
    myScp = Scp()
    #open the config file
    output = myScp.open_remote_file(tpc_ip, file)
    
    scon = ssh()
    scon.connect_with_user(tpc_ip, 'root', 'Ignition01')
    #hold the current value of the variable to build the sed string
    current_value = ''
    #go through each line of the config and find the live and commented variables
    for line in output:        
        config_variable = re.findall("^"+target+"=(.+)", line)
        #if you find a uncommented variable, build the sed command to change the values
        if config_variable:
            current_value = config_variable[0]
            cmd = 'sed -i.bak s/^'+target+'='+str(current_value)+'/'+target+'='+str(new_value)+'/g '+file

            print "running: " + cmd
            cl_stdoutd, cl_stderrd = c_ssh_as_root(tpc_ip, cmd)

    #print cl_stdoutd
    #print cl_stderrd
    #return cl_stdoutd, cl_stderrd

def c_ssh_as_root(address, command):
    scon = ssh()
    scon.connect_with_user(address, 'root', 'Ignition01')
    cl_stdoutd, cl_stderrd = scon.action(command)
    #print cl_stderrd
    #print cl_stdoutd
    scon.close()
    return cl_stdoutd, cl_stderrd

def c_ssh_as_root_DellCloud(address, command):
    scon = ssh()
    scon.connect_with_user(address, 'root', 'DellCloud')
    cl_stdoutd, cl_stderrd = scon.action(command)
    #print cl_stderrd
    #print cl_stdoutd
    scon.close()
    return cl_stdoutd, cl_stderrd

def c_ssh_as_root_ignition(address, command):
    scon = ssh()
    scon.connect_with_user(address, 'root', 'Ignition01')
    cl_stdoutd, cl_stderrd = scon.action(command)
    #print cl_stderrd
    #print cl_stdoutd
    scon.close()
    return cl_stdoutd, cl_stderrd

class ssh():

    def __init__(self):
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 

    def connect(self,address):
        os = sys.platform
        if "win" in os :
            retstr= subprocess.check_output("del %HOMEPATH%\\.ssh\\known_hosts",stderr=subprocess.STDOUT, shell=True)
        elif "linux" in os:
            retstr= subprocess.check_output("ssh-keygen -R " + address,stderr=subprocess.STDOUT, shell=True)
        self.connect_with_user(address, 'crowbar', 'cr0wBar!')
    
    def connect_with_user(self, address, usr, pwd):
        self.address = address
        self.client.connect(self.address, username=usr, password=pwd)

    def action(self, command):
        stdin, ss_stdout, ss_stderr = self.client.exec_command(command)
        return ss_stdout.read(), ss_stderr.read()

    def close(self):
        self.client.close()  

def upload_results(ResultsSummary):
    try:
        os.remove('upload.log')
    except OSError:
        pass
    try:
        f = open('upload.log','a')
    except Exception, e:
        logging.exception(e)
        log(e)

    for res in ResultsSummary:
        ptr = ""
        for i in range(0, len(res)):
            ptr = ptr + "|" + str(res[i])
        print ptr
        f.write( ptr + "\n")
    f.close()     
    
    #upload the above 
    url = 'http://10.21.255.226/performance_result.php'
    files = {'file': open('upload.log', 'rb')}
    r = requests.post(url, files=files)

def convert_to_utc(time):
    #print 'time: '+ str(time)
    log('time: '+ str(time))
    os_time = datetime.datetime.now()
    #print 'os time: '+str(os_time)
    log('os time: '+str(os_time))
    utc_time = datetime.datetime.utcnow()
    #print 'utc_time: '+str(utc_time)
    log('utc_time: '+str(utc_time))
    diff = os_time - utc_time
    log('diff: ' +str(diff))

    time = time + diff
    log('time: ' + str(time))
    return time

def check_disks(name_node_ip):
    print 'checking disks'
    cmd2 = 'sudo -u hdfs hadoop fs -ls hdfs:///user/hdfs'
    cl_stdoutd, cl_stderrd = c_ssh_as_root(name_node_ip, cmd2)
    if cl_stderrd != '':
        print 'check disk error: ' +str(cl_stderrd)
        sys.exit()
    if cl_stdoutd == '':
        print 'no files to delete'
        return 0
    else:
        print 'Files found by disk check: ' + str(cl_stdoutd)
        return 1

def clear_disks(name_node_ip):
    if check_disks(name_node_ip):
        log("Clearing Disks")
        #name_node_ip = '172.16.11.141'
        cmd = 'sudo -u hdfs hadoop fs -rm -R -f -skipTrash /user/hdfs/*'
        print "running " + cmd 
        cl_stdoutd, cl_stderrd = c_ssh_as_root(name_node_ip, cmd)        
        print cl_stdoutd
        print cl_stderrd

        if cl_stderrd != '':
            print cl_stderrd
            sys.exit()
        return cl_stdoutd, cl_stderrd
    else:
        print 'skipping clear disks'
        return '', ''

def clear_cache(name_node_ip):
    log("Clearing cache")
    #name_node_ip = '172.16.11.141'
    cmd = 'clush -w r3s1xd[1-10] "sync"'
    cmd2 = 'clush -w r3s1xd[1-12] "echo 3> /proc/sys/vm/drop_caches"'
    print "running " + cmd 
    syncOut, syncError = c_ssh_as_root(name_node_ip, cmd)
    #print 'syncOut' + str(syncOut)
    #print 'syncError' + str(syncError)
    if syncError != '':
        print 'sync error: ' + str(syncError)
        sys.exit()
    
    print "running " + cmd2
    cl_stdoutd, cl_stderrd = c_ssh_as_root(name_node_ip, cmd2)
    
    print cl_stdoutd
    #print cl_stderrd
    if cl_stderrd != '':
        print 'cache clearing error: ' + str(cl_stderrd)
        sys.exit()

    if cl_stdoutd == '':
        print 'cache not cleared'
        sys.exit()

    #output =  re.search("Deleted ", cl_stdoutd)
    #print 'line: ' + str(output)
    
    return cl_stdoutd, cl_stderrd

def tpc_benchmark(name_node_ip, tpc_location, tpc_size):
    print 'running TPC Benchmark'
    address = str(tpc_location)
    cmd = 'cd '+address+'; ./TPCx-HS-master.sh -g '+ tpc_size
    cl_stdoutd, cl_stderrd = c_ssh_as_root(name_node_ip, cmd)
    #print cmd
    #print 'TPC error: ' +str(cl_stderrd)
    #print 'TPC output: ' + str(cl_stdoutd)
    return cl_stdoutd, cl_stderrd

def run_tpc_benchmark(tpc_ip, tpc_location, tpc_size):
    jobIDs = []
    starttimes = []
    finishtimes = []
    job_names = []

    edge_node_ip = "172.16.14.101"
    timeA = datetime.datetime.now()-datetime.timedelta(1)
    print str(timeA)
    
    out1, out2 = tpc_benchmark(tpc_ip, tpc_location, tpc_size)
    
    jobIDs =  re.findall("Job complete: (.+)", out1)
    #jobIDs = ['job_201504081546_0163', 'job_201504081546_0164', 'job_201504081546_0165', 'job_201504081546_0166', 'job_201504081546_0167', 'job_201504081546_0168']
    #jobIDs = ['job_201504160841_0187', 'job_201504160841_0188', 'job_201504160841_0189', 'job_201504160841_0190', 'job_201504160841_0191', 'job_201504160841_0192']
    print "jobIds " +str(jobIDs)
    #log('jobids: ' +str(jobIDs))
    time.sleep(30)
    minute = timedelta(minutes=1)
    timeB = datetime.datetime.now()+datetime.timedelta(1)+minute
    print str(timeB)
    session = ApiResource(edge_node_ip,  7180, "admin", "admin", version=6)
    #log('jobIds = ' + str(jobIDs))
    #log(str(id))
    #id = 'job_1411634913292_0068'
    for id in jobIDs:
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
                
        print timeA
        print timeB
        
        #ac =  mapreduce.get_yarn_applications(timeA, timeB)
        ac = mapreduce.get_activity(id)
        job_type = ac.name
        #print jobIDs
        print str(ac.startTime)
        print str(ac.finishTime)
        log('API time details for jobID: '+str(id)+ ' ' +str(job_type))
        log(str(ac.startTime))
        log(str(ac.finishTime))
        start = datetime.datetime.strptime(ac.startTime, '%Y-%m-%dT%H:%M:%S.%fZ')
        finish = datetime.datetime.strptime(ac.finishTime, '%Y-%m-%dT%H:%M:%S.%fZ')
        
        start = convert_to_utc(start)
        finish = convert_to_utc(finish)
        log(str(start))
        log(str(finish))
        start = start-datetime.timedelta(hours=-1)
        finish = finish-datetime.timedelta(hours=-1)
        #log('ac.starttime: ' +str(ac.startTime))
        #log('ac.finishtime: ' + str(ac.finishTime))
        starttimes.append(start)
        finishtimes.append(finish)
        job_names.append(job_type)
        #print str(ac)
            #############
            #if s.name == "yarn":
            #    mapreduce = s
        #ac =  mapreduce.get_yarn_applications(timeA, timeB)
            #print str(ac)
            #print str(ac.warnings)
        #for job in ac.applications:
        #    if id == str(job.applicationId):
        #        ob = job
        #        #log('ob = '+str(ob))         
        #start = ob.startTime
        #starttimes.append(start)
        #finish = ob.endTime
        
        
    return jobIDs, starttimes, finishtimes, job_names
    

#def convert_cpu_stats(cpu_stats, numCores):
    #edge_ip = "172.16.2.21"
    #clustername = "Cluster 1"

    #session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    #cluster = session.get_cluster(clustername)

    #hostlist = session.get_all_hosts("full")
    #print str(hostlist)
    #print cpu_stats

    # cpu_user_rate / getHostFact(numCores, 1) * 100

    #for stats in cpu_stats:
#    cpu_data_perc = float(cpu_stats)#/numCores*100
#    return cpu_data_perc

def get_other_cpu_stats(timestamp, host, rowCount, job_type, fileCount, fileSize, cpu_user_value, job_name):
    config = importlib.import_module('config_cdh5')
    edge_ip = config.edge_node_ip
    clustername = config.cluster_name
    #stat = 'cpu_system_rate'

    cpu_stats = ('cpu_soft_irq_rate',
                 'cpu_iowait_rate',
                 'cpu_irq_rate',
                 'cpu_system_rate'
                 )
    #converted = convert_cpu_stats(cpu_user_value, 24)

    #log("cpu user value = " + str(cpu_user_value))
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    data = []
    cpu_total = []
    full_total = 0
    
    #host = hostlist[2]
    print 'host = '+str(host)
    hostname = get_datanode_entityname(edge_ip, clustername, host)
    numCores = get_datanode_cores(edge_ip, clustername, host)
    print 'hostname = ' + str(hostname)
    print 'CORES cpu data: ' +str(numCores)
    #tsquery = "select "+stat+" where hostname = \""+ host +"\" and category = Host"
    sec = timedelta(seconds=10)

    time_start = timestamp-sec   # GMT +1
 
    time_end = timestamp+sec
    if job_type == 'tpc':
        time_start = convert_to_utc(time_start)
        time_end = convert_to_utc(time_end)
        time_start = time_start-datetime.timedelta(hours=-1)
        time_end = time_end-datetime.timedelta(hours=-1)

    
    for stat in cpu_stats:
        #log('stat: '+ str(stat))
        #log('stime = '+str(time_start))
        #log('CPUetime = '+str(time_end))
        tsquery = "select "+stat+" / "+str(numCores)+" * 100 where hostname = \""+ host +"\" and category = Host"
        #log('tsquery other_cpu: '+str(tsquery))
        #testing if the tpc other stats need to 
        #if job_type == 'tpc':
        #    time_start = convert_to_utc(time_start)
        #    time_end = convert_to_utc(time_end)

        hostRes = session.query_timeseries(tsquery, time_start, time_end)
        #log(str(hostRes))

        for rez in hostRes[0].timeSeries:
            #print str(len(rez.data))
            #log('rez: ' + (str(rez)))
            for point in rez.data:
                cpu_total.append(point.value)
                data.append(str(stat)+ " : " + str(point.value))
                timestamp = point.timestamp
                #log('point: ' + str(point))
                print "timestampGURR = "+  str(timestamp)
                if job_type == 'dfsio':
                    log(job_type +" | " + str(fileCount)  + "-" + str(fileSize) + " | "+ str(host) +" | " + stat + " | " + str(point.value) )
                elif job_type == 'HIVE-Join':
                    log(job_type +" | "+ str(host) +" | " + stat + " | " + str(point.value) )
                elif job_type == 'kmeans':
                    log(job_type +" | "+ str(host) +" | " + stat + " | " + str(point.value) )
                elif job_type == 'tpc':
                    log(job_type +"-"+str(job_name)+" | "+ str(host) +" | " + stat + " | " + str(point.value) )
                    #log(str(time_end))
                else:
                    log(job_type + " | " + str(rowCount) + " | "+ str(host) +" | " + stat + " | " + str(point.value) )
                    
    #print point.value
    total = 0
    for value in cpu_total:
        #log('cpu total: ' +str(cpu_total))
        #log('value: '+ str(value))
        #log('total: ' + str(total))
        total = total+value
        #log('new total: '+str(total))
    #total = total + cpu_user_value
    #log(job_type + " | " + str(rowCount) + " | cpu_total | " + str(total) )
    #full_totals.append(total)
    print data
    return data, total

def get_datanode_hosts(edge_ip, clustername):
    hosts = []
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    print "clustername: "+str(clustername)
    view = session.get_all_hosts("full")
    print "view: "+str(view)
    for host in view:
       for each in host.roleRefs:
           if 'DATANODE' in  each.roleName :
               hosts.append(host.ipAddress)
    return hosts

def get_datanode_objects(edge_ip, clustername):
    hosts = []
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
       for each in host.roleRefs:
           if 'DATANODE' in  each.roleName :
		hosts.append(host)
    return view, hosts

def get_datanode_entityname(edge_ip, clustername, ipAddress):
    hosts = []
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
        if ipAddress ==  host.ipAddress:
               return host.hostname
    return hosts    

def get_datanode_cores(edge_ip, clustername, hostname):
    hosts = []
    print hostname
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
        if host.hostname == hostname:
            return host.numCores
    return hosts

def teragen(rowNumber, folderName, edge_node_ip, teragen_params):
    '''
    note for this to work : 
    on the edge node : 
    bluepill chef-client stop
    sudo vi /etc/sudoers
    add :
    Defaults:root   !requiretty
    '''
    cmd = 'cd /opt/cloudera/parcels/CDH-5.5.0-1.cdh5.5.0.p0.8/lib/hadoop-0.20-mapreduce/;sudo -u hdfs hadoop jar hadoop-examples-2.6.0-mr1-cdh5.5.0.jar teragen ' + teragen_params + ' ' + str(rowNumber) +' '+ str(folderName)
    print "running " + cmd 
    teregen_ip = '172.16.14.97'
    cl_stdoutd, cl_stderrd = c_ssh_as_root(teregen_ip, cmd)        
    print cl_stdoutd
    print cl_stderrd
    return cl_stdoutd, cl_stderrd

def terasort(folderName, edge_node_ip, terasort_params):
    destFolder = folderName + '_Sorted'

    cmd = 'cd /opt/cloudera/parcels/CDH-5.5.0-1.cdh5.5.0.p0.8/lib/hadoop-0.20-mapreduce/;sudo -u hdfs hadoop jar hadoop-examples-2.6.0-mr1-cdh5.5.0.jar terasort ' + terasort_params + ' '+ str(folderName) + ' ' + str(destFolder)
    print "running " + cmd 
    teregen_ip = '172.16.14.97'
    cl_stdoutd, cl_stderrd = c_ssh_as_root(teregen_ip, cmd)        
    print cl_stdoutd
    print cl_stderrd
    return cl_stdoutd, cl_stderrd

def log(entry, printOutput=True):
    if printOutput:
        print entry
    f = open('Results.log','a')
    f.write(entry + "\n")
    f.close()
    
def log_hive(entry, printOutput=True):
    if printOutput:
        print entry
    f = open('Hive_Results.log','a')
    f.write(entry + "\n")
    f.close()

def dfsio(numFiles, fileSize, edge_node_ip):
    edge_node_ip = "172.16.14.97"
    
    #cmd = 'cd /usr/lib/hadoop-0.20-mapreduce;sudo -u hdfs hadoop jar hadoop-test-2.2.0-mr1-cdh5.0.0-beta-2.jar TestDFSIO -write -nrFiles '+ str(numFiles) +' -fileSize '+ str(fileSize) + ' -resFile /tmp/results.txt'
    cmd = 'cd /opt/cloudera/parcels/CDH-5.4.2-1.cdh5.4.2.p0.2/lib/hadoop-0.20-mapreduce;sudo -u hdfs hadoop jar hadoop-test-2.6.0-mr1-cdh5.4.2.jar TestDFSIO   -write -nrFiles '+ str(numFiles) +' -fileSize '+ str(fileSize) + ' -resFile /tmp/results.txt'
    print "running  " + cmd;
    cl_stdoutd, cl_stderrd = c_ssh_as_root(edge_node_ip, cmd)        
    return cl_stdoutd, cl_stderrd

def dfsioREAD(numFiles, fileSize, edge_node_ip):
    edge_node_ip = "172.16.14.97"
    cmd = 'cd /opt/cloudera/parcels/CDH-5.4.2-1.cdh5.4.2.p0.2/lib/hadoop-0.20-mapreduce;sudo -u hdfs hadoop jar hadoop-test-2.6.0-mr1-cdh5.4.2.jar TestDFSIO   -read -nrFiles '+ str(numFiles) +' -fileSize '+ str(fileSize) + ' -resFile /tmp/results.txt'
    print "running  " + cmd;
    cl_stdoutd, cl_stderrd = c_ssh_as_root(edge_node_ip, cmd)        
    return cl_stdoutd, cl_stderrd
    
def rrdtoolXtract(start, end, metric, host, crowbar_admin_ip, time_offset):
    offset = time_offset*60*60
    start = start - offset
    end = end - offset
    #host = "172.16.2.29"
    #host = "da0-36-9f-32-73-74.dell.com"
    #log('rrd start = ' + str(start))
    #log(str(end))
    #log(str(host))
    #hostName = re.search("(.[a-z0-9]+)", host)
    #host = hostName.group(1)
    cmd = 'rrdtool fetch /var/lib/ganglia/rrds/13g\ Performance\ Stamp/'+ str(host) + '/' + metric +'.rrd AVERAGE -s '+ str(start) +' -e ' + str(end) 
    log(str(cmd))
    cl_stdoutd, cl_stderrd = c_ssh_as_root_DellCloud(crowbar_admin_ip, cmd)
    return cl_stdoutd, cl_stderrd

def run_dfsio_job(fileCount, fileSize, edge_ip):
    bla = dfsio(fileCount, fileSize, edge_ip)
    ls = bla[1].split('\r' );
    timeA = datetime.datetime.now()-datetime.timedelta(1)
    print str(timeA)
    for line in ls:
        print str(line)
        ma =  re.search("Test exec time sec:\s(.+)", line)
        if ma:
            runTime = ma.group(1)
        ma2 =  re.search("Throughput mb/sec:\s(.+)", line)
        if ma2:
            Throughput = ma2.group(1)
        #ma3 =  re.search("Job (.+) completed", line)
        ma3 =  re.search("Job complete:\s(.+)", line)
        if ma3:
                jobID = ma3.group(1)   
        
        time.sleep(30)
    timeB = datetime.datetime.now()+datetime.timedelta(1)
    print str(timeB)
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=6)

    # Get the MapReduce job runtime from the job id
    cdh4 = None
    for c in session.get_all_clusters():
      print "in get all clusters"
      print str(c)
      print str(c.version)
      if c.version == "CDH5":
          cdh4 = c 
    for s in cdh4.get_all_services():
        print "in get_all_services"
        print str(s)
        print str(s.name)
    if s.name == "mapreduce":
        mapreduce = s
        ac = mapreduce.get_activity(jobID)
        print jobID
        print str(ac.startTime)
        print str(ac.finishTime)
        
        print str(ac)
        #print str(ac.warnings)
        #for job in ac.applications:
        #    if jobID == str(job.applicationId):
        #        ob = job         
        #start = ob.startTime
        #finish = ob.endTime
        start = ac.startTime
        finish = ac.finishTime

    else:
        ac =  mapreduce.get_yarn_applications(timeA, timeB)
        for job in ac.applications:
            if jobID == str(job.applicationId):
                ob = job         
        start = ob.startTime
        finish = ob.endTime
        
    #ac =  mapreduce.get_yarn_applications(timeA, timeB)
    #ab = mapreduce.get_activity(jobID)
    #print str(ac)
    #print str(ac.warnings)
    #for job in ac.applications:
    #    if jobID == str(job.applicationId):
    #        ob = job         
    #start = ob.startTime
    #finish = ob.endTime
    
    start = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S.%fZ')
    finish = datetime.datetime.strptime(finish, '%Y-%m-%dT%H:%M:%S.%fZ')

    hourOffset = timedelta(hours=5)
    start = start-hourOffset
    finish = finish-hourOffset
#################
                
    return start, finish, runTime, Throughput, jobID

def run_dfsioREAD_job(fileCount, fileSize, edge_ip):
    bla = dfsioREAD(fileCount, fileSize, edge_ip)
    ls = bla[1].split('\r' );
    timeA = datetime.datetime.now()-datetime.timedelta(1)
    print str(timeA)
    for line in ls:
        print str(line)
        ma =  re.search("Test exec time sec:\s(.+)", line)
        if ma:
            runTime = ma.group(1)
        ma2 =  re.search("Throughput mb/sec:\s(.+)", line)
        if ma2:
            Throughput = ma2.group(1)
        ma3 =  re.search("Job complete:\s(.+)", line)
        if ma3:
                jobID = ma3.group(1)   
        
        time.sleep(30)
    timeB = datetime.datetime.now()+datetime.timedelta(1)
    print str(timeB)
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=6)

    # Get the MapReduce job runtime from the job id
    cdh4 = None
    for c in session.get_all_clusters():
      print "in get all clusters"
      print str(c)
      print str(c.version)
      if c.version == "CDH5":
          cdh4 = c 
    for s in cdh4.get_all_services():
        print "in get_all_services"
        print str(s)
        print str(s.name)
    if s.name == "mapreduce":
        mapreduce = s
        ac = mapreduce.get_activity(jobID)
        print jobID
        print str(ac.startTime)
        print str(ac.finishTime)
        
        print str(ac)
        #print str(ac.warnings)
        #for job in ac.applications:
        #    if jobID == str(job.applicationId):
        #        ob = job         
        #start = ob.startTime
        #finish = ob.endTime
        start = ac.startTime
        finish = ac.finishTime

    else:
        ac =  mapreduce.get_yarn_applications(timeA, timeB)
        for job in ac.applications:
            if jobID == str(job.applicationId):
                ob = job         
        start = ob.startTime
        finish = ob.endTime
        
    #ac =  mapreduce.get_yarn_applications(timeA, timeB)
    #ab = mapreduce.get_activity(jobID)
    #print str(ac)
    #print str(ac.warnings)
    #for job in ac.applications:
    #    if jobID == str(job.applicationId):
    #        ob = job         
    #start = ob.startTime
    #finish = ob.endTime
    
    start = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S.%fZ')
    finish = datetime.datetime.strptime(finish, '%Y-%m-%dT%H:%M:%S.%fZ')

    hourOffset = timedelta(hours=5)
    start = start-hourOffset
    finish = finish-hourOffset
                
    return start, finish, runTime, Throughput, jobID
    

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
    
def get_cloudera_dataNodesAverage(edge_node_ip, dataNodes, stat, time_start, time_end, cluster_name, rowCount, job_type, fileCount, fileSize):
        session = ApiResource(edge_node_ip, 7180, "admin", "admin", version=6)
        avg = 0.00
        DataNodesCount = 0
        
        highests = []
        cpu_total = []
        full_totals = []
        highestCPU = 0
        print "time start: "+str(time_start)
        print "time end: "+str(time_end)
        #time_start = convert_to_utc(time_start)
        #time_end = convert_to_utc(time_end)
        #time_start = time_start-datetime.timedelta(hours=5)
        #time_end = time_end-datetime.timedelta(hours=5)

        for host in dataNodes:
            print host
            host = get_datanode_entityname(edge_node_ip, cluster_name, host)
            numCores = get_datanode_cores(edge_node_ip, cluster_name, host)
            print "NUM_CORES: " + str(numCores)
            #time.sleep(10)
            #system.exit()
            if stat == 'cpu_user_rate':
                tsquery = "select "+stat+" / "+str(numCores)+" *100 where hostname = \""+ host +"\" and category = Host"
                print tsquery
                #time.sleep(10)
                #system.exit()
            else:
                tsquery = "select "+stat+" where hostname = \""+ host +"\" and category = Host"
            print tsquery
            #log(str(tsquery))
            data = []
            points = {}
            timestamps = []
            total = 0

	    #timestamp = []
	    #rowCount = 10000000000
            #timeAdj = datetime.timedelta(hours=1)
            #time_start = time_start+timeAdj
            #time_end = time_end+timeAdj
            #qtime_start = convert_to_utc(time_start)
            #qtime_end = convert_to_utc(time_end)
            #log('tsquery =: ' +str(tsquery))
            print "time start::: "+str(time_start)
            print "time End::: " + str(time_end)
            hostRes = session.query_timeseries(tsquery, time_start, time_end)
            print 'hostRes[0] = ' + str(hostRes[0])       
            for rez in hostRes[0].timeSeries:
                print "len(rez.data) = "+str(len(rez.data))
                #time.sleep(2)
                if (len(rez.data) > 0) :
                    for point in rez.data:
                        data.append(point.value)
                        points.update(dict({point.value:point.timestamp}))          
                else :
                    pass
            print "data = " + str(data)
            if len(data) > 0:
                highestValue = 0.00
                highestValue = sorted(data, key=float, reverse=True)[0]
                highestCPU = highestValue
                for key in sorted(points.iterkeys(), reverse=True):
                    timestamps.append(points[key])
                    #timestamp = timestamps[0]
                    #print timestamp

                avg = avg  + highestValue
                if highestValue != 0.00:
                    print str(highestValue)
                    highests.append(dict({host:highestValue}))
                    DataNodesCount += 1
                else:
                    timestamp = 0
                    highests.append(dict({host:'0'}))
            else:
                #timestamps.append(0)
                highests.append(dict({host:'0'}))
            if stat == 'cpu_user_rate':
                #log("Highest "+ str(highests))
                #log("highestCPU "+ str(highestCPU))
                #log("Host "+ str(host))
                #log("index "+ str(dataNodes))
                print "TIMESTAMPS: "+str(timestamps)
                adjustedtimestamps = convert_to_utc(timestamps[0])
                #log('adjTimeCpu: '+str(adjustedtimestamps))
                #log(str(host))
                #log(str(rowCount))
                #log(str(job_type))
                #log(str(fileCount))
                #log(str(fileSize))
                #log(str(highestCPU))
                #log(str('getting other cpu stats for host ')+ str(host))
                other_cpu_stats, full_total = get_other_cpu_stats(adjustedtimestamps, host, rowCount, job_type, fileCount, fileSize, highestCPU, job_type)
                full_totals.append(full_total)
                #total = total + cpu_total
                #log("otherStats " + str(other_cpu_stats))
                #log(str(full_totals))
        if DataNodesCount == 0:
            return "0", [], [], []
        print DataNodesCount
        #log(str(DataNodesCount))
        return str(avg / DataNodesCount) , highests, timestamps[0], full_totals

def getHIVE_cloudera_dataNodesAverage(edge_node_ip, dataNodes, stat, time_start, time_end, cluster_name, rowCount, job_type, fileCount, fileSize, job_name):
        session = ApiResource(edge_node_ip, 7180, "admin", "admin", version=6)
        avg = 0.00
        DataNodesCount = 0
        highests = []
	cpu_total = []
	full_totals = []
	highestCPU = 0
        for host in dataNodes:
            print host
            host = get_datanode_entityname(edge_node_ip, cluster_name, host)
            numCores = get_datanode_cores(edge_node_ip, cluster_name, host)
            print "NUM_CORES: " + str(numCores)
            #host = get_datanode_entityname(edge_node_ip, cluster_name, host)
            
            if stat == 'cpu_user_rate':
                tsquery = "select "+stat+" / "+str(numCores)+" *100 where hostname = \""+ host +"\" and category = Host"
                print tsquery
                #log(str(tsquery))
                #time.sleep(10)
                #system.exit()
            else:
                tsquery = "select "+stat+" where hostname = \""+ host +"\" and category = Host"
                #log(str(tsquery))
            #tsquery = "select "+stat+" where hostname = \""+ host +"\" and category = Host"
            print tsquery
            data = []
	    points = {}
	    timestamps = []
	    total = 0

	    #timestamp = []
	    #rowCount = 10000000000
            #qtime_start = convert_to_utc(time_start)
            #qtime_end = convert_to_utc(time_end)
            #log('getHIVE_cloudera_dataNodesAverage' + str(time_start))
            hostRes = session.query_timeseries(tsquery, time_start, time_end)
	    print 'hostRes[0] = ' + str(hostRes[0])
	    #time.sleep(15)       
        
            for rez in hostRes[0].timeSeries:
                print str(len(rez.data))
                if (len(rez.data) > 0) :
                    for point in rez.data:
                        data.append(point.value)
			points.update(dict({point.value:point.timestamp}))          
                else :
                    pass
	    print "data = " + str(data)
	    #time.sleep(20)
            if len(data) > 0:
                highestValue = 0.00
                highestValue = sorted(data, key=float, reverse=True)[0]
		highestCPU = highestValue
		for key in sorted(points.iterkeys(), reverse=True):
			timestamps.append(points[key])
		#timestamp = timestamps[0]
		#print timestamp

                avg = avg  + highestValue
                if highestValue != 0.00:
                    print str(highestValue)
                    highests.append(dict({host:highestValue}))
                    DataNodesCount += 1
                else:
		    #timestamp = 0
                    highests.append(dict({host:'0'}))
            else:
		timestamps.append(0)
                highests.append(dict({host:'0'}))

	    if len(data) > 0:

	            if stat == 'cpu_user_rate':
			#log("Highest "+ str(highests))
			#log("highestCPU "+ str(highestCPU))
			#log("Host "+ str(host))
			#log("index "+ str(dataNodes))
			#log("cpu_user_rate peaked at: " + str(timestamps[0]))
                        #print "TIMESTAMPS: "+str(timestamps)
                        adjustedtimestamps = convert_to_utc(timestamps[0])
	    		other_cpu_stats, full_total = get_other_cpu_stats(timestamps[0], host, rowCount, job_type, fileCount, fileSize, highestCPU, job_name)
			full_totals.append(full_total)
         		#total = total + cpu_total
			#log("otherStats " + str(other_cpu_stats))
			#log(str(full_totals))
	    else:
		log("no cpu data")
		full_totals.append(0)
			
        if DataNodesCount == 0:
            return "0", [], [], []
        return str(avg / DataNodesCount) , highests, timestamps[0], full_totals

def get_cpu_stats_dataNodesAverage(edge_node_ip, dataNodes, stat, time_start, time_end, cluster_name):
        cpu_stats = ('cpu_soft_irq_rate',
		 'cpu_iowait_rate',
		 'cpu_irq_rate',
		 'cpu_system_rate'
		)

	cpu_stat = []
	cpu_data = []

	for stat in cpu_stats:

		session = ApiResource(edge_node_ip, 7180, "admin", "admin", version=6)
        	avg = 0.00
        	DataNodesCount = 0
        	highests = []
        	for host in dataNodes:
            		print host
            		host = get_datanode_entityname(edge_node_ip, cluster_name, host)
            		tsquery = "select "+stat+" where hostname = \""+ host +"\" and category = Host"
            		print tsquery
            		data = []
                #qtime_start = convert_to_utc(time_start)
                #qtime_end = convert_to_utc(time_end)
            	hostRes = session.query_timeseries(tsquery, time_start, time_end)       
            	for rez in hostRes[0].timeSeries:
                	    print str(len(rez.data))
                	    if (len(rez.data) > 0) :
                                for point in rez.data:
                                    data.append(point.value)
                                    timestamp = point.timestamp 
                                    cpu_data.append(point.value)       
                		else :
                    			pass
            		    if len(data) > 0:
                		    highestValue = 0.00
                		    highestValue = sorted(data, key=float, reverse=True)[0]
                		    avg = avg  + highestValue
                		    if highestValue != 0.00:
                    			    print str(highestValue)
                    			    highests.append(dict({host:highestValue}))
                    			    DataNodesCount += 1
                		    else:
                    			    highests.append(dict({host:'0'}))
            		    else:
                		    highests.append(dict({host:'0'}))
                     
        	if DataNodesCount == 0:
            		return "0", []
        return str(avg / DataNodesCount) , highests

              
def run_terragen_job(rowCount, edge_node_ip, teragen_params):
        randFolderName = uuid.uuid4()
        timeA = datetime.datetime.now()-datetime.timedelta(1)
        print str(timeA)
        bla = teragen(rowCount, randFolderName, edge_node_ip, teragen_params)
        #jobID = 'job_201412100459_0011'
        #log('===bla====')
        #log(str(bla))
        time.sleep(60)
        ls = bla[1].split('\r' );
        #log('===ls===')
        #log(str(ls))
        for line in ls:
            print "line: "+str(line)
            #time.sleep(2)
            ma =  re.search("Job complete: (.+)", line)
            #ma =  re.search("Job (.+) complete", line)
            print ma
            if ma:
                jobID = ma.group(1) 
        #time.sleep(30)
        print "waiting 30 seconds"
        time.sleep(30)
        minute = timedelta(minutes=0)

        timeB = datetime.datetime.now()+datetime.timedelta(1)+minute
        print str(timeB)
        print edge_node_ip
        edge_node_ip = "172.16.14.101"
        session = ApiResource(edge_node_ip,  7180, "admin", "admin", version=6)
        print session.version
        # Get the MapReduce job runtime from the job id
        cdh4 = None
        for c in session.get_all_clusters():
            print "c: " +str(c)
            if c.version == "CDH5":
                cdh4 = c 
        for s in cdh4.get_all_services():
            print "s = " + str(s)
            slist = []
            if s.name == "yarn":
                mapreduce = s
                ac =  mapreduce.get_yarn_applications(timeA, timeB)
                for job in ac.applications:
                    if jobID == str(job.applicationId):
                        ob = job         
                start = ob.startTime
                finish = ob.endTime


            elif s.name == "mapreduce":
                mapreduce = s
                slist.append(s)
                #ac =  mapreduce.get_yarn_applications(timeA, timeB)
                ac = mapreduce.get_activity(jobID)
                print jobID
                print str(ac.startTime)
                print str(ac.finishTime)
        
                print str(ac)
                #print str(ac.warnings)
                #for job in ac.applications:
                #    if jobID == str(job.applicationId):
                #        ob = job         
                #start = ob.startTime
                #finish = ob.endTime
                start = ac.startTime
                finish = ac.finishTime



                
        print timeA
        print timeB
#        if s.name == "mapreduce":
            

#        else:
            

        #removed to allow yarn to complete - add back for mapreduce
        start = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S.%fZ')
        finish = datetime.datetime.strptime(finish, '%Y-%m-%dT%H:%M:%S.%fZ')

        hourOffset = timedelta(hours=5)
        start = start-hourOffset
        finish = finish-hourOffset
        print str(start)
        print str(finish)

        return jobID, start, finish, randFolderName

def run_terasort_job(folderName, edge_node_ip, terasort_params):
        #randFolderName = uuid.uuid4()
        timeA = datetime.datetime.now()-datetime.timedelta(0)
        print str(timeA)
        bla = terasort(folderName, edge_node_ip, terasort_params)
        time.sleep(60)
        ls = bla[1].split('\r' );
        #jobID = 'job_201412100459_0011'
        for line in ls:
            print str(line)
            ma =  re.search("Job complete: (.+)", line)
            #ma =  re.search("Job (.+) completed", line)
            if ma:
                jobID = ma.group(1)
                print jobID
        time.sleep(30)
        timeB = datetime.datetime.now()+datetime.timedelta(0)
        print str(timeB)
        edge_node_ip = "172.16.14.101"
        session = ApiResource(edge_node_ip,  7180, "admin", "admin", version=6)
        print "session: " + str(session)
        # Get the MapReduce job runtime from the job id
        cdh4 = None
        for c in session.get_all_clusters():
            print "terasort c: " + str(c)
            if c.version == "CDH5":
                cdh4 = c 
        for s in cdh4.get_all_services():
            if s.name == "yarn":
                mapreduce = s
                ac =  mapreduce.get_yarn_applications(timeA, timeB)
                for job in ac.applications:
                    if jobID == str(job.applicationId):
                        ob = job         
                start = ob.startTime
                finish = ob.endTime

            elif s.name == "mapreduce":
                mapreduce = s
                #ac =  mapreduce.get_yarn_applications(timeA, timeB)
                ac = mapreduce.get_activity(jobID)
                print jobID
                print str(ac.startTime)
                print str(ac.finishTime)
        
                print str(ac)
                #print str(ac.warnings)
                #for job in ac.applications:
                #    if jobID == str(job.applicationId):
                #        ob = job         
                #start = ob.startTime
                #finish = ob.endTime
                start = ac.startTime
                finish = ac.finishTime

#        if s.name == "mapreduce":
            

#        else:
            
        
        #ac =  mapreduce.get_yarn_applications(timeA, timeB)
        #ab = mapreduce.get_activity(jobID)
        #print str(ac)
        #print str(ac.warnings)
        #for job in ac.applications:
        #    if jobID == str(job.applicationId):
        #        ob = job         
        #start = ob.startTime
        #finish = ob.endTime
    
        start = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S.%fZ')
        finish = datetime.datetime.strptime(finish, '%Y-%m-%dT%H:%M:%S.%fZ')

        hourOffset = timedelta(hours=5)
        start = start-hourOffset
        finish = finish-hourOffset
        
        return jobID, start, finish

def prepare(edge_node_ip):

    file = '/var/lib/hadoop-hdfs/hibench/hivebench/conf/configure.sh'
    config = importlib.import_module('config_cdh5') 
    
    uservisits = 'USERVISITS'
    pages = 'PAGES'
    num_visits = config.uservisits
    num_pages = config.pages
    
    #if isinstance(num_visits, int) == 0 or isinstance(num_pages, int) == 0:
    #    print 'visits or pages config problem'
    #    #time.sleep(15)
    #    sys.exit()
    #else:
    #    edit_file(uservisits, num_visits, file)
    #    edit_file(pages, num_pages, file)

    edit_file(uservisits, num_visits, file)
    edit_file(pages, num_pages, file)
    #log('prepare start')
    #cmd = 'su hdfs; cd /var/lib/hadoop-hdfs/hibench/hivebench/bin/; ./prepare.sh'
    cmd = ' su hdfs - -c "/var/lib/hadoop-hdfs/hibench/hivebench/bin/prepare.sh"'
    #cmd = 'su hdfs'

    print "running: " + cmd 
    cl_stdoutd, cl_stderrd = c_ssh_as_root(edge_node_ip, cmd)        
    print cl_stdoutd
    print cl_stderrd
    #log('prepare end')
    return cl_stdoutd, cl_stderrd

def agg(edge_node_ip):
    log("running aggregation")
    cmd = 'su hdfs - -c "/var/lib/hadoop-hdfs/hibench/hivebench/bin/run-aggregation.sh"'
    print "running: " + cmd 
    cl_stdoutd, cl_stderrd = c_ssh_as_root(edge_node_ip, cmd)        
    print cl_stdoutd
    print cl_stderrd
    return cl_stdoutd, cl_stderrd

def run_agg(edge_node_ip):
    timeA = datetime.datetime.now()-datetime.timedelta(1)
    print str(timeA)
    bla = agg(edge_node_ip)
    #log('bla: ' + str(bla))
    #time.sleep(60)
    ls = bla[1].split('\r' );
    #log('ls: ' + str(ls))
    for line in ls:
        print str(line)
        ma =  re.search("Job = (.+),", line)
        if ma:
            jobID = ma.group(1)
            print jobID   

    print "waiting 30 seconds"
    time.sleep(30)
    minute = timedelta(minutes=1)

    timeB = datetime.datetime.now()+datetime.timedelta(1)+minute
    print str(timeB)
    session = ApiResource(edge_node_ip,  7180, "admin", "admin", version=6)

    # Get the MapReduce job runtime from the job id
    cdh4 = None
    for c in session.get_all_clusters():
        if c.version == "CDH5":
            cdh4 = c 
    for s in cdh4.get_all_services():
        print s
        if s.name == "yarn":
            mapreduce = s
    ac =  mapreduce.get_yarn_applications(timeA, timeB)
    print str(ac)
    print str(ac.warnings)
    for job in ac.applications:
        if jobID == str(job.applicationId):
            #log(str(jobID))
            ob = job         
    start = ob.startTime
    finish = ob.endTime
    return jobID, start, finish

def get_agg_stats(jobtype, edge_ip, runId, visits, pages, dataNodes, cluster_name, crowbar_admin_ip, time_offset, datapointsToCheck):
    ResultsSummary = []
    jobID, start, finish = run_agg(edge_ip)
    print jobID
    start_epoch = int(time.mktime(start.timetuple()))
    finish_epoch = int(time.mktime(finish.timetuple()))

    runTime = finish_epoch - start_epoch
    log("HIVE-AGG | visits | "+str(visits)+" | pages | "+str(pages)+" | job | runtime | " + str(runTime ))
    ResultsSummary.append([str(runId),
                                   "HIVE-agg",
                                  "job",
                                  "runtime",
                                  str(runTime)]                                   
                                  )
        
        #datapointsToCheck = config.hive_cloudera_stats
    for stat in datapointsToCheck:
        #log(stat)
        print 'start = ' + str(start)
        print 'finish = ' + str(finish)
        job_type = 'HIVE-Agg'
        file = '/var/lib/hadoop-hdfs/hibench/hibench.report'
        fileCount = 0
        fileSize = 0
        rowCount = 0
        job_name = ''
        cluster_highest_average_cm, individialHostsHighestPoints, timestamp, full_totals = getHIVE_cloudera_dataNodesAverage(edge_ip, dataNodes, stat, start, finish, cluster_name, rowCount, job_type, fileCount, fileSize, job_name)
        print individialHostsHighestPoints
        if timestamp == 0:
            print timestamp
            pass
    
        if stat == 'cpu_user_rate':
            log("HIVE-Agg | average | " + stat + " | " + str(cluster_highest_average_cm) )
    
    	else:
            log("HIVE-Agg | average | " + stat + " | " + str(cluster_highest_average_cm) )
    
            ResultsSummary.append([str(runId),
                                      "HIVE-Agg",
                                      "average",
                                      str(stat),
                                      str(cluster_highest_average_cm)])
        x = 0
        for host in individialHostsHighestPoints:
            if stat == 'cpu_user_rate':
                output = int(host.items()[0][1])
    	        log("Hive-Agg | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(output) )
            	ResultsSummary.append([str(runId),
                    	                       "Hive-Agg",
                                    	      str(host.items()[0][0]),
                                         	      str(stat),
                                          	      str(output)]                                      
                                          	      )
                full_total = full_totals[x] + output
    			#log("Hive-Agg | CPU Total | " + str(cpu_total[individialHostsHighestPoints.index(host)]) )
                log("Hive-Agg | "+ str(host.items()[0][0]) +" | CPU Total | " + str(full_total) )
                x = x+1
            else:
                log("Hive-Agg | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
            	ResultsSummary.append([str(runId),
                                       "Hive-agg",
                                 	      str(host.items()[0][0]),
                                   	      str(stat),
                                   	      str(host.items()[0][1])]                                      
                                  	      )
	#log("terragen | " + str(rowCount) + " | cpu_total | " + str(cpu_total) )

	ganglia_stats = (#'boottime',
			 'bytes_in',
			 'bytes_out',
			)
	print "------ Ganglia Stats ! ------ "
        for stat in ganglia_stats:
            cluster_highest_average_ganglia, individialHostsHighestPoints = get_ganglia_datanodesAverage(dataNodes, stat, start_epoch, finish_epoch, edge_ip, time_offset)
           
            log("ganglia | average | " + stat + " | " + str(cluster_highest_average_ganglia) )
            ResultsSummary.append([str(runId),
                                   "HIVE-Agg",
                                  "average",
                                  str(stat),
                                  str(cluster_highest_average_ganglia)])
            for host in individialHostsHighestPoints:
                log("HIVE-Agg | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                ResultsSummary.append([str(runId),
                                       "HIVE-Agg",
                                      str(host.items()[0][0]),
                                      str(stat),
                                      str(host.items()[0][1])]                                      
                                      )
        upload_results(ResultsSummary)
        
        hive_out = get_hive_output(edge_ip, 'HIVEAGGR', file)
        #log_hive(runId)
        #log_hive('Type             Date       Time     Duration(s)')
        #log_hive(hive_out)
        
    return hive_out, jobID
    #file = '/var/lib/hadoop-hdfs/hibench/hibench.report'
    #hive_out = get_hive_output('HIVEAGGR', file)
    
def join(edge_node_ip):
    cmd = 'sudo su - hdfs - -c "/var/lib/hadoop-hdfs/hibench/hivebench/bin/run-join.sh"' 
    print "running: " + str(cmd) 
    cl_stdoutd, cl_stderrd = c_ssh_as_root(edge_node_ip, cmd)      
    print cl_stdoutd
    print cl_stderrd
    return cl_stdoutd, cl_stderrd

def get_multi_jobIDs(job_type, edge_node_ip):
    jobIDs = []
    starttimes = []
    finishtimes = []
    #job_type = 'kmeans'
    timeA = datetime.datetime.now()-datetime.timedelta(1)
    print str(timeA)
    
    if job_type == 'kmeans':
        job = kmeans(edge_node_ip)
    elif job_type == 'HIVE-Join':
        job = join(edge_node_ip)
    elif job_type == 'tpc':
        job = tpc_benchmark(name_node_ip, tpc_location, tpc_size)
    else:
        print 'job_type problem'
    #log(str(bla))
    #time.sleep(60)
    if job_type == 'tpc':
        ls = job
    else:
        ls = job[1].split('\r' );
    #log('ls: ' + str(ls))
    x = 0
    for line in ls:
        x = x+1
        print str(line)
        #log('line ' + str(ls.index(line)) +': ' + str(line) + ' LINE END')
        if job_type == 'kmeans':
            jobIDs =  re.findall("Job (.+) completed", line)
        else:
            jobIDs =  re.findall("Starting Job = (.+),", line)

    time.sleep(30)
    minute = timedelta(minutes=1)
    timeB = datetime.datetime.now()+datetime.timedelta(1)+minute
    print str(timeB)
    session = ApiResource(edge_node_ip,  7180, "admin", "admin", version=6)
    #log('jobIds = ' + str(jobIDs))
    #log(str(id))
    #id = 'job_1411634913292_0068'
    for id in jobIDs:
        # Get the MapReduce job runtime from the job id
        cdh4 = None
        for c in session.get_all_clusters():
            if c.version == "CDH5":
                cdh4 = c 
        for s in cdh4.get_all_services():
            if s.name == "yarn":
                mapreduce = s
        ac =  mapreduce.get_yarn_applications(timeA, timeB)
            #print str(ac)
            #print str(ac.warnings)
        for job in ac.applications:
            if id == str(job.applicationId):
                ob = job
                #log('ob = '+str(ob))         
        start = ob.startTime
        #start = start-datetime.timedelta(hours=5)
        start = convert_to_utc(start)
        starttimes.append(start)
        
        finish = ob.endTime
        finish = convert_to_utc(finish)
        #finish = finish-datetime.timedelta(hours=5)
        finishtimes.append(finish)
        #log(str(start))
        #log(str(finish))

    return jobIDs, starttimes, finishtimes
	

def get_join_stats(jobtype, runId, visits, pages, dataNodes, cluster_name, crowbar_admin_ip, time_offset, datapointsToCheck):
    log("getting join stats")
    config = importlib.import_module('config_cdh5') 
    ResultsSummary = []
    edge_ip = config.edge_node_ip
    #job_type = 'HIVEJOIN'
    jobIDs, starttimes, finishtimes = get_multi_jobIDs(jobtype, edge_ip)
    #log(str(jobIDs))
    #log(str(starttimes))
    #log(str(finishtimes))
    stage = 5678
    file = '/var/lib/hadoop-hdfs/hibench/hibench.report'

    for each in jobIDs:
        log("getting join stats for JobID" + str(each))
        start = starttimes[jobIDs.index(each)]
        finish = finishtimes[jobIDs.index(each)]

        start_epoch = int(time.mktime(start.timetuple()))
        finish_epoch = int(time.mktime(finish.timetuple()))
        stage = jobIDs.index(each) + 1
        
        runTime = finish_epoch - start_epoch
        log(str(jobtype) + " | visits | "+str(visits)+" | pages | "+str(pages)+" | stage " + str(stage) + " | runtime | " + str(runTime ))
        ResultsSummary.append([str(runId),
                                       "HIVE-join",
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )

        for stat in datapointsToCheck:
            #print 'start = ' + str(start)
            #print 'finish = ' + str(finish)
            job_type = 'HIVE-Join'
            fileCount = 0
            fileSize = 0
            rowCount = 0
            job_name = ''
            print "start: " + str(start)
            print "finish: " + str(finish) 
            #time.sleep(10)
            cluster_highest_average_cm, individialHostsHighestPoints, timestamp, full_totals = getHIVE_cloudera_dataNodesAverage(edge_ip, dataNodes, stat, start, finish, cluster_name,  rowCount, job_type, fileCount, fileSize, job_name)
            print individialHostsHighestPoints
            print "timestamp = " + str(timestamp)
			#time.sleep(12)
	    	#if timestamp == 0:
			#	print timestamp
			#	pass
	    

            if stat == 'cpu_user_rate':
                log("HIVE-Join | average | " + stat + " | " + str(cluster_highest_average_cm) )

            else:
                log("HIVE-Join | average | " + stat + " | " + str(cluster_highest_average_cm) )

                ResultsSummary.append([str(runId),
                                  "HIVE-Join",
                                  "average",
                                  str(stat),
                                  str(cluster_highest_average_cm)])
                x = 0
                for host in individialHostsHighestPoints:
	    			if stat == 'cpu_user_rate':
					output = int(host.items()[0][1])
	                		log("HIVE-Join | stage "+ str(stage) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(output) )
        	        		ResultsSummary.append([str(runId),
                	                       "HIVE-Join",
                                	      str(host.items()[0][0]),
                                     	      str(stat),
                                      	      str(output)]                                      
                                      	      	)
					full_total = full_totals[x] + output
					#log("HIVE-Join | CPU Total | " + str(cpu_total[individialHostsHighestPoints.index(host)]) )
					log("HIVE-Join | stage "+ str(stage) + " | " + str(host.items()[0][0]) +" | CPU Total | " + str(full_total) )
					x = x+1
				else:
					log("HIVE-Join | stage "+ str(stage) +" | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
        	        		ResultsSummary.append([str(runId),
                	                       "HIVE-Join",
                                	      str(host.items()[0][0]),
                                     	      str(stat),
                                      	      str(host.items()[0][1])]                                      
                                      	      )

		ganglia_stats = (#'boottime',
			 'bytes_in',
			 'bytes_out',
			)
		print "------ Ganglia Stats ! ------ "
        	for stat in ganglia_stats:
            		cluster_highest_average_ganglia, individialHostsHighestPoints = get_ganglia_datanodesAverage(dataNodes, stat, start_epoch, finish_epoch, crowbar_admin_ip, time_offset)
           
            		log("ganglia | average | " + stat + " | " + str(cluster_highest_average_ganglia) )
            		ResultsSummary.append([str(runId),
                                   "HIVE-Join",
                                  "average",
                                  str(stat),
                                  str(cluster_highest_average_ganglia)])
            		for host in individialHostsHighestPoints:
                		log("HIVE-Join | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                		ResultsSummary.append([str(runId),
                                       "HIVE-Join",
                                      str(host.items()[0][0]),
                                      str(stat),
                                      str(host.items()[0][1])]                                      
                                      )
        	upload_results(ResultsSummary)
            
    hive_out = get_hive_output(edge_ip, 'HIVEJOIN', file)
    #log_hive('---------[[ '+runId+' ]]-----------')
    #log_hive('Type             Date       Time     Input_data_size      Duration(s)          Throughput(bytes/s)  Throughput/node')       
    #log_hive(hive_out)
    
    return hive_out, jobIDs
            
    #file = '/var/lib/hadoop-hdfs/hibench/hibench.report'
    #hive_out = get_hive_output('HIVEJOIN', file)            


def get_multi_stats(job_type, runId, visits, pages, dataNodes, cluster_name, crowbar_admin_ip, time_offset, datapointsToCheck):
    log("getting " + job_type + " stats")
    config = importlib.import_module('config_cdh5') 
    ResultsSummary = []
    edge_ip = config.edge_node_ip
    name_ip = config.name_node_ip
    tpc_ip = config.tpc_ip
    interations = config.num_iterations
    param = config.tpc_size
    #job_type = 'HIVEJOIN'
    if job_type == 'tpc':
        print job_type
        jobIDs, starttimes, finishtimes, job_names = run_tpc_benchmark(tpc_ip, config.tpc_location, config.tpc_size)
        log('Get_multi - starttimes: '+str(starttimes) +' endtimes: ' +str(finishtimes))
        #jobIDs = ['job_201511271433_0059', 'job_201511271433_0060', 'job_201511271433_0061', 'job_201511271433_0062', 'job_201511271433_0063', 'job_201511271433_0064']
    else:
        job_names =''
        jobIDs, starttimes, finishtimes = get_multi_jobIDs(job_type, edge_ip)
        del jobIDs[-1]

    
    #log(str(jobIDs))
    #log(str(starttimes))
    #log(str(finishtimes))
    stage = 5678
    file = '/var/lib/hadoop-hdfs/hibench/hibench.report'

    for each in jobIDs:
        log("getting " +job_type+ " stats for JobID: " + str(each))
        start = starttimes[jobIDs.index(each)]
        finish = finishtimes[jobIDs.index(each)]
        #start = convert_to_utc(start)
        #finish = convert_to_utc(finish)
        job_name = job_names[jobIDs.index(each)]

        start_epoch = int(time.mktime(start.timetuple()))
        finish_epoch = int(time.mktime(finish.timetuple()))
        stage = jobIDs.index(each) + 1

        runTime = finish_epoch - start_epoch
        if job_type == 'kmeans':
            log(str(job_type) + " | interation "+str(stage)+ " | runtime | " + str(runTime ))
            ResultsSummary.append([str(runId),
                                      "Kmeans",
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                  )
        elif job_type == 'HIVE-Join':
            log(str(job_type) + " | visits | "+str(visits)+" | pages | "+str(pages)+" | stage " + str(stage) + " | runtime | " + str(runTime ))
            ResultsSummary.append([str(runId),
                                       "HIVE-join",
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                  )
        elif job_type =='tpc':
            rowCount = 12345
            
            if jobIDs.index(each)%3 == 0:
                #need to find out the row-counts for TPC Teragen or alternative TPC 
                #log("terragen | " + str(rowCount) + " | job | runtime | " + str(runTime ))
                log(str(job_type) + "-" +str(job_name)+" | "+str(rowCount)+" | job | runtime | " + str(runTime ))
                ResultsSummary.append([str(runId),
                                       "HIVE-join",
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )
            elif jobIDs.index(each)%3 == 1:
                log(str(job_type) + "-" +str(job_name)+" | "+str(rowCount)+" | job | runtime | " + str(runTime ))
                ResultsSummary.append([str(runId),
                                       "HIVE-join",
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )
            elif jobIDs.index(each)%3 == 2:
                log(str(job_type)  + "-" +str(job_name)+" | "+str(rowCount)+" | job | runtime | " + str(runTime ))
                ResultsSummary.append([str(runId),
                                       "HIVE-join",
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )
                
        else:
            print 'job type problem in multi_stats'
            
            
        #log(str(datapointsToCheck))
        for stat in datapointsToCheck:
                    #print 'start = ' + str(start)
                #print 'finish = ' + str(finish)
                #job_type = 'HIVE-Join'
            fileCount = 0
            fileSize = 0
            rowCount = 0
            print "start: " + str(start)
            print "finish: " + str(finish)
            #log("start: " + str(start))
            #log("finish: " + str(finish))
            #time.sleep(10)
            cluster_highest_average_cm, individialHostsHighestPoints, timestamp, full_totals = getHIVE_cloudera_dataNodesAverage(edge_ip, dataNodes, stat, start, finish, cluster_name,  rowCount, job_type, fileCount, fileSize, job_name)
            print individialHostsHighestPoints
            print "timestamp = " + str(timestamp)
            #log(str(individialHostsHighestPoints))
            #log(str("timestamp = " + str(timestamp)))
            #time.sleep(12)
                #if timestamp == 0:
            #    print timestamp
            #    pass
        

            if stat == 'cpu_user_rate':
                log(job_type +"-"+str(job_name)+ " | average | " + stat + " | " + str(cluster_highest_average_cm) )

            else:
                log(job_type +"-"+str(job_name)+ " | average | " + stat + " | " + str(cluster_highest_average_cm) )

                ResultsSummary.append([str(runId),
                                  str(job_type),
                                  "average",
                                  str(stat),
                                  str(cluster_highest_average_cm)])
            x = 0
            if job_type == 'kmeans':
                variable_name = 'iteration'
            elif job_type == 'Hive-Join':
                variable_name = 'stage'
            elif job_type == 'tpc':
                if param == '1':
                    variable_name = '100GB'
                elif param == '2':
                    variable_name = '300GB'
                elif param == '3':
                    variable_name = '1TB'
                elif param == '4':
                    variable_name = '3TB'
                elif param == '5':
                    variable_name = '10TB'
                elif param == '6':
                    variable_name = '30TB'
                elif param == '7':
                    variable_name = '100TB'
                elif param == '8':
                    variable_name = '300TB'
                elif param == '9':
                    variable_name = '1PB'
            #log(str(stat))
            for host in individialHostsHighestPoints:
                if stat == 'cpu_user_rate':
                    output = host.items()[0][1]    
                    if job_type == "tpc":
                        log(job_type+ "-"+str(job_name)+ " | "+ variable_name + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(output) )
                         
                        ResultsSummary.append([str(runId),
                                       job_type,
                                       str(host.items()[0][0]),
                                       str(stat),
                                       str(output)]                                      
                                             )
                    else:
                        log(job_type+ "-"+str(job_name)+ " | "+ variable_name +"asdf "+ str(stage) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(output) )
                        ResultsSummary.append([str(runId),
                                       job_type,
                                       str(host.items()[0][0]),
                                       str(stat),
                                       str(output)]                                      
                                             )
                    full_total = full_totals[x] + float(output)
                    #log('full tot: '+str(full_total)+ ' fulltotals[x]: ' +str(full_totals[x])+ 'output: '+str(output))
                    #log("HIVE-Join | CPU Total | " + str(cpu_total[individialHostsHighestPoints.index(host)]) )
                    if job_type == 'tpc':
                        log(job_type+"-"+str(job_name)+" | "+variable_name+" | " + str(host.items()[0][0]) +" | CPU Total | " + str(full_total) )
                    else:
                        log(job_type+"-"+str(job_name)+" | "+variable_name+" "+ str(stage) + " | " + str(host.items()[0][0]) +" | CPU Total | " + str(full_total) )                           
                    x = x+1
                else:
                    if job_type == 'tpc':
                        log(job_type+"-"+str(job_name)+" | "+str(variable_name)+" | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                        ResultsSummary.append([str(runId),
                                         job_type,
                                          str(host.items()[0][0]),
                                               str(stat),
                                                str(host.items()[0][1])]                                      
                                              )
                    else:
                        log(job_type+"-"+str(job_name)+" | "+str(variable_name)+" "+ str(stage) +" | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                        ResultsSummary.append([str(runId),
                                         job_type,
                                          str(host.items()[0][0]),
                                               str(stat),
                                                str(host.items()[0][1])]                                      
                                              )

        ganglia_stats = (#'boottime',
             'bytes_in',
             'bytes_out',
            )
        print "------ Ganglia Stats ! ------ "
        for stat in ganglia_stats:
            cluster_highest_average_ganglia, individialHostsHighestPoints = get_ganglia_datanodesAverage(dataNodes, stat, start_epoch, finish_epoch, crowbar_admin_ip, time_offset)
            log("ganglia | average | " + stat + " | " + str(cluster_highest_average_ganglia) )
            ResultsSummary.append([str(runId),
                                   job_type,
                                  "average",
                                  str(stat),
                                  str(cluster_highest_average_ganglia)])
            for host in individialHostsHighestPoints:
                log(job_type + "-"+str(job_name)+ " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                ResultsSummary.append([str(runId),
                                       job_type,
                                      str(host.items()[0][0]),
                                      str(stat),
                                      str(host.items()[0][1])]                                      
                                     )
    #removed this because it was unavailable during TPC testing.
    #upload_results(ResultsSummary)
    
    if job_type == 'tpc':
        hive_out = 0
        return hive_out, jobIDs
    else:
        job_type = 'KMEANS' ##fix this, change all occurrances of kmeans to KMEANS
        hive_out = get_hive_output(edge_ip, job_type, file)
    #log_hive('---------[[ '+runId+' ]]-----------')
    #log_hive('Type             Date       Time     Input_data_size      Duration(s)          Throughput(bytes/s)  Throughput/node')       
    #log_hive(hive_out)
    
    return hive_out, jobIDs

def get_hive_output(edge_ip, target, file):
    #config = importlib.import_module('config_cdh5') 
    edge_node_ip = edge_ip
    myScp = Scp()
    hive_output = []
    
    file_contents = myScp.open_remote_file(edge_node_ip, file)
    
    scon = ssh()
    scon.connect_with_user(edge_node_ip, 'root', 'crowbar')
    
    for line in file_contents:
        joins = re.search("^"+target+"(.+)$", line)
        if joins:
            data = joins.group(1)
            #log(str(data))
            joins = target+"    " + data
            hive_output.append(joins)
    #print hive_output
    print "length: " + str(len(hive_output))
    #time.sleep(10)
    return hive_output[-1]

def kmeans_prepare(edge_node_ip):
    log("running kmeans prepare")
    cmd = 'su hdfs - -c "/var/lib/hadoop-hdfs/hibench/kmeans/bin/prepare.sh"'
    print "running: " + cmd 
    cl_stdoutd, cl_stderrd = c_ssh_as_root(edge_node_ip, cmd)        
    print cl_stdoutd
    print cl_stderrd
    return cl_stdoutd, cl_stderrd

def kmeans(edge_node_ip):
    log("running kmeans")
    cmd = 'su hdfs - -c "/var/lib/hadoop-hdfs/hibench/kmeans/bin/run.sh"'
    print "running: " + cmd 
    cl_stdoutd, cl_stderrd = c_ssh_as_root(edge_node_ip, cmd)        
    print cl_stdoutd
    print cl_stderrd
    return cl_stdoutd, cl_stderrd

def main():
    

    '''
    on the edge node : 
    sudo vi /etc/sudoers
    add :
    Defaults:root   !requiretty
    '''
    config = importlib.import_module('config_cdh5') 
    edge_ip = config.edge_node_ip
    hadoop_ip = config.hadoop_ip
    run_id = config.run_id
    name_node_ip = config.name_node_ip
    clean_up_ip = config.clean_up_ip
    
    dataNodes = get_datanode_hosts(edge_ip,  config.cluster_name)
    #gangliaDataNodes = get_datanode_entityname(edge_ip, clustername, ipAddress)
    hostObjs, dataHostObjs = get_datanode_objects(edge_ip,  config.cluster_name)
    host1 = hostObjs[2]
    numCores = host1.numCores
    numCoresList = []
    log("numCores" + str(numCores))
    for each in dataHostObjs:
        numCoresList.append(each.numCores)
        
    print numCoresList
    folderNames = []

    cluster_name = config.cluster_name
    time_offset = config.time_offset
    clean_up_ip = config.clean_up_ip
    crowbar_admin_ip = config.edge_node_ip
    runId = str(datetime.datetime.now()) + "__" + config.run_id
    
    #removing datanodes and edge_ip lines, they are repeated above.
    #dataNodes = get_datanode_hosts(edge_ip, config.cluster_name)
    #edge_ip = config.edge_node_ip
    
    log("------------[[["+str(run_id) + "]]]------------------------------")
    out1, out2 = clear_disks(clean_up_ip)
    print out1
    out1, out2 = clear_cache(clean_up_ip)
    log( "[[[ Terragen tests ]]]")
    rowCountsBatchValues = config.teragen_row_counts
    teragen_params = config.teragen_parameters 
    for rowCount in rowCountsBatchValues:
        log( "[[ Terragen Row Count Cycle  " + str(rowCount)   + "]]")
        ResultsSummary = []
        
        jobID, start, finish, teragenFolder = run_terragen_job(rowCount, hadoop_ip, teragen_params)
        folderNames.append(teragenFolder)
        #minute = timedelta(minutes=15)
        #finish = finish+minute
        start_epoch = int(time.mktime(start.timetuple()))
        finish_epoch = int(time.mktime(finish.timetuple()))

        runTime = finish_epoch - start_epoch
        log("getting teragen stats for JobID: " + str(jobID))
        log("terragen | " + str(rowCount) + " | job | runtime | " + str(runTime ))
        ResultsSummary.append([str(runId),
                                       "terragen",
                                      str(rowCount),
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )

        time.sleep(30) # give time for the stats to become available
        # Checking the cm_api stats
        datapointsToCheck = config.teragen_cloudera_stats
        print "------ Cloud Era Stats ! ------ "
        #cluster_highest_average_cm, stat = log_cpu_stats()
        #log("terragen | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_cm) )
        #ResultsSummary.append([runId,
                                   #"terragen",
                                  #str(rowCount),
                                  #"average",
                                  #stat,
                                  #str(cluster_highest_average_cm)])

        for stat in datapointsToCheck:
            print 'start = ' + str(start)
            print 'finish = ' + str(finish)
            job_type = 'terragen'
            fileCount = 0
            fileSize = 0 
            cluster_highest_average_cm, individialHostsHighestPoints, timestamp, full_totals = get_cloudera_dataNodesAverage(edge_ip, dataNodes, stat, start, finish, config.cluster_name, rowCount, job_type, fileCount, fileSize)
            print individialHostsHighestPoints
            if timestamp == 0:
                print timestamp
                pass
            if stat == 'cpu_user_rate':
                log("terragen1 | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_cm) )
            else:
                log("terragen2 | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_cm) )

            ResultsSummary.append([str(runId),
                                   "terragen",
                                  str(rowCount),
                                  "average",
                                  str(stat),
                                  str(cluster_highest_average_cm)])
            x = 0
            for host in individialHostsHighestPoints:
                if stat == 'cpu_user_rate':
                    #output = convert_cpu_stats(host.items()[0][1], numCores)
                    log("terragen | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                    ResultsSummary.append([str(runId),
                                           "terragen",
                                           str(rowCount),
                                           str(host.items()[0][0]),
                                           str(stat),
                                           str(host.items()[0][1])]
                                          )
                    full_total = full_totals[x] + host.items()[0][1]
                    #log("terragen | " + str(rowCount) + " | CPU Total | " + str(cpu_total[individialHostsHighestPoints.index(host)]) )
                    log("terragen | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | CPU Total | " + str(full_total) )
                    x = x+1
                else:
                    log("terragen | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                    ResultsSummary.append([str(runId),
                                           "terragen",
                                           str(rowCount),
                                           str(host.items()[0][0]),
                                           str(stat),
                                           str(host.items()[0][1])]
                                          )
                    #log("terragen | " + str(rowCount) + " | cpu_total | " + str(cpu_total) )
              
        # Checking Ganglia stats
        ganglia_stats = config.teragen_ganglia_stats

        #print( "[Getting ganglia stats]")
        print "------ Ganglia Stats ! ------ "
        for stat in ganglia_stats:
            cluster_highest_average_ganglia, individialHostsHighestPoints = get_ganglia_datanodesAverage(dataNodes, stat, start_epoch, finish_epoch, config.crowbar_admin_ip, time_offset)
           
            log("ganglia | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_ganglia) )
            ResultsSummary.append([str(runId),
                                   "terragen",
                                  str(rowCount),
                                  "average",
                                  str(stat),
                                  str(cluster_highest_average_ganglia)])
            for host in individialHostsHighestPoints:
                log("terragen | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                ResultsSummary.append([str(runId),
                                       "terragen",
                                      str(rowCount),
                                      str(host.items()[0][0]),
                                      str(stat),
                                      str(host.items()[0][1])]                                      
                                      )
        #removed during TPC tesing because upload is not available
        #upload_results(ResultsSummary)
        log( "[[[ Terasort tests ]]]")
        terasort_params = config.terasort_parameters

        log( "[[ Terasort Cycle  " + str(rowCount)   + "]]")
        jobID, start, finish = run_terasort_job(str(teragenFolder), hadoop_ip, terasort_params)
        
        start_epoch = int(time.mktime(start.timetuple()))
        finish_epoch = int(time.mktime(finish.timetuple()))
        
        runTime = finish_epoch - start_epoch
        log("getting terasort stats for JobID: " + str(jobID))
        log("terasort | " + str(rowCount) + " | job | runtime | " + str(runTime ))
        ResultsSummary.append([str(runId),
                                       "terasort",
                                      str(rowCount),
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )
    
        #time.sleep(60)
        
        # Checking the cm_api stats
        datapointsToCheck = config.terasort_cloudera_stats
        

        print "------ Cloudera Stats ! ------ "
         
        for stat in datapointsToCheck:
            print 'start = ' + str(start)
            print 'finish = ' + str(finish)
            job_type = 'terasort'
            fileCount = 0
            fileSize = 0
            cluster_highest_average_cm, individialHostsHighestPoints, timestamp, full_totals = get_cloudera_dataNodesAverage(edge_ip, dataNodes, stat, start, finish, config.cluster_name, rowCount, job_type, fileCount, fileSize)
            print individialHostsHighestPoints
            if stat == 'cpu_user_rate':
                log("terasort | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_cm) )
            else:
            	log("terasort | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_cm) )
            
            ResultsSummary.append([str(runId),
                                   "terasort",
                                  str(rowCount),
                                  "average",
                                  str(stat),
                                  str(cluster_highest_average_cm)])
            x2 = 0
            for host in individialHostsHighestPoints:
                if stat == 'cpu_user_rate':
                    output = host.items()[0][1]
                    log("terasort | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                    ResultsSummary.append([str(runId),
                                           "terasort",
                                           str(rowCount),
                                           str(host.items()[0][0]),
                                           str(stat),
                                           str(host.items()[0][1])]
                                          )
                    full_total = full_totals[x2] + host.items()[0][1]
                    #log("terragen | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | CPU Total | " + str(cpu_total[individialHostsHighestPoints.index(host)]) )
                    log("terasort | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | CPU Total | " + str(full_total) )
                    x2 = x2+1

                else:
                    log("terasort | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                    ResultsSummary.append([str(runId),
                                       		"terasort",
                                      		str(rowCount),
                                      		str(host.items()[0][0]),
                                      		str(stat),
                                      		str(host.items()[0][1])]                                      
                                      		)
                
        #log("terasort | " + str(rowCount) + " | average | cpu_total | " + str(full_total) )               
        # Checking Ganglia stats
        ganglia_stats = config.terasort_ganglia_stats
        
        print "------ Ganglia Stats ! ------ "
        
        for stat in ganglia_stats:
    
            cluster_highest_average_ganglia, individialHostsHighestPoints = get_ganglia_datanodesAverage(dataNodes, stat, start_epoch, finish_epoch, config.crowbar_admin_ip, time_offset)
            log("ganglia | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_ganglia) )
            
            ResultsSummary.append([str(runId),
                                   "terasort",
                                  str(rowCount),
                                  "average",
                                  str(stat),
                                  str(cluster_highest_average_ganglia)])
            
            for host in individialHostsHighestPoints:
                log("terasort | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                ResultsSummary.append([str(runId),
                                       "terasort",
                                      str(rowCount),
                                      str(host.items()[0][0]),
                                      str(stat),
                                      str(host.items()[0][1])]                                      
                                      )
        #removed during TPC testing because upload not available.    
        #upload_results(ResultsSummary)

        #temp-removed**
        #out1, out2 = clear_disks(clean_up_ip)

        #print out1
        #temp-removed**
        #out1, out2 = clear_cache(clean_up_ip)

        #print out1
    i = 0
    for f in folderNames:
        print "Folder name: " + str(folderNames[i])
        i = i+1
    #log(folderNames)
        #time.sleep(60)
        
        # Checking the cm_api stats
            
    
    log( "[[[ DFSIO tests ]]]")

    datapointsToCheck = config.dfsio_cloudera_stats
    #print datapointsToCheck
    
    filesCount_fileSize = config.dfsio_test_values
    
    for fileCount, fileSize in filesCount_fileSize.iteritems():
        log( "[[ DFSIO WRITE Cycle  - file count " + str(fileCount)   + " - file size " + str(fileSize) + "]]")
        ResultsSummary = []
        
       
        dfsio_start, dfsio_end, runtime, throughput, jobID = run_dfsio_job(fileCount, fileSize, edge_ip)
               
        #dfsio_epoch_start = int(time.mktime(dateutil.parser.parse(dfsio_start).timetuple()))
        #dfsio_epoch_end = int(time.mktime(dateutil.parser.parse(dfsio_end).timetuple()))

        dfsio_epoch_start = int(time.mktime(dfsio_start.timetuple()))
        dfsio_epoch_end = int(time.mktime(dfsio_end.timetuple()))
        
       
        runTime = dfsio_epoch_end - dfsio_epoch_start
        log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | job |  runtime | " + str(runTime ))
        ResultsSummary.append([str(runId),
                                       "dfsio",
                                      str(fileCount)  + "-" + str(fileSize),
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )

        
        time.sleep(60) # give time for the stats to become available
        
        # Checking the cm_api stats
        datapointsToCheck = config.dfsio_cloudera_stats
        #print datapointsToCheck
        
        #log( "[Getting cloudera stats]")
        for stat in datapointsToCheck:
            #print stat
            print dfsio_start
            print dfsio_end
	    job_type = 'dfsio'
	    rowCount = 0
            cluster_highest_average_cm, individialHostsHighestPoints, timestamp, full_totals = get_cloudera_dataNodesAverage(edge_ip, dataNodes, stat, dfsio_start, dfsio_end, config.cluster_name, rowCount, job_type, fileCount, fileSize)
            print individialHostsHighestPoints

	    if stat == 'cpu_user_rate':
	    	log("DFsio | " + str(fileCount)  + "-" + str(fileSize) +  " | average | " + stat + " | " + str(cluster_highest_average_cm) )

	    else:
            	log("DFsio | " + str(fileCount)  + "-" + str(fileSize) +  " | average | " + stat + " | " + str(cluster_highest_average_cm) )
	    x = 0
            for host in individialHostsHighestPoints:
		if stat == 'cpu_user_rate':
			output = host.items()[0][1]
			log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(output) )
        	        ResultsSummary.append([str(runId),
                	                       "dfsio",
                        	              	str(fileCount)  + "-" + str(fileSize),
                                	      	str(host.items()[0][0]),
                                      		str(stat),
                                      		str(output)]                                      
                                      		)
			full_total = full_totals[x] + output
			#log("terragen | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | CPU Total | " + str(cpu_total[individialHostsHighestPoints.index(host)]) )
			log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | "+ str(host.items()[0][0]) +" | CPU Total | " + str(full_total) )
			x = x+1
		else:

	                log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
        	        ResultsSummary.append([str(runId),
                	                       "dfsio",
                        	              	str(fileCount)  + "-" + str(fileSize),
                                	      	str(host.items()[0][0]),
                                      		str(stat),
                                      		str(host.items()[0][1])]                                      
                                      		)
	#log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | average | cpu_total | " + str(cpu_total) )
#    	upload_results(ResultsSummary)

####################################DFSIO READ################################################

        log( "[[ DFSIO READ Cycle  - file count " + str(fileCount)   + " - file size " + str(fileSize) + "]]")
        ResultsSummary = []
        
       
        dfsio_start, dfsio_end, runtime, throughput, jobID = run_dfsioREAD_job(fileCount, fileSize, edge_ip)
               
        #dfsio_epoch_start = int(time.mktime(dateutil.parser.parse(dfsio_start).timetuple()))
        #dfsio_epoch_end = int(time.mktime(dateutil.parser.parse(dfsio_end).timetuple()))

        dfsio_epoch_start = int(time.mktime(dfsio_start.timetuple()))
        dfsio_epoch_end = int(time.mktime(dfsio_end.timetuple()))
        
       
        runTime = dfsio_epoch_end - dfsio_epoch_start
        log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | job |  runtime | " + str(runTime ))
        ResultsSummary.append([str(runId),
                                       "dfsio",
                                      str(fileCount)  + "-" + str(fileSize),
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )

        
        time.sleep(60) # give time for the stats to become available
        
        # Checking the cm_api stats
        datapointsToCheck = config.dfsio_cloudera_stats
        #print datapointsToCheck
        
        #log( "[Getting cloudera stats]")
        for stat in datapointsToCheck:
            #print stat
            print dfsio_start
            print dfsio_end
	    job_type = 'dfsio'
            cluster_highest_average_cm, individialHostsHighestPoints, timestamp, full_totals = get_cloudera_dataNodesAverage(edge_ip, dataNodes, stat, dfsio_start, dfsio_end, config.cluster_name, rowCount, job_type, fileCount, fileSize)
            print individialHostsHighestPoints

	    if stat == 'cpu_user_rate':
	    	log("DFsio | " + str(fileCount)  + "-" + str(fileSize) +  " | average | " + stat + " | " + str(cluster_highest_average_cm) )

	    else:
            	log("DFsio | " + str(fileCount)  + "-" + str(fileSize) +  " | average | " + stat + " | " + str(cluster_highest_average_cm) )
	    x = 0
            for host in individialHostsHighestPoints:
		if stat == 'cpu_user_rate':
			output = host.items()[0][1]
			log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(output) )
        	        ResultsSummary.append([str(runId),
                	                       "dfsio",
                        	              	str(fileCount)  + "-" + str(fileSize),
                                	      	str(host.items()[0][0]),
                                      		str(stat),
                                      		str(output)]                                      
                                      		)
			full_total = full_totals[x] + output
			#log("terragen | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | CPU Total | " + str(cpu_total[individialHostsHighestPoints.index(host)]) )
			log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | "+ str(host.items()[0][0]) +" | CPU Total | " + str(full_total) )
			x = x+1
		else:

	                log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
        	        ResultsSummary.append([str(runId),
                	                       "dfsio",
                        	              	str(fileCount)  + "-" + str(fileSize),
                                	      	str(host.items()[0][0]),
                                      		str(stat),
                                      		str(host.items()[0][1])]                                      
                                      		)
	#log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | average | cpu_total | " + str(cpu_total) )
    	#upload_results(ResultsSummary)

#####################################################################

##################################################################
 #       # Checking Ganglia stats
 #       ganglia_stats = config.dfsio_ganglia_stats
        
 #       print "------ Ganglia Stats ! ------ "
        
 #       for stat in ganglia_stats:
    
 #           cluster_highest_average_ganglia, individialHostsHighestPoints = get_ganglia_datanodesAverage(dataNodes, stat, dfsio_epoch_start, dfsio_epoch_end, config.crowbar_admin_ip, time_offset)
 #           log("ganglia | " + str(rowCountsBatchValues[y]) + " | average | " + stat + " | " + str(cluster_highest_average_ganglia) )
            
 #           ResultsSummary.append([runId,
 #                                  "dfsio",
 #                                 str(rowCountsBatchValues[y]),
 #                                 "average",
 #                                 stat,
 #                                 str(cluster_highest_average_ganglia)])
            
 #           for host in individialHostsHighestPoints:
 #               log("dfsio | " + str(rowCountsBatchValues[y]) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
 #               ResultsSummary.append([runId,
 #                                      "dfsio",
 #                                     str(rowCountsBatchValues[y]),
 #                                     str(host.items()[0][0]),
 #                                     stat,
 #                                     str(host.items()[0][1])]                                      
 #                                     )
            
 #       upload_results(ResultsSummary)
            
 #       y = y+1

##################################################################
    run_list = 0
    joinFlag = config.hive_join_flag
    aggFlag = config.hive_aggregation_flag
    visits = config.uservisits
    pages = config.pages
    datapointsToCheck = config.hive_cloudera_stats

    if joinFlag == 'True':
        run_list = -2
    if aggFlag == 'True':
        run_list += 1
    #if config.uservisits | config.pages == '':
    #    run_list = 3
        
    #try :
    log( "[[[ Hive tests ]]]")            
    if run_list == 0:
        log('do nothing')

    elif run_list == -1:
        log("[[Running Aggregation then Join]]")
        jobtype = 'HIVE-Agg'
        #stages = [1,2]
        #visits = config.uservisits
        #pages = config.pages
        prepare(edge_ip)
        agg_out, agg_jobID = get_agg_stats(jobtype, edge_ip, runId, visits, pages, dataNodes, cluster_name, crowbar_admin_ip, time_offset, datapointsToCheck)    
        jobtype = 'HIVE-Join'
        join_out, join_jobIDs = get_join_stats(jobtype, runId, visits, pages, dataNodes, cluster_name, crowbar_admin_ip, time_offset, datapointsToCheck)
        hive_run_id = str(config.run_id + " | " + str(join_jobIDs))
        log_hive('---------[[ '+hive_run_id+' ]]-----------')
        log_hive('---------[[agg Id: '+str(agg_jobID)+' ]]-----------')
        log_hive('Type             Date       Time     Duration(s)')
        log_hive(agg_out)
        #log_hive('---------[[ '+runId+' ]]-----------')
        log_hive('Type             Date       Time     Input_data_size      Duration(s)          Throughput(bytes/s)  Throughput/node')       
        log_hive(join_out)
        
    elif run_list == 1:
        log("[[Running Aggregation Only]]")
        prepare(edge_ip)
        jobtype = 'HIVE-Agg'
        #stages = [1,2]
        #visits = config.uservisits
        #pages = config.pages
        agg_out, agg_jobID = get_agg_stats(jobtype, edge_ip, runId, visits, pages, dataNodes, cluster_name, crowbar_admin_ip, time_offset, datapointsToCheck)
        hive_run_id = str(config.run_id + " | " + str(agg_jobID))
        log_hive('---------[[ '+runId+' ]]-----------')
        log_hive('Type             Date       Time     Duration(s)')
        log_hive(agg_out)    
        #print ResultsSummary
    elif run_list == -2:
        log("[[Running Join Only]]")
        #job = 'stage 1'
        jobtype = 'HIVE-Join'
        #stages = [1,2]
        visits = config.uservisits
        pages = config.pages
        #log('run just join')
        prepare(edge_ip)
        join_out, join_jobIDs = get_join_stats(jobtype, runId, visits, pages, dataNodes, cluster_name, crowbar_admin_ip, time_offset, datapointsToCheck)
        hive_run_id = str(config.run_id + " | " + str(join_jobIDs))
        log_hive('---------[[ '+hive_run_id+' ]]-----------')
        #log_hive('---------[[ '+runId+' ]]-----------')
        log_hive('Type             Date       Time     Input_data_size      Duration(s)          Throughput(bytes/s)  Throughput/node')       
        log_hive(join_out)
    else:
        print 'HIVE Uservisists or Pages not set'
            
    #except:
    #    print 'HIVE Uservisists or Pages not set2'
    #    pass
    
    ######################### kmeans ########################################### 
    log("[[[Running Kmeans Test]]]")
    if config.kmeans_flag == 'True':
        #log("running kmeans")
        config_file = '/var/lib/hadoop-hdfs/hibench/kmeans/conf/configure.sh'
        
        #max_iterations = 'MAX_ITERATION'
        #num_clusters = 'NUM_OF_CLUSTERS'
        #num_samples = 'NUM_OF_SAMPLES'
        #samples_per_input = 'SAMPLES_PER_INPUTFILE'
        #dimensions = 'DIMENSIONS'

        #num_iterations = '4'
        num_iterations = config.num_iterations
        num_clusters = config.num_of_clusters
        num_samples = config.num_of_samples
        samples_per_input = config.samples_per_inputfile
        dimensions = config.dimensions

        edit_file('MAX_ITERATION', num_iterations, config_file)
        edit_file('NUM_OF_CLUSTERS', num_clusters, config_file)
        edit_file('NUM_OF_SAMPLES', num_samples, config_file)
        edit_file('SAMPLES_PER_INPUTFILE', samples_per_input, config_file)
        edit_file('DIMENSIONS', dimensions, config_file)
        
        jobtype = 'kmeans'
        log("MAX_ITERATION = " +str(num_iterations)+ " | NUM_OF_CLUSTERS = " +str(num_clusters)+ " | NUM_OF_SAMPLES = " +str(num_samples)+ " | SAMPLES_PER_INPUTFILE = " +str(samples_per_input)+" | DIMENSIONS = " +str(dimensions))
        kmeans_prepare(edge_ip)
        kmeans_out, kmeans_jobIDs = get_multi_stats(jobtype, runId, visits, pages, dataNodes, cluster_name, crowbar_admin_ip, time_offset, datapointsToCheck)
        #log_hive('---------[[ '+runId+' ]]-----------')
        hive_run_id = str(config.run_id + " | " + str(kmeans_jobIDs))
        log_hive('---------[[ '+hive_run_id+' ]]-----------')
        
        log_hive('Type            Date            Time            Input_data_size      Duration(s)          Throughput(bytes/s)  Throughput/node')           
        log_hive(kmeans_out)
    else:
        print "Kmeans not running, flag set to: "+config.kmeans_flag        
        
    #out1, out2 = clean_disks()
    #print out1
    #print out2
    
    #################### TPC Benchmark###########################
    log("[[[Running TPC Benchmark]]")
    num_maps = config.NUM_MAPS
    num_reducers = config.NUM_REDUCERS
    hadoop_user = config.HADOOP_USER
    hdfs_user = config.HDFS_USER
    sleep_between_runs = config.SLEEP_BETWEEN_RUNS
    file = config.tpc_location +'/Benchmark_Parameters.sh'

    
    jobtype = 'tpc'
    if config.tpc_flag == 'true':
        print 'updating config file'
        print file
        #edit_file('NUM_MAPS', num_maps, file)
        #edit_file('NUM_REDUCERS', num_reducers, file)
        #edit_file('HADOOP_USER', hadoop_user, file)
        #edit_file('HDFS_USER', hdfs_user, file)
        #edit_file('SLEEP_BETWEEN_RUNS', sleep_between_runs, file)

        tpc_out, jobIDs = get_multi_stats(jobtype, runId, visits, pages, dataNodes, cluster_name, crowbar_admin_ip, time_offset, datapointsToCheck)
        print jobIDs
        #print out1
        #jobIDs, errors = run_tpc_benchmark(name_node_ip, config.tpc_location, config.tpc_size)
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
        
    
    #
 
if __name__ == '__main__':
    main()
    

    