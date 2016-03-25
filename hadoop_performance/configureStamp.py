import time, calendar, re, uuid,  importlib
import ConfigParser
from cm_api.api_client import ApiResource
from cm_api.endpoints.services import ApiService
from cm_api.endpoints.types import BaseApiObject
from cm_api.endpoints.role_config_groups import ApiRoleConfigGroup


def main():

    #config = importlib.import_module('config_cdh5')
    config_cluster = importlib.import_module('SF1_RPC_5')
    cm_api_ip = config_cluster.cm_api_ip
    clustername = config_cluster.cluster_name

    API = ApiResource(cm_api_ip,  7180, "admin", "admin", version=5)

    print "Connected to CM host on " + cm_api_ip

    CLUSTER = API.get_cluster(clustername)

    c_services = CLUSTER.get_all_services()
    for cs in c_services:
        if cs.name == 'hdfs':
            print 'configuring HDFS'
            cs.update_config(config_cluster.dn_config)
            hdfs_groups = cs.get_all_role_config_groups()
            for each in hdfs_groups:
                if each.name == 'hdfs-DATANODE-BASE':
                    print 'configuring: ' + str(each.name)
                    each.update_config(config_cluster.hdfs_dn_config)
                if each.name == 'hdfs-NAMENODE-BASE':
                    print 'configuring: ' + str(each.name)
                    each.update_config(config_cluster.hdfs_nn_config)
                if each.name == 'hdfs-SECONDARYNAMENODE-BASE':
                    print 'configuring: ' + str(each.name)
                    each.update_config(config_cluster.hdfs_snn_config)

        if cs.name == 'yarn':
            yarn_groups = cs.get_all_role_config_groups()
            for each in yarn_groups:
                if each.name == 'yarn-NODEMANAGER-BASE':
                    print 'configuring: ' + str(each.name)
                    each.update_config(config_cluster.nm_config)
                if each.name == 'yarn-GATEWAY-BASE':
                    print 'configuring: ' + str(each.name)
                    each.update_config(config_cluster.gw_config)  
                if each.name == 'yarn-RESOURCEMANAGER-BASE':
                    print 'configuring: ' + str(each.name)
                    each.update_config(config_cluster.rm_config)
                    
    print "Restarting cluster"
    CLUSTER.restart().wait()
    CLUSTER.deploy_client_config().wait()
    print "Cluster restarted"

    for c in API.get_all_clusters():
        if c.version == "CDH5":
            cdh4 = c
    for s in cdh4.get_all_services():
        print s
        if s.name == 'mapreduce':
            print "Found mapreduce running - how dare it... stopping Mapreduce"
            s.stop().wait()
            print "Mapreduce stopped"

if __name__ == "__main__":
   main()