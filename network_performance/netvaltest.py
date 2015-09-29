import argparse
import threading
import time
import random
import re

from threading import Thread
from auto_common import *

class runThreadedIperf (threading.Thread):
    def __init__(self, threadID, server_name, client_name, command, port):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.server_name = server_name
        self.client_name = client_name
        self.command = command
        self.port = port
        self.results = ''
        self.err = ''

    def run(self):
        cmd = 'my iperf command'
        # print "Starting Iperf to run on " + str(self.client_name)
        self.results, self.err = iperf3(self.server_name, self.client_name, self.command, self.port)
    
    def join(self):
        Thread.join(self)
        return self.results

def log(entry, printOutput=True):
    if printOutput:
        print entry
    f = open('ValResults.log','a')
    f.write(entry + "\n")
    f.close()

def getResults(server_node, client_node, param_list, output, direction, expected_rate, rate_window, test_time):
    
    """
    Validate the connections between nodes.

    Keyword arguments:

    server_node -- the Iperf server node IP address
    client_node  -- the Iperf client node IP address
    param_list -- the parameters entered in the command line arguments
    output -- the output from the Iperf command
    direction --  the direction the command run
    expected_rate -- the expected rate argument from the command line
    rate_window -- the modifier for the exected rate
    test_time -- the test time parameter from the command line

    """

    results_list = []
    speed_list = []
    bandwidth = re.findall("\d+\.\d*\D*/sec", str(output))
    # print bandwidth
    results_list.append(bandwidth)
    for i in bandwidth:
        num = re.findall("\d+\.\d*", i)
        speed_list.append(num)

    speed = speed_list[-1]

    # calculates the rate window, only fails if the speed is UNDER the rate window.
    if float(speed[0]) >= (float(expected_rate)-((float(expected_rate))*(float(rate_window)/float(100.0)))):
        result = 'Pass'
    else:
        result = 'Fail'
    #print float(expected_rate)
    #print str(float(speed[0]))
    #print str((float(expected_rate)*float(rate_window)/100))
    #print (float(expected_rate)-((float(expected_rate))*(float(rate_window)/float(100.0))))

    # need to add an error message to say why the test failed and handle how we report multiple fails (connectvity, time, bandwidth.)
    if test_time < 10:
        print 'Time exceeded'
        #result = 'Fail'
    else:
        #print 'Time not exceeded'
        #result = 'Pass'
        pass_flag = True
       
    if '-c' in param_list:
        mode = 'Concurrent'
    else:
        mode = 'Sequential'

    if '-b' in param_list:
        order = 'Both'
        return str(server_node) +'\t '+ str(client_node)+ '\t' + str(order)+'-'+str(direction)\
        + '\t' + str(bandwidth[-1]) + '\t'+ result+'\t' + mode
    else:
        return str(server_node) +'\t '+ str(client_node)+ '\t' + str(direction)\
        + '\t\t' + str(bandwidth[-1]) + '\t'+ result+'\t' + mode

def commandGenerator(n1, n2):
    #n1 = a, b, c, d
    #n2 = w, x, y, z
    params = ['','-R']
    # mode = [-s, -c]
    cmds = []
    cmds_list = []
    run_list = []
    port = 0
    server_list = []
    client_list = []
    
    for n in n1:
        for s in n:
            server_list.append(s)
            #print s
    for n in n2:
        for c in n:
            #print c
            client_list.append(c)
    print server_list
    print client_list
    
    for server in server_list:
        #print server
        for client in client_list:
            #print client
            for p in params:
                #print client, server
                if p == '-R':
                    direction = 'reverse'
                else:
                    direction = 'forward'

                if server_list.index(server) == client_list.index(client):
                    pair = True
                else:
                    pair = False
                port = 1000 + int(server_list.index(server)*100)+int(client_list.index(client)*10)+int(params.index(p))
                cmd = 'iperf -c ' + str(server) +' '+ str(p)
                cmds_list.append({'server': server, 'client': client, 'command': cmd, 'is_pair': pair, 'direction': direction, 'port_number': port})
                #for each in cmds_list:
                #    print '**************'
                #    print each
                #    print '========='
                #print cmds_list
    #for each in cmds_list:
    #    print each
    return cmds_list

