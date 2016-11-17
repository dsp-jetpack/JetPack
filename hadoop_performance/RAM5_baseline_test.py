import time, calendar, re, uuid,  importlib, datetime, subprocess, paramiko, sys, os, requests, logging
import fileinput
from cm_api.api_client import ApiResource
import dateutil.parser
from datetime import timedelta
from auto_common import *
from sandbox import ConfigStamp, ReportBuilder
from shutil import copyfile

params = {yarn_nodemanager_resource_memory_mb	=	204800
yarn_nodemanager_resource_cpu_vcores	=	56
yarn_scheduler_minimum_allocation_mb	=	5120
yarn_scheduler_minimum_allocation_vcores	=	1
yarn_scheduler_increment_allocation_mb	=	512
yarn_scheduler_increment_allocation_vcores	=	1
yarn_scheduler_maximum_allocation_mb	=	204800
yarn_scheduler_maximum_allocation_vcores	=	56
mapreduce_map_memory_mb	=	5120
mapreduce_map_cpu_vcores	=	1
mapreduce_reduce_memory_mb	=	10240
mapreduce_reduce_cpu_vcores	=	1
mapreduce_map_java_opts_max_heap	=	4294967296
mapreduce_reduce_java_opts_max_heap	=	8589934592
yarn_app_mapreduce_am_resource_mb	=	10240
yarn_app_mapreduce_am_max_heap	=	8589934592
}
set_config_params(params)