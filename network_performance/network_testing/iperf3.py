"""
Abstraction for iperf3 execution and result processing.

This module implements wrappers aorund iperf3 using the 
Python threading module.

See: http://software.es.net/iperf/

"""
import datetime
import json
import re
import threading
import time

import paramiko

import netlog

# time in seconds to delay the IO pool loops
IO_CHECK_INTERVAL = 5

class Iperf3Server(threading.Thread):
    """An iperf3 server"""

    def __init__(self, server_node, server_port_number):

        super(Iperf3Server, self).__init__()
        self.remote_pid = None
        self.start_time = None
        self.end_time = None
        self.exit_code = 0
        self.server_node = server_node
        self.server_port_number = server_port_number
        self.ssh_client = None
        self.stdout = ""
        self.stderr = ""
        self._stop_request = threading.Event()

    def run(self):
        """the iperf3 server thread

        This runs on a thread until we either kill the 
        server or it exits for some reason.

        """
        self.start_time = datetime.datetime.now()

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.connect(self.server_node)

        transport = self.ssh_client.get_transport()
        channel = transport.open_session()
        #channel.setblocking(0)
        #channel.settimeout(0)
        # no pty; we want stderr and stdout on separate streams.
        # channel.get_pty()
        channel.invoke_shell()

        command = 'echo PID$$DIP ; exec iperf3 -s --version4 -p {0}'.format(
            self.server_port_number)
        channel.sendall(command + '\n')
        #netlog.debug('sent command')

        # babysit the server process by reading stdout and stderr.
        #  It is expected to run forever, unless we stop it.
        # TODO need to limit how much standard output we store.
        block_size = 2048
        stdout_done = False
        stderr_done = False

        done = False
        while not done:
            # loop until there's an exit status, or we are 
            # requested to stop
            time.sleep(IO_CHECK_INTERVAL)
            #netlog.debug("check recv_ready ")
            if channel.recv_ready():
                data = channel.recv(block_size)
                if not (data):
                    stdout_done = True 
                else:
                    self.stdout += data
            #netlog.debug("check recv_stderr_ready ")
            if channel.recv_stderr_ready():
                data = channel.recv_stderr(block_size)
                if not (data):
                    stderr_done = True 
                else:
                    self.stderr += data
            #netlog.debug("check exit_status_ready ")
            if channel.exit_status_ready():
                self.exit_code = channel.recv_exit_status()
                done = True
            #netlog.debug("check stop_request")
            if self._stop_request.is_set():
                # kill the process, and we will pick up the exit code
                # next time around
                self._kill_iperf()

        # pick up any remaining data available. We read
        # until the channel is empty unless it was done already.
        #netlog.debug("final check recv_ready ")
        if not stdout_done and channel.recv_ready():
            while (not stdout_done):
                data = channel.recv(block_size)
                if not data:
                    stdout_done = True
                else:
                    self.stdout += data

        #netlog.debug("final check recv_stderr_ready ")
        if not stderr_done and channel.recv_stderr_ready():
            while not stderr_done:
                data = channel.recv_stderr(block_size)
                if not (data):
                    stderr_done = True 
                else:
                    self.stderr += data

        # extract the remote pid from stdout
        self.remote_pid = self._get_pid()

        # exit code processing.  
        # If we were flagged to stop, fudge the exit code to zero
        # since we killed iperf.
        if self._stop_request.is_set():
            self.exit_code = 0
        # XXX HACK: check stderr for possible errors, since iperf3 3.0.11 
        # returns a success exit code if it fails to bind to a port.
        # e.g. 
        # iperf3: error - unable to start listener for connections: 
        #   Address already in use
        if self.exit_code == 0:
            if self.stderr.find('error') != -1:
                self.exit_code = 1
        #netlog.info('Remote iperf server exited with code: %d',
        #    self.exit_code) 

        self.ssh_client.close()
        self.end_time = datetime.datetime.now()

    def _get_pid(self):
        """determine iperf PID from stdout"""
        
        match = re.search(r'PID(\d*)DIP', self.stdout)
        if match:
            return int(match.group(1))
        else:
            assert False, 'did not determine remote server pid'

    def _kill_iperf(self):
        """terminate the remote iperf process

        We open another session on the same transport and kill
        the process. 

        """
        #netlog.debug("server got stop request, killing remote process")
        transport = self.ssh_client.get_transport()
        channel = transport.open_session()
        channel.exec_command('kill %d' % self._get_pid())

    def is_running(self):
        """Determine if the thread is running"""
        return self.is_alive()

    def stop(self):
        """stop the iperf3 server

        Ths routine flags the main thread to stop itself.

        """
        self._stop_request.set()


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
        self.remote_pid = None
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
        self._stop_request = threading.Event()
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
        command = 'echo PID$$DIP ; exec iperf3 --version4 -c {1} -p {0} --json --i 0\n'.format(
            self.server_port_number, self.server_node)
        channel.sendall(command)
        # wait for the command to complete, 
        block_size = 2048
        stdout_done = False
        stderr_done = False

        done = False
        while not done:
            # loop until there's an exit status, or we are 
            # requested to stop
            time.sleep(IO_CHECK_INTERVAL)
            #netlog.debug("check recv_ready ")
            if channel.recv_ready():
                data = channel.recv(block_size)
                if not (data):
                    stdout_done = True 
                else:
                    self.stdout += data
            #netlog.debug("check recv_stderr_ready ")
            if channel.recv_stderr_ready():
                data = channel.recv_stderr(block_size)
                if not (data):
                    stderr_done = True 
                else:
                    self.stderr += data
            #netlog.debug("check exit_status_ready ")
            if channel.exit_status_ready():
                self.exit_code = channel.recv_exit_status()
                done = True
            #netlog.debug("check stop_request")
            if self._stop_request.is_set():
                # kill the process, and we will pick up the exit code
                # next time around
                self._kill_iperf()

        # pick up any remaining data available. We read
        # until the channel is empty unless it was done already.
        #netlog.debug("final check recv_ready ")
        if not stdout_done and channel.recv_ready():
            while (not stdout_done):
                data = channel.recv(block_size)
                if not data:
                    stdout_done = True
                else:
                    self.stdout += data

        #netlog.debug("final check recv_stderr_ready ")
        if not stderr_done and channel.recv_stderr_ready():
            while not stderr_done:
                data = channel.recv_stderr(block_size)
                if not (data):
                    stderr_done = True 
                else:
                    self.stderr += data

        # extract the remote pid from stdout, then clean stdout
        self.remote_pid = self._get_pid()
        self._fixup_stdout()

        # exit code processing.  
        # If we were flagged to stop, fudge the exit code to zero
        # since we killed iperf.
        if self._stop_request.is_set():
            self.exit_code = 0

        self.ssh_client.close()
        self.end_time = datetime.datetime.now()

    def _get_pid(self):
        """determine iperf PID from stdout"""
        
        match = re.search(r'PID(\d*)DIP', self.stdout)
        if match:
            return int(match.group(1))
        else:
            assert False, 'did not determine remote server pid'

    def _fixup_stdout(self):
        """Remove the PID embedded in stdout"""

        self.stdout = re.sub(r'PID(\d*)DIP', '', self.stdout)

    def _kill_iperf(self):
        """terminate the remote iperf process

        We open another session on the same transport and kill
        the process. 

        """
        #netlog.debug("server got stop request, killing remote process")
        transport = self.ssh_client.get_transport()
        channel = transport.open_session()
        channel.exec_command('kill %d' % self._get_pid())

    def is_running(self):
        return self.is_alive()

    def stop(self):
        """stop the iperf3 server

        Ths routine flags the main thread to stop itself.

        """
        self._stop_request.set()

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
        netlog.debug('parse_results()')

        try:
            if json_data:
                parsed_results = json.load(json_data)
            else:
                parsed_results = json.loads(self.stdout)
        except ValueError as e:
            netlog.error('json parse failed in parse_results')
            netlog.error('Bad json:')
            netlog.error(self.stdout)
            raise e

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


