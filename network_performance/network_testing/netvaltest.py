import argparse
import datetime
import os
import random
import re
import time

import netlog
from iperf3 import Iperf3Server, Iperf3Client
# from iperf3 import Iperf3IntervalResult

def getResults(server_node, client_node, param_list, output, direction,
               expected_rate, rate_window, test_time, run_time):

    # XXX A mixture of result collection and validation.
    # This can be likely be replaced with a per node test result check 
    """

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
    netlog.debug('getResults()')
    netlog.debug('getting results for: ' + str(client_node))

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
        netlog.info('Pass')
    else:
        netlog.info('fail')
        result = 'FAIL'

    if test_time < run_time:
        # print 
        netlog.error('Time exceeded for: ' + str(client_node) + ' and ' +str(server_node))
        time_result = 'Fail'
    else:
        # print 'Time not exceeded'
        time_result = 'Pass'
        # pass_flag = True

    if '-c' in param_list:
        mode = 'Concurrent'
    else:
        mode = 'Sequential'
    
    netlog.info('results for ' + str(client_node) + '-' + str(server_node) + ' = ' + str(bandwidth[-1]))

    if '-b' in param_list:
        order = 'Both'
        return str(server_node) + '\t ' + str(client_node) + '\t' + str(order)\
            + '-' + str(direction) + '\t' + str(bandwidth[-1]) + '\t'\
            + result + '\t' + time_result + '\t\t' + mode
    else:
        return str(server_node) + '\t ' + str(client_node) + '\t'\
            + str(direction) + '\t\t' + str(bandwidth[-1]) + '\t' + result\
            + '\t' + time_result + '\t\t' + mode

def commandGenerator(n1, n2, arguments):

    """
    Validate the connections between nodes.

    Keyword arguments:

    n1 -- the Iperf servers node IP address list
    n2  -- the Iperf clients node IP address list

    """
    netlog.debug('commandGenerator()')
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
    netlog.debug("Generating commands for: " + str(n1) + ' ' + str(n2) )

    for server in server_list:
        for client in client_list:
            if arguments.reverse:
                direction = 'reverse'
                cmd = 'iperf3 -c ' + str(server) + ' ' + str(p)
            else:
                direction = 'forward'
                cmd = 'iperf3 -c ' + str(server)

            if server_list.index(server) == client_list.index(client):
                pair = True
            else:
                pair = False
            #port = 5000 + int(server_list.index(server)*100)\
            #    + int(client_list.index(client)*10) + int(params.index(p))
            # XXX need to revisit port assignment logic
            port = 5000 + int(server_list.index(server)*100)

            cmds_list.append({'server': server, 'client': client,
                              'command': cmd, 'is_pair': pair,
                              'direction': direction, 'port_number': port})
    netlog.debug("Command generation complete, generated " + str(len(cmds_list)) + " commands")
    return cmds_list

def Main():

    param_list = []
    metrics_list = []
    full_results = []
    # thread_list = []
    # mode = ''
    # direction = ''

    # setup logging early
    netlog.init()
    netlog.enable_log_file()

    netlog.info(str(datetime.datetime.now()))

    # argument parser for command line.

    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--forward", 
        action="store_true", 
        default=True)
    group.add_argument("-r", "--reverse", 
        action="store_true", 
        default=False)
    group.add_argument("-b", "--both",
        action="store_true", 
        default=False)

    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument("-s", "--sequential", 
        action="store_true", 
        default=True)
    group2.add_argument("-c", "--concurrent", 
        action="store_true", 
        default=False)

    group3 = parser.add_mutually_exclusive_group()
    group3.add_argument("-a", "--allpermutations", 
        action="store_true")
    group3.add_argument("-p", "--pairs", 
        action="store_true")

    parser.add_argument("-e", "--expected_rate", 
        type=int,
        default=0,
        help="expected rate")
    parser.add_argument("-w", "--rate_window", 
        type=int, 
        default=0,
        help="window rate")
    parser.add_argument("-t", "--test_time", 
        type=int, 
        default=10,
        help="test time")

    parser.add_argument('--node_list1', 
        action='append',
        nargs='+', 
        required=True,
        help='first list of nodes to test')
    parser.add_argument('--node_list2', 
        action='append', 
        nargs='+',
        required=True,
        help='second list of nodes to test')
    parser.add_argument("-v", "--verbose", 
        help="increase output verbosity",
        action="store_true")

    # with just 2 nodes the concurrent/sequential
    # /allperm options are irrelevant.

    args = parser.parse_args()
    if args.verbose:
        netlog.enable_debug() 
    # catching all invalid argument combinations.

    # XXX should this code logging arguments / operation mode be in a 
    # log_arguments function ? Probably

    if args.allpermutations:
        netlog.info("you are running all-permutations of tests across"
               " nodes: " + str(args.node_list1) + ' and ' + str(args.node_list2))
    elif args.pairs:
        netlog.info("you are running pairs of tests across"
               " nodes: " + str(args.node_list1) + 'and ' + str(args.node_list2))
    else:
        netlog.info('no permutations set, running in pair mode')

    if args.concurrent:
        netlog.info("you are running tests concurrently")
    elif args.sequential:
        netlog.info("you are running tests sequentially.")
    else:
        netlog.info('no Order parameter set')

    if args.reverse:
        netlog.info("Testing connectivity in reverse direction.")
    elif args.both:
        netlog.info("Testing connectivity in both directions.")
    elif args.forward:
        netlog.info("Testing connectivity in forward direction.")
    else:
        netlog.info("Testing connectivity in forward direction.")

    netlog.info("Expected Rate: " + str(args.expected_rate))
    netlog.info("rate window: " + str(args.rate_window))
    netlog.info("test_time: " + str(args.test_time))

    # Build the list of iperf tests to execute
    """
    pairs:  
        check both server lists are equal length
        run test between list1[n] and list2[n]
            do forward or reverse or both
            David thought we should do all forwards before doing reverses
            should warn if nodes are the same, but not skip

    
    permutation
        for each server in list 1:
            for each server in list 2:
                run test list1[n] - list2[n]
                filter out cases already run
                do forward or reverse or both

    # filtering the command matrix using the param_list to
    # only run selected jobs

    """

    server_list = args.node_list1
    client_list = args.node_list2
    run_list = commandGenerator(server_list, client_list, args)
    netlog.debug("Command generation complete, generated " + str(len(run_list)) + " commands")
    netlog.debug(str(run_list))
    exec_list = []

    # temporarily disable argument checks 
    """

    #if (args.both and args.allpermutations) or
    #    (args.allpermutations and not args.reverse)) 
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
        netlog.critical('why are we here, we should never be here - params are broken')
        assert False, 'parameters are broken'

    # log the ouput from each command run.

    if len(exec_list) <= 1 and ('-c' in param_list or '-a' in param_list):
        netlog.error('only one job, cannot run concurrently.')
        assert False, 'only one job, cannot run concurrently.'

    if args.concurrent: 
        # run in concurrent mode.
        netlog.info('Running in concurrent  mode')
        assert False, 'concurrent not implemented'
    else:
        # sequential mode
        netlog.info('Running in Sequential mode')
    """
        
    # New Logic
    # create IPerf3 server and client for each test to run
    # in sequential mode, run one by one and wait.
    # in parallel mode start all and wait

    testcase = {
        'server':'localhost',
        'port_number': 5201,
        'client' : 'localhost'
    }
    exec_list.append(testcase)
    print exec_list
    for linktest in exec_list:

        netlog.debug('starting server')
        server = Iperf3Server(linktest['server'], linktest['port_number'])
        server.start()
        netlog.debug('starting client')
        client = Iperf3Client(linktest['client'], 
            linktest['server'], linktest['port_number'])
        client.start()
        while client.is_running():
            time.sleep(1)
        if client.exit_code:
            netlog.info("iperf client failed with exit code %d", 
                client.exit_code)
            netlog.info("stdout:")
            netlog.info(client.stdout)
        else:
            client.parse_results()
            print client.final_recv_data

        # stop the server, and wait for the thread to complete
        server.stop()
        server.join(10)
                    
    netlog.info('Done')
