#!/bin/bash

# Copyright (c) 2016-2018 Dell EMC or its subsidiaries.
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

# to exit on failure:
# set -e
shopt -s nullglob  # pathname expansion which match no files returns null string

exec > >(tee -a $HOME/update/update-js10.2.0.log)
exec 2>&1

OPENSTACK_POOL_ID="$1"
CEPH_POOL_ID="$2"
SUBSCRIPTION_ID="$3"
SUBSCRIPTION_PW="$4"
STACK_NAME="${5:-overcloud}"
OVERCLOUD_IMG_ROOT_PW="$6"
SUBSCRIPTION_PROXY="$7"
SUBSCRIPTION_PROXY_UN="$8"
SUBSCRIPTION_PROXY_PW="$9"

if [ "$#" -lt 4 ]; then
    echo "Usage: $0 <openstack_pool_id> <ceph_pool_id> <rh_subscription_id> <rh_subscription_pw> [ <stack_name> ] [ <overcloud_img_pw> ] [ <rh_subscription_proxy_url> ] [ <sm_proxy_username> ] [ <sm_proxy_password> ]"
    exit 1
fi

SUBSCRIPTION_JSON="$HOME/pilot/subscription.json"
CONTROLLERS=$(openstack server list  -c Name -c Networks -f value | grep 'control' | awk -F "=" '{ print $2 }')
COMPUTES=$(openstack server list  -c Name -c Networks -f value | grep 'compute' | awk -F "=" '{ print $2 }')
OVERCLOUD=$(openstack server list  -c Name -c Networks -f value | awk -F "=" '{ print $2 }')

DEPLOY_CMD_PATH=$HOME/pilot/overcloud_deploy_cmd.log

# Logging levels
FATAL=0
ERROR=1
WARN=2
INFO=3
DEBUG=4

# Default logging level
LOG_LEVEL=$INFO

# Logging functions
log() { echo -e "$(date '+%F %T'): $@" >&2; }
fatal() { log "FATAL: $@" >&2; exit 1; }
error() { [[ $ERROR -le $LOG_LEVEL ]] && log "ERROR: $@"; }
warn() { [[ $WARN -le $LOG_LEVEL ]] && log "WARN: $@"; }
info() { [[ $INFO -le $LOG_LEVEL ]] && log "INFO: $@"; }
debug() { [[ $DEBUG -le $LOG_LEVEL ]] && log "DEBUG: $@"; }

# Fail fast and exit if original deploy command is not found, required for update.
info "Original deployment log file path: $DEPLOY_CMD_PATH"

if [ ! -e "$DEPLOY_CMD_PATH" ]; then
    fatal "Original deployment command log does not exist, required to run this update!"
fi

# Fail fast if not 3 or more controllers
cntls_arr=($CONTROLLERS)
if [ ${#cntls_arr[@]} -lt 3 ]; then
    fatal "You must have 3 or more controllers to perform update."
fi

mkdir -p ~/update/update-js10.2-lockfiles


# Updating JS 10.1 to latest OSP 10 packages
# Script based on Red Hat documentation see:
# https://access.redhat.com/documentation/en-us/red_hat_openstack_platform/10/html-single/upgrading_red_hat_openstack_platform/#sect-Updating_the_Environment

update_subscription_json() {
    cp ~/pilot/subscription.json subscription.json.orig
    sed -i "s/CHANGEME_openstack_pool_id/$OPENSTACK_POOL_ID/" ~/pilot/subscription.json 
    sed -i "s/CHANGEME_ceph_pool_id/$CEPH_POOL_ID/" ~/pilot/subscription.json 
}

update_director_packages() {
    # on Director node as osp_admin (or whomever the stack owner is): 
    cd ~
    [ -e ~/update/update-js10.2-lockfiles/director-updated.lock ] && return

    # disable version locking
    sudo sed -i 's/enabled = 1/enabled = 0/' /etc/yum/pluginconf.d/versionlock.conf
    sudo systemctl stop 'openstack-*'
    sudo systemctl stop 'neutron-*'
    sudo systemctl stop 'openvswitch'
    # new in OSP 10
    sudo systemctl stop httpd


    # update director packages and restart some services
    sudo yum -y update python-tripleoclient

    info "Begin undercloud upgrade"
    openstack undercloud upgrade
    info "Upgrade undercloud complete."

    sleep 5
    touch ~/update/update-js10.2-lockfiles/director-updated.lock

    # to be sure to incorporate OS updates, we should reboot - next
    # run will not update packages because of lock file
    info "Rebooting director VM to incorporate possible new kernel."
    info "When Director VM comes back up re-run this update script to update the overcloud and complete the minor update."
    read -p "Press any key to continue..."
    sleep 5
    sudo reboot
}

# See: https://access.redhat.com/documentation/en-us/red_hat_openstack_platform/10/html-single/upgrading_red_hat_openstack_platform/#sect-Updating_Overcloud_and_Introspection_Images
update_overcloud_images() {

    [ -e ~/update/update-js10.2-lockfiles/overcloud-images-updated.lock ] && return

    info "Updating and uploading overcloud images"
    source ~/stackrc

    cd ~/pilot/images
    for i in /usr/share/rhosp-director-images/overcloud-full-latest-10.0.tar /usr/share/rhosp-director-images/ironic-python-agent-latest-10.0.tar; do tar -xvf $i; done

    info "Customizing the overcloud image & uploading images"

    ~/pilot/customize_image.sh "$SUBSCRIPTION_ID" "$SUBSCRIPTION_PW" "$CEPH_POOL_ID" "$SUBSCRIPTION_PROXY"

    if [ -n "${OVERCLOUD_IMG_ROOT_PW}" ]; then
      info "# Setting overcloud image root password"
      virt-customize -a overcloud-full.qcow2 --root-password password:$OVERCLOUD_IMG_ROOT_PW
    fi

    openstack overcloud image upload --update-existing --image-path ~/pilot/images/
    openstack baremetal configure boot
    # Verify the timestamps of the new images:
    for IMAGE in `openstack image list | tail -n+3 | awk -F "|" '{ print $2 }'` ; do openstack image show $IMAGE | grep "updated_at" ; done
    ls -l /httpboot

    touch ~/update/update-js10.2-lockfiles/overcloud-images-updated.lock
}

# Update the Overcloud Subscriptions
subscribe_overcloud() {
    # subscribe the overcloud nodes
    [ -e ~/update/update-js10.2-lockfiles/overcloud-registered.lock ] && return
    info "Registering overcloud nodes with Red Hat Subscription Manger"
    cd ~/pilot

    CMD="~/pilot/register_overcloud.py -u ${SUBSCRIPTION_ID} -p ${SUBSCRIPTION_PW}"
    # If there is a sm proxy add args
    if [[ -n "$SUBSCRIPTION_PROXY" && -n "$SUBSCRIPTION_PROXY_UN" && -n "$SUBSCRIPTION_PROXY_PW" ]]; then
      CMD+=" -l ${SUBSCRIPTION_PROXY} -n ${SUBSCRIPTION_PROXY_UN} -s ${SUBSCRIPTION_PROXY_PW}"
    fi
    info "SM - register overcloud command is: ${CMD}"
    if ! eval ${CMD} ; then
      fatal "Could not successfully register overcloud - please fix issue and re-run update script"
    fi
    touch ~/update/update-js10.2-lockfiles/overcloud-registered.lock
}

# Update templates in pilot with ones laid down from "openstack undercloud upgrade", and apply any patches, if required.
update_heat_templates() {
    [ -e ~/update/update-js10.2-lockfiles/heat_templates_updated.lock ] && return
    cd ~/pilot

    # Patch the Heat templates
    info "Updating Heat templates on Director node"

    rm -rf ~/pilot/templates/overcloud

    # copy upgraded templates into template dir
    cp -r /usr/share/openstack-tripleo-heat-templates ~/pilot/templates/overcloud

    # If we are using old style osd definitions in ceph.yaml instead of putting them
    # in dell-environment, copy them to correct spot.
    if [ -e ~/pilot/templates/overrides/puppet/hieradata/ceph.yaml ]; then
      cp ~/pilot/templates/overrides/puppet/hieradata/ceph.yaml ~/pilot/templates/overcloud/puppet/hieradata
    fi

    touch ~/update/update-js10.2-lockfiles/heat_templates_updated.lock
}

# https://access.redhat.com/documentation/en-us/red_hat_openstack_platform/10/html-single/upgrading_red_hat_openstack_platform/#sect-Updating_the_Overcloud
update_overcloud() {
    [ -e ~/update/update-js10.2-lockfiles/overcloud-updated.lock ] && return
    info "Updating overcloud"
    cd ~
    source ~/stackrc
    C=($CONTROLLERS)

    # capture stonith state:
    STONITH_ENABLED=$(ssh heat-admin@${C} "sudo pcs property show stonith-enabled" | grep "stonith-enabled: true")
    info "Stonith Enabled?:  $STONITH_ENABLED"
    
    # Adjust resource timeouts for: https://bugzilla.redhat.com/show_bug.cgi?id=1383780
    # Note: default is still 200s in OSP 10, bz above has not seen any action so we 
    # still need to apply workaround.
    ssh heat-admin@${C} 'sudo pcs resource update rabbitmq op add stop timeout=300s'

    # workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1455224
    for N in $OVERCLOUD
    do
      ssh heat-admin@${N} "sudo yum update -y nss* nspr; sudo rm -rf /var/lib/heat-config/heat-config-script/OVS_UPGRADE"
    done
    echo Done updating nss* and nspr on all overcloud nodes

    # Parse out -e arguments from existing logged deployment command
    envs=()
    while read -r line || [[ -n "$line" ]]; do
      if [[ $line == -e* ]]; then
        envs+=(${line::-2})
      fi
    done < "$DEPLOY_CMD_PATH"
    info "Environement variable files: ${envs[@]}"
    
    # Build openstack overcloud update commands
    # The OSP 10 minor update of overcloud is broken into two commands
    # "openstack overcloud deploy ..." with the --update-plan-only switch. 
    # Then "openstack overcloud update stack ..." is called.

    # Addition in 10.2.0: "openstack overcloud deploy" now requires --stack attribute or it will default to "overcloud"
    # Replace all "~" with value of $HOME when building command otherwise ~ will not be evaluated correctly.
    info "Update overcloud plan next, additional -e args that will be applied: ${envs[@]//\~/$HOME}"
    openstack overcloud deploy --debug --update-plan-only --stack $STACK_NAME --templates ~/pilot/templates/overcloud -e ~/pilot/templates/overcloud/overcloud-resource-registry-puppet.yaml ${envs[@]//\~/$HOME}

    info "Now do the full overcloud update..."
    yes ""|openstack overcloud update stack --debug $STACK_NAME -i  

    # if fencing was enabled, we'll ensure it is still enabled:
    [ "$STONITH_ENABLED" ] && ssh heat-admin@${C} "sudo pcs property set stonith-enabled=true"

    # If heat failed updating the overcloud stack fail without creating lock file.
    if $(openstack stack list | grep $STACK_NAME | grep -q UPDATE_FAILED); then
      fatal "Overcloud stack: $STACK_NAME, update failed.  Please check status of the overcloud nodes and pcs status and fix any issues you find, then re-run update script."
    fi

    touch ~/update/update-js10.2-lockfiles/overcloud-updated.lock
}

# main 
update_subscription_json
update_director_packages
update_overcloud_images
subscribe_overcloud
update_heat_templates
update_overcloud

info "Update completed, please reboot the overcloud nodes to ensure that new kernel version is running."
