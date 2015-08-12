
# OpenStack - A set of software tools for building and managing cloud computing
# platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.

# Setup required before running those tests :
# on the edge node :
# Stop the chef client (if running) to prevent sudoer file being overwritten :
# 	 bluepill chef-client stop 
# Enable tty for the root account:
#    sudo vi /etc/sudoers
#    add the following line to the end of the file:
#    Defaults:root   !requiretty

# Edge node ip address 
edge_node_ip = "172.16.14.100"

#point to ganglia node
crowbar_admin_ip = "172.16.14.100" # 

time_offset = 0 #hours
cluster_name = "Cluster 1"

hadoop_ip = "172.16.14.100"
name_node_ip = "172.16.14.100"

tpc_ip = "172.16.14.97"
clean_up_ip = "172.16.14.97"

#run_id = 'terasort_Nicholas_repeat test5 & mapred.child.ulimit=2GB'

run_id = 'TPC kit-30TB MaxRes 1GB blocksize slowstart=0.05 map 48/reduce.max=32 maps/reduce=576/320'
#run_id = 'config2_Test4_3_iv_MAX'
#run_id = 'config1_MAX-mr2_high-perf-mr1_test2'
#run_id = 'Config3_test4_2d_cpu_default_mem_MAx_MINUS_1'
#run_id = 'Config3_test4_2ab_CPU_Half_Mem_1Gb'
#T4_Set_yarn_nodemanager_resource_cpu-vcores_to_1_b

#-D dfs.replication=1 -D dfs.blocksize=536870912 -D mapred.tasktracker.map.tasks.maximum=24 -D mapred.tasktracker.reduce.tasks.maximum=8 -D mapred.map.tasks=90 -D mapred.reduce.tasks=30
             
# Teragen Row Count test values
#teragen_parameters ='-D dfs.replication=3 -D dfs.blocksize=1073741824 -D mapred.tasktracker.map.tasks.maximum=32 -D mapred.tasktracker.reduce.tasks.maximum=16 -D mapred.map.tasks=180 -D mapred.reduce.tasks=98'
teragen_parameters ='-D dfs.replication=3 -D dfs.blocksize=536870912 -D mapred.tasktracker.map.tasks.maximum=48 -D mapred.tasktracker.reduce.tasks.maximum=24 -D mapred.map.tasks=180 -D mapred.reduce.tasks=98'
#teragen_parameters ='-D yarn.nodemanager.resource.cpu-vcores=32 -D yarn.nodemanager.resource.memory-mb=30720 -D dfs.replication=1 -D dfs.blocksize=536870912 -D mapreduce.map.cpu.vcores=1 -D mapreduce.reduce.cpu.vcores=1 -D mapreduce.map.memory.mb=1024 -D mapreduce.reduce.memory.mb=2048'
#teragen_parameters ='-D yarn.nodemanager.resource.cpu-vcores=32 -D yarn.nodemanager.resource.memory-mb=30720 -D yarn.scheduler.maximum-allocation-vcores=32 -D yarn.scheduler.minimum-allocation-mb=2048 -D yarn.scheduler.minimum-allocation-vcores=1 -D dfs.replication=1 -D dfs.blocksize=536870912 -D mapreduce.map.cpu.vcores=1 -D mapreduce.reduce.cpu.vcores=1 -D mapreduce.map.memory.mb=2048 -D mapreduce.reduce.memory.mb=4096 -D mapreduce.map.java.opts=1638 -D mapreduce.reduce.java.opts=3276 -D yarn.app.mapreduce.am.resource.mb=4096 -D yarn.app.mapreduce.am.command-opts=3276'
#teragen_parameters ='-D yarn.nodemanager.resource.cpu-vcores=32 -D yarn.nodemanager.resource.memory-mb=31744 -D dfs.replication=1 -D dfs.blocksize=536870912 -D mapred.tasktracker.map.tasks.maximum=24 -D mapred.tasktracker.reduce.tasks.maximum=8 -D mapred.map.tasks=90 -D mapred.reduce.tasks=30'
#teragen_parameters ='-D yarn.nodemanager.resource.cpu-vcores=8 -D yarn.nodemanager.resource.memory-mb=8'
#teragen_parameters = ''
#params ignored by yarn
teragen_row_counts = (#5000000000,
                      #1000000000,
                      #10000000000,--1TB
                      #10000000000,
                      #10000000000,
		      #140000000,                     
		      #2000000001,
              #NICHOLAS_run#3000000000,
              #2000000003,
                      #4550500000,
 		      #2700000002,
                      #1700000003,
                      #50000000000,
                      )
             
# Teragen Cloud Era manager statistic to collect 
teragen_cloudera_stats = (#'cpu_soft_irq_rate',
		           #'cpu_iowait_rate',
			   #'cpu_irq_rate',
			   'cpu_user_rate',
			   #'load_15',
			   #'load_5',
			   #'load_1',
			   #'cpu_system_rate',
			   #'physical_memory_buffers',
			   #'physical_memory_cached',
			   'physical_memory_used',
			   #'swap_used',
			   #'swap_out_rate',
			   #'total_bytes_receive_rate_across_network_interfaces',
                           #'total_bytes_transmit_rate_across_network_interfaces',
			   #'await_time',
			   'total_read_bytes_rate_across_disks',
			   'total_write_bytes_rate_across_disks',
			   #'total_read_ios_rate_across_disks',
			   #'total_write_ios_rate_across_disks'

			 )
