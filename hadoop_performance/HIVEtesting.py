import time, calendar, re, uuid,  importlib, datetime,  subprocess, paramiko, sys, os, requests
from cm_api.api_client import ApiResource
import dateutil.parser
from datetime import timedelta

def c_ssh_as_root(address, command):
    scon = ssh()
    scon.connect_with_user(address, 'root', 'cr0wBar!')
    cl_stdoutd, cl_stderrd = scon.action(command)
    scon.close()
    return cl_stdoutd, cl_stderrd

def c_ssh_as_shell_noOutput(address, command, sleepFor):
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(address,username = "root",password = "crowbar")
        channel = conn.invoke_shell()
        time.sleep(1)
        channel.recv(9999) # ptompt
        channel.sendall(command)
        time.sleep(sleepFor) 
        out = channel.recv(9999)

def c_ssh_as_shell(address, command, sleepFor):
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(address,username = "root",password = "crowbar")
        channel = conn.invoke_shell()
        time.sleep(1)
        channel.recv(9999) # ptompt
        channel.sendall(command)
        time.sleep(sleepFor)       
        out = channel.recv(9999)
        ret = []
        ls = re.split("\n|\r", out)
        del ls[0]
        del ls[-1]
        for each in ls:
            if (each!=""):
                ret.append(each)
        return ret

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
        self.connect_with_user(address, 'crowbar', 'crowbar')
    
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

    f = open('upload.log','a')
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


def get_other_cpu_stats(timestamp, host, rowCount, job_type, fileCount, fileSize, cpu_user_value):
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
    numCores = 32
    #get_datanode_cores(edge_ip, clustername, host)
    print 'hostname = ' + str(hostname)
    print 'CORES cpu data: ' +str(numCores)
    #tsquery = "select "+stat+" where hostname = \""+ host +"\" and category = Host"
    sec = timedelta(seconds=1)

    time_start = timestamp-sec   # GMT +1
 
    time_end = timestamp+sec


    
    for stat in cpu_stats:
        
        tsquery = "select "+stat+" / "+str(numCores)+" * 100 where hostname = \""+ host +"\" and category = Host"
        print str(tsquery)
        print time_start
        print time_end
        hostRes = session.query_timeseries(tsquery, time_start, time_end)
        #for x in hostRes:
            #log('host rez[x]: '+ str(hostRes[hostRes.index(x)]))
        for rez in hostRes[0].timeSeries:
            #print str(len(rez.data))
            for point in rez.data:
                cpu_total.append(point.value)
                data.append(str(stat)+ " : " + str(point.value))
                #timestamp = point.timestamp
                #print "timestamp = "+  str(timestamp)
                if job_type == 'dfsio':
                    log(job_type +" | " + str(fileCount)  + "-" + str(fileSize) + " | "+ str(host) +" | " + stat + " | " + str(point.value) )
                elif job_type == 'HIVE-Join':
                    log(job_type +" | "+ str(host) +" | " + stat + " | " + str(point.value) )
                elif job_type == 'kmeans':
                    log(job_type +" | "+ str(host) +" | " + stat + " | " + str(point.value) )
                else:
                    log(job_type + " | " + str(rowCount) + " | "+ str(host) +" | " + stat + " | " + str(point.value) )
                    
    #print point.value
    total = 0
    for value in cpu_total:
        total = total+value
    #total = total + cpu_user_value
    #log(job_type + " | " + str(rowCount) + " | cpu_total | " + str(total) )
    #full_totals.append(total)
    print data
    return data, total

def get_datanode_hosts(edge_ip, clustername):
    hosts = []
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
       for each in host.roleRefs:
           if 'DATANODE' in  each.roleName :
               hosts.append(host.ipAddress)
    return hosts

def get_datanode_entityname(edge_ip, clustername, ipAddress):
    hosts = []
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
        if ipAddress ==  host.ipAddress:
               return host.hostname
    return hosts    

def convert_cpu_stats(cpu_stats, numCores):
    #edge_ip = "172.16.2.21"
    #clustername = "Cluster 1"

    #session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    #cluster = session.get_cluster(clustername)

    #hostlist = session.get_all_hosts("full")
    #print str(hostlist)
    #print cpu_stats

    # cpu_user_rate / getHostFact(numCores, 1) * 100

    #for stats in cpu_stats:
    cpu_data_perc = float(cpu_stats)/numCores*100
    return cpu_data_perc


