# Setup required before running those tests :
# on the edge node :
# Stop the chef client (if running) to prevent sudoer file being overwritten :
# 	 bluepill chef-client stop 
# Enable tty for the root account:
#    sudo vi /etc/sudoers
#    add the following line to the end of the file:
#    Defaults:root   !requiretty

# Edge node ip address 
edge_node_ip = "172.16.2.21"
crowbar_admin_ip = "172.16.2.18" # 
time_offset = 6 #hours
cluster_name = "Cluster 1"

run_id = 'lowvaluesTesting7'

#run_id = 'Config3_test4_2d_cpu_default_mem_MAx_MINUS_1'
#run_id = 'Config3_test4_2ab_CPU_Half_Mem_1Gb'
#T4_Set_yarn_nodemanager_resource_cpu-vcores_to_1_b

             
# Teragen Row Count test values
teragen_parameters ='-D yarn.nodemanager.resource.cpu-vcores=8 -D yarn.nodemanager.resource.memory-mb=8'
#params ignored by yarn
teragen_row_counts = (#50000001,
                      #130000000,
                      #10000000000,
		      120000000,                 
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
			   'total_bytes_receive_rate_across_network_interfaces',
                           'total_bytes_transmit_rate_across_network_interfaces',
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
			   'total_bytes_receive_rate_across_network_interfaces',
                           'total_bytes_transmit_rate_across_network_interfaces',
			   #'await_time',
			   'total_read_bytes_rate_across_disks',
			   'total_write_bytes_rate_across_disks',
			   #'total_read_ios_rate_across_disks',
			   #'total_write_ios_rate_across_disks'

			 ) 
                                
# Teragen ganglia stast to collect                              
teragen_ganglia_stats = ('boottime',
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
terasort_ganglia_stats = ('boottime',
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


terasort_parameters ='-D yarn.nodemanager.resource.cpu-vcores=8 -D yarn.nodemanager.resource.memory-mb=8'

# dfsio number of files : file Size test value
dfsio_test_values = {
		     #24:42667,
		     160:30,
                     #10:10
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
			   'total_bytes_receive_rate_across_network_interfaces',
			   'total_bytes_transmit_rate_across_network_interfaces',
			   #'await_time',
			   'total_read_bytes_rate_across_disks',
			   'total_write_bytes_rate_across_disks',
			   #'total_read_ios_rate_across_disks',
			   #'total_write_ios_rate_across_disks'

			 )


