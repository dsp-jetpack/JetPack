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

# NOTES: 

# to exit on failure:
#set -e
shopt -s nullglob  # pathname expansion which match no files returns null string

exec > >(tee -a $HOME/update_upgrade/update-js10.0.1.log)
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

# TODO if this file cannot be found we need to fail fast and tell user they need to build one up. 
# TODO put sample command in guide incase this file does not exist
DEPLOY_CMD_PATH=~/pilot/overcloud_deploy_cmd.log 

# Fail fast if not 3 or more controllers
cntls_arr=($CONTROLLERS)
if [ ${#cntls_arr[@]} -lt 3 ]; then
    echo "You must have 3 or more controllers to perform update."
    exit 1
fi

mkdir -p ~/update_upgrade/update-js10-lockfiles

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


# Updating JS-6x to latest OSP10 packages

# https://access.redhat.com/documentation/en-us/red_hat_openstack_platform/10/html-single/upgrading_red_hat_openstack_platform/#sect-Update_Process

update_subscription_json() {
    cp ~/pilot/subscription.json subscription.json.orig
    sed -i "s/CHANGEME_openstack_pool_id/$OPENSTACK_POOL_ID/" ~/pilot/subscription.json 
    sed -i "s/CHANGEME_ceph_pool_id/$CEPH_POOL_ID/" ~/pilot/subscription.json 
}


patch_network_environment_yaml() {
    grep -q "NovaColdMigrationNetwork: internal_api" ~/pilot/templates/network-environment.yaml && return  # already patched

    sed -i.bak 's/^  ServiceNetMap:/  ServiceNetMap:\
    NovaColdMigrationNetwork: internal_api\
    NovaLibvirtNetwork: internal_api/' ~/pilot/templates/network-environment.yaml
}


upgrade_undercloud() {
    info "upgrade_undercloud begin."
    openstack undercloud upgrade
    info "upgrade_undercloud complete."
}

update_director_packages() {
    # on Director node as osp_admin (or whomever the stack owner is): 
    cd ~
    [ -e ~/update_upgrade/update-js10-lockfiles/director-updated.lock ] && return

    # disable version locking (JS-6.0-specific)
    # versionlock.conf set enabled=0 to disable
    sudo sed -i 's/enabled = 1/enabled = 0/' /etc/yum/pluginconf.d/versionlock.conf
    sudo systemctl stop 'openstack-*'
    sudo systemctl stop 'neutron-*'
    sudo systemctl stop 'openvswitch'
	# new in OSP 10
	sudo systemctl stop httpd


    # update director packages and restart some services
    sudo yum -y update python-tripleoclient

    upgrade_undercloud

    sleep 5
    touch ~/update_upgrade/update-js10-lockfiles/director-updated.lock

    # to be sure to incorporate OS updates, we should reboot - next
    # run will not update packages because of lock file
    echo "Rebooting director VM to incorporate possible new kernel. "
    read -p "Press any key to continue..."
    sleep 5
    sudo reboot
}

# See: https://access.redhat.com/documentation/en-us/red_hat_openstack_platform/10/html-single/upgrading_red_hat_openstack_platform/#sect-Updating_Overcloud_and_Introspection_Images
update_overcloud_images() {

    [ -e ~/update_upgrade/update-js10-lockfiles/overcloud-images-updated.lock ] && return

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

    touch ~/update_upgrade/update-js10-lockfiles/overcloud-images-updated.lock
}

# Update the Overcloud Subscriptions
subscribe_overcloud() {
    # subscribe the overcloud nodes
    [ -e ~/update_upgrade/update-js10-lockfiles/overcloud-registered.lock ] && return
    info "Registering overcloud nodes with Red Hat Subscription Manger"
    cd ~/pilot
	
	CMD="~/pilot/register_overcloud.py -u ${SUBSCRIPTION_ID} -p ${SUBSCRIPTION_PW}"
    # If there is a sm proxy add args
    if [[ -n "$SUBSCRIPTION_PROXY" && -n "$SUBSCRIPTION_PROXY_UN" && -n "$SUBSCRIPTION_PROXY_PW" ]]; then
      CMD+=" -l ${SUBSCRIPTION_PROXY} -n ${SUBSCRIPTION_PROXY_UN} -s ${SUBSCRIPTION_PROXY_PW}"
    fi
	info "Command is: ${CMD}"
    if ! eval ${CMD} ; then
      fatal "Could not successfully register overcloud - please fix issue and re-run update script"
    fi
    touch ~/update_upgrade/update-js10-lockfiles/overcloud-registered.lock
}

# Update templates in pilot with ones from "openstack undercloud upgrade", and make any needed patches
prepare_overcloud() {
    [ -e ~/update_upgrade/update-js10-lockfiles/overcloud-prepared.lock ] && return
    cd ~/pilot

    # Patch the Heat templates
    info "Patching Heat templates for Director node"

    rm -rf ~/pilot/templates/overcloud

    # copy upgraded templates into template dir
    cp -r /usr/share/openstack-tripleo-heat-templates ~/pilot/templates/overcloud
    # TODO we still need this in 10.0.1 update? dpaterson: I left this in for first update osp 10 pass
	# and update was successful, still not sure we need this call or not anymore.
    patch_network_environment_yaml

    # If we are using old style osd definitions in ceph.yaml instead of putting them
    # in dell-environment, copy them to correct spot.
	if [ -e ~/pilot/templates/overrides/puppet/hieradata/ceph.yaml ]; then
      cp ~/pilot/templates/overrides/puppet/hieradata/ceph.yaml ~/pilot/templates/overcloud/puppet/hieradata
    fi
	
	# TODO: Why are we doing this at all?  Remove for 10.0.1? dpaterson: I searched JetPack repo and the only
	# place tripleo-overcloud-passwords is referenced is here.
	if [ -e ~/tripleo-overcloud-passwords ]; then
	  if ! grep "MYSQL_CLUSTERCHECK_PASSWORD" ~/tripleo-overcloud-passwords; then 
        echo "MYSQL_CLUSTERCHECK_PASSWORD=u3DFKs4TEdbRDjb6eRzVpc4B9" >> ~/tripleo-overcloud-passwords
      fi
	fi
    touch ~/update_upgrade/update-js10-lockfiles/overcloud-prepared.lock
}


update_overcloud() {
    [ -e ~/update_upgrade/update-js10-lockfiles/overcloud-updated.lock ] && return
    info "Updating overcloud"
    cd ~
    source ~/stackrc
    C=($CONTROLLERS)

    # capture stonith state:
    STONITH_ENABLED=$(ssh heat-admin@${C} "sudo pcs property show stonith-enabled" | grep "stonith-enabled: true")
    info "STONITH_ENABLED:  $STONITH_ENABLED"
    
    # adjust resource timeouts for:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1383780
    ssh heat-admin@${C} 'sudo pcs resource update rabbitmq op add stop timeout=300s'


    # workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1455224. 
    # This BZ may get broken into two BZs as the two calls are really two seperate issues.
	# TODO: could be unndeeded in 10.0.1.
	# dpaterson- tried first pass at update with workaround still in place and update worked fine.
	# Don't think it is hurting anything so leaving it for now.
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
    
    # Build openstaack overcloud update stack command 
    # Note we replace all "~" with value of $HOME or environment files 
	# the change in osp 10 update is updateing overcloud is broken into two commands
	# "openstack overcloud deploy ..." with the --update-plan-only switch then: 
	# "openstack overcloud update stack ..." is called
	
	info "Update overcloud plan next.."
	openstack overcloud deploy --debug --update-plan-only --templates ~/pilot/templates/overcloud -e ~/pilot/templates/overcloud/overcloud-resource-registry-puppet.yaml ${envs[@]//\~/$HOME}

    info "Now do the full overcloud update..."
    yes ""|openstack overcloud update stack --debug $STACK_NAME -i  
	
    # if fencing was enabled, we'll ensure it is still enabled:
    [ "$STONITH_ENABLED" ] && ssh heat-admin@${C} "sudo pcs property set stonith-enabled=true"

    # If heat failed updating the overcloud stack fail without creating lock file.
    if $(openstack stack list | grep $STACK_NAME | grep -q UPDATE_FAILED); then
      fatal "Overcloud stack: $STACK_NAME, update failed.  Please check status of the overcloud nodes and pcs status and fix any issues you find, then re-run update script."
    fi

    touch ~/update_upgrade/update-js10-lockfiles/overcloud-updated.lock
}

# TODO: we still need this in osp 10?
patch_ha_proxy() {
    # do unconditionally - files might have been overwritten by update
    # step 11 from Overcloud Minor Update in wiki:

    for C in $CONTROLLERS
    do
        ssh heat-admin@${C} 'sudo sed -i "s|:8080\ check|:7480\ check|" /etc/haproxy/haproxy.cfg'
    done

    for N in $OVERCLOUD
    do
        ssh heat-admin@${N} "sudo sed -i \"s|ports             => '8080'|ports             => '7480'|\" /usr/share/openstack-puppet/modules/tripleo/manifests/loadbalancer.pp"
    done

    # on controller: (may need a --force)
    C=($CONTROLLERS) # select first controller
    ssh heat-admin@${C} sudo pcs resource cleanup --all --force    
    info "Updated HA proxy settings"
}

# main 

update_subscription_json
update_director_packages
update_overcloud_images
subscribe_overcloud
prepare_overcloud
update_overcloud
# Do we still need to do this in OSP 10?
# dpaterson - don't think so and first upadate test went fine without it.
# patch_ha_proxy

info "Update completed, please reboot the overcloud nodes to ensure that new kernel version is running"
