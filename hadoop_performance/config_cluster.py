#RAM per Container = 1

# 48	yarn.nodemanager.resource.memory-mb
# 48	yarn.nodemanager.resource.cpu-vcores 

# 1	    yarn.scheduler.minimum-allocation-mb
# 1	    yarn.scheduler.minimum-allocation-vcores
# 512	yarn.scheduler.increment-allocation-mb
# 1	    yarn.scheduler.increment-allocation-vcores
# 48	yarn.scheduler.maximum-allocation-mb
# 48	yarn.scheduler.maximum-allocation-vcores

# 1	    mapreduce.map.memory.mb
# 1	    mapreduce.map.cpu.vcores
# 2	    mapreduce.reduce.memory.mb
# 1	    mapreduce.reduce.cpu.vcores
# 0.8	mapreduce.map.java.opts
# 1.6	mapreduce.reduce.java.opts
# 2	    yarn.app.mapreduce.am.resource.mb
# 1.6	yarn.app.mapreduce.am.command-opts

yarn_nodemanager_resource_memory_mb	=	49152
yarn_nodemanager_resource_cpu_vcores	=	48
yarn_scheduler_minimum_allocation_mb	=	1024
yarn_scheduler_minimum_allocation_vcores	=	1
yarn_scheduler_increment_allocation_mb	=	512
yarn_scheduler_increment_allocation_vcores	=	1
yarn_scheduler_maximum_allocation_mb	=	49152
yarn_scheduler_maximum_allocation_vcores	=	48
mapreduce_map_memory_mb	=	1024
mapreduce_map_cpu_vcores	=	1
mapreduce_reduce_memory_mb	=	2048
mapreduce_reduce_cpu_vcores	=	1
mapreduce_map_java_opts_max_heap	=	858993459
mapreduce_reduce_java_opts_max_heap	=	1717986918
yarn_app_mapreduce_am_resource_mb	=	2048
yarn_app_mapreduce_am_max_heap	=	1717986918


mapred_reduce_tasks = 240 # 240 # 480 # 576 # mapreduce.job.reduces
mapred_reduce_slowstart_completed_maps = 0.05

dfs_block_size = 1073741824 # 536870912 # 1073741824
datanode_java_heapsize = 2147483648 # 1073741824 # 2147483648
namenode_java_heapsize = 4294967296 # 2695091978 # 4294967296
secondary_namenode_java_heapsize = namenode_java_heapsize

#cloudera manager api IP address
cm_api_ip = "172.16.14.156"

cluster_name = "Cluster 1"

nm_config = {'yarn_nodemanager_resource_memory_mb' : yarn_nodemanager_resource_memory_mb, 
             'yarn_nodemanager_resource_cpu_vcores' : yarn_nodemanager_resource_cpu_vcores
            }

gw_config = {'mapreduce_map_memory_mb' : mapreduce_map_memory_mb, #Gateway
             'mapreduce_map_cpu_vcores' : mapreduce_map_cpu_vcores, #GW
             'mapreduce_reduce_memory_mb' : mapreduce_reduce_memory_mb, #GW
             'mapreduce_reduce_cpu_vcores' : mapreduce_reduce_cpu_vcores, #GW
             'mapreduce_map_java_opts_max_heap' : mapreduce_map_java_opts_max_heap, #5153960755, #    GW 858993459
             'mapreduce_reduce_java_opts_max_heap' : mapreduce_reduce_java_opts_max_heap, #10307921510, # 1717986918
             'yarn_app_mapreduce_am_resource_mb' : yarn_app_mapreduce_am_resource_mb, #GW
             'yarn_app_mapreduce_am_max_heap' : yarn_app_mapreduce_am_max_heap, #10307921510
             'mapred_reduce_tasks' : mapred_reduce_tasks,
             'mapred_reduce_slowstart_completed_maps' : mapred_reduce_slowstart_completed_maps
            }

rm_config = {'yarn_scheduler_minimum_allocation_mb' : yarn_scheduler_minimum_allocation_mb,
             'yarn_scheduler_minimum_allocation_vcores' : yarn_scheduler_minimum_allocation_vcores,
             'yarn_scheduler_increment_allocation_mb' : yarn_scheduler_increment_allocation_mb,
             'yarn_scheduler_increment_allocation_vcores' : yarn_scheduler_increment_allocation_vcores,
             'yarn_scheduler_maximum_allocation_mb' : yarn_scheduler_maximum_allocation_mb,
             'yarn_scheduler_maximum_allocation_vcores' : yarn_scheduler_maximum_allocation_vcores
            }

dn_config = {'dfs_replication' : 3,
             'dfs_block_size' : dfs_block_size
            }

hdfs_dn_config = {'datanode_java_heapsize': datanode_java_heapsize 
            }

hdfs_nn_config = {'namenode_java_heapsize': namenode_java_heapsize 
            }

hdfs_snn_config = {'secondary_namenode_java_heapsize': secondary_namenode_java_heapsize 
            }