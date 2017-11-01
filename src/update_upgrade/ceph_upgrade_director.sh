#!/bin/bash

# Copyright (c) 2016-2017 Dell Inc. or its subsidiaries.
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

# Logging functions
log() { echo -e "$(date '+%F %T'): $@" >&2; }
fatal() { log "FATAL: $@" >&2; exit 1; }
error() { [[ $ERROR -le $LOG_LEVEL ]] && log "ERROR: $@"; }
warn() { [[ $WARN -le $LOG_LEVEL ]] && log "WARN: $@"; }
info() { [[ $INFO -le $LOG_LEVEL ]] && log "INFO: $@"; }
debug() { [[ $DEBUG -le $LOG_LEVEL ]] && log "DEBUG: $@"; }


execute_command(){
  cmd="$1"

  info "Executing: $cmd"

  $cmd
  if [ $? -ne 0 ]; then
    echo "command failed"
    exit 1
  fi
}
function validate_url(){
  p_url=$1 
  if curl --output /dev/null --silent --head --fail "$p_url"; then
    info '%s\n' "$p_url exist"
  else
    info '%s\n' "$p_url does not exist"
    error 'Failed url'
  fi
}


  info "### Upgrading ceph on Director"
  
  if [[ $# -ne 2 ]]; then
      error 'Number of parameters = $#'
      error "Expecting two parameters <rhscon_node_ip> <root_password>"
      exit 1
  fi
  RHSCON_NODE_IP=$1
  ROOT_PASSWORD=$2
  cd ~/update_upgrade
  execute_command "./config_rhscon_6.py $RHSCON_NODE_IP $ROOT_PASSWORD"

  info "### Verify"
  url="http://$RHSCON_NODE_IP/skyring"
  validate_url $url  

  info "##DONE"

