import time, calendar, re, uuid,  importlib, datetime,  subprocess, paramiko, sys, os, requests
from cm_api.api_client import ApiResource
import dateutil.parser

def c_ssh_as_root(address, command):
    scon = ssh()
    scon.connect_with_user(address, 'root', 'crowbar')
    cl_stdoutd, cl_stderrd = scon.action(command)
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

def teragen(rowNumber, folderName, edge_node_ip):
    '''
    note for this to work : 
    on the edge node : 
    bluepill chef-client stop
    sudo vi /etc/sudoers
    add :
    Defaults:root   !requiretty
    '''
    cmd = 'cd /usr/lib/hadoop-0.20-mapreduce;sudo -u hdfs hadoop jar hadoop-examples-2.0.0-mr1-cdh4.5.0.jar teragen ' + str(rowNumber) +' '+ str(folderName)
    cl_stdoutd, cl_stderrd = c_ssh_as_root(edge_node_ip, cmd)        
    return cl_stdoutd, cl_stderrd

def log(entry, printOutput=True):
    if printOutput:
        print entry
    f = open('Results.log','a')
    f.write(entry + "\n")
    f.close()

def dfsio(numFiles, fileSize, edge_node_ip):
    
    cmd = 'cd /usr/lib/hadoop-0.20-mapreduce;sudo -u hdfs hadoop jar hadoop-test-2.0.0-mr1-cdh4.5.0.jar TestDFSIO -write -nrFiles '+ str(numFiles) +' -fileSize '+ str(fileSize) + ' -resFile /tmp/results.txt'
    cl_stdoutd, cl_stderrd = c_ssh_as_root(edge_node_ip, cmd)        
    return cl_stdoutd, cl_stderrd
    
def rrdtoolXtract(start, end, metric, host, crowbar_admin_ip):
    
    cmd = 'rrdtool fetch /var/lib/ganglia/rrds/Crowbar\ PoC/'+ host + '/' + metric +'.rrd AVERAGE -s '+ str(start) +' -e ' + str(end) 
    cl_stdoutd, cl_stderrd = c_ssh_as_root(crowbar_admin_ip, cmd)
    return cl_stdoutd, cl_stderrd

def run_dfsio_job(fileCount, fileSize, edge_ip):
    bla = dfsio(fileCount, fileSize, edge_ip)
    ls = bla[1].split('\r' );
    for line in ls:
        ma =  re.search("Test exec time sec:\s(.+)", line)
        if ma:
            runTime = ma.group(1)
        ma2 =  re.search("Throughput mb/sec:\s(.+)", line)
        if ma2:
            Throughput = ma2.group(1)
        ma3 =  re.search("Job complete\:\s(.+)", line)
        if ma3:
                jobID = ma3.group(1)   
        
        time.sleep(30)
        session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)

        # Get the MapReduce job runtime from the job id
        cdh4 = None
        for c in session.get_all_clusters():
            if c.version == "CDH4":
                cdh4 = c 
        for s in cdh4.get_all_services():
            if s.name == "mapreduce1":
                mapreduce = s
        ac =  mapreduce.get_activity(jobID)
        start = ac.startTime
        finish = ac.finishTime
                
    return start, finish, runTime, Throughput, jobID
    
    
    
def get_datanode_hosts(edge_ip, clustername):
    hosts = []
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    view = session.get_all_hosts("full")
    for host in view:
       for each in host.roleRefs:
           if 'DATANODE' in  each.roleName :
               hosts.append(host.hostname)
    return hosts


def get_ganglia_datanodesAverage(dataNodes, stat, start_epoch, end_epoch, crowbar_admin_ip):
        # Checking Ganglia stats
        DataNodesCount = 0
        avg = 0.00
        highests = []
        for host in dataNodes: 
                ganglia = rrdtoolXtract(start_epoch, end_epoch, stat, host, crowbar_admin_ip)
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
    
def get_cloudera_dataNodesAverage(edge_node_ip, dataNodes, stat, time_start, time_end):
        session = ApiResource(edge_node_ip, 7180, "admin", "admin", version=5)
        avg = 0.00
        DataNodesCount = 0
        highests = []
        for host in dataNodes:
            tsquery = "select "+ stat  +" where hostid= \""+ host +"\""
            data = []
            hostRes = session.query_timeseries(tsquery, time_start, time_end)       
            for rez in hostRes[0].timeSeries:
                if (len(rez.data) > 0) :
                    for point in rez.data:
                        data.append(point.value)         
                else :
                    pass
            if len(data) > 0:
                highestValue = 0.00
                highestValue = sorted(data, key=float, reverse=True)[0]
                avg = avg  + highestValue
                if highestValue != 0.00:
                    highests.append(dict({host:highestValue}))
                    DataNodesCount += 1
                else:
                    highests.append(dict({host:'0'}))
            else:
                highests.append(dict({host:'0'}))
                     
        if DataNodesCount == 0:
            return "0", []
        return str(avg / DataNodesCount) , highests
               
def run_terragen_job(rowCount, edge_node_ip):
        randFolderName = uuid.uuid4()
       
        bla = teragen(rowCount, randFolderName, edge_node_ip)
        time.sleep(60)
        ls = bla[1].split('\r' );
        for line in ls:
            ma =  re.search("Job complete\:\s(.+)", line)
            if ma:
                jobID = ma.group(1)   
        time.sleep(30)
        session = ApiResource(edge_node_ip,  7180, "admin", "admin", version=5)

        # Get the MapReduce job runtime from the job id
        cdh4 = None
        for c in session.get_all_clusters():
            if c.version == "CDH4":
                cdh4 = c 
        for s in cdh4.get_all_services():
            if s.name == "mapreduce1":
                mapreduce = s
        ac =  mapreduce.get_activity(jobID)
        start = ac.startTime
        finish = ac.finishTime
        return jobID, start, finish

def main():
    

    '''
    on the edge node : 
    sudo vi /etc/sudoers
    add :
    Defaults:root   !requiretty
    '''
    config = importlib.import_module('config') 
    
    
    runId = str(datetime.datetime.now()) + "__" + config.run_id
    
    edge_ip = config.edge_node_ip
    dataNodes = get_datanode_hosts(edge_ip, config.cluster_name)
    
    log( "[[[ Terragen tests ]]]")
    
    rowCountsBatchValues = config.teragen_row_counts
       
    for rowCount in rowCountsBatchValues:
        log( "[[ Terragen Row Count Cycle  " + str(rowCount)   + "]]")
        ResultsSummary = []
        
        jobID, start, finish = run_terragen_job(rowCount, edge_ip)
        
        start_epoch = int(time.mktime(dateutil.parser.parse(start).timetuple()))
        finish_epoch = int(time.mktime(dateutil.parser.parse(finish).timetuple()))

        runTime = finish_epoch - start_epoch
        log("terragen | " + str(rowCount) + " | job | runtime | " + str(runTime ))
        ResultsSummary.append([runId,
                                       "terragen",
                                      str(rowCount),
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )

        time.sleep(60) # give time for the stats to become available
         

        # Checking the cm_api stats
        datapointsToCheck = config.teragen_cloudera_stats
        

        print "------ Cloud Era Stats ! ------ "
        for stat in datapointsToCheck:
            cluster_highest_average_cm, individialHostsHighestPoints = get_cloudera_dataNodesAverage(edge_ip, dataNodes, stat, start, finish)
        
            log("terragen | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_cm) )
            ResultsSummary.append([runId,
                                   "terragen",
                                  str(rowCount),
                                  "average",
                                  stat,
                                  str(cluster_highest_average_cm)])
            
            for host in individialHostsHighestPoints:
                log("terragen | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                ResultsSummary.append([runId,
                                       "terragen",
                                      str(rowCount),
                                      str(host.items()[0][0]),
                                      stat,
                                      str(host.items()[0][1])]                                      
                                      )
              
        # Checking Ganglia stats
        ganglia_stats = config.teragen_ganglia_stats

        #print( "[Getting ganglia stats]")
        print "------ Ganglia Stats ! ------ "
        for stat in ganglia_stats:
            cluster_highest_average_ganglia, individialHostsHighestPoints = get_ganglia_datanodesAverage(dataNodes, stat, start_epoch, finish_epoch, config.crowbar_admin_ip)
           
            log("ganglia | " + str(rowCount) + " | average | " + stat + " | " + str(cluster_highest_average_ganglia) )
            ResultsSummary.append([runId,
                                   "terragen",
                                  str(rowCount),
                                  "average",
                                  stat,
                                  str(cluster_highest_average_ganglia)])
            for host in individialHostsHighestPoints:
                log("terragen | " + str(rowCount) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                ResultsSummary.append([runId,
                                       "terragen",
                                      str(rowCount),
                                      str(host.items()[0][0]),
                                      stat,
                                      str(host.items()[0][1])]                                      
                                      )
        upload_results(ResultsSummary)    
     
    log( "[[[ DFSIO tests ]]]")
    
    filesCount_fileSize = config.dfsio_test_values
    
    for fileCount, fileSize in filesCount_fileSize.iteritems():
        log( "[[ DFSIO Cycle  - file count " + str(fileCount)   + " - file size " + str(fileSize) + "]]")
        ResultsSummary = []
        
       
        dfsio_start, dfsio_end, runtime, throughput, jobID = run_dfsio_job(fileCount, fileSize, edge_ip)
               
        dfsio_epoch_start = int(time.mktime(dateutil.parser.parse(dfsio_start).timetuple()))
        dfsio_epoch_end = int(time.mktime(dateutil.parser.parse(dfsio_end).timetuple()))
        
       
        runTime = dfsio_epoch_end - dfsio_epoch_start
        log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | job |  runtime | " + str(runTime ))
        ResultsSummary.append([runId,
                                       "dfsio",
                                      str(fileCount)  + "-" + str(fileSize),
                                      "job",
                                      "runtime",
                                      str(runTime)]                                   
                                      )

        
        time.sleep(60) # give time for the stats to become available
        
        # Checking the cm_api stats
        datapointsToCheck = config.dfsio_cloudera_stats
        
        
        #log( "[Getting cloudera stats]")
        for stat in datapointsToCheck:
            cluster_highest_average_cm, individialHostsHighestPoints = get_cloudera_dataNodesAverage(edge_ip, dataNodes, stat, dfsio_start, dfsio_end)
            log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | average | " + stat + " | " + str(cluster_highest_average_cm) )
            ResultsSummary.append([runId,
                                   "dfsio",
                                  str(fileCount)  + "-" + str(fileSize),
                                  "average",
                                  stat,
                                  str(cluster_highest_average_cm)])
            
            for host in individialHostsHighestPoints:
                log("dfsio | " + str(fileCount)  + "-" + str(fileSize) + " | "+ str(host.items()[0][0]) +" | " + stat + " | " + str(host.items()[0][1]) )
                ResultsSummary.append([runId,
                                       "dfsio",
                                      str(fileCount)  + "-" + str(fileSize),
                                      str(host.items()[0][0]),
                                      stat,
                                      str(host.items()[0][1])]                                      
                                      )
        upload_results(ResultsSummary)
    log( "[[[ That's all folks ]]]"  )
    
    
    #
    
    
    
    
    
    
        
if __name__ == '__main__':
    main()
    

    