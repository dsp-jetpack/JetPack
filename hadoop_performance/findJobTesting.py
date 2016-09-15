# This tests the repeatability of Teragen - compare runtimes of each teragen run.
from perftest2 import findJob
import time

ip = '172.16.14.97'
dir = 'hdfs:///user/hdfs/*'


sf = 1
ls = findJob(ip, sf)

sf = 3
ls = findJob(ip, sf)

sf = 10
ls = findJob(ip, sf)

sf = 2
ls = findJob(ip, sf)