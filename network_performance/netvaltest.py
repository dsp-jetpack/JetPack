import argparse
import datetime
import logging
import os
import threading
import time
import random
import re

from optparse import OptionParser
from threading import Thread
from auto_common import *

class Result():
    def __init__(self):
        self.start_time
        self.end_time
        self.results
        self.error

class runThreadedIperf (threading.Thread):
    def __init__(self, threadID, server_name, client_name, command, port):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.server_name = server_name
        self.client_name = client_name
        self.command = command
        #self.command = 'ping 172.16.30.115 -c 30'
        self.port = port
        self.results = ''
        self.err = ''

    def run(self):
        # print '+++++++++++++'
        # print self.server_name
        # print self.client_name
        # print self.command
        # print self.port
        # print self.results
        # print self.err
        # print '+++++++++++++'
        
        cmd = str(self.command) + ' -p ' + str(self.port)
        # logging.debug(cmd)
        # print "Starting Iperf to run on " + str(self.client_name)
        # print 'self.command == ' + str(cmd)
        #result = Result()
        #result.start_time = datetime.datetime.now()
        self.results, self.err = runIperf3(str(self.server_name), str(self.client_name),
                                        str(cmd), str(self.port))
        #logging.debug('self.results: ' + self.results)
        #logging.debug('self.err: ' + self.err)
        # print cmd
        # print self.err

    def join(self):
        Thread.join(self)
        # print self.err
        return self.results, self.err


def log(entry, printOutput=True):
    if printOutput:
        print entry
    f = open('ValResults.log', 'a')
    f.write(entry + "\n")
    f.close()


def getResults(server_node, client_node, param_list, output, direction,
               expected_rate, rate_window, test_time, run_time):

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
    mylog = logging.getLogger('Net Validation log') 
    # logging.debug('getResults()')
    # logging.debug('getting results for: ' + str(client_node))

    results_list = []
    speed_list = []
    # print output
    # bandwidth = re.findall("\d+\.\d*\D*/sec", str(output))
    bandwidth = re.findall("\d+\d*\D*/sec", str(output))
    # print bandwidth
    #if len(bandwidth) == 0:
    #    bandwidth = re.findall("\d+\d*\D*/sec", str(output))
    results_list.append(bandwidth)
    # logging.info('Result = ' + str(bandwidth[0]))
    run_time = (run_time).total_seconds()
    # print run_time
    # print test_time
    for i in bandwidth:
        #num = re.findall("\d+\.\d*", i)
        num = re.findall("\d+\d*", i)
        speed_list.append(num)

    # print len(speed_list)
    if len(speed_list) <= 0:
        speed_list.append(['0'])
        bandwidth.append(['0 Gbits/sec'])

    # print speed_list
    speed = speed_list[-1]

    # calculates the rate window, only fails if the speed
    # is UNDER the rate window.
    if float(speed[0]) >= (float(expected_rate)-((float(expected_rate))
                           * (float(rate_window) / float(100.0)))):
        result = 'Pass'
        mylog.info('Pass')
    else:
        mylog.info('fail')
        result = 'FAIL'

    if test_time < run_time:
        # print 
        mylog.error('Time exceeded for: ' + str(client_node) + ' and ' +str(server_node))
        time_result = 'Fail'
    else:
        # print 'Time not exceeded'
        time_result = 'Pass'
        # pass_flag = True

    if '-c' in param_list:
        mode = 'Concurrent'
    else:
        mode = 'Sequential'
    
    mylog.info('results for ' + str(client_node) + '-' + str(server_node) + ' = ' + str(bandwidth[-1]))

    if '-b' in param_list:
        order = 'Both'
        return str(server_node) + '\t ' + str(client_node) + '\t' + str(order)\
            + '-' + str(direction) + '\t' + str(bandwidth[-1]) + '\t'\
            + result + '\t' + time_result + '\t\t' + mode
    else:
        return str(server_node) + '\t ' + str(client_node) + '\t'\
            + str(direction) + '\t\t' + str(bandwidth[-1]) + '\t' + result\
            + '\t' + time_result + '\t\t' + mode