terasort_cloudera_stats = (#'cpu_soft_irq_rate',
		           #'cpu_iowait_rate',
			   #'cpu_irq_rate',
			   'cpu_user_rate',
			   #'load_15',
			   #'load_5',
			   #'load_1',
			   #'cpu_system_rate',
			   #'physical_memory_buffers',
			   #'physical_memory_cached',
			   'physical_memory_used',
			   #'swap_used',
			   #'swap_out_rate',
			   #'total_bytes_receive_rate_across_network_interfaces',
                           #'total_bytes_transmit_rate_across_network_interfaces',
			   #'await_time',
			   'total_read_bytes_rate_across_disks',
			   'total_write_bytes_rate_across_disks',
			   #'total_read_ios_rate_across_disks',
			   #'total_write_ios_rate_across_disks'

			 ) 
                                
# Teragen ganglia stast to collect                              
teragen_ganglia_stats = (#'boottime',
			 'bytes_in',
			 'bytes_out',
			)
   			 
			 #'boottime'
			 #'bytes_in',
                         #'bytes_out',
			 #'cpu_aidle'
			 #'cpu_idle'
			 #'cpu_nice'
			 #'cpu_num'
			 #'cpu_speed'
			 #'cpu_system'
			 #'cpu_user'
			 #'cpu_wio'
			 #'disk_free'
			 #'disk_total'
			 #'load_fifteen'
			 #'load_five'
			 #'load_one'
			 #'mem_buffers'
			 #'mem_cached'
			 #'mem_free'
			 #'mem_shared'
			 #'mem_total'
			 #'part_max_used'
			 #'pkts_in'
			 #'pkts_out'
			 #'proc_run'
			 #'proc_total'
			 #'swap_free'
			 #'swap_total'


# Terasort ganglia stast to collect                              
terasort_ganglia_stats = (#'boottime',
			 'bytes_in',
			 'bytes_out',
			 )
   			 
			 #'bytes_in',
                         #'bytes_out',
                         #'write_bytes_disk_sum',
                         #'total_cpu_user',
                         #'total_cpu_iowait',
                         #'total_cpu_system',
                         #'total_cpu_soft_irq')

# DFSIO ganglia stats to collect                              
dfsio_ganglia_stats = (#'boottime',
			 'bytes_in',
			 'bytes_out',
			 )
   			 
			 #'bytes_in',
                         #'bytes_out',
                         #'write_bytes_disk_sum',
                         #'total_cpu_user',
                         #'total_cpu_iowait',
                         #'total_cpu_system',
                         #'total_cpu_soft_irq')


terasort_parameters ='-D dfs.replication=3 -D dfs.blocksize=536870912 -D mapred.tasktracker.map.tasks.maximum=48 -D mapred.tasktracker.reduce.tasks.maximum=24 -D mapred.map.tasks=180 -D mapred.reduce.tasks=98'
#terasort_parameters ='-D yarn.nodemanager.resource.cpu-vcores=32 -D yarn.nodemanager.resource.memory-mb=30720 -D dfs.replication=1 -D dfs.blocksize=536870912 -D mapreduce.map.cpu.vcores=1 -D mapreduce.reduce.cpu.vcores=1 -D mapreduce.map.memory.mb=1024 -D mapreduce.reduce.memory.mb=2048'
#terasort_parameters = '-D yarn.nodemanager.resource.cpu-vcores=32 -D yarn.nodemanager.resource.memory-mb=30720 -D yarn.scheduler.maximum-allocation-vcores=32  -D yarn.scheduler.minimum-allocation-mb=2048 -D yarn.scheduler.minimum-allocation-vcores=1 -D dfs.replication=1 -D dfs.blocksize=536870912 -D mapreduce.map.cpu.vcores=1 -D mapreduce.reduce.cpu.vcores=1 -D mapreduce.map.memory.mb=2048 -D mapreduce.reduce.memory.mb=4096 -D mapreduce.map.java.opts=1638 -D mapreduce.reduce.java.opts=3276 -D yarn.app.mapreduce.am.resource.mb=4096 -D yarn.app.mapreduce.am.command-opts=3276'
#terasort_parameters = '-D yarn.nodemanager.resource.cpu-vcores=32 -D yarn.nodemanager.resource.memory-mb=31744 -D dfs.replication=1 -D dfs.blocksize=536870912 -D mapred.tasktracker.map.tasks.maximum=24 -D mapred.tasktracker.reduce.tasks.maximum=8 -D mapred.map.tasks=90 -D mapred.reduce.tasks=30'
#terasort_parameters = '-D yarn.nodemanager.resource.cpu-vcores=1 -D yarn.nodemanager.resource.memory-mb=1'
# dfsio number of files : file Size test value
dfsio_test_values = {
		     #320:50,
		     #310:55,
		     #24:4267,
		     #24:21333,
		     #24:42667,
		     #24:128000,
                     #24:213333,
                     }

