import argparse


def iperf3(server_node, client_node, cmd):

    """Opens an ssh session and runs the cmd on the client node

    Keyword arguments:

    server_node -- the IP address of the Iperf server node
    client_node -- the IP address of the Iperf client node
    cmd -- the Iperf3 command to execute on the client node

    """

    print server_node
    print client_node
    print cmd

    stdout = 'whatever output comes from the ssh session running iperf.'
    errout = 'any error info from the ssh session running iperf.'

    return stdout, errout


def runValidation(nodes1, nodes2, metrics, params):

    """Validate the connections between nodes.

    Keyword arguments:

    nodes1 -- the first node or list of nodes
    nodes2  -- the second node or list of nodes
    metrics -- the metrics to be tested
    params -- the parameters to construct the Iperf3 command

    """
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

        if ('-s' in params or '-a' in params) and '-b' not in params:
            out = 'exit: cannot run single job in sequential mode or\
with more than one permutation.'
        else:
            # construct iperf command. this is just a sample of
            # what ill have do do for each use case.
            if '-r' in params:
                server_cmd = 'iperf3 -s'
                client_command = 'iperf3 -c '+str(nodes2[0][0])+' -R'
            else:
                server_cmd = 'iperf3 -s'
                client_command = 'iperf3 -c '+str(nodes2[0][0])

            out = 'ssh to: '+str(nodes2[0]) + ' and run: '+str(client_command)

    # if there is one node in the first list and more than one in
    # the second list we need to ignore the p argument.

    elif len(nodes1[0]) == 1 and len(nodes2[0]) > 1:
        print 'in one-to-many mode'
        if '-p' in params:
            out = 'error, cannot run in pairs mode when \
list 1 has only one node.'
        else:
            out = 'run n1 against all nodes in list 2'

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
            out = 'error, lists are not the same length.'
        else:
            # all groups of params are allowed here.
            out = 'list-to-list mode'

    return out


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
        print ("you are running all-permutations of tests across\
                nodes: " + str(args.node_list1))
        print 'and ' + str(args.node_list2)
        param_list.append('-a')
    elif args.pairs:
        print ("you are running pairs of tests across\
                nodes: " + str(args.node_list1))
        print 'and ' + str(args.node_list2)
        param_list.append('-p')

    if args.concurrent:
        print ("you are running concurrent tests\
                on nodes: " + str(args.node_list1))
        print 'and ' + str(args.node_list2)
        param_list.append('-c')
    elif args.sequential:
        print ("you are running sequential tests on\
                    nodes: "+str(args.node_list1))
        print 'and ' + str(args.node_list2)
        param_list.append('-s')
    else:
        print 'no Order paramter set'

    if args.reverse:
        print ("you are running in reverse mode.")
        param_list.append('-R')
    elif args.both:
        print ("you are running in both directions mode.")
        param_list.append('-b')
    else:
        print ("you are running in forward mode.")
        param_list.append('-f')

    if args.expected_rate:
        print ("Expected Rate: " + str(args.expected_rate))
        metrics_list.append({'-e': args.expected_rate})
    if args.rate_window:
        print ("rate window: " + str(args.rate_window))
        metrics_list.append({'-w': args.rate_window})
    if args.test_time:
        print ("test_time: " + str(args.test_time))
        metrics_list.append({'-t': args.test_time})

    out = runValidation(args.node_list1, args.node_list2,
                        metrics_list, param_list)
    print out


if __name__ == '__main__':
    Main()
