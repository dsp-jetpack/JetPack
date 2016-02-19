"""
Abstraction for iperf3 execution and result processing.

See: http://software.es.net/iperf/

"""

import datetime
import json
import time
import threading

import paramiko

import netlog

class Iperf3(object):
    """An instance of Iperf3"""

    pass

class Iperf3Server(Iperf3):
    """An iperf3 server"""

    def __init__(self, server_node, server_port_number):
        self.remote_pid = None
        self.start_time = None
        self.end_time = None
        self.server_node = server_node
        self.server_port_number = server_port_number
        self.ssh_client = None
        self.stdout = None
        self.stderr = None

    def start(self):
        """start the iperf3 server"""

        self.start_time = datetime.datetime.now()

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.connect(self.server_node)

        transport = self.ssh_client.get_transport()
        channel = transport.open_session()
        #channel.setblocking(0)
        channel.invoke_shell()

        command = 'echo $$ ; exec iperf3 -s -p {0}'.format(
            self.server_port_number)
        channel.sendall(command + '\n')
        netlog.debug('sent command')

        # XXX(mikeyp) need to tidy up waiting here, to avoid
        # potential deadlocks and be compatible with threading.
        # TODO(mikeyp) nedd to parse result for pid
        # XXX the iperf server generates output while a client 
        # test is running;
        # need to be sure we don't block with a full buffer.

        while not channel.recv_ready():
            time.sleep(1)
            netlog.debug('waiting for output')
        self.stdout = channel.recv(1024)

        #while not channel.recv_stderr_ready():
        #    time.sleep(1)
        #    netlog.debug ('waiting for stderr')
        #self.stderr = channel.recv_stderr(1024)

        status_count = 0
        while not channel.exit_status_ready():
            time.sleep(1)
            status_count += 1
            if status_count >= 5:
                break
        if channel.exit_status_ready():
            # somethings wrong, should not have exited....
            exit_code = channel.recv_exit_status()
            netlog.debug( 'remote error:%d', exit_code)
            # XXX(mikeyp) need to check stdout/err ofr startup error
            # since iperf3 returns success when the port was busy....
        self.ssh_client.close()

    def is_running():
        pass

    def stop(self):
        """stop the iperf3 server"""

        # TODO must ssh to to remote host, and explicitly kill the 
        # pid 
        pass


class Iperf3IntervalResult(object):
    """The results of an Iperf3 interval """

    def __init__(self):
        self.stream = 0
        self.start_secs = 0.0
        self.end_secs = 0.0
        self.length_secs = 0.0
        self.bytes = 0
        self.bits_per_second = 0.0
        self.retransmits = 0
        pass


    def __str__(self):
        s = 'interval start: {0} end: {1} total: {2}'
        s += ' data bytes: {3} Kbps: {4} retransmits: {5}'
        return s.format(
            self.start_secs, self.end_secs, self.length_secs,
            self.bytes, self.bits_per_second/1024.0, self.retransmits)

class Iperf3Client(threading.Thread):
    """Represents an iperf3 client run. 

    Keyword arguments:

    server_node -- the IP address of the Iperf server node
    client_node -- the IP address of the Iperf client node
    server_port_number -- the port the iperf server is running on.

    """
    def __init__(self, client_node, server_node, server_port_number):

        super(Iperf3Client, self).__init__()

        self.daemon = False
        self.start_time = None
        self.end_time = None
        self.exit_code = 0 
        self.client_node = client_node
        self.server_node = server_node
        self.server_port_number = server_port_number
        self.ssh_client = None
        self.stdin = ""
        self.stdout = ""
        self.stderr = ""
        # iperf result data
        self.final_send_data = Iperf3IntervalResult()
        self.final_recv_data = Iperf3IntervalResult()

    def run(self):
        """the iperf3 client thread

        This thread will run until the iperf3 client completes.

        """
        self.start_time = datetime.datetime.now()
        netlog.debug('iperf3Client.run()')

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.connect(self.client_node)

        transport = self.ssh_client.get_transport()
        channel = transport.open_session()
        #channel.setblocking(0)
        channel.invoke_shell()

        # we run iperf in json output mode, with no intervals
        command = 'exec iperf3 -c {1} -p {0} --json --i 0\n'.format(
            self.server_port_number, self.server_node)
        #command = 'echo $$ ; exec iperf3 -c -p {0} {1} --json --i 0'.format(
        #    self.server_port_number, self.server_node)
        channel.sendall(command)
        # wait for the command to complete, 
        block_size = 2048
        stdout_done = False
        stderr_done = False

        done = False
        while not done:
            # loop until there's an exit status, 
            if channel.recv_ready():
                data = channel.recv(block_size)
                if not (data):
                    stdout_done = True 
                else:
                    self.stdout += data
            if channel.recv_stderr_ready():
                data = channel.recv_stderr(block_size)
                if not (data):
                    stderr_done = True 
                else:
                    self.stderr += data
            if channel.exit_status_ready():
                self.exit_code = channel.recv_exit_status()
                done = True
        while not stdout_done and not stderr_done:
            # pick up any remaining data available. We don't 
            # check for recv_ready() ready here, either there's data
            # or we're done 
            data = channel.recv(block_size)
            if not (data):
                stdout_done = True 
            else:
                self.stdout += data
            data = channel.recv_stderr(block_size)
            if not (data):
                stderr_done = True 
            else:
                self.stderr += data
        self.end_time = datetime.datetime.now()

    def parse_results(self, json_data=None):
        """parse the results of the client run

        If json_data is provided, it is used as the results,  Otherwise,
        results are read from the stream self.stdout.  json_data is
        mainly intended as a unit testing convenience.

        The thread must have completed before calling this.

        These are typical iperf3 text output results.

        Connecting to host 10.148.44.215, port 5201\
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

        The json format is similar, with more structure and some extra
        detail.  See tests/test_data for exmaples.

        The results include send and receive data for for each interval
        and each stream if multiple streams are used.   The 'end' data
        includes a rolled up summary of each stream over all intervals,
        and the consolidated stream results.

        There is one confusing aspect of the iperf results.  An iperf3
        run can either read or write.  However, the results always include
        sent and received statistics.

        Currently, We only collect the final rolled up statistics,
        ignoring iperf streams and intervals

        """

        assert not self.is_running()
        netlog.debug('get_results()')

        if json_data:
            parsed_results = json.load(json_data)
        else:
            parsed_results = json.loads(self.stdout)

        # get some handy references and pick the data out
        # of the nested structure representing the json
        # send data first
        result_stanza =  parsed_results['end']['sum_sent']
        destination = self.final_send_data
        
        destination.start_secs = float(result_stanza['start']) 
        destination.end_secs = float(result_stanza['end'])
        destination.length_secs = float(result_stanza['seconds'])
        destination.bytes = result_stanza['bytes']
        destination.retransmits  = result_stanza['retransmits']
        destination.bits_per_second = float(result_stanza['bits_per_second'])

        # same thing, for receive data
        result_stanza =  parsed_results['end']['sum_received']
        destination = self.final_recv_data

        destination.start_secs = float(result_stanza['start'] )
        destination.end_secs = float(result_stanza['end'])
        destination.length_secs = float(result_stanza['seconds'])
        destination.bytes = result_stanza['bytes']
        #no retransmits in received data
        destination.retransmits  = 0
        destination.bits_per_second = float(result_stanza['bits_per_second'])

    def is_running(self):
        return self.is_alive()

    def stop(self):
        """stop the iperf3 client """
        # XXX There's no apparent way to kil a thread....
        pass

