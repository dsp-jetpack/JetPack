#!/bin/bash

source ~/stackrc
env | grep OS_
SSH_CMD="ssh -l heat-admin"

function usage {
   echo "USAGE: $0"
   exit 1
}

function disable_stonith {
  # For all controller nodes (select by flavor rather than name)
  for i in $(nova list --flavor control --fields networks | awk ' /ctlplane/ { print $4 } ' | cut -f2 -d=)
  do
    echo $i
  done

  # enable STONITH devices from any controller
  $SSH_CMD $i 'sudo pcs property set stonith-enabled=false'
  $SSH_CMD $i 'sudo pcs property show'
}

disable_stonith