def commandGenerator(n1, n2):

    """
    Validate the connections between nodes.

    Keyword arguments:

    n1 -- the Iperf servers node IP address list
    n2  -- the Iperf clients node IP address list

    """
    mylog = logging.getLogger('Net Validation log')
    # logging.debug('commandGenerator()')
    params = ['', '-R']
    # cmds = []
    cmds_list = []
    # run_list = []
    port = 0
    server_list = []
    client_list = []

    for n in n1:
        for s in n:
            server_list.append(s)
    for n in n2:
        for c in n:
            client_list.append(c)
    # print server_list
    # print client_list
    # logging.debug("Generating commands for: " + str(n1) + ' ' + str(n2) )

    for server in server_list:
        for client in client_list:
            for p in params:
                if p == '-R':
                    direction = 'reverse'
                    cmd = 'iperf3 -c ' + str(server) + ' ' + str(p)
                else:
                    direction = 'forward'
                    cmd = 'iperf3 -c ' + str(server)

                if server_list.index(server) == client_list.index(client):
                    pair = True
                else:
                    pair = False
                port = 5000 + int(server_list.index(server)*100)\
                    + int(client_list.index(client)*10) + int(params.index(p))
   
                cmds_list.append({'server': server, 'client': client,
                                  'command': cmd, 'is_pair': pair,
                                  'direction': direction, 'port_number': port})
    # mylog.debug("Command generation complete, generated " + str(len(cmds_list)) + " commands")
    return cmds_list


def startIperf3Server(server_node, port_number):

    """Starts the Iperf server in demon mode.

    Keyword arguments:

    server_node -- the IP address of the Iperf server node
    port_number -- the port number to open a connection on

    """
    mylog = logging.getLogger('Net Validation log')
    # logging.debug('startIperf3Server()')
    usr = 'root'
    pwd = 'Ignition01'
    cmd = 'iperf3 -s -D -p ' + str(port_number)
    # print "Iperf server running on: " + str(server_node)\
    #     + " " + str(port_number)
    # print "running: " + cmd
    mylog.debug('Iperf server running on: ' + str(server_node)\
                   + ' ' + str(port_number))
    # cl_stdoutd = cmd
    # cl_stderrd = cmd
    time.sleep(1)
    cl_stdoutd, cl_stderrd = Ssh.execute_command(server_node, usr, pwd, cmd)
    return cl_stdoutd, cl_stderrd


def runIperf3(server_node, client_node, cmd, port_number):

    """Opens an ssh session and runs the cmd on the client node

    Keyword arguments:

    server_node -- the IP address of the Iperf server node
    client_node -- the IP address of the Iperf client node
    cmd -- the Iperf3 command to execute on the client node
    port_number -- the port to open the iperf client and server on.

    """
    #logging.debug('runIperf3()')

    # print server_node
    # print client_node
    # print cmd

    usr = 'root'
    pwd = 'Ignition01'
    mylog = logging.getLogger('Net Validation log')
    # need to remover this so i can start all servers before a concurrent run.
    #std_out, std_err = startIperf3Server(server_node, port_number)
    # time.sleep(10)
    # simulating 10 percent of connections failing to respond.
    error_gen = random.random()*10
    if error_gen >= 10:
        cl_stderrd = 'there was no data from ssh session between server: '\
            + str(server_node) + ' and client: ' + str(client_node)
        # print cl_stderrd
        mylog.error(cl_stderrd)

    else:
        cl_stderrd = 'no error'

        time.sleep(1)
        # print cmd
        mylog.info('Iperf3 running between: Server node: ' + server_node + ' and Client node: ' + client_node)
        cl_stdoutd, cl_stderrd = Ssh.execute_command(client_node, usr, pwd, cmd)
        # cl_stdoutd = 'ssh output for cmd: ' + str(cmd)
        #cl_stdoutd = '[  4]   0.00-10.00  sec  25.0 GBytes  100 Gbits/sec                  receiver'
