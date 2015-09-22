import argparse
import thread
import time
import re
# import logging
from auto_common import *

def log(entry, printOutput=True):
    if printOutput:
        print entry
    f = open('ValResults.log','a')
    f.write(entry + "\n")
    f.close()


def startIperf3Server(server_node, port_number = 5008):

    """Starts the Iperf server in demon mode.

    Keyword arguments:

    server_node -- the IP address of the Iperf server node
    port_number -- the port number to open a connection on (default 5008)

    """
    usr = 'root'
    pwd = 'cr0wBar!'
    cmd = 'iperf3 -s -D'
    print "ssh to server node: " + str(server_node) + " " + str(port_number)
    print "running: " + cmd
    # cl_stdoutd, cl_stderrd = Ssh.execute_command(server_node, usr, pwd, cmd)


def iperf3(server_node, client_node, cmd):

    """Opens an ssh session and runs the cmd on the client node

    Keyword arguments:

    server_node -- the IP address of the Iperf server node
    client_node -- the IP address of the Iperf client node
    cmd -- the Iperf3 command to execute on the client node

    """

    # print server_node
    # print client_node
    # print cmd

    usr = 'root'
    pwd = 'cr0wBar!'
    startIperf3Server(server_node)
    print "running: " + cmd
    # cl_stdoutd, cl_stderrd = Ssh.execute_command(client_node, usr, pwd, cmd)
    cl_stdoutd = 'ssh output for cmd: ' + str(cmd)
    cl_stderrd = 'ssh error'


    return cl_stdoutd, cl_stderrd


def runValidation(nodes1, nodes2, metrics, params):

    """Validate the connections between nodes.

    Keyword arguments:

    nodes1 -- the first node or list of nodes
    nodes2  -- the second node or list of nodes
    metrics -- the metrics to be tested
    params -- the parameters to construct the Iperf3 command

    """
    # return [{nodeA: address}, {nodeB: address}, {output: ''}, {direction: ''}, {} ]
    out = []

    print 'len(nodes1[0]) = '+str(len(nodes1[0]))
    print 'len(nodes2[0]) = '+str(len(nodes2[0]))

    # the first node list cannot be bigger than the second node list.

    if len(nodes1[0]) > len(nodes2[0]):
        out = 'Error: list 1 is bigger than list 2'

    # if there are only 2 nodes AND the Both parameter is NOT set,
    # then give an error. if the all permutations paramater or
    # concurrent parameter is entered then, construct the server and
    # client commands for the test.
    # the both parameter means 2 instances of Iperf will be run so that
    # the order of these needs to be set,
    # that is, sequentially, or concurrently.

    elif len(nodes1[0]) == 1 and len(nodes2[0]) == 1:

        # if there any sequential or all permutation parameters give
        #  an error because they are not valid in a 2 node run.
        # A single job cannot run sequentially or in
        #  mutiple permutations, so concurrent mode is assumed for this.

        server_node = nodes1[0][0]
        client_node = nodes2[0][0]

        if ('-s' in params or '-a' in params) and '-b' not in params:
            return 0, 0, 'exit: cannot run single job in sequential mode or'\
                  ' with more than one permutation.'
        else:
            # construct iperf command.
            # command list needs to keep a record of it's direction.
            # cmd_list = [[{cmd:'ssh output for cmd: iperf3 -c 5.6.7.8'}, {direction:'-f'}, {mode:'-b'}],\
            #              [{cmd:'ssh output for cmd: iperf3 -c 5.6.7.8'}, {direction:'-r'}, {mode:'-b'}]]
            cmd_list = []
            dict_list = []
            dict = {}
            dict2 = {}

            if '-b' in params:
                cmd_list.append('iperf3 -c '+str(client_node))
                cmd_list.append('iperf3 -c '+str(client_node)+' -R')
                # cmd = string above, direction = Both-forward.
                # cmd = string above, direction = Both-reverse.
                
                dict['command'] = 'iperf3 -c '+str(client_node)
                dict['direction'] = 'forward'
                dict['both'] = True

                dict_list.append(dict)

                dict2['command'] = 'iperf3 -c '+str(client_node)+' -R'
                dict2['direction'] = 'reverse'
                dict2['both'] = True

                dict_list.append(dict2)
                #cmd_list.append(dict)
                print dict_list

            elif '-R' in params:
                client_command = 'iperf3 -c '+str(client_node)+' -R'
                cmd_list.append(client_command)

                dict['command'] = 'iperf3 -c '+str(client_node)+' -R'
                dict['direction'] = 'reverse'
                dict['mode'] = False

                dict_list.append(dict)

                # cmd = string above, direction = Reverse.
            else:
                client_command = 'iperf3 -c '+str(client_node)
                cmd_list.append(client_command)

                dict['command'] = 'iperf3 -c '+str(client_node)
                dict['direction'] = 'reverse'
                dict['mode'] = False

                dict_list.append(dict)

                # cmd = string above, direction = Forward

            for cmd in cmd_list:
                time.sleep(2)
                # check if the tests should be run concurrently or in sync.
                if '-c' in params:
                    print 'create thread for each iperf instance'
                    print 'create port list for each instance on the same node'
                    print 'run all instances at the same time.'
                    # out = 'list of concurrent outputs'
                    
                    out, err = iperf3(server_node, client_node, cmd)
                    print "item x in dict list: "+str(cmd_dict[cmd_list.index(cmd)])
                    # log('log results for each - ID by port number?')
                else:
                    output, err = iperf3(server_node, client_node, cmd)
                    out.append(output)
                    print "item x in dict list: "+str(dict_list[cmd_list.index(cmd)])
                    dict_list[cmd_list.index(cmd)]['results'] = output
                    # log(out)
                    # print dict_list
            # out = 'ssh to: '+str(nodes2[0]) + ' and run: '+str(client_command)

    # if there is one node in the first list and more than one in
    # the second list we need to ignore the p argument.

    elif len(nodes1[0]) == 1 and len(nodes2[0]) > 1:
        print 'in one-to-many mode'
        if '-p' in params:
            out = 'error, cannot run in pairs mode when'\
                  'list 1 has only one node.'
        else:
            return 'run n1 against all nodes in list 2'

    # the only node list combination not caught above is the
    # many-to-many lists combination.
    # the lists need to be the same length so if they are
    # not an error is displayed.

    else:
        # multiple nodes - we can do something here to divide and
        # even up the number of nodes.
        # i think that whatever the program is doing for
        # this should be obvious and sensible but logic will go here anyway.)
        server_cmd = 'iperf3 -s'
        print server_cmd

        # if both  node lists are not the same length print an error.
        if len(nodes1[0]) != len(nodes2[0]):
            return 'error, lists are not the same length.'
        else:
            # all groups of params are allowed here.
            out = 'list-to-list mode'

    return server_node, client_node, out, dict_list