def getHIVE_cloudera_dataNodesAverage(edge_node_ip, dataNodes, stat, time_start, time_end, cluster_name, job_type):
        session = ApiResource(edge_node_ip, 7180, "admin", "admin", version=6)
        avg = 0.00
        DataNodesCount = 0
        highests = []
	cpu_total = []
	full_totals = [2, 4, 5]
	highestCPU = 0
        for host in dataNodes:
            print host
            host = get_datanode_entityname(edge_node_ip, cluster_name, host)
            tsquery = "select "+stat+" where hostname = \""+ host +"\" and category = Host"
            print tsquery
            data = []
	    points = {}
	    timestamps = []
	    total = 0

	    #timestamp = []
	    #rowCount = 10000000000

            hostRes = session.query_timeseries(tsquery, time_start, time_end)
	    print 'hostRes[0] = ' + str(hostRes[0])       
            for rez in hostRes[0].timeSeries:
                print str(len(rez.data))
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
		    #timestamp = 0
                    highests.append(dict({host:'0'}))
            else:
		timestamps.append(0)
                highests.append(dict({host:'0'}))
            #if stat == 'cpu_user_rate':
		#log("Highest "+ str(highests))
		#log("highestCPU "+ str(highestCPU))
		#log("Host "+ str(host))
		#log("index "+ str(dataNodes))
	    	#other_cpu_stats, full_total = get_other_cpu_stats(timestamps[0], host, rowCount, job_type, fileCount, fileSize, highestCPU)
		#full_totals.append(full_total)
         	#total = total + cpu_total
		#log("otherStats " + str(other_cpu_stats))
		#log(str(full_totals))
        if DataNodesCount == 0:
            return "0", [], [], []
        return str(avg / DataNodesCount) , highests, timestamps[0], full_totals


def c_ssh_multiple_commands(address, commands):
        
    scon = ssh()
    scon.connect(address)
    cmd = ''
    for com in commands:
    	cmd = cmd + com + ";"
    cl_stdoutd, cl_stderrd = scon.action(cmd) 
    scon.close()
         
    return  cl_stdoutd, cl_stderrd

def log(entry, printOutput=True):
    if printOutput:
        print entry
    f = open('Results.log','a')
    f.write(entry + "\n")
    f.close()

def rrdtoolXtract(start, end, metric, host, crowbar_admin_ip, time_offset):
    offset = time_offset*60*60
    start = start - offset
    end = end - offset
    #host = "172.16.2.29"
    #host = "da0-36-9f-32-73-74.dell.com"
    #log(str(start))
    #log(str(end))
    #log(str(host))
    cmd = 'rrdtool fetch /var/lib/ganglia/rrds/Crowbar\ PoC/'+ host + '/' + metric +'.rrd AVERAGE -s '+ str(start) +' -e ' + str(end) 
    #log(str(cmd))
    cl_stdoutd, cl_stderrd = c_ssh_as_root(crowbar_admin_ip, cmd)
    return cl_stdoutd, cl_stderrd

def get_ganglia_datanodesAverage(dataNodes, stat, start_epoch, end_epoch, crowbar_admin_ip, time_offset):
        # Checking Ganglia stats
        DataNodesCount = 0
        avg = 0.00
        highests = []
	#config = importlib.import_module('config_cdh5')
	edge_ip = '172.16.2.21'
	clustername = "Cluster 1"
    	crowbar_admin_ip = "172.16.2.18"
        for host in dataNodes:
		entity = get_datanode_entityname(edge_ip, clustername, host)
                ganglia = rrdtoolXtract(start_epoch, end_epoch, stat, entity, crowbar_admin_ip, time_offset)
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

def update_config_file():
    log("updating config file")

def run_hive_join():
    log("running join")

def run_hive_agg():
    log("running join")

