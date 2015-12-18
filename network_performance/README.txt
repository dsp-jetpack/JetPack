Network Testing Toolkit
=======================

 The nework testing tool is a command line tool for testing  network connectivity and throughput between nodes in a cluster. For more information  on the command line arguments you can use the help argument  --help when   running the toolkit.


Prerequisites
=============
 Before running the Network Testing Toolkit, applications and pyton packages must be installed on the node running the tool and the target nodes for the tool as follows:

Node running the Network Testing Toolkit
----------------------------------------

 Applications
 ------------
 - python 2.x
 - Iperf3

 Python Packages
 ---------------
 - Paramiko
 - Selenium

Target nodes in the cluster
---------------------------

 Applications
 ------------
 - Iperf3


Running the Network Testing Toolkit
===================================

Where to run the toolkit
------------------------
The toolkit can be run from any Linux or Windows node on a network that meets the prerequistes definited in this README file.

How to run the toolkit
----------------------
1. Navigate to the directory where the toolkit run script is located:
    cd <install-directory>/network_performance/netvaltest.py
2. Run netvaltest.py and choose from the following options:

usage: netvaltest.py [-h] [-f | -R | -b] [-s | -c] [-a | -p]
                     [-e EXPECTED_RATE] [-w RATE_WINDOW] [-t TEST_TIME]
                     --node_list1 NODE_LIST1 [NODE_LIST1 ...] --node_list2
                     NODE_LIST2 [NODE_LIST2 ...] [-v]

optional arguments:
  -h, --help            show this help message and exit
  -f, --forward
  -R, --reverse
  -b, --both
  -s, --sequential
  -c, --concurrent
  -a, --allpermutations
  -p, --pairs
  -e EXPECTED_RATE, --expected_rate EXPECTED_RATE
                        expected rate
  -w RATE_WINDOW, --rate_window RATE_WINDOW
                        window rate
  -t TEST_TIME, --test_time TEST_TIME
                        test time
  --node_list1 NODE_LIST1 [NODE_LIST1 ...]
                        first list of nodes to test
  --node_list2 NODE_LIST2 [NODE_LIST2 ...]
                        second list of nodes to test
  -v, --verbose         increase output verbosity



Installing Iperf3 using the EPEL repo
=====================================
You can install Iperf3 from the EPEL repo.
Installing the EPEL repo requires internet access.
To download and install the EPEL repo run:

 wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
 sudo rpm -Uvh epel-release-6*.rpm

To install Iperf3 from the EPEL repo, run:
 yum -y install iperf3

Installing Iperf3 from source
=============================
Alternatively you can install Iperf3 from source.
You can download the source code from:
 http://downloads.es.net/pub/iperf/

Supported version of Iperf3
===========================
Iperf version 3.0.2