# Connecting to host 10.148.44.215, port 5201\
# [  4] local 10.148.44.220 port 36765 connected to 10.148.44.215 port 5201\
# [ ID] Interval           Transfer     Bandwidth       Retr  Cwnd\
# [  4]   0.00-1.00   sec  2.59 GBytes  22.2 Gbits/sec    0   3.03 MBytes\
# [  4]   1.00-2.00   sec  2.90 GBytes  24.9 Gbits/sec    0   3.03 MBytes\
# [  4]   2.00-3.00   sec  3.39 GBytes  29.1 Gbits/sec    0   3.03 MBytes\
# [  4]   3.00-4.00   sec  2.49 GBytes  21.4 Gbits/sec  119   1.08 MBytes\
# [  4]   4.00-5.00   sec  2.21 GBytes  19.0 Gbits/sec    0   1.15 MBytes\
# [  4]   5.00-6.00   sec  2.23 GBytes  19.2 Gbits/sec    0   1.20 MBytes\
# [  4]   6.00-7.00   sec  2.31 GBytes  19.9 Gbits/sec    0   1.23 MBytes\
# [  4]   7.00-8.00   sec  2.29 GBytes  19.7 Gbits/sec    0   1.25 MBytes\
# [  4]   8.00-9.00   sec  2.29 GBytes  19.7 Gbits/sec    0   1.26 MBytes\
# [  4]   9.00-10.00  sec  2.29 GBytes  19.7 Gbits/sec    0   1.27 MBytes\
# - - - - - - - - - - - - - - - - - - - - - - - - -\
# [ ID] Interval           Transfer     Bandwidth       Retr\
# [  4]   0.00-10.00  sec  25.0 GBytes  21.5 Gbits/sec  119             sender\
# [  4]   0.00-10.00  sec  25.0 GBytes  21.0 Gbits/sec                  receiver'
    # cl_stderrd = 'ssh error'
    # logging.debug('ssh out: ' + str(cl_stdoutd) + ' Client node: ' + str(cl_stderrd))
    return cl_stdoutd, cl_stderrd


def Main():

    param_list = []
    metrics_list = []
    full_results = []
    # thread_list = []
    # mode = ''
    # direction = ''

    mylog = logging.getLogger('Net Validation log')

    log('\n' + str(datetime.datetime.now()))

    # argument parser for command line.

    parser = argparse.ArgumentParser()

    level = 1
    log_to_file = True

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
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
    # with just 2 nodes the concurrent/sequential
    # /allperm options are irrelevant.

    args = parser.parse_args()
    if args.verbose:
        #mylog.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        mylog.addHandler(ch)
        fh = logging.FileHandler('NetVal.log')
        fh.setLevel(logging.DEBUG)
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', filename='debug.log', level=logging.DEBUG)
        fh.setFormatter(formatter)
        mylog.addHandler(fh)
        #logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.DEBUG)
    #logging.debug('Only shown in debug mode')

    # catching all invalid argument combinations.

    if args.allpermutations:
        #logging.basicConfig(level=logging.DEBUG)
        mylog.info("you are running all-permutations of tests across"
               " nodes: " + str(args.node_list1) + ' and ' + str(args.node_list2))
        param_list.append('-a')
    elif args.pairs:
        mylog.info("you are running pairs of tests across"
               " nodes: " + str(args.node_list1) + 'and ' + str(args.node_list2))
        param_list.append('-p')
    else:
        mylog.info('no permutations set, running in pair mode')
        param_list.append('-p')

    if args.concurrent:
        mylog.info("you are running tests concurrently")
        param_list.append('-c')
        # mode = 'Concurrent'

    elif args.sequential:
        mylog.info("you are running tests sequentially.")
        param_list.append('-s')
        # mode = 'Sequential'
    else:
        mylog.info('no Order parameter set')
        # print 'no Order parameter set'
        # mode = 'Sequential'

    if args.reverse:
        mylog.info("Testing connectivity in reverse direction.")
        # print ("Testing connectivity in reverse direction.")
        param_list.append('-R')
        # direction = 'Reverse'
    elif args.both:
        mylog.info("Testing connectivity in both directions.")
        # print ("Testing connectivity in both directions.")
        param_list.append('-b')
        # direction = 'Both'
    elif args.forward:
        mylog.info("Testing connectivity in forward direction.")
        # print ("Testing connectivity in forward direction.")
        param_list.append('-f')
        # direction = 'forward'
    else:
        mylog.info("Testing connectivity in forward direction.")
        # print ("Testing connectivity in forward direction.")
        # param_list.append('-f')
        # direction = 'forward'

    # setting the defaults for metrics if they are not entered.
    if args.expected_rate:
        mylog.info("Expected Rate: " + str(args.expected_rate))
        # print ("Expected Rate: " + str(args.expected_rate))
        metrics_list.append({'-e': args.expected_rate})
        expected_rate = args.expected_rate
    else:
        expected_rate = 0.0

    if args.rate_window:
        mylog.info("rate window: " + str(args.rate_window))
        # print ("rate window: " + str(args.rate_window))
        metrics_list.append({'-w': args.rate_window})
        rate_window = args.rate_window
    else:
        rate_window = 0

    if args.test_time:
        mylog.info("test_time: " + str(args.test_time))
        # print ("test_time: " + str(args.test_time))
        metrics_list.append({'-t': args.test_time})
        test_time = args.test_time
    else:
        test_time = 60

    # filtering the command matrix using the param_list to
    # only run selected jobs

    server_list = args.node_list1
    client_list = args.node_list2
    run_list = commandGenerator(server_list, client_list)
    mylog.debug("Command generation complete, generated " + str(len(run_list)) + " commands")
    exec_list = []

    if ('-b' in param_list and '-a' in param_list) or\
        ('-a' in param_list and ('-R' not in param_list
         and '-f' not in param_list)):
            exec_list = run_list
            # print 'run the entire list.'
    elif '-b' in param_list or ('-b' in param_list and '-p' in param_list):
        # print '-b or -b and -p'
        for each in run_list:
            if each['is_pair'] is True:
                exec_list.append(each)
        # print 'run all where server equals the first server,
        # and client = first client'
    elif '-f' in param_list or '' in param_list:
        # or if there are no params.
        if '-p' in param_list:
            # print '[-f, -p]'
            for each in run_list:
                if each['direction'] == 'forward' and each['is_pair'] is True:
                    exec_list.append(each)
        else:
            for each in run_list:
                if each['direction'] == 'forward':
                    exec_list.append(each)
        # print ' taking out all instances that have -R in command'
    elif '-R' in param_list:
        if '-p' in param_list:
            for each in run_list:
                if each['direction'] == 'reverse' and each['is_pair'] is True:
                    exec_list.append(each)
        else:
            for each in run_list:
                if each['direction'] == 'reverse':
                    exec_list.append(each)
        # print 'taking out all instances that have -f in command'
        # print 'run only where there is -R in the command'
    elif '-p' in param_list:
        # print 'IN -P'
        for each in run_list:
            if each['is_pair'] is True and each['direction'] == 'forward':
                exec_list.append(each)
        # print 'remove all with -R then run all where server equals
        # the first server, and client = first client'
    else:
        mylog.critical('why are we here, we should never be here - params are broken')
        print 'empty'

    # log the ouput from each command run.

    if len(exec_list) <= 1 and ('-c' in param_list or '-a' in param_list):
        # print param_list
        print 'only one job, cannot run concurrently.'
        mylog.error('only one job, cannot run concurrently.')
    else:
        if '-c' in param_list:
            # run in concurrent mode.
            threads = []
            for each in exec_list:
                # create a thread for each iperf instance
                # and start all iperf3 servers.
                server_node = each['server']
                client_node = each['client']
                cmd = str(each['command']) + ' -p ' + str(each['port_number'])
                port_number = each['port_number']

                # start all the Iperf3 servers.
                # print server_node
                # print port_number
                std_out, std_err = startIperf3Server(server_node, port_number)

                # print 'create a thread for: ' +str(each)
                # thread_list.append(getThread())
                # print exec_list.index(each)
                # print server_node
                # print client_node
                # print each
                # print port_number

                iperfRunThr = runThreadedIperf(exec_list.index(each),
                                               server_node, client_node,
                                               each['command'], port_number)
                threads.append(iperfRunThr)
                #print err

            title = 'Source \t \t ' + 'Destination \t' + 'Direction \t' +\
                    'Speed \t\t' + 'Result' + '\t' + 'Time Result \t' + 'Mode'
            #log('Source \t \t ' + 'Destination \t' + 'Direction \t' +
            #    'Speed \t\t' + 'Result' + '\t' + 'Time Result \t' + 'Mode')
            # for each in exec_list:
            #    server_node = each['server']
            #    client_node = each['client']
            #    cmd = each['command']
            #    port_number = each['port_number']

            start_times = []

            mylog.debug(' Starting ' + str(len(threads)) + ' threads one for each Iperf3 instance.')
            for thr in threads:
                # print datetime.datetime.now()
                # print 'STARTING THREAD: ' +str(thr)
                start_times.append(datetime.datetime.now())
                thr.start()
                #time.sleep(1)
            #time.sleep(3)
            for thr in threads:
                start_time = start_times[threads.index(thr)]
                #print 'start_time == ' + str(start_times[threads.index(thr)])
                thr.join()
                #time.sleep(10)
                # print 'thr.join(): ' + str(thr.join())
                # print thr.getName()
                # print thr.server_name
                # print thr.client_name
                # print exec_list[threads.index(thr)]['direction']
                # print thr.results
                # print '--------------------'

                if len(thr.err) > 100:
                    # print thr.err
                    mylog.error(str(thr.err))
                    # log('Error:... ' + str(thr.err))
                else:
                    end_time = datetime.datetime.now()
                    # print 'end time: ' + str(end_time)
                    run_time = end_time - start_time
                    # print thr.server_name
                    # print thr.client_name
                    # print param_list
                    # print thr.results
                    # print exec_list[threads.index(thr)]['direction']
                    # print expected_rate
                    # print rate_window
                    # print test_time
                    # print run_time
                    
                    result = getResults(thr.server_name, thr.client_name,
                                        param_list, thr.results,
                                        exec_list[threads.index(thr)]
                                        ['direction'],
                                        expected_rate, rate_window, test_time,
                                        run_time)
                    # log('run time: ' + str(run_time))
                    #log(result)
                    full_results.append(result)
        else:
            title = 'Source \t \t ' + 'Destination \t' + 'Direction \t' +\
                'Speed \t\t' + 'Result' + '\t' +\
                'Time Result' + '\t' + 'Mode'
            for each in exec_list:
                server_node = each['server']
                client_node = each['client']
                port_number = each['port_number']
                cmd = str(each['command']) + ' -p ' + str(port_number)
                start_time = datetime.datetime.now()
                output, err = runIperf3(server_node, client_node,
                                     cmd, port_number)
                end_time = datetime.datetime.now()
                run_time = end_time - start_time
                # print run_time
                if len(err) > 10:
                    mylog.error(str(err))
                    # log('Error: ' + str(err))
                else:
                    
                    result = getResults(server_node, client_node, param_list,
                                        output, each['direction'],
                                        expected_rate, rate_window,
                                        test_time, run_time)
                    # log('run time: ' + str(run_time))
                    #log(result)
                    full_results.append(result)
    log(title)
    for each in full_results:
        log(each)
                    
    log('Done')
if __name__ == '__main__':
    Main()
