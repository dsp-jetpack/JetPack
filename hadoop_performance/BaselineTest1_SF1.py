
#RAM per Container = 6

# 240	yarn.nodemanager.resource.memory-mb
# 48	yarn.nodemanager.resource.cpu-vcores 

# 6	mapreduce.map.memory.mb
# 1	mapreduce.map.cpu.vcores
# 12	mapreduce.reduce.memory.mb
# 1	mapreduce.reduce.cpu.vcores
# 4.8	mapreduce.map.java.opts
# 9.6	mapreduce.reduce.java.opts
# 12	yarn.app.mapreduce.am.resource.mb
# 9.6	yarn.app.mapreduce.am.command-opts

# 6	yarn.scheduler.minimum-allocation-mb
# 1	yarn.scheduler.minimum-allocation-vcores
# 512	yarn.scheduler.increment-allocation-mb
# 1	yarn.scheduler.increment-allocation-vcores
# 240	yarn.scheduler.maximum-allocation-mb
# 48	yarn.scheduler.maximum-allocation-vcores

nm_config = {'yarn_nodemanager_resource_memory_mb' : 245760, 
             'yarn_nodemanager_resource_cpu_vcores' : 48
            }

gw_config = {'mapreduce_map_memory_mb' : 6144, #Gateway
             'mapreduce_map_cpu_vcores' : 1, #GW
             'mapreduce_reduce_memory_mb' : 12288, #GW
             'mapreduce_reduce_cpu_vcores' : 1, #GW
             'mapreduce_map_java_opts_max_heap' : 5153960755, #    GW 858993459
             'mapreduce_reduce_java_opts_max_heap' : 10307921510, # 1717986918
             'yarn_app_mapreduce_am_resource_mb' : 12288, #GW
             'yarn_app_mapreduce_am_max_heap' : 10307921510
            }
          
rm_config = {'yarn_scheduler_minimum_allocation_mb' : 6144,
             'yarn_scheduler_minimum_allocation_vcores' : 1,
             'yarn_scheduler_increment_allocation_mb' : 512,
             'yarn_scheduler_increment_allocation_vcores' : 1,
             'yarn_scheduler_maximum_allocation_mb' : 245760,
             'yarn_scheduler_maximum_allocation_vcores' : 48
            }
            
dn_config = {'dfs_replication' : 3,
             'dfs_block_size' : 536870912
            }
hdfs_dn_config = {'datanode_java_heapsize': 2147483648 #1073741824
            }
            
hdfs_nn_config = {#'dfs_replication' : 2,
             'namenode_java_heapsize': 4294967296#2695091978
            }
            
hdfs_snn_config = {#'dfs_replication' : 2,
             'secondary_namenode_java_heapsize': 4294967296#2695091978
            }   