import argparse

def runIperf(nodes):
    out = "i am doing iperf3 tests on nodes: " + nodes
    return out

def Main():
    parser=argparse.ArgumentParser()
    parser2=argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--forward",action="store_true")
    group.add_argument("-r", "--reverse",action="store_true")
    group.add_argument("-b", "--bidirectional",action="store_true")

    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument("-s", "--sequential", action="store_true")
    group2.add_argument("-c", "--concurrent", action="store_true")
    group2.add_argument("-a", "--allpermutations", action="store_true")

    parser.add_argument("-e", "--expected_rate",type=int, help="expected rate")
    parser.add_argument("-w", "--rate_window", type=int, help="window rate")
    parser.add_argument("-t", "--test_time", type=int, help="test time")

    parser.add_argument("nodes", help="Enter the node you'd like to test.")
    args=parser.parse_args()

    parser.add_argument("metrics", help="Enter the metric value you'd like to set.", type=int)
    #args=parser.parse_args()

    out=runIperf(args.nodes)
    if args.allpermutations:
        print ("you are running all-permutations of tests across nodes: "+str(args.nodes))
    elif args.concurrent:
        print ("you are running concurrent tests on nodes: "+str(args.nodes))
    else:
        print ("you are running sequential tests on nodes: "+str(args.nodes))

    if args.reverse:
        print ("you are running in reverse mode.")
    elif args.bidirectional:
        print ("you are running in bi-directional mode.")
    else:
        print ("you are running in forward mode.")

    if args.expected_rate:
        print ("Expected Rate: " + str(args.expected_rate))
    if args.rate_window:
        print ("rate window: " + str(args.rate_window))
    if args.test_time:
        print ("test_time: " + str(args.test_time))


if __name__ == '__main__':
    Main()