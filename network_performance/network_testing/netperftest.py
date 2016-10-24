#
# Copyright (c) 2015-2016 Dell Inc. or its subsidiaries.
#
# This file is free software:  you can redistribute it and or modify
# it under the terms of the GNU General Public License, as published
# by the Free Software Foundation, version 3 of the license or any
# later version.
#
# This file is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.


import time, calendar, re, uuid,  importlib, datetime,  subprocess, paramiko, sys, os, requests, logging, random
from cm_api.api_client import ApiResource
import dateutil.parser
from datetime import timedelta
from auto_common import *
import logging
import threading

logging.basicConfig()

class Scp():

    def __init(self):

        self.client = paramiko.SSHClient()

        self.client.load_system_host_keys()

        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def open_remote_file(self, address, file):
        output = []
        trans = paramiko.Transport((address, 22))
        trans.connect(username = 'root', password = 'crowbar')
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

        trans.connect(username = 'root', password = 'crowbar')

        sftp = paramiko.SFTPClient.from_transport(trans)
        sftp.put(localfile, remotefile)
        
        sftp.close()

        trans.close()

def edit_file(target, new_value, file):
    config = importlib.import_module('config_cdh5') 
    edge_node_ip = config.edge_node_ip
    myScp = Scp()
    #open the config file
    output = myScp.open_remote_file(edge_node_ip, file)
    
    scon = ssh()
    scon.connect_with_user(edge_node_ip, 'root', 'crowbar')
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
            usr = 'root'
            pwd = 'crowbar'
            cl_stdoutd, cl_stderrd = Ssh.execute_command(edge_node_ip, usr, pwd, cmd)

    #print cl_stdoutd
    #print cl_stderrd
    return current_value

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

def log(entry, printOutput=True):
    if printOutput:
        print entry
    f = open('Results.log','a')
    f.write(entry + "\n")
    f.close()


def start_iperf_server(serverNode):
    log("starting iperf server")
    usr = 'root'
    pwd = 'cr0wBar!'
    cmd = 'iperf3 -s -D'
    print "running: " + cmd 
    cl_stdoutd, cl_stderrd = Ssh.execute_command(serverNode, usr, pwd, cmd)    

def run_iperf3(clientNode, serverNode, params):
    log("running iperf3")
    usr = 'root'
    pwd = 'cr0wBar!'
    cmd = 'iperf3 -J -c '+ str(serverNode) + ' ' + str(params)
    print "running: " + cmd 
    cl_stdoutd, cl_stderrd = Ssh.execute_command(clientNode, usr, pwd, cmd)
    return cl_stdoutd, cl_stderrd

def run_transmitFile(fname, size, clientIP, serverIP):
    log("run transmitFile")
    filename, size = generateFile(clientIP, fname, size)
    params = '-F filename'
    cl_stdoutd, cl_stderrd = run_iperf3(clientIP, serverIP, params)
    return cl_stdoutd, filename, size

def get_duplexMode(mode, speed, serverIP, interface):
    log("getting duplex mode")
    
    return dupMode, ipaddress

def set_duplexMode(mode, speed, autoNeg, serverIP, interface):
    log("setting duplex mode on :" +str(server)+" interface: "+str(interface))
    file = '/etc/sysconfig/network-scripts'
    target = 'ETHTOOL_OPTS'
    new_value = 'speed '+str(speed)+' duplex '+str(mode)+' autoneg '+str(autoNeg)
    oldMode = edit_file(target, new_value, file)
    usr = 'root'
    pwd = 'cr0wBar!'
    cmd = '/etc/init.d/network restart'
    print "running: " + cmd 
    cl_stdoutd, cl_stderrd = Ssh.execute_command(serverIP, usr, pwd, cmd)

    return oldMode, newMode, serverIP, interface

def loggingJSON(run_id, clusterId, entry, printOutput=True):
    log("logging output in JSON format")
    if printOutput:
        print entry
    #rand = random.randrange(100000, 999999)
    fileName = 'runid_'+str(run_id)+''+str(clusterId)+'.json'
    f = open(fileName,'a')
    f.write(entry + "\n")
    f.close()

def generateFile(client, name, size):
    log("starting iperf server")
    usr = 'root'
    pwd = 'cr0wBar!'
    cmd = 'dd if=/dev/zero of=/home/'+str(name)+' bs=1024 count='+str(size)+'M'
    print "running: " + cmd 
    cl_stdoutd, cl_stderrd = Ssh.execute_command(client, usr, pwd, cmd) 
    return name, size

def main():
    

    '''
    on the edge node : 
    sudo vi /etc/sudoers
    add :
    Defaults:root   !requiretty
    '''
    config = importlib.import_module('config_netPerf')
    serverNode = config.serverNode
    #clientNode = config.clientNode
    run_id = config.run_id
    params = config.params
    clusterNodes = config.clusterNodes
    print clusterNodes
    s_status = start_iperf_server(serverNode)
    #c_out, c_err = run_iperf3(clientNode, serverNode, params)
    #print s_status
    #print c_out

    #t = threading.Thread(target=start_iperf_server, args=(serverNode,))
    #t.start()
    name = 'NetTest2GigB'
    size = '20'
    #name, size = generateFile(clientNode, name, size)
    x = 0
    #for node in clusterNodes:
        #output, file, size = run_transmitFile(name, size, clusterNodes[x], serverNode)
        #loggingJSON(run_id, str(clusterNodes.index(node)), str(output))
        #x=x+1

    for node in clusterNodes:
        #print node
        log(str(clusterNodes.index(node)))
        time.sleep(3)
        #c_out, c_err = run_iperf3(clusterNodes[x], serverNode, params)
        c_out, c_err = run_iperf3(node, serverNode, params)
        
        log(str(c_out))
        clusterId = int(clusterNodes.index(node)) + 1
        loggingJSON(run_id, clusterId, str(c_out))
        time.sleep(10)
        x = x+1

    
    log( "[[[ That's all folks ]]]"  )
    #name = threading.currentThread().getName()
    #print name
    #print t.getName()
