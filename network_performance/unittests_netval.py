from netvaltest import getResults, runIperf3, startIperf3Server, commandGenerator, runThreadedIperf, log
import unittest
import time
import datetime
from datetime import timedelta

class TestMyFunctions(unittest.TestCase):
    #(server_node, client_node, param_list, output, direction,
    #           expected_rate, rate_window, test_time, run_time):
    def setUp(self):
        self.node1 = 'node1'
        self.node2 = 'nodeA'
        self.param_list = ['-p', '-c']
        self.output = ['555 Gbits/sec']
        self.direction = 'forward'
        self.expected_rate = 500
        self.window_rate = 10
        self.test_time = 60
        self.run_time = timedelta(seconds=15)
        self.command = 'iperf3 -c node1 -p 5000'
        
        self.result = 'node1	 nodeA	forward		555 Gbits/sec	Pass	Pass		Concurrent'
        self.result2 = 'node1	 nodeA	reverse		555 Gbits/sec	Pass	Pass		Concurrent'
        self.result3 = 'node1	 nodeA	Both-forward		555 Gbits/sec	Pass	Pass		Concurrent'
        self.result4 = 'node1	 nodeA	Both-reverse		555 Gbits/sec	FAIL	Pass		Concurrent'
        self.result5 = 'node1	 nodeA	forward		555 Gbits/sec	Pass	Pass		Sequential'
        self.result6 = 'node1	 nodeA	reverse		555 Gbits/sec	Pass	Pass		Sequential'
        self.result7 = 'node1	 nodeA	Both-forward		555 Gbits/sec	Pass	Pass		Sequential'
        self.result8 = 'node1	 nodeA	Both-reverse		555 Gbits/sec	FAIL	Pass		Sequential'
        self.result9 = 'node1	 nodeA	Both-reverse		555 Gbits/sec	FAIL	Fail		Sequential'

    def test_getResults(self):
        # good data
        self.assertTrue(getResults(self.node1, self.node2, self.param_list, self.output,
        self.direction, self.expected_rate, self.window_rate, self.test_time, self.run_time))

        # bad output
        self.assertTrue(getResults(self.node1, self.node2, self.param_list, ['asa'],
        self.direction, self.expected_rate, self.window_rate, self.test_time, self.run_time))

        self.assertTrue(getResults(self.node1, self.node2, self.param_list, ['22.1'],
        self.direction, self.expected_rate, self.window_rate, self.test_time, self.run_time))

        # output is correct for given params and directions.
        self.assertEquals(getResults(self.node1, self.node2, self.param_list, self.output,
        self.direction, self.expected_rate, self.window_rate, self.test_time, self.run_time), self.result)

        self.assertEquals(getResults(self.node1, self.node2, ['-c'], self.output,
        'reverse', self.expected_rate, self.window_rate, self.test_time, self.run_time), self.result2)
        
        self.assertEquals(getResults(self.node1, self.node2, ['-c'], self.output,
        'Both-forward', self.expected_rate, self.window_rate, self.test_time, self.run_time), self.result3)
        
        self.assertEquals(getResults(self.node1, self.node2, ['-c'], self.output,
        'Both-reverse', 800, self.window_rate, self.test_time, self.run_time), self.result4)
        
        self.assertEquals(getResults(self.node1, self.node2, ['-s'], self.output,
        'forward', self.expected_rate, self.window_rate, self.test_time, self.run_time), self.result5)
        
        self.assertEquals(getResults(self.node1, self.node2, [''], self.output,
        'reverse', self.expected_rate, self.window_rate, self.test_time, self.run_time), self.result6)
        
        self.assertEquals(getResults(self.node1, self.node2, [''], self.output,
        'Both-forward', self.expected_rate, self.window_rate, self.test_time, self.run_time), self.result7)
        
        self.assertEquals(getResults(self.node1, self.node2, [''], self.output,
        'Both-reverse', 800, self.window_rate, self.test_time, self.run_time), self.result8)
        
        self.assertEquals(getResults(self.node1, self.node2, [''], self.output,
        'Both-reverse', 800, self.window_rate, 4, timedelta(seconds=5)), self.result9)
        
        '''
        self.assertTrue(getResults('node1', '', ['-p'], ['555'],
        'forward', 550, 10, 11, timedelta(seconds=5)))
        self.assertTrue(getResults('', '', ['-p'], ['555'],
        'forward', 550, 10, 11, timedelta(seconds=5)))
        self.assertTrue(getResults('', 'nodeb', ['-p'], ['555 Gbits/sec'],
        'forward', 550, 0, 11, timedelta(seconds=5)))
        self.assertTrue(getResults('', 'nodeb', ['-Q'], ['555 Gbits/sec'],
        'forward', 0, 0, 0, timedelta(seconds=0)))
        self.assertTrue(getResults('', 'nodeb', ['99'], ['555 Gbits/sec'],
        'forward', 0, 0, 0, timedelta(seconds=0)))
        '''
    def test_commandGenerator(self):
        self.assertTrue(commandGenerator([['node1', 'node2', 'node3']],
        [['nA', 'nB', 'nC']]))
        self.assertTrue(commandGenerator([['node1']], [['nA', 'nB', 'nC']]))
        self.assertTrue(commandGenerator([['node1']], [['nodeA']]))
        self.assertEquals(commandGenerator([['node1']], [['nodeA']]), 
        [{'client': 'nodeA', 'command': 'iperf3 -c node1',
        'direction': 'forward', 'is_pair': True,
        'port_number': 5000, 'server': 'node1'}, 
        {'client': 'nodeA', 'command': 'iperf3 -c node1 -R', 
        'direction': 'reverse', 'is_pair': True,
        'port_number': 5001, 'server': 'node1'}])
        self.assertEquals(commandGenerator([['node1']],
        [['nodeA', 'nodeB', 'nodeC']]), 
        [{'client': 'nodeA', 'command': 'iperf3 -c node1',
        'direction': 'forward', 'is_pair': True, 'port_number': 5000,
        'server': 'node1'}, {'client': 'nodeA', 'command': 'iperf3 -c node1 -R', 'direction': 'reverse', 'is_pair': True, 'port_number': 5001, 
        'server': 'node1'}, 
        {'client': 'nodeB', 'command': 'iperf3 -c node1', 'direction': 'forward', 'is_pair': False, 'port_number': 5010,
        'server': 'node1'}, {'client': 'nodeB', 'command': 'iperf3 -c node1 -R', 'direction': 'reverse', 'is_pair': False, 'port_number': 5011, 
        'server': 'node1'},
        {'client': 'nodeC', 'command': 'iperf3 -c node1', 'direction': 'forward', 'is_pair': False, 'port_number': 5020,
        'server': 'node1'}, {'client': 'nodeC', 'command': 'iperf3 -c node1 -R', 'direction': 'reverse', 'is_pair': False, 'port_number': 5021, 
        'server': 'node1'}])
        self.assertEquals(commandGenerator([['node1', 'node2', 'node3']], [['nodeA', 'nodeB', 'nodeC']]), 
        [{'client': 'nodeA', 'command': 'iperf3 -c node1', 'direction': 'forward', 'is_pair': True, 'port_number': 5000,
        'server': 'node1'}, {'client': 'nodeA', 'command': 'iperf3 -c node1 -R', 'direction': 'reverse', 'is_pair': True, 'port_number': 5001, 
        'server': 'node1'}, 
        {'client': 'nodeB', 'command': 'iperf3 -c node1', 'direction': 'forward', 'is_pair': False, 'port_number': 5010,
        'server': 'node1'}, {'client': 'nodeB', 'command': 'iperf3 -c node1 -R', 'direction': 'reverse', 'is_pair': False, 'port_number': 5011, 
        'server': 'node1'},
        {'client': 'nodeC', 'command': 'iperf3 -c node1', 'direction': 'forward', 'is_pair': False, 'port_number': 5020,
        'server': 'node1'}, {'client': 'nodeC', 'command': 'iperf3 -c node1 -R', 'direction': 'reverse', 'is_pair': False, 'port_number': 5021, 
        'server': 'node1'},
        {'client': 'nodeA', 'command': 'iperf3 -c node2', 'direction': 'forward', 'is_pair': False, 'port_number': 5100,
        'server': 'node2'}, {'client': 'nodeA', 'command': 'iperf3 -c node2 -R', 'direction': 'reverse', 'is_pair': False, 'port_number': 5101, 
        'server': 'node2'}, 
        {'client': 'nodeB', 'command': 'iperf3 -c node2', 'direction': 'forward', 'is_pair': True, 'port_number': 5110,
        'server': 'node2'}, {'client': 'nodeB', 'command': 'iperf3 -c node2 -R', 'direction': 'reverse', 'is_pair': True, 'port_number': 5111, 
        'server': 'node2'},
        {'client': 'nodeC', 'command': 'iperf3 -c node2', 'direction': 'forward', 'is_pair': False, 'port_number': 5120,
        'server': 'node2'}, {'client': 'nodeC', 'command': 'iperf3 -c node2 -R', 'direction': 'reverse', 'is_pair': False, 'port_number': 5121, 
        'server': 'node2'},
        {'client': 'nodeA', 'command': 'iperf3 -c node3', 'direction': 'forward', 'is_pair': False, 'port_number': 5200,
        'server': 'node3'}, {'client': 'nodeA', 'command': 'iperf3 -c node3 -R', 'direction': 'reverse', 'is_pair': False, 'port_number': 5201, 
        'server': 'node3'}, 
        {'client': 'nodeB', 'command': 'iperf3 -c node3', 'direction': 'forward', 'is_pair': False, 'port_number': 5210,
        'server': 'node3'}, {'client': 'nodeB', 'command': 'iperf3 -c node3 -R', 'direction': 'reverse', 'is_pair': False, 'port_number': 5211, 
        'server': 'node3'},
        {'client': 'nodeC', 'command': 'iperf3 -c node3', 'direction': 'forward', 'is_pair': True, 'port_number': 5220,
        'server': 'node3'}, {'client': 'nodeC', 'command': 'iperf3 -c node3 -R', 'direction': 'reverse', 'is_pair': True, 'port_number': 5221, 
        'server': 'node3'}])

    def test_runIperf3(self):
        self.assertTrue(runIperf3('nodeA', 'node1', self.command, 5000))
        # self.assertEquals(runIperf3('nodeA', 'node1', 'cmd', 5000), ('[  4]   0.00-10.00  sec  25.0 GBytes  100 Gbits/sec                  receiver', 'no error'))

    def test_startIperf3Server(self):
        self.assertTrue(startIperf3Server('nodeA', 5000))
        # self.assertEquals(startIperf3Server('nodeA', 5000), ('iperf3 -s -D -p 5000', 'iperf3 -s -D -p 5000'))

    def test_runThreadedIperf(self):
        #self, threadID, server_name, client_name, command, port
        self.assertTrue(runThreadedIperf('tID', 'nodeS', 'NodeC', self.command, 1000))


if __name__ == '__main__':
    unittest.main(exit=False)