def prepare(edge_node_ip):
    log('prepare start')
    #cmd = 'su hdfs; cd /var/lib/hadoop-hdfs/hibench/hivebench/bin/; ./prepare.sh'
    cmd = ' su hdfs - -c "/var/lib/hadoop-hdfs/hibench/hivebench/bin/prepare.sh"'
    #cmd = 'su hdfs'

    print "running: " + cmd 
    cl_stdoutd, cl_stderrd = c_ssh_as_root(edge_node_ip, cmd)        
    print cl_stdoutd
    print cl_stderrd
    log('prepare end')
    return cl_stdoutd, cl_stderrd

def get_join_jobIDs(edge_node_ip):
	jobIDs = []
	starttimes = []
	finishtimes = []

	timeA = datetime.datetime.now()-datetime.timedelta(1)
        print str(timeA)
	bla = join(edge_node_ip)
	#log(str(bla))
        time.sleep(60)
        ls = bla[1].split('\r' );
	#log('ls: ' + str(ls))
	x = 0
        for line in ls:
	    x = x+1
            print str(line)
	    #log('line ' + str(ls.index(line)) +': ' + str(line) + ' LINE END')
            jobIDs =  re.findall("Starting Job = (.+),", line)
	    #jobIDs.append(ma)
	    #jobIDs.append(line)
	    #for each in jobIDs:
		    #if each:
        	       #jobID = each[0].group(1)
	       	       #jobIDs.append(jobID)
		       #jobIDs.append(ma)
	       	       #log(str(each))

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
		starttimes.append(start)
        	finish = ob.endTime
		finishtimes.append(finish)
		log(str(start))
		log(str(finish))

        return jobIDs, starttimes, finishtimes
	

def run_join(edge_node_ip):
	jobIDs = get_join_jobIDs(edge_node_ip)

        timeA = datetime.datetime.now()-datetime.timedelta(1)
        print str(timeA)
        bla = join(edge_node_ip)
        time.sleep(60)
        ls = bla[1].split('\r' );
        for line in ls:
            print str(line)
            ma =  re.findall("Started Job = (.+),", line)
	    #log(str(ma))
	    if ma:
                jobID = ma.group(1)
		jobIDs.append(jobID)
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
            if s.name == "yarn":
                mapreduce = s
        ac =  mapreduce.get_yarn_applications(timeA, timeB)
        print str(ac)
        print str(ac.warnings)
        for job in ac.applications:
            if jobID == str(job.applicationId):
                ob = job         
        start = ob.startTime
        finish = ob.endTime
        return jobID, start, finish


def join(edge_node_ip):
    cmd = 'sudo su - hdfs - -c "/var/lib/hadoop-hdfs/hibench/hivebench/bin/run-join.sh"' 
    print "running: " + str(cmd) 
    cl_stdoutd, cl_stderrd = c_ssh_as_root(edge_node_ip, cmd)      
    print cl_stdoutd
    print cl_stderrd
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
        time.sleep(60)
        ls = bla[1].split('\r' );
	#log('ls: ' + str(ls))
        for line in ls:
            print str(line)
            ma =  re.search("Job = (.+),", line)
            if ma:
                jobID = ma.group(1)   
        #time.sleep(30)
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
            if s.name == "yarn":
                mapreduce = s
        ac =  mapreduce.get_yarn_applications(timeA, timeB)
        print str(ac)
        print str(ac.warnings)
        for job in ac.applications:
            if jobID == str(job.applicationId):
		log(str(jobID))
                ob = job         
        start = ob.startTime
        finish = ob.endTime
        return jobID, start, finish

