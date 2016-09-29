# num of containers = 40
# RAM per Container = 5 mapreduce.job.reduce=480	additional params:   -D mapred.map.tasks=576

# 200	yarn_nodemanager_resource_memory_mb
# 48	yarn_nodemanager_resource_cpu_vcores
# 5	yarn_scheduler_minimum_allocation_mb
# 1	yarn_scheduler_minimum_allocation_vcores
# 512	yarn_scheduler_increment_allocation_mb
# 1	yarn_scheduler_increment_allocation_vcores
# 200	yarn_scheduler_maximum_allocation_mb
# 48	yarn_scheduler_maximum_allocation_vcores
# 5	mapreduce_map_memory_mb
# 1	mapreduce_map_cpu_vcores
# 10	mapreduce_reduce_memory_mb
# 1	mapreduce_reduce_cpu_vcores
# 4	mapreduce_map_java_opts_max_heap
# 8	mapreduce_reduce_java_opts_max_heap
# 10	yarn_app_mapreduce_am_resource_mb
# 8	yarn_app_mapreduce_am_max_heap


yarn_nodemanager_resource_memory_mb	=	204800
yarn_nodemanager_resource_cpu_vcores	=	48
yarn_scheduler_minimum_allocation_mb	=	5120
yarn_scheduler_minimum_allocation_vcores	=	1
yarn_scheduler_increment_allocation_mb	=	512
yarn_scheduler_increment_allocation_vcores	=	1
yarn_scheduler_maximum_allocation_mb	=	204800
yarn_scheduler_maximum_allocation_vcores	=	48
mapreduce_map_memory_mb	=	5120
mapreduce_map_cpu_vcores	=	1
mapreduce_reduce_memory_mb	=	10240
mapreduce_reduce_cpu_vcores	=	1
mapreduce_map_java_opts_max_heap	=	4294967296
mapreduce_reduce_java_opts_max_heap	=	8589934592
yarn_app_mapreduce_am_resource_mb	=	10240
yarn_app_mapreduce_am_max_heap	=	8589934592
mapred_reduce_tasks = 480 # 240 # 576
mapred_reduce_slowstart_completed_maps = 0.05

dfs_block_size = 536870912 # 1073741824
datanode_java_heapsize = 1073741824 # 1073741824
namenode_java_heapsize = 2695091978 # 1073741824 # 2695091978
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