# num of containers = 40
#RAM per Container = 3 mapreduce.job.reduce=480	additional params:   -D mapred.map.tasks=576

# 120	yarn_nodemanager_resource_memory_mb
# 48	yarn_nodemanager_resource_cpu_vcores
# 3	yarn_scheduler_minimum_allocation_mb
# 1	yarn_scheduler_minimum_allocation_vcores
# 512	yarn_scheduler_increment_allocation_mb
# 1	yarn_scheduler_increment_allocation_vcores
# 120	yarn_scheduler_maximum_allocation_mb
# 48	yarn_scheduler_maximum_allocation_vcores
# 3	mapreduce_map_memory_mb
# 1	mapreduce_map_cpu_vcores
# 6	mapreduce_reduce_memory_mb
# 1	mapreduce_reduce_cpu_vcores
# 2.4	mapreduce_map_java_opts_max_heap
# 4.8	mapreduce_reduce_java_opts_max_heap
# 6	yarn_app_mapreduce_am_resource_mb
# 4.8	yarn_app_mapreduce_am_max_heap


yarn_nodemanager_resource_memory_mb	=	122880
yarn_nodemanager_resource_cpu_vcores	=	48
yarn_scheduler_minimum_allocation_mb	=	3072
yarn_scheduler_minimum_allocation_vcores	=	1
yarn_scheduler_increment_allocation_mb	=	512
yarn_scheduler_increment_allocation_vcores	=	1
yarn_scheduler_maximum_allocation_mb	=	122880
yarn_scheduler_maximum_allocation_vcores	=	48
mapreduce_map_memory_mb	=	3072
mapreduce_map_cpu_vcores	=	1
mapreduce_reduce_memory_mb	=	6144
mapreduce_reduce_cpu_vcores	=	1
mapreduce_map_java_opts_max_heap	=	2576980378
mapreduce_reduce_java_opts_max_heap	=	5153960755
yarn_app_mapreduce_am_resource_mb	=	6144
yarn_app_mapreduce_am_max_heap	=	5153960755


dfs_block_size = 1073741824 # 536870912
datanode_java_heapsize = 2147483648 # 1073741824
namenode_java_heapsize = 4294967296 # 2695091978
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
             'yarn_app_mapreduce_am_max_heap' : yarn_app_mapreduce_am_max_heap #10307921510
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