def startIperf3Server(server_node, port_number):

    """Starts the Iperf server in demon mode.

    Keyword arguments:

    server_node -- the IP address of the Iperf server node
    port_number -- the port number to open a connection on

    """
    usr = 'root'
    pwd = 'cr0wBar!'
    cmd = 'iperf3 -s -D'
    print "Iperf server running on: " + str(server_node) + " " + str(port_number)
    #print "running: " + cmd
    # cl_stdoutd, cl_stderrd = Ssh.execute_command(server_node, usr, pwd, cmd)


def iperf3(server_node, client_node, cmd, port_number):

    """Opens an ssh session and runs the cmd on the client node

    Keyword arguments:

    server_node -- the IP address of the Iperf server node
    client_node -- the IP address of the Iperf client node
    cmd -- the Iperf3 command to execute on the client node
    port_number -- the port to open the iperf client and server on.

    """

    # print server_node
    # print client_node
    # print cmd

    usr = 'root'
    pwd = 'cr0wBar!'
    # need to remover this so i can start all servers before a concurrent run.
    # startIperf3Server(server_node, port_number)
    time.sleep(10)
    # simulating 10 percent of connections failing to respond.
    error_gen = random.random()*10
    if error_gen >= 10:
        cl_stderrd = 'there was no data from ssh session between server: ' +str(server_node) + ' and client: ' +str(client_node)
        #print cl_stderrd
        
    else:
        cl_stderrd = 'no error'
        #print error_gen

    #print "running: " + str(cmd)
    # cl_stdoutd, cl_stderrd = Ssh.execute_command(client_node, usr, pwd, cmd)
    #cl_stdoutd = 'ssh output for cmd: ' + str(cmd)
    cl_stdoutd = 'Connecting to host 10.148.44.215, port 5201\
[  4] local 10.148.44.220 port 36765 connected to 10.148.44.215 port 5201\
[ ID] Interval           Transfer     Bandwidth       Retr  Cwnd\
[  4]   0.00-1.00   sec  2.59 GBytes  22.2 Gbits/sec    0   3.03 MBytes\
[  4]   1.00-2.00   sec  2.90 GBytes  24.9 Gbits/sec    0   3.03 MBytes\
[  4]   2.00-3.00   sec  3.39 GBytes  29.1 Gbits/sec    0   3.03 MBytes\
[  4]   3.00-4.00   sec  2.49 GBytes  21.4 Gbits/sec  119   1.08 MBytes\
[  4]   4.00-5.00   sec  2.21 GBytes  19.0 Gbits/sec    0   1.15 MBytes\
[  4]   5.00-6.00   sec  2.23 GBytes  19.2 Gbits/sec    0   1.20 MBytes\
[  4]   6.00-7.00   sec  2.31 GBytes  19.9 Gbits/sec    0   1.23 MBytes\
[  4]   7.00-8.00   sec  2.29 GBytes  19.7 Gbits/sec    0   1.25 MBytes\
[  4]   8.00-9.00   sec  2.29 GBytes  19.7 Gbits/sec    0   1.26 MBytes\
[  4]   9.00-10.00  sec  2.29 GBytes  19.7 Gbits/sec    0   1.27 MBytes\
- - - - - - - - - - - - - - - - - - - - - - - - -\
[ ID] Interval           Transfer     Bandwidth       Retr\
[  4]   0.00-10.00  sec  25.0 GBytes  21.5 Gbits/sec  119             sender\
[  4]   0.00-10.00  sec  25.0 GBytes  21.0 Gbits/sec                  receiver'
    #cl_stderrd = 'ssh error'


    return cl_stdoutd, cl_stderrd