def get_agg_stats(jobtype, edge_ip, runId, visits, pages, dataNodes, cluster_name, crowbar_admin_ip, time_offset):

	ResultsSummary = []
	jobID, start, finish = run_agg(edge_ip)
	print jobID
	start_epoch = int(time.mktime(start.timetuple()))
        finish_epoch = int(time.mktime(finish.timetuple()))

        runTime = finish_epoch - start_epoch
        log("HIVE-AGG | visits | "+str(visits)+" | pages | "+str(pages)+" | job | runtime | " + str(runTime ))
        ResultsSummary.append([runId,
                                       "HIVE-agg",
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )
	datapointsToCheck = (#'cpu_soft_irq_rate',
		           #'cpu_iowait_rate',
			   #'cpu_irq_rate',
			   'cpu_user_rate',
			   #'load_15',
			   #'load_5',
			   #'load_1',
			   #'cpu_system_rate',
			   #'physical_memory_buffers',
			   #'physical_memory_cached',
			   'physical_memory_used',
			   #'swap_used',
			   #'swap_out_rate',
			   #'total_bytes_receive_rate_across_network_interfaces',
                           #'total_bytes_transmit_rate_across_network_interfaces',
			   #'await_time',
			   'total_read_bytes_rate_across_disks',
			   'total_write_bytes_rate_across_disks',
			   #'total_read_ios_rate_across_disks',
			   #'total_write_ios_rate_across_disks'

			 )
	for stat in datapointsToCheck:
    	    print 'start = ' + str(start)
	    print 'finish = ' + str(finish)
	    job_type = 'HIVE-Agg'
	    fileCount = 0
	    fileSize = 0 
            cluster_highest_average_cm, individialHostsHighestPoints, timestamp, full_totals = getHIVE_cloudera_dataNodesAverage(edge_ip, dataNodes, stat, start, finish, cluster_name, job_type)
            print individialHostsHighestPoints
	    if timestamp == 0:
		print timestamp
		pass
	    

	    if stat == 'cpu_user_rate':
	    	log("HIVE-Agg | average | " + stat + " | " + str(convert_cpu_stats(cluster_highest_average_cm, 24)) )

	    else:
            	log("HIVE-Agg | average | " + stat + " | " + str(cluster_highest_average_cm) )

            ResultsSummary.append([runId,
                                  "HIVE-Agg",
                                  "average",
                                  stat,
                                  str(cluster_highest_average_cm)])
            x = 0
            for host in individialHostsHighestPoints:
	    	if stat == 'cpu_user_rate':
			output = convert_cpu_stats(host.items()[0][1], 24)	
	                log("Hive-Agg | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(output) )
        	        ResultsSummary.append([runId,
                	                       "Hive-Agg",
                                	      str(host.items()[0][0]),
                                     	      stat,
                                      	      str(output)]                                      
                                      	      )
			full_total = full_totals[x] + output
			#log("Hive-Agg | CPU Total | " + str(cpu_total[individialHostsHighestPoints.index(host)]) )
			log("Hive-Agg | "+ str(host.items()[0][0]) +" | CPU Total | " + str(full_total) )
			x = x+1
		else:
			log("Hive-Agg | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
        	        ResultsSummary.append([runId,
                	                       "Hive-agg",
                                	      str(host.items()[0][0]),
                                     	      stat,
                                      	      str(host.items()[0][1])]                                      
                                      	      )
	#log("terragen | " + str(rowCount) + " | cpu_total | " + str(cpu_total) )

	ganglia_stats = (#'boottime',
			 'bytes_in',
			 'bytes_out',
			)
	print "------ Ganglia Stats ! ------ "
        for stat in ganglia_stats:
            cluster_highest_average_ganglia, individialHostsHighestPoints = get_ganglia_datanodesAverage(dataNodes, stat, start_epoch, finish_epoch, crowbar_admin_ip, time_offset)
           
            log("ganglia | average | " + stat + " | " + str(cluster_highest_average_ganglia) )
            ResultsSummary.append([runId,
                                   "HIVE-Agg",
                                  "average",
                                  stat,
                                  str(cluster_highest_average_ganglia)])
            for host in individialHostsHighestPoints:
                log("HIVE-Agg | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                ResultsSummary.append([runId,
                                       "HIVE-Agg",
                                      str(host.items()[0][0]),
                                      stat,
                                      str(host.items()[0][1])]                                      
                                      )
        upload_results(ResultsSummary)    


def get_join_stats(jobtype, runId, visits, pages, dataNodes, cluster_name, crowbar_admin_ip, time_offset):

	ResultsSummary = []
	edge_ip = '172.16.2.21'
	jobIDs, starttimes, finishtimes = get_join_jobIDs(edge_ip)
	stage = 5678
	#if jobtype == 'HIVE-Join':
	#	if stage == 1:
	#		start = starttimes[0]
	#		finish = finishtimes[0]
	#	elif stage == 2:
	#		start = starttimes[1]
	#		finish = finishtimes[1]
	#	else:
	#		print 'stage not defined'

	for each in jobIDs:
		if jobIDs.index(each) == 0:
			start = starttimes[0]
			finish = finishtimes[0]
		elif jobIDs.index(each) == 1:
			start = starttimes[1]
			finish = finishtimes[1]
		else:
			print 'stage not defined'



		start_epoch = int(time.mktime(start.timetuple()))
        	finish_epoch = int(time.mktime(finish.timetuple()))

        	runTime = finish_epoch - start_epoch
        	log(str(jobtype) + " | visits | "+str(visits)+" | pages | "+str(pages)+" | " + jobtype + " | runtime | " + str(runTime ))
        	ResultsSummary.append([runId,
                                       "HIVE-join",
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )

		datapointsToCheck = (#'cpu_soft_irq_rate',
		           #'cpu_iowait_rate',
			   #'cpu_irq_rate',
			   'cpu_user_rate',
			   #'load_15',
			   #'load_5',
			   #'load_1',
			   #'cpu_system_rate',
			   #'physical_memory_buffers',
			   #'physical_memory_cached',
			   'physical_memory_used',
			   #'swap_used',
			   #'swap_out_rate',
			   #'total_bytes_receive_rate_across_network_interfaces',
                           #'total_bytes_transmit_rate_across_network_interfaces',
			   #'await_time',
			   'total_read_bytes_rate_across_disks',
			   'total_write_bytes_rate_across_disks',
			   #'total_read_ios_rate_across_disks',
			   #'total_write_ios_rate_across_disks'

			 	)

		for stat in datapointsToCheck:
    	    		print 'start = ' + str(start)
	    		print 'finish = ' + str(finish)
	    		#job_type = 'HIVE-Join'
	    		fileCount = 0
	    		fileSize = 0 
            		cluster_highest_average_cm, individialHostsHighestPoints, timestamp, full_totals = getHIVE_cloudera_dataNodesAverage(edge_ip, dataNodes, stat, start, finish, cluster_name, jobtype)
            		print individialHostsHighestPoints
	    		if timestamp == 0:
				print timestamp
				pass
	    

	    		if stat == 'cpu_user_rate':
	    			log("HIVE-Join | average | " + stat + " | " + str(convert_cpu_stats(cluster_highest_average_cm, 24)) )

	    		else:
            			log("HIVE-Join | average | " + stat + " | " + str(cluster_highest_average_cm) )

            		ResultsSummary.append([runId,
                                  "HIVE-Join",
                                  "average",
                                  stat,
                                  str(cluster_highest_average_cm)])
            		x = 0
            		for host in individialHostsHighestPoints:
	    			if stat == 'cpu_user_rate':
					output = convert_cpu_stats(host.items()[0][1], 24)	
	                		log("Hive-Join | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(output) )
        	        		ResultsSummary.append([runId,
                	                       "Hive-Join",
                                	      str(host.items()[0][0]),
                                     	      stat,
                                      	      str(output)]                                      
                                      	      	)
					full_total = full_totals[x] + output
					#log("Hive-Join | CPU Total | " + str(cpu_total[individialHostsHighestPoints.index(host)]) )
					log("Hive-Join | "+ str(host.items()[0][0]) +" | CPU Total | " + str(full_total) )
					x = x+1
				else:
					log("Hive-Join | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
        	        		ResultsSummary.append([runId,
                	                       "Hive-Join",
                                	      str(host.items()[0][0]),
                                     	      stat,
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
            		ResultsSummary.append([runId,
                                   "HIVE-Join",
                                  "average",
                                  stat,
                                  str(cluster_highest_average_ganglia)])
            		for host in individialHostsHighestPoints:
                		log("HIVE-Join | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                		ResultsSummary.append([runId,
                                       "HIVE-Join",
                                      str(host.items()[0][0]),
                                      stat,
                                      str(host.items()[0][1])]                                      
                                      )
        	upload_results(ResultsSummary)    
	
def clean_disks():
    name_node_ip = '172.16.11.141'
    cmd = 'sudo -u hdfs hadoop fs -rm -R -f -skipTrash /user/hdfs/*'
    print "running " + cmd 
    #cl_stdoutd, cl_stderrd = c_ssh_as_root(name_node_ip, cmd)        
    print cl_stdoutd
    print cl_stderrd
    return cl_stdoutd, cl_stderrd

def check_disks(name_node_ip):
    cmd2 = 'sudo -u hdfs hadoop fs -ls hdfs:///user/hdfs'
    cl_stdoutd, cl_stderrd = c_ssh_as_root(name_node_ip, cmd2)
    print 'ls out: ' + str(cl_stdoutd)
    if cl_stderrd != '':
        print 'error: ' +str(cl_stderrd)
        sys.exit()
    if cl_stdoutd != '':
        print 'files not deleted: ' + str(cl_stdoutd)
        sys.exit()

def check_cache(name_node_ip):
    #cmd2 = 'sudo -u hdfs hadoop fs -ls hdfs:///user/hdfs'
    cl_stdoutd, cl_stderrd = c_ssh_as_root(name_node_ip, cmd2)
    print 'ls out: ' + str(cl_stdoutd)
    if cl_stderrd != '':
        print 'error: ' +str(cl_stderrd)
        sys.exit()
    if cl_stdoutd != '':
        print 'cache not cleared'
        sys.exit()

def clear_disks(name_node_ip):
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

    check_disks(name_node_ip)
    return cl_stdoutd, cl_stderrd

def clear_cache(name_node_ip):
    log("Clearing cache")
    #name_node_ip = '172.16.11.141'
    cmd = 'clush -w r2s1xd[1-10] "sync"'
    cmd2 = 'clush -w r2s1xd[1-10] "echo 3> /proc/sys/vm/drop_caches"'
    print "running " + cmd 
    syncOut, syncError = c_ssh_as_root(name_node_ip, cmd)
    print 'syncOut' + str(syncOut)
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

def main():
    

    '''
    on the edge node : 
    sudo vi /etc/sudoers
    add :
    Defaults:root   !requiretty
    '''

    print "5.2 api testing"
    edge_node_ip = '172.16.11.143'
    runId = 'run1'
    crowbar_admin_ip = "172.16.2.18"
    time_offset = 6
    ResultsSummary = []

    session = ApiResource(edge_node_ip,  7180, "admin", "admin", version=6)
    jobID = 'job_201501051811_0045'

    # Get the MapReduce job runtime from the job id
    cdh4 = None
    for c in session.get_all_clusters():
        print "c: " +str(c)
        if c.version == "CDH5":
            cdh4 = c 
    for s in cdh4.get_all_services():
        print "s = " + str(s)
        if s.name == "yarn":
            mapreduce = s
        elif s.name == "mapreduce":
            mapreduce = s

    ac = mapreduce.get_activity(jobID)
    print jobID
    print str(ac.startTime)
    print str(ac.finishTime)
    tsquery = 'select total_write_bytes_rate_across_disks where hostname = "r2s1xd8.rcbd.lab" and category = Host'
    time_start = '2014-12-12 06:15:00.616000'
    time_end = '2014-12-10 06:17:00.616000'

    start = '2014-12-12T11:21:08.000Z'
    start = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S.%fZ')

    end = '2014-12-12T11:22:09.301Z'
    end = datetime.datetime.strptime(end, '%Y-%m-%dT%H:%M:%S.%fZ')
    
    #hostRes = session.query_timeseries(tsquery, start, end)
    
    #print hostRes
    #abb = hostRes[0].timeSeries
    #print "Timeseries: " + str(abb)
    #print str(abb[0].data)
    #for x in abb[0].data:
    #    print abb[0].data[abb[0].data.index(x)].value
    #    print abb[0].data[abb[0].data.index(x)].timestamp
    #    print abb[0].data[abb[0].data.index(x)].type

    timestamp = datetime.datetime(2015, 1, 6, 7, 21, 53)
    timestamp2 = datetime.datetime(2015, 1, 6, 7, 22, 6)
    timestamp3 = datetime.datetime(2015, 1, 6, 7, 21, 53)
    timestamp4 = datetime.datetime(2015, 1, 6, 7, 22, 6)
    timestamp5 = datetime.datetime(2015, 1, 6, 7, 21, 53)
    timestamp6 = datetime.datetime(2015, 1, 6, 7, 22, 6)
    timestamp7 = datetime.datetime(2015, 1, 6, 7, 21, 53)
    timestamp8 = datetime.datetime(2015, 1, 6, 7, 22, 6)
    timestamp9 = datetime.datetime(2015, 1, 6, 7, 21, 52)
    timestamp10 = datetime.datetime(2015, 1, 6, 7, 22, 6)
    #2014-12-15 09:47:03
    #r2s1xd8.rcbd.lab
    #1500000000
    #terasort
    #0
    #0
    #46.3817708333 

    host = 'r2s1xd6.rcbd.lab'
    rowCount = 100
    job_type = 'teragen'
    fileCount = 123
    fileSize = 321
    cpu_user_value = 998877

    host2 = 'r2s1xd1.rcbd.lab'
    rowCount2 = 100
    job_type2 = 'teragen'
    fileCount2 = 123
    fileSize2 = 321
    cpu_user_value2 = 998877
    
    host3 = 'r2s1xd3.rcbd.lab'
    host4 = 'r2s1xd4.rcbd.lab'
    host5 = 'r2s1xd5.rcbd.lab'
    host7 = 'r2s1xd7.rcbd.lab'
    host8 = 'r2s1xd8.rcbd.lab'
    host9 = 'r2s1xd9.rcbd.lab'
    host10 = 'r2s1xd10.rcbd.lab'
    
    
    #otherCPU = get_other_cpu_stats(timestamp, host, rowCount, job_type, fileCount, fileSize, cpu_user_value)

    #otherCPU2 = get_other_cpu_stats(timestamp2, host2, rowCount2, job_type2, fileCount2, fileSize2, cpu_user_value2)
    #otherCPU3 = get_other_cpu_stats(timestamp3, host2, rowCount2, job_type2, fileCount2, fileSize2, cpu_user_value2)
    #otherCPU4 = get_other_cpu_stats(timestamp4, host2, rowCount2, job_type2, fileCount2, fileSize2, cpu_user_value2)
    #otherCPU5 = get_other_cpu_stats(timestamp5, host2, rowCount2, job_type2, fileCount2, fileSize2, cpu_user_value2)
    #otherCPU6 = get_other_cpu_stats(timestamp6, host2, rowCount2, job_type2, fileCount2, fileSize2, cpu_user_value2)
    #otherCPU7 = get_other_cpu_stats(timestamp7, host2, rowCount2, job_type2, fileCount2, fileSize2, cpu_user_value2)
    #otherCPU8 = get_other_cpu_stats(timestamp8, host2, rowCount2, job_type2, fileCount2, fileSize2, cpu_user_value2)
    #otherCPU9 = get_other_cpu_stats(timestamp9, host9, rowCount2, job_type2, fileCount2, fileSize2, cpu_user_value2)
    #otherCPU10 = get_other_cpu_stats(timestamp10, host2, rowCount2, job_type2, fileCount2, fileSize2, cpu_user_value2)

    #print otherCPU

    #print otherCPU2
    #print otherCPU9
    host = 'r2s1xd10.rcbd.lab'
    hostName = re.search("(.[a-z0-9]+)", host)
    host1 = hostName.group(1)
    host0 = hostName.group(0)

    #print host0
    #print host1
    name_node_ip = '172.16.11.141'
    
    #out1, out2 = clear_disks(name_node_ip)
    #out1, out2 = clear_cache(name_node_ip)
    #print out1
    #print out2
    
    #2015-01-06 07:21:51
    #2015-01-06 07:21:53
    
    print '---------------------------'
    tsquery = 'select cpu_soft_irq_rate / 32 * 100 where hostname = "r2s1xd6.rcbd.lab" and category = Host'
    time_start = datetime.datetime(2015, 1, 6, 7, 21, 51)
    time_end = datetime.datetime(2015, 1, 6, 7, 21, 53)    
    hostRes = session.query_timeseries(tsquery, time_start, time_end)
    print 'tsquery =    ' + str(tsquery)
    print 'time_start = '+str(time_start)
    print 'time_end =   '+str(time_end)

    for rez in hostRes[0].timeSeries:
        for point in rez.data:
            print 'point:           ' + str(point)
            print 'point.value:     ' + str(point.value)
            print 'point.timestamp: ' + str(point.timestamp)

if __name__ == '__main__':
    main()
    