# dfsio Cloudera manager statistics to collect 
dfsio_cloudera_stats = (#'cpu_soft_irq_rate',
		           #'cpu_iowait_rate',
			   #'cpu_irq_rate',
			   'cpu_user_rate',
			   #'load_15',
			   #'load_5',
			   #'load_1',
			   #'cpu_system_rate',
			   #'physical_memory_buffers',
			   #'physical_memory_cached',
			   'physical_memory_used',
			   #'swap_used',
			   #'swap_out_rate',
			   #'total_bytes_receive_rate_across_network_interfaces',
			   #'total_bytes_transmit_rate_across_network_interfaces',
			   #'await_time',
			   'total_read_bytes_rate_across_disks',
			   'total_write_bytes_rate_across_disks',
			   #'total_read_ios_rate_across_disks',
			   #'total_write_ios_rate_across_disks'

			 )

hive_join_flag = 'NTrue' # 'True' or 'False'
hive_aggregation_flag = 'NTrue'
#pages = 1200000000
uservisits = 100000000
pages = 120000000
#uservisits = 10000000000
#pages = 13450000
#uservisits = 198700000

# HIVE Cloudera manager statistics to collect 
hive_cloudera_stats = (#'cpu_soft_irq_rate',
		           #'cpu_iowait_rate',
			   #'cpu_irq_rate',
			   'cpu_user_rate',
			   #'load_15',
			   #'load_5',
			   #'load_1',
			   #'cpu_system_rate',
			   #'physical_memory_buffers',
			   #'physical_memory_cached',
			   'physical_memory_used',
			   #'swap_used',
			   #'swap_out_rate',
			   #'total_bytes_receive_rate_across_network_interfaces',
			   #'total_bytes_transmit_rate_across_network_interfaces',
			   #'await_time',
			   'total_read_bytes_rate_across_disks',
			   'total_write_bytes_rate_across_disks',
			   #'total_read_ios_rate_across_disks',
			   #'total_write_ios_rate_across_disks'

			 )

# HIVE ganglia stats to collect                              
hive_ganglia_stats = (#'boottime',
			 'bytes_in',
			 'bytes_out',
			 )
   			 
			 #'bytes_in',
                         #'bytes_out',
                         #'write_bytes_disk_sum',
                         #'total_cpu_user',
                         #'total_cpu_iowait',
                         #'total_cpu_system',
                         #'total_cpu_soft_irq')
                         
# KMEANS VARIABLES                         
kmeans_flag = 'False' #or True/False
num_iterations = 2
num_of_clusters = 25
#num_of_clusters=100
#NUM_OF_SAMPLES=20000000
num_of_samples = 10000000
#samples was 100
#SAMPLES_PER_INPUTFILE=4000000
#SAMPLES_PER_INPUTFILE=6000000
samples_per_inputfile = 6000000
#inputfile was 10000
dimensions = 40

# Kmeans Cloudera Manager statistics to collect
kmeans_cloudera_stats = (#'cpu_soft_irq_rate',
                   #'cpu_iowait_rate',
               #'cpu_irq_rate',
               'cpu_user_rate',
               #'load_15',
               #'load_5',
               #'load_1',
               #'cpu_system_rate',
               #'physical_memory_buffers',
               #'physical_memory_cached',
               'physical_memory_used',
               #'swap_used',
               #'swap_out_rate',
               #'total_bytes_receive_rate_across_network_interfaces',
               #'total_bytes_transmit_rate_across_network_interfaces',
               #'await_time',
               'total_read_bytes_rate_across_disks',
               'total_write_bytes_rate_across_disks',
               #'total_read_ios_rate_across_disks',
               #'total_write_ios_rate_across_disks'

             )

# kmeans ganglia stats to collect                              
kmeans_ganglia_stats = (#'boottime',
             'bytes_in',
             'bytes_out',
             )
                
             #'bytes_in',
                         #'bytes_out',
                         #'write_bytes_disk_sum',
                         #'total_cpu_user',
                         #'total_cpu_iowait',
                         #'total_cpu_system',
                         #'total_cpu_soft_irq')
                         

tpc_flag = 'true'
tpc_size = '6'
#tpc_location = '/tpc_xhs_kit/TPCx-HS_Kit_v1.2.0_external/TPCx-HS-Runtime-Suite'
tpc_location = '/tpc_xhs_kit/tpcx-hs_kit_v1.2.0_external/TPCx-HS_Kit_v1.2.0_external/TPCx-HS-Runtime-Suite'
tpc_file = 'Benchmark_Parameters.sh'
NUM_MAPS = '576'
NUM_REDUCERS = '320'
HADOOP_USER = 'root'
HDFS_USER='hdfs'
SLEEP_BETWEEN_RUNS= '60'