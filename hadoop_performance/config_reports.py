#!/usr/bin/env python

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


report_location = 'ResultLogArch'

results_file = 'Results-10000000000 T37.log'
tpc_log = 'tpc_log.log'

job_history_ip = '172.16.14.97'

history_location = 'hdfs:///user/history/done/2016/02/04/000000/'

#job_id = 'job_1453282072018_0006'
#job_id = 'job_1453363483287_0002'
job_id = 'job_1454593041052_0002'

node = 'r3s1xd8.ignition.dell.'

params = ('dfs.replication',
            'dfs.blocksize',
            #'mapreduce.tasktracker.map.tasks.maximum',
            #'mapreduce.tasktracker.reduce.tasks.maximum',
            #'mapred.map.tasks=576(HSGen); 320 (HSValidate)',
            #'mapred.reduce.tasks=320(HSSort); 1 (HSValidate)',
            'mapreduce.task.io.sort.mb',
            #'io.sort.record.percent',
            'mapreduce.map.sort.spill.percent',
            #'Java Heap Size of Namenode= 4GB',
            #'Java Heap Size of Secondary Namenode=4GB',
            'mapreduce.job.reduce.slowstart.completedmaps',
            'dfs.namenode.handler.count',
            'dfs.datanode.handler.count',
            #'MTU=9710',
            'mapreduce.map.java.opts',
            'mapreduce.reduce.java.opts',
            'yarn.nodemanager.resource.memory-mb',
            'yarn.nodemanager.resource.cpu-vcores',
            'yarn.scheduler.minimum-allocation-mb',
            'yarn.scheduler.minimum-allocation-vcores',
            'yarn.scheduler.increment-allocation-mb',
            'yarn.scheduler.increment-allocation-vcores',
            'yarn.scheduler.maximum-allocation-mb',
            'yarn.scheduler.maximum-allocation-vcores',
            'mapreduce.map.memory.mb',
            'mapreduce.map.cpu.vcores',
            'mapreduce.reduce.memory.mb',
            'mapreduce.reduce.cpu.vcores',
            'yarn.app.mapreduce.am.resource.mb',
            'yarn.app.mapreduce.am.command-opts')

'''
# Edge node ip address 
edge_node_ip = "172.16.14.101"

#cloudera manager api IP address
cm_api_ip = "172.16.14.101"

#ganglia server IP address
ganglia_ip = "172.16.14.101"
ganglia_stat_locations = '/var/lib/ganglia/rrds/13g\ Performance\ Stamp/'

#point to ganglia node
crowbar_admin_ip = "172.16.14.101" # 

time_offset = 6 #hours
cluster_name = "Cluster 1"

hadoop_ip = "172.16.14.97"
name_node_ip = "172.16.14.97"
teragen_ip = '172.16.14.97'

tpc_node_ip = "172.16.14.97"
clean_up_ip = "172.16.14.97"
'''
