# Delete all files in HDFS
from perftest2 import clear_disks
import time

clean_up_ip = "172.16.14.97"

out, err = clear_disks(clean_up_ip)

print out