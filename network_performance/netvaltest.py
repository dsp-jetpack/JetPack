import argparse

def iperf3(serverNode, clientNode, cmd):
    print serverNode
    print clientNode
    print cmd
    #this method will open a ssh session with the nodes involved and run whatever the cmd is.
    stdout = 'whatever output comes from the ssh session running iperf.'
    errout = 'any error info from the ssh session running iperf.'

    return stdout, errout

def runValidation(nodes1, nodes2, metrics, params):
    #out = "Running iperf3 tests on nodes: " + str(nodes1) + " and " + str(nodes2)
    print 'len(nodes1[0]) = ' + str(len(nodes1[0]))
    print 'len(nodes2[0]) = ' + str(len(nodes2[0]))

    #the first node list cannot be bigger than the second node list.
    if len(nodes1[0])>len(nodes2[0]):
        #print 'Error: list 1 is bigger than list 2'
        out = 'Error: list 1 is bigger than list 2'

    #if there are only 2 nodes AND the Both parameter is NOT set, then give an error if the all permutations paramater or concurrent parameter is entered.
    #... then, construct the server and client commands for the the test.
    #the both parameter means 2 instances of Iperf will be run so the order of these needs to be set, that is, sequentially, or concurrently.

    elif len(nodes1[0])==1 and len(nodes2[0])==1:

        #if there any sequential or all permutation parameters give an error because they are not valid in a 2 node run.
        #a single job cannot run sequentially or in mutiple permutations, so concurrent mode is assumed for this.

        if ('-s' in params or '-a' in params) and '-b' not in params:
            #print 'exit: cannot run single job in sequential mode or with more than one permutation.'
            out = 'exit: cannot run single job in sequential mode or with more than one permutation.'
        else:
            #construct iperf command. this is just a sample of what ill have do do for each use case.
            #print 'A two node test so ignoring Order and Mappings parameters.'
            if '-r' in params:
               server_cmd = 'iperf3 -s'
               client_command = 'iperf3 -c '+str(nodes2[0][0]) + ' -r'
            else:
                server_cmd = 'iperf3 -s'    
                client_command = 'iperf3 -c '+str(nodes2[0][0])

            #print 'ssh to: '+str(nodes1[0][0]) +' and run: '+server_cmd 
            #print 'ssh to: ' +str(nodes2[0]) + ' and run: ' +str(client_command)
            out = 'ssh to: ' +str(nodes2[0]) + ' and run: ' +str(client_command)

    #if there is one node in the first list and more than one in the second list we need to ignore the -p paris argument.
    elif len(nodes1[0])==1 and len(nodes2[0])>1:
        print 'in one-to-many mode'
        if '-p' in params:
            #print 'error, cannot run in pairs mode when list 1 has only one node.'
            out = 'error, cannot run in pairs mode when list 1 has only one node.'
        else:
            #print 'run n1 against all nodes in list 2'
            out = 'run n1 against all nodes in list 2'

    #elif len(nodes1[0])>1 and len(nodes2[0])>1:
    # the only node list combination not caught above is the many-to-many lists combination.
    #the lists need to be the same length so if they are not an error is displayed.
    else:
        #multiple nodes - we can do something here to divide and even up the number of nodes.
        #i think that whatever the program is doing for this should be obvious and sensible but logic will go here anyway.)
        server_cmd = 'iperf3 -s'
        #print 'ssh to designated server node'
        #print 'ssh to nodex and run iperf3 with configured params.'
        #if both  node lists are not the same length print an error.
        if len(nodes1[0]) != len(nodes2[0]):
            #print 'error, lists are not the same length.'
            out = 'error, lists are not the same length.'
        else:
            #all groups of params are allowed here.
            #print 'list-to-list mode'
            out = 'list-to-list mode'

    #print metrics
    #print params
    return out

def Main():

    paramList = []
    metricsList = []

    parser=argparse.ArgumentParser()
    parser2=argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--forward",action="store_true")
    group.add_argument("-r", "--reverse",action="store_true")
    group.add_argument("-b", "--both",action="store_true")

    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument("-s", "--sequential", action="store_true")
    group2.add_argument("-c", "--concurrent", action="store_true")

    group3 = parser.add_mutually_exclusive_group()
    group3.add_argument("-a", "--allpermutations", action="store_true")
    group3.add_argument("-p", "--pairs", action="store_true")

    parser.add_argument("-e", "--expected_rate",type=int, help="expected rate")
    parser.add_argument("-w", "--rate_window", type=int, help="window rate")
    parser.add_argument("-t", "--test_time", type=int, help="test time")

    #group3 = parser.add_mutually_exclusive_group()
    #parser.add_argument("nodes1", action='append', nargs='+', help='first list of nodes to test')
    
    parser.add_argument('--nodelist1', action='append', nargs='+', required=True, help='first list of nodes to test')
    parser.add_argument('--nodelist2', action='append', nargs='+', required=True, help='second list of nodes to test')
    
    #parser.add_argument("-n", "--nodePair", action='store', nargs='2', help='node pair')
    #parser.add_argument("node", action='append', nargs='1', help='single node')

    #with just 2 nodes the concurrent/sequential/allperm options are irrelevant.

    args=parser.parse_args()

    #parser.add_argument("metrics", help="Enter the metric value you'd like to set.", type=int)
    #args=parser.parse_args()

    #out=runIperf(args.nodes)
    if args.allpermutations:
        print ("you are running all-permutations of tests across nodes: "+str(args.nodelist1))
        print 'and ' +str(args.nodelist2)
        paramList.append('-a')
    elif args.pairs:
        print "you are running pairs of tests across nodes: "+str(args.nodelist1)
        print 'and ' +str(args.nodelist2)
        paramList.append('-p')

    if args.concurrent:
        print ("you are running concurrent tests on nodes: "+str(args.nodelist1))
        print 'and ' +str(args.nodelist2)
        paramList.append('-c')
    elif args.sequential:
        print ("you are running sequential tests on nodes: "+str(args.nodelist1))
        print 'and ' +str(args.nodelist2)
        paramList.append('-s')
    else:
        print 'no Order paramter set'

    if args.reverse:
        print ("you are running in reverse mode.")
        paramList.append('-r')
    elif args.both:
        print ("you are running in both directions mode.")
        paramList.append('-b')
    else:
        print ("you are running in forward mode.")
        paramList.append('-f')

    if args.expected_rate:
        print ("Expected Rate: " + str(args.expected_rate))
        metricsList.append({'-e':args.expected_rate})
    if args.rate_window:
        print ("rate window: " + str(args.rate_window))
        metricsList.append({'-w':args.rate_window})
    if args.test_time:
        print ("test_time: " + str(args.test_time))
        metricsList.append({'-t':args.test_time})

    out=runValidation(args.nodelist1, args.nodelist2, metricsList, paramList)
    print out


if __name__ == '__main__':
    Main()