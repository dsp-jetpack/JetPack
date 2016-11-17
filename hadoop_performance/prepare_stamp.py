# prepare stamp for Cluster redeployment

from perftest2 import prepare_cluster
import time

name_node = "172.16.14.97"
secondary_nn = name_node

# deleting files from /var/dfs/nn and /var/dfs/snn
out, err = prepare_cluster(name_node, secondary_nn)

print out