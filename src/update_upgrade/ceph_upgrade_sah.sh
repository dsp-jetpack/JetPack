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

#CHANGEME             
LEGACY_VM_NAME=ceph
NEW_VM_NAME=rhscon
RHEL_ISO=/store/data/iso/RHEL7.iso
BASE_FOLDER=/root/JetStream/cloud_repo

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

run(){

  info "### Upgrading ceph"
  info "### Delete legacy ceph vm"
  execute_command "virsh list --all"

  instance_status=$(virsh list | grep "$LEGACY_VM_NAME" | awk '{print $3}')
  info "### Instance Status = $instance_status"

  if [ "$instance_status" = "running" ]; then
      execute_command "virsh destroy $LEGACY_VM_NAME"
      execute_command "virsh undefine $LEGACY_VM_NAME"
      execute_command "rm -rf /store/data/images/$LEGACY_VM_NAME.img"
  else
     info "### $LEGACY_VM_NAME vm is not running"
  fi

  info "### TODO Edit the cephvm.cfg  with right parameters"

  info "### Deploy new RHSCon VM"

  #execute_command "cd $BASE_FOLDER/src/mgmt"

  execute_command "./deploy-rhscon-vm-6.py /root/$LEGACY_VM_NAME.cfg $RHEL_ISO"

  info "### Waiting for the rhs con vm to be deployed..."
  instance_status=$(virsh list --all | grep "$NEW_VM_NAME" | awk '{print $3}')
  while [ "$instance_status" != "shut" ]; do
      sleep 60
      instance_status=$(virsh list --all | grep "$NEW_VM_NAME" | awk '{print $3}')
      info "instance_status = $instance_status"
  done
  info "### VM is built, status is ${instance_status}"

  info "### Waiting for the rhs con vm to be started..."
  execute_command "virsh start rhscon"
  instance_status=$(virsh list | grep "$NEW_VM_NAME" | awk '{print $3}')
  while [ "$instance_status" != "running" ]; do
      sleep 10
      instance_status=$(virsh list | grep "$NEW_VM_NAME" | awk '{print $3}')
      info "instance_status = $instance_status"
  done
  info "### VM is started, status is ${instance_status}"

}

info "###Upgrading ceph on SAH###"

run
