#!/bin/bash

# Copyright (c) 2016 Dell Inc. or its subsidiaries.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

IDRAC_USER=$1
IDRAC_PASS=$2

function usage {
  echo "USAGE: $0 idrac_user idrac_password [ enable | disable ]"
  exit -1
}
 
if [ $# -le 2 ]
then
  usage
fi

source ~/stackrc
env | grep OS_
SSH_CMD="ssh -l heat-admin"

function enable_stonith {
  # For all controller nodes (select by flavor rather than name)
  for i in $(nova list | awk ' /controller/ && /ctlplane/ { print $12 } ' | cut -f2 -d=)
  do
    # create the fence device
    IPADDR=`$SSH_CMD $i 'sudo ipmitool lan print 1 | grep -v Source | grep "IP Address " | cut -d: -f2' | tr -d ' '` 
    HOSTNAME=`$SSH_CMD $i 'echo "$(hostname -s)"'`
    STONITH_NAME="$HOSTNAME-ipmi"
  
    $SSH_CMD $i "sudo pcs stonith create $STONITH_NAME fence_ipmilan pcmk_host_list=$HOSTNAME ipaddr=$IPADDR login=$IDRAC_USER passwd=$IDRAC_PASS lanplus=1 cipher=1 op monitor interval=60s"
  
    # avoid fencing yourself
    $SSH_CMD $i "sudo pcs constraint location $STONITH_NAME avoids $HOSTNAME"
  done

  # enable STONITH devices from any controller; hence we can use the last node 
  $SSH_CMD $i 'sudo pcs property set stonith-enabled=true'
  $SSH_CMD $i 'sudo pcs property show'
}

function disable_stonith {
  for i in $(nova list --flavor control --fields networks | awk ' /ctlplane/ { print $4 } ' | cut -f2 -d=)
  do
    STONITH_NAME=`$SSH_CMD $i 'echo "$(hostname -s)-ipmi"'`
    $SSH_CMD $i "sudo pcs stonith delete $STONITH_NAME"
  done 

  # disable STONITH devices from any controller; hence we can use the last node 
  $SSH_CMD $i 'sudo pcs property set stonith-enabled=false'
  $SSH_CMD $i 'sudo pcs property show'
}

if [[ $3 == "enable" ]]
then
  enable_stonith
elif [[ $3 == "disable" ]]
then 
  disable_stonith
else
  echo "ERROR: Third passed argument mmust be either \"enable\" or \"disable\"." 
  usage
fi
