import os
import time
import unittest

# These are sometimes handy for debugging...
# from network_testing import netlog
# netlog.init()
# netlog.enable_debug()

from network_testing.iperf3 import Iperf3IntervalResult
from network_testing.iperf3 import Iperf3Server, Iperf3Client

data_dir = 'tests/test_data'

class TestIperf3IntervalResult(unittest.TestCase):

    def test_instance(self):
        """object creation with default arguments"""
        instance = Iperf3IntervalResult()
        self.assertTrue(instance)


class TestIperf3Server(unittest.TestCase):

    def test_instance(self):
        """object creation with default arguments"""
        instance = Iperf3Server('localhost', 8080)
        self.assertTrue(instance)

    def test_start_stop(self):
        """start and stop an iperf server"""
        server = Iperf3Server('localhost', 8080)
        server.start()
        time.sleep(3)
        server.stop()
        server.join(10)
        self.assertFalse(server.is_alive())
        self.assertEqual(server.exit_code, 0)

class TestIperf3Client(unittest.TestCase):

    def test_instance(self):
        """object creation with default arguments"""
        instance = Iperf3Client('localhost', 'remote_host', 8080)
        self.assertTrue(instance)


    def test_results_no_intervals(self): 
        """parse_results with no intermediate intervals (-i 0)"""

        client = Iperf3Client('localhost', 'remote_host', 8080)
        json_file_path = os.path.join(data_dir, 'iperf3_one_interval.json')
        with open(json_file_path) as json_file:
            client.parse_results(json_file)
    
        # sent results
        self.assertEqual(client.final_send_data.bytes, 47610935416)
        self.assertAlmostEqual(client.final_send_data.start_secs, 0, 3)
        self.assertAlmostEqual(client.final_send_data.end_secs, 10, 3)
        self.assertAlmostEqual(client.final_send_data.length_secs, 10, 3)
        self.assertEqual(client.final_send_data.bytes,  47610935416)
        self.assertEqual(client.final_send_data.retransmits,  1)
        self.assertAlmostEqual(client.final_recv_data.bits_per_second,
            3.80883e+10, 3)

        # received results
        self.assertEqual(client.final_recv_data.bytes, 47610935416)
        self.assertAlmostEqual(client.final_recv_data.start_secs, 0, 3)
        self.assertAlmostEqual(client.final_recv_data.end_secs, 10, 3)
        self.assertAlmostEqual(client.final_recv_data.length_secs, 10, 3)
        self.assertEqual(client.final_recv_data.bytes,  47610935416)
        # retransmits always zero for receive
        self.assertEqual(client.final_recv_data.retransmits,  0)
        self.assertAlmostEqual(client.final_recv_data.bits_per_second,
            3.80883e+10, 3)

    def test_running(self):
        """iperf3 client run test"""

        # Assumes an iperf server is running !
        server = Iperf3Server('localhost', 5201)
        server.start()

        client = Iperf3Client('localhost', 'localhost', 5201)
        client.start()
        # it runs async - wait for it to finish
        while client.is_running():
            time.sleep(1)
        self.assertFalse(client.is_running())
        self.assertEqual(client.exit_code, 0)
        self.assertEqual(len(client.stderr), 0)
        self.assertTrue(len(client.stdout) >0 )
        client.parse_results()

        server.stop()
        server.join(10)
        self.assertEqual(server.exit_code, 0)

        
# suite is all the test cases in this module

suite = unittest.TestSuite([
    unittest.TestLoader().loadTestsFromTestCase(TestIperf3IntervalResult),
    unittest.TestLoader().loadTestsFromTestCase(TestIperf3Server),
    unittest.TestLoader().loadTestsFromTestCase(TestIperf3Client),
    ])

