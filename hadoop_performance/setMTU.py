import time, calendar, re, uuid,  importlib, datetime,  subprocess, paramiko, sys, os, requests
from cm_api.api_client import ApiResource
import dateutil.parser
import urllib2
from datetime import timedelta

def c_ssh_as_root(address, command):
    scon = ssh()
    scon.connect_with_user(address, 'root', 'Ignition01')
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

class Scp():

    def __init(self):

        self.client = paramiko.SSHClient()

        self.client.load_system_host_keys()

        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def open_remote_file(self, address, file):
        output = []
        trans = paramiko.Transport((address, 22))
        try:

            trans.connect(username = 'root', password = 'Ignition01')
            sftp = paramiko.SFTPClient.from_transport(trans)
            remote_file = sftp.open(file)
        #try:
            for line in remote_file:
                #print line
                output.append(line)
        except:
            print 'password error'			
        finally:
            if len(output)>0:
                remote_file.close()

        return output
        
    def put_file(self, address, localfile, remotefile):
        trans = paramiko.Transport((address, 22))

        trans.connect(username = 'root', password = 'cr0wBar!')

        sftp = paramiko.SFTPClient.from_transport(trans)
        sftp.put(localfile, remotefile)
        
        sftp.close()

        trans.close()

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

def edit_file(node, target, new_value, file):
    myScp = Scp()
    #open the config file
    output = myScp.open_remote_file(node, file)
    
    scon = ssh()
    scon.connect_with_user(node, 'root', 'Ignition01')
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
            cl_stdoutd, cl_stderrd = c_ssh_as_root(node, cmd)

def get_datanode_hosts(edge_ip, clustername):
    hosts = []
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    print "cluster: " + str(cluster)
    view = session.get_all_hosts("full")
    print view
    for host in view:
        for each in host.roleRefs:
            if 'DATANODE' in  each.roleName :
                hosts.append(host.ipAddress)
    return hosts
	
def get_all_hosts(edge_ip, clustername):
    hosts = []
    session = ApiResource(edge_ip,  7180, "admin", "admin", version=5)
    cluster = session.get_cluster(clustername)
    print "cluster: " + str(cluster)
    view = session.get_all_hosts("full")
    print view
    for host in view:
        for each in host.roleRefs:
            if host.ipAddress in hosts:
                print 'already in'
            else:
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

def getStat(node, target, file):
    myScp = Scp()
    #open the config file
    output = myScp.open_remote_file(node, file)
    
    scon = ssh()
    try:
        scon.connect_with_user(node, 'root', 'Ignition01')
    except:
        print 'Unexpected error: '#, sys.exc_info()[0]
    #hold the current value of the variable to build the sed string
    current_value = ''
    #go through each line of the config and find the live and commented variables
    if len(output) > 0:
        for line in output:
            config_variable = re.findall("^"+target+"=(.+)", line)
            # print 'Node: ' + str(node) + ', Value: ' + str(config_variable)
            #cl_stdoutd, cl_stderrd = c_ssh_as_root(node, cmd)
        return node, config_variable
    else:
        config_variable = 'Not available'
        return node, config_variable

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

    print "setting MTU on all nodes"
    edge_node_ip = '172.16.14.101'
    clustername = 'Cluster 1'
    runId = 'run1'
    crowbar_admin_ip = "172.16.116.220"
    ResultsSummary = []

    print urllib2.getproxies()

    session = ApiResource(edge_node_ip,  7180, "admin", "admin", version=6)
    print session.get_cloudera_manager
    print session.version
    print session.get_all_users()
    view = session.get_all_hosts("full")

    target = 'MTU'
    new_value = '9710'
    file = '/etc/sysconfig/network-scripts/ifcfg-bond0'

    for each in view:
        print each

    for c in session.get_all_clusters():
        print str(c.name)
        if c.version == "CDH5":
            cdh4 = c 
    for s in cdh4.get_all_services():
        print s.name
        if s.name == "yarn":
            mapreduce = s
        elif s.name == "mapreduce":
            mapreduce = s

    all_nodes = get_all_hosts(edge_node_ip,  clustername)
    for each in all_nodes:
        #print each
        #each = '172.16.14.89'
        #edit_file(each, target, new_value, file)
        node, value = getStat(each, target, file)
        print 'Node: ' +str(node) + 'MTU value: ' + str(value)

if __name__ == '__main__':
    main()
    