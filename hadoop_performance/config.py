# Setup required before running those tests :
# on the edge node :
# Stop the chef client (if running) to prevent sudoer file being overwritten :
# 	 bluepill chef-client stop 
# Enable tty for the root account:
#    sudo vi /etc/sudoers
#    add the following line to the end of the file:
#    Defaults:root   !requiretty

# Edge node ip address 
edge_node_ip = "192.168.124.83"
crowbar_admin_ip = "192.168.124.10" # 
cluster_name = "Cluster 1 - CDH4"

run_id = 'test_run'

             
# Teragen Row Count test values
teragen_row_counts = (#500,
                      #1000,
                      #1500,
					  #2000,
                      #2300,
                      #2500,
					  10000,
                      10001,
                      10002,
                      10003,
                      10004,
                      10005,
                      10006,
                      10007,
                      10008,
                      10009,
                      10010,
                      10011,
                      10012,
                      10013,
                      10014,
                      
                      #12000,
                      #15000,
                      #18000,
                      )
             
# Teragen Cloud Era manager statistic to collect 
teragen_cloudera_stats = ('write_bytes_disk_sum', 
                             'total_cpu_iowait', 
                             'physical_memory_used',
                             'total_cpu_user',
                             'total_cpu_system') 

# Teragen ganglia stast to collect                              
teragen_ganglia_stats = ('bytes_in',
                         'bytes_out',
                         'cpu_wio',
                         'cpu_user',
                         'cpu_system',
                         'mem_buffers',
                         'mem_cached',
                          'mem_free',
                          'mem_shared',
                          'mem_total'
                          )
                         

# dfsio number of files : file Size test value
dfsio_test_values = {5:5,
                     #"8:8,
                     #10:10,
                     #20:12,
                     } 

# dfsio Cloud Era manager statistics to collect 
dfsio_cloudera_stats = ('write_bytes_disk_sum',
                         'total_cpu_user',
                         'total_cpu_iowait',
                         'total_cpu_system',
                         'total_cpu_soft_irq',
                         )

                         