def getPort(seed_number):

    """Opens an ssh session and runs the cmd on the client node

    Keyword arguments:

    none
    
    """
    # add logic here to decide how many iperf instances
    #  we need running on each machine - maybe always one per command.
    # if a instance is opened on the same port number 
    port = 6000 + seed_number

    return port

def getThread():
    thread = 'a thread'
    return thread

def Main():

    param_list = []
    metrics_list = []
    thread_list = []
    mode = ''
    direction = ''

    # argument parser for command line.

    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--forward", action="store_true")
    group.add_argument("-R", "--reverse", action="store_true")
    group.add_argument("-b", "--both", action="store_true")

    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument("-s", "--sequential", action="store_true")
    group2.add_argument("-c", "--concurrent", action="store_true")

    group3 = parser.add_mutually_exclusive_group()
    group3.add_argument("-a", "--allpermutations", action="store_true")
    group3.add_argument("-p", "--pairs", action="store_true")

    parser.add_argument("-e", "--expected_rate", type=int,
                        help="expected rate")
    parser.add_argument("-w", "--rate_window", type=int, help="window rate")
    parser.add_argument("-t", "--test_time", type=int, help="test time")

    parser.add_argument('--node_list1', action='append',
                        nargs='+', required=True,
                        help='first list of nodes to test')
    parser.add_argument('--node_list2', action='append', nargs='+',
                        required=True,
                        help='second list of nodes to test')

    # with just 2 nodes the concurrent/sequential
    # /allperm options are irrelevant.

    args = parser.parse_args()

    # catching all invalid argument combinations.

    if args.allpermutations:
        print ("you are running all-permutations of tests across"\
                " nodes: " + str(args.node_list1))
        print 'and ' + str(args.node_list2)
        param_list.append('-a')
    elif args.pairs:
        print ("you are running pairs of tests across"\
                " nodes: " + str(args.node_list1))
        print 'and ' + str(args.node_list2)
        param_list.append('-p')
    else:
        print 'no permutations set, running in all-permutations mode'
        param_list.append('-a')

    if args.concurrent:
        print ("you are running concurrent tests"\
                " on nodes: " + str(args.node_list1))
        print 'and ' + str(args.node_list2)
        param_list.append('-c')
        mode = 'Concurrent'

    elif args.sequential:
        print ("you are running sequential tests on"\
                    " nodes: "+str(args.node_list1))
        print 'and ' + str(args.node_list2)
        param_list.append('-s')
        mode = 'Sequential'
    else:
        print 'no Order parameter set'
        mode = 'Sequential'

    if args.reverse:
        print ("you are running in reverse mode.")
        param_list.append('-R')
        direction = 'Reverse'
    elif args.both:
        print ("you are running in both directions mode.")
        param_list.append('-b')
        direction = 'Both'
    elif args.forward:
        print ("you are running in forward mode.")
        param_list.append('-f')
        direction = 'forward'
    else:
        print ("you are running in forward mode.")
        #param_list.append('-f')
        direction = 'forward'

    # setting the defaults for metrics if they are not entered.
    if args.expected_rate:
        print ("Expected Rate: " + str(args.expected_rate))
        metrics_list.append({'-e': args.expected_rate})
        expected_rate = args.expected_rate
    else:
        expected_rate = 20.0

    if args.rate_window:
        print ("rate window: " + str(args.rate_window))
        metrics_list.append({'-w': args.rate_window})
        rate_window = args.rate_window
    else:
        rate_window = 10

    if args.test_time:
        print ("test_time: " + str(args.test_time))
        metrics_list.append({'-t': args.test_time})
        test_time = args.test_time
    else:
        test_time = 10
    
    # filtering the command matrix using the param_list to only run selected jobs
    
    server_list = args.node_list1
    client_list = args.node_list2
    run_list = commandGenerator(server_list, client_list)
    exec_list = []
    
    #for each in server_list:
    #    for e in each:
    #        print e

    if ('-b' in param_list and '-a' in param_list) or ('-a' in param_list and ('-R' not in param_list and '-f' not in param_list)):
        exec_list = run_list
        print 'run the entire list.'
    elif '-b' in param_list or ('-b' in param_list and '-p' in param_list):
        print '-b or -b and -p'
        for each in run_list:
            if each['is_pair'] == True:
                exec_list.append(each)
        # print 'run all where server equals the first server, and client = first client'
    elif '-f' in param_list or '' in param_list: # or if there are no params.
        if '-p' in param_list:
            print '[-f, -p]'
            for each in run_list:
                if each['direction'] == 'forward' and each['is_pair'] == True:
                    exec_list.append(each)
        else:
            for each in run_list:
                if each['direction'] == 'forward':
                    exec_list.append(each)
        # print ' taking out all instances that have -R in command'
    elif '-R' in param_list:
        if '-p' in param_list:
            for each in run_list:
                if each['direction'] == 'reverse' and each['is_pair'] == True:
                    exec_list.append(each)
        else:
            for each in run_list:
                if each['direction'] == 'reverse':
                    exec_list.append(each)
        # print 'taking out all instances that have -f in command'
        # print 'run only where there is -R in the command'
    elif '-p' in param_list:
        print 'IN -P'
        for each in run_list:
            if each['is_pair'] == True and each['direction'] == 'forward':
                exec_list.append(each)
        # print 'remove all with -R then run all where server equals the first server, and client = first client'
    else:
        print 'empty'

    # log the ouput from each command run.

    if len(exec_list) <= 1 and ('-c' in param_list or '-a' in param_list):
        print 'only one job, cannot run seqentially.'
    else:
        if '-c' in param_list:
            # run in concurrent mode.
            threads = []
            for each in exec_list:
                # create a thread for each iperf instance and start all iperf3 servers.
                server_node = each['server']
                client_node = each['client']
                cmd = each['command']
                port_number = each['port_number']
            
                # start all the Iperf3 servers.
                startIperf3Server(server_node, port_number)
            
                print 'create a thread for: ' +str(each)
                #thread_list.append(getThread())
                iperfRunThr = runThreadedIperf(exec_list.index(each), server_node, client_node, each, port_number)
                threads.append(iperfRunThr)

            log('Source \t '+ 'Destination \t'+ 'Direction \t'+ 'Speed \t\t'+ 'Result' +'\t'+'Mode')
            for each in exec_list: #((server_node, client_node, cmd, port_number = 5008)
                server_node = each['server']
                client_node = each['client']
                cmd = each['command']
                port_number = each['port_number']
                # output, err = iperf3(server_node, client_node, cmd, port_number)
            
            for thr in threads:
                thr.start()

            for thr in threads:
                thr.join()
                # print thr.getName()
                # print thr.results
                if len(thr.err)>10:
                    log('Error: ' +str(thr.err))
                else:
                    result = getResults(thr.server_name, thr.client_name, param_list, thr.results, exec_list[threads.index(thr)]['direction'], expected_rate, rate_window, test_time)
                    log(result)
        else:
            log('Source \t '+ 'Destination \t'+ 'Direction \t'+ 'Speed \t\t'+ 'Result' +'\t'+'Mode')
            for each in exec_list: #((server_node, client_node, cmd, port_number = 5008)
                server_node = each['server']
                client_node = each['client']
                cmd = each['command']
                port_number = each['port_number']
                output, err = iperf3(server_node, client_node, cmd, port_number)
                if len(err)>10:
                    log('Error: ' +str(err))
                else:
                    result = getResults(server_node, client_node, param_list, output, each['direction'], expected_rate, rate_window, test_time)
                    log(result)
        
if __name__ == '__main__':
    Main()
