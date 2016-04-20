#!/bin/bash

source ~/stackrc
env | grep OS_
SSH_CMD="ssh -l heat-admin"

function usage {
   echo "USAGE: $0"
   exit 1
}

function enable_stonith {
  # For all controller nodes (select by flavor rather than name)
  for i in $(nova list --flavor control --fields networks | awk ' /ctlplane/ { print $4 } ' | cut -f2 -d=)
  # original: nova list | awk ' /controller/ { print $12 } ' | cut -f2 -d=)
  do
    echo $i
    # create the fence device
    if ! $SSH_CMD $i 'sudo pcs stonith | grep "$(hostname -s)-ipmi"' ; then
      $SSH_CMD $i 'sudo pcs stonith create $(hostname -s)-ipmi fence_ipmilan pcmk_host_list=$(hostname -s) ipaddr=$(sudo ipmitool lan print 1 | awk " /IP Address / { print \$4 } ") login=root passwd=PASSWORD lanplus=1 cipher=1 op monitor interval=60sr'
  
      # avoid fencing yourself
      $SSH_CMD $i 'sudo pcs constraint location $(hostname -s)-ipmi avoids $(hostname -s)'
    fi
  done

  # enable STONITH devices from any controller
  $SSH_CMD $i 'sudo pcs property set stonith-enabled=true'
  $SSH_CMD $i 'sudo pcs property show'
}

enable_stonith