def Main():

    param_list = []
    metrics_list = []

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

    if args.concurrent:
        print ("you are running concurrent tests"\
                " on nodes: " + str(args.node_list1))
        print 'and ' + str(args.node_list2)
        param_list.append('-c')
    elif args.sequential:
        print ("you are running sequential tests on"\
                    " nodes: "+str(args.node_list1))
        print 'and ' + str(args.node_list2)
        param_list.append('-s')
    else:
        print 'no Order paramter set'
    direction = ''
    if args.reverse:
        print ("you are running in reverse mode.")
        param_list.append('-R')
        direction = 'Reverse'
    elif args.both:
        print ("you are running in both directions mode.")
        param_list.append('-b')
        direction = 'Both'
    else:
        print ("you are running in forward mode.")
        param_list.append('-f')
        direction = 'forward'

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
        rate_window = 0.9

    if args.test_time:
        print ("test_time: " + str(args.test_time))
        metrics_list.append({'-t': args.test_time})
        test_time = args.test_time
    else:
        test_time = 10
    
    server_node, client_node, out, dict_list = runValidation(args.node_list1, args.node_list2,
                                                  metrics_list, param_list)

    print out
    # take the output and use reg ex to get and verify the data you want.
    out = ['Connecting to host 10.148.44.215, port 5201\
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
[  4]   0.00-10.00  sec  25.0 GBytes  17.0 Gbits/sec                  receiver',\

'Connecting to host 10.148.44.215, port 5201\
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
[  4]   0.00-10.00  sec  25.0 GBytes  25.0 Gbits/sec                  receiver']

    speed_list = []
    result = ''
    results_list = []

    log('Source \t '+ 'Destination \t'+ 'Direction \t'+ 'Speed \t\t'+ 'Result')

    for output in out:
        bandwidth = re.findall("\d+\.\d*\D*/sec", output)
        results_list.append(bandwidth)

        for i in bandwidth:
            num = re.findall("\d+\.\d*", i)
            speed_list.append(num)

        speed = speed_list[-1]

        # print speed[0]
        # print float(float(expected_rate)*float(rate_window))
        # print rate_window
        # print expected_rate

        if float(speed[0]) > (float(expected_rate)*float(rate_window)):
            result = 'Pass'
        else:
            result = 'Fail'

        log(str(server_node) +'\t '+ str(client_node)+ '\t' + str(direction)+'-'+str(dict_list[out.index(output)]['direction'])\
            + '\t' + str(bandwidth[-1]) + '\t'+ result)


if __name__ == '__main__':
    Main()
