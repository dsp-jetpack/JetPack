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
# need cluster reboot function?
# TODO: patch clock skew info: https://blog.headup.ws/node/36 into ceph health
#       integrate ceph 1.3-2.0 upgrade

# to exit on failure:
#set -e
shopt -s nullglob  # pathname expansion which match no files returns null string

exec > >(tee -a $HOME/pilot/upgrade-js6.0.1.log)
exec 2>&1

CONTROL_SCALE="$1"
COMPUTE_SCALE="$2"
CEPH_SCALE="$3"
VLAN_RANGE="$4"
SUBSCRIPTION_MGR_USER="$5"
SUBSCRIPTION_MGR_PASSWORD="$6"
OPENSTACK_POOL_ID="$7"
CEPH_POOL_ID="$8"

if [ "$#" -lt 8 ]; then
    echo "Usage: $0 <control_scale> <compute_scale> <ceph_scale> <vlan_range> \
<subscription_mgr_user> <subscription_mgr_password> <ceph_pool_id> <openstack_pool_id> <ceph_pool_id"
    exit 1         
fi

source ~/stackrc

DEPLOY_CMD_PATH=~/pilot/overcloud_deploy_cmd.log
SUBSCRIPTION_JSON="$HOME/pilot/subscription.json"
CONTROLLERS=$(openstack server list  -c Name -c Networks -f value | grep 'control' | awk -F "=" '{ print $2 }')
CONTROLLER=($CONTROLLERS)
COMPUTES=$(openstack server list  -c Name -c Networks -f value | grep 'compute' | awk -F "=" '{ print $2 }')
STORAGE=$(openstack server list  -c Name -c Networks -f value | grep 'compute' | awk -F "=" '{ print $2 }')
OVERCLOUD=$(openstack server list  -c Name -c Networks -f value | awk -F "=" '{ print $2 }')
STACKNAME=$(openstack stack list -f value -c "Stack Name")
GUIDANCE="- please fix issue and re-run upgrade-script"

mkdir -p ~/pilot/upgrade-lockfiles

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

info "Log file is: $HOME/pilot/upgrade-js6.0.log"

# Generally following Chapter 3 of the Red Hat Openstack Platform 10
# document:
# https://access.redhat.com/documentation/en/red-hat-openstack-platform/10/paged/upgrading-red-hat-openstack-platform/chapter-3-director-based-environments-performing-upgrades-to-major-versions

# 3.1. IMPORTANT PRE-UPGRADE NOTES
# update the customized yamls in the ~pilot/templates directory by comparing with JS-10.0 versions.


deploy_subscription_json() {
    # deploy this file fresh every time so one can change pool_id's if need be
    completed subscription_json_deployed && return
    info "updating subscription.json with needed repositories"
    cd ~/pilot
    cp "${SUBSCRIPTION_JSON}" "${SUBSCRIPTION_JSON}.bak"
    cat >"${SUBSCRIPTION_JSON}" <<EOF
{
    "cdn_credentials": {
        "cdn_username": "CHANGEME_username",
        "cdn_password": "CHANGEME_password"
    },
    "_comment": [ "If using a proxy, remove the leading underscore from",
                  "_proxy_credentials below and fill in the following proxy",
                  "information." ],
    "_proxy_credentials": {
        "proxy_url": "CHANGEME_hostname:CHANGEME_port",
        "proxy_username": "CHANGEME_username",
        "proxy_password": "CHANGEME_password"
    },
    "roles": {
        "control": {
            "pool_ids": [ "$OPENSTACK_POOL_ID",
                          "$CEPH_POOL_ID"  ],
            "repos": [ "rhel-7-server-rpms",
                       "rhel-7-server-extras-rpms",
                       "rhel-7-server-rh-common-rpms",
                       "rhel-ha-for-rhel-7-server-rpms",
                       "rhel-7-server-openstack-10-rpms",
                       "rhel-7-server-openstack-10-devtools-rpms",
                       "rhel-7-server-rhceph-2-mon-rpms",
                       "rhel-7-server-rhceph-2-osd-rpms",
                       "rhel-7-server-rhceph-2-tools-rpms" ]
        },
        "compute": {
            "pool_ids": [ "$OPENSTACK_POOL_ID",
                          "$CEPH_POOL_ID"  ],
            "repos": [ "rhel-7-server-rpms",
                       "rhel-7-server-extras-rpms",
                       "rhel-7-server-rh-common-rpms",
                       "rhel-ha-for-rhel-7-server-rpms",
                       "rhel-7-server-openstack-10-rpms",
                       "rhel-7-server-openstack-10-devtools-rpms",
                       "rhel-7-server-rhceph-2-mon-rpms",
                       "rhel-7-server-rhceph-2-osd-rpms",
                       "rhel-7-server-rhceph-2-tools-rpms" ]
        },
        "ceph-storage": {
            "pool_ids": [ "$OPENSTACK_POOL_ID",
                          "$CEPH_POOL_ID" ],
            "repos": [ "rhel-7-server-rpms",
                       "rhel-7-server-extras-rpms",
                       "rhel-7-server-rh-common-rpms",
                       "rhel-ha-for-rhel-7-server-rpms",
                       "rhel-7-server-openstack-10-rpms",
                       "rhel-7-server-openstack-10-devtools-rpms",
                       "rhel-7-server-rhceph-2-mon-rpms",
                       "rhel-7-server-rhceph-2-osd-rpms",
                       "rhel-7-server-rhceph-2-tools-rpms",
                       "rhel-7-server-rhscon-2-agent-rpms" ]
        }
    }
}
EOF
    status=$?
    [ ${status} -eq 0 ] || fatal "Could not find or update subscription.json"
    set_completed subscription_json_deployed
}


patch_stack_rc_format() {
    # convert assignments to exports with assignments
    perl -pi -e "s/^([^\s]+=.*)/export \1/g" ~/stackrc
    # remove exports without assignments
    perl -pi -e "s/^export [^=]+$//g" ~/stackrc
}


subscribe_overcloud() {
    # subscribe the overcloud nodes
    completed overcloud-registered && return
    info "Registering overcloud nodes with Red Hat Subscription Manger"
    patch_stack_rc_format
    cd ~/pilot
    # The updated subscription.json should have been deployed already
    if ! ~/pilot/register_overcloud.py -u ${SUBSCRIPTION_MGR_USER} -p ${SUBSCRIPTION_MGR_PASSWORD} ; then
        fatal "Could not successfully register overcloud - please fix issue and re-run update script"
    fi
    set_completed overcloud-registered
}


patch_stack_rc_format() {
    # convert assignments to exports with assignments
    perl -pi -e "s/^([^\s]+=.*)/export \1/g" ~/stackrc
    # remove exports without assignments	
    perl -pi -e "s/^export [^=]+$//g" ~/stackrc
}


patch_ceph_conf_for_health() {
    info "Checking Ceph heath"
    local health=$(ssh heat-admin@$CONTROLLER 'sudo ceph health')
    [[ $health == "HEALTH_OK" ]] && return

    local regexp='too many PGs'
    if [[ $health =~ $regexp ]] ;
    then
        info "Suppressing Ceph PG to OSG ratio warning"
        for C in $CONTROLLERS
        do
            [[ $(ssh heat-admin@${C} 'grep mon_pg_warn_max_per_osd /etc/ceph/ceph.conf') ]] || ssh heat-admin@${C} 'sudo sed -i "s|\[global\]|\[global\]\nmon_pg_warn_max_per_osd = 0|" /etc/ceph/ceph.conf'
        done
    fi
    
    regexp='skew'
    if [[ $health =~ $regexp ]] ;
    then
        fatal "Ceph monitor clock skew detected, please sync controller nodes and rerun script"
    fi
    
    # restart Ceph mon services
    for C in $CONTROLLERS 
    do    
        local service=$(ssh heat-admin@${C} 'sudo systemctl | grep ceph-mon\..*\.service')
        regexp='(ceph-mon\.[a-z0-9-]+\.[0-9]+\.[0-9]+)\.service'
        local host=$(ssh heat-admin@${C} hostname)
        if [[ $service =~ $regexp ]] && \
            ssh heat-admin@${C} sudo systemctl restart ${BASH_REMATCH[1]} ;
        then
            echo "restarting ceph-mon service ${BASH_REMATCH[1]} on ${host} ($C)"
        else
            ccho "failed to find or restart ceph-mon service ${BASH_REMATCH[1]} on ${host} ($C)"
        fi
    done
}


patch_post_deploy_yaml() {
    grep -q "radosgw.gateway" ~/pilot/templates/post-deploy.yaml && return  # already patched

    perl -i -pe "undef $/; s/echo \"Restarting RGW...\".*\} \>\>/echo \"Restarting RGW...\"\n\
          chkconfig --add ceph-radosgw
          sudo pkill radosgw
          sudo systemctl restart ceph-radosgw\@radosgw.gateway
        \} \>\>/ms"  ~/pilot/templates/post-deploy.yaml
}


completed() {
    [ -e ~/pilot/upgrade-lockfiles/${1}.lock ]
}


set_completed() {
    info "Stage $1 completed"
    touch ~/pilot/upgrade-lockfiles/${1}.lock
}


# 3.2 Upgrading the Director
# On director node as OSP admin (user stack or osp_admin, whomever):

prepare_upgrade() {
    completed upgrade-prepared && return
    # versionlock.conf set enabled=0 to disable
    sudo sed -i 's/enabled = 1/enabled = 0/' /etc/yum/pluginconf.d/versionlock.conf

    sudo subscription-manager repos --disable=rhel-7-server-openstack-9-rpms --disable=rhel-7-server-openstack-9-director-rpms || fatal "Could not disable current openstack-8 repos $GUIDANCE"
    sudo subscription-manager repos --enable=rhel-7-server-openstack-10-rpms || fatal "Could not enable repos $GUIDANCE"

    # **** Don't need anymore, it causes that package hang problem with nova
    #sudo yum -y upgrade || fatal "Yum upgrade of director failed $GUIDANCE"
    set_completed upgrade-prepared
#    info "rebooting to ensure latest kernel version running - please re-run this script after.."
#    sleep 5
#    sudo reboot
}


upgrade_undercloud() {
    completed undercloud-upgraded && return
    
    sudo systemctl stop 'openstack-*'
    sudo systemctl stop 'neutron-*'
    yum update python-tripleoclient  # possible already done?
    openstack undercloud upgrade || fatal "Undercloud upgrade failed $GUIDANCE"

    # copy the updated heat templates to ~/pilot/tempates/overcloud
    mv ~/pilot/templates/overcloud ~/overcloud.bak
    cp -r /usr/share/openstack-tripleo-heat-templates ~/pilot/templates/overcloud
    # copy and patch various files
    # cp ~/pilot/templates/overrides/puppet/hieradata/ceph.yaml ~/pilot/templates/overcloud/puppet/hieradata/ceph.yaml
    patch_ceph_conf_for_health
    patch_post_deploy_yaml

    # informational..
    diff -Nary /usr/share/openstack-heat-templates/ /home/pilot/templates/overcloud >upgrade-template-diff.txt

    set_completed undercloud-upgraded
    info "rebooting to ensure latest software is running - please re-run this script after.."
    sleep 5
    sudo reboot
}


check_undercloud_upgrade() {
    completed undercloud-upgrade-checked && return
    # check output programatically somehow
    sleep 60 # wait for service restrat
    local counter=0
    until sudo systemctl list-units "openvswitch*" | grep "openvswitch.service" ; do 
	sleep 30
	let counter=counter+1  # 5 minutes
	[[ $counter -lt 10 ]] || fatal "openvswitch service did not start $GUIDANCE" 
    done
    counter=0
    until sudo systemctl list-units "neutron*" | grep "neutron-server.service" ; do 
	sleep 30
	let counter=counter+1  # 5 minutes
	[[ $counter -lt 10 ]] || fatal "neutron-server service did not start $GUIDANCE" 
    done
    counter=0
    until sudo systemctl list-units "openstack*" | grep "openstack-nova-compute.service" ; do 
	sleep 30
	let counter=counter+1  # 10 minutes
	[[ $counter -lt 20 ]] || fatal "openstack-nova-compute service did not start $GUIDANCE" 
    done
     
    source ~/stackrc
    openstack server list
    openstack baremetal list
    openstack stack list
    set_completed undercloud-upgrade-checked
}


# 3.3 Upgrading the overcloud images on director

######### Let's call the JS-10.0.1 version of the customize_image.sh!!!

upgrade_overcloud_images() {
    completed overcloud-images-upgraded && return
    rm -rf ~/pilot/images/*
    ln -sf /usr/share/rhosp-director-images/overcloud-full-latest-10.0.tar ~/pilot/images/overcloud-full.tar
    ln -sf /usr/share/rhosp-director-images/ironic-python-agent-latest-10.0.tar ~/pilot/images/ironic-python-agent.tar
    
    cd ~/pilot/images
    for i in ~/pilot/images/overcloud-full.tar ~/pilot/images/ironic-python-agent.tar; do tar -xvf $i; done
    
    # customize the images and upload them
    ~/customize_image.sh $SUBSCRIPTION_MGR_USER $SUBSCRIPTION_MGR_PASSWORD $CEPH_POOL_ID || fatal "overcloud images were not successfully customized $GUIDANCE"
    # you should see messages that the images have been uploaded

    cd ~
    openstack baremetal configure boot
    openstack image list
    ls -l /httpboot
    set_completed overcloud-images-upgraded
}


# 3.4. UPGRADING THE OVERCLOUD

check_overcloud_status () {
    # in case the update/upgrade is still in progress after command returns
    # these will time out eventually
    sleep 60 # breathe
    info "Waiting for stack resouces to complete..."
    local counter=0
    until ! openstack stack resource list $STACKNAME | grep PROGRESS ; do 
	sleep 30
	let counter=counter+1  # 30 minutes
	[[ $counter -lt 60 ]] || break
    done
    info "Waiting for software deployments to complete..."
    counter=0
    until ! openstack software deployment list | grep PROGRESS ; do 
	sleep 30
	let counter=counter+1  # 30 min
	[[ $counter -lt 60 ]] || break
    done
    info "Checking stack status and pcs status for failures or stuck progress"
    # fail if any of these conditions are true..
    ! (openstack stack list | grep FAIL || \
	openstack  stack resource list $STACKNAME | egrep "(FAIL|PROGRESS)" || \
	openstack software deployment list | egrep "(FAIL|PROGRESS)" || \
	ssh heat-admin@$CONTROLLER "sudo pcs status" | grep Stop)
    local status=$?
    [[ $status -eq 0 ]] || show_overcloud_status 
    return $status
}


show_overcloud_status() {
    info "Stack status:\n $(openstack stack list)"
    info "Stack resource status:\n $(openstack  stack resource list $STACKNAME | egrep '(FAIL|PROGRESS)')"
    info "Stack software deployment status:\n $(openstack software deployment list | egrep '(FAIL|PROGRESS)')"
    info "Stack PCS status:\n $(ssh heat-admin@$CONTROLLER "sudo pcs status" | grep -B 2 Stop)"
}


overcloud_deploy_test() {
    check_overcloud_status
}

deploy_stage_test() {
    overcloud_deploy_test || fatal "overcloud status failed! $?"
    local status=$?
    info "***overcloud_deploy_test succeeded!  status: $status"
}

overcloud_deploy() {
    # i think we only need scale args and the vlan-range (3,3,3,201:220)
    local env_arg="$1"
    # workaround for bug https://bugzilla.redhat.com/show_bug.cgi?id=1385190
    # and others unknown
    local force="$2"

    # Parse out -e arguments from existing logged deployment command
    envs=()
    while read -r line || [[ -n "$line" ]]; do
      if [[ $line == -e* ]]; then
        envs+=(${line::-2})
      fi
    done < "$DEPLOY_CMD_PATH"
    info "Environement variable files: ${envs[@]}"

    local cinder_env=''
    # include dell-cinder-backends only if configured 
    egrep -q "cinder_user_enabled_backends: \[\s*\]" ~/pilot/templates/dell-cinder-backends.yaml || cinder_env="-e ~/pilot/templates/dell-cinder-backends.yaml"
    info "Force: $force"
    info "Including $env_arg"
    echo    "openstack overcloud deploy --stack \"$STACKNAME\" \
-t 180 \
$force \
--templates ~/pilot/templates/overcloud \
${envs[@]//\~/$HOME} \
-e $env_arg \
--control-flavor control \
--compute-flavor compute \
--ceph-storage-flavor ceph-storage \
--swift-storage-flavor swift-storage \
--block-storage-flavor block-storage \
--neutron-public-interface bond1 \
--neutron-network-type vlan \
--neutron-disable-tunneling \
--control-scale $CONTROL_SCALE \
--compute-scale $COMPUTE_SCALE \
--ceph-storage-scale $CEPH_SCALE \
--ntp-server 0.centos.pool.ntp.org \
--neutron-network-vlan-ranges physint:${VLAN_RANGE},physext \
--neutron-bridge-mappings physint:br-tenant,physext:br-ex"

    # We are not trusting return status of overcloud deploy - we will 
    # check overcloud status be heat and pcs status
    openstack overcloud deploy --stack "$STACKNAME" \
-t 180 \
$force \
--templates ~/pilot/templates/overcloud \
${envs[@]//\~/$HOME} \
-e $env_arg \
--control-flavor control \
--compute-flavor compute \
--ceph-storage-flavor ceph-storage \
--swift-storage-flavor swift-storage \
--block-storage-flavor block-storage \
--neutron-public-interface bond1 \
--neutron-network-type vlan \
--neutron-disable-tunneling \
--control-scale $CONTROL_SCALE \
--compute-scale $COMPUTE_SCALE \
--ceph-storage-scale $CEPH_SCALE \
--ntp-server 0.centos.pool.ntp.org \
--neutron-network-vlan-ranges physint:${VLAN_RANGE},physext \
--neutron-bridge-mappings physint:br-tenant,physext:br-ex

    check_overcloud_status
}


upgrade_telemetry() {
    completed telemetry_upgraded && return

    overcloud_deploy ~/pilot/templates/overcloud/environments/major-upgrade-ceilometer-wsgi-mitaka-newton.yaml || fatal "telemetry upgrade failed $GUIDANCE"
    # sanity test runs at this point
    set_completed telemetry_upgraded
}


patch_ha_proxy() {
    # do unconditionally - files might have been overwritten by previous
    # actions

    for C in $CONTROLLERS
    do
	ssh heat-admin@${C} 'sudo sed -i "s|:8080\ check|:7480\ check|" /etc/haproxy/haproxy.cfg'
    done

    for N in $OVERCLOUD
    do
	ssh heat-admin@${N} "sudo sed -i \"s|ports             => '8080'|ports             => '7480'|\" /usr/share/openstack-puppet/modules/tripleo/manifests/loadbalancer.pp"
    done

    ssh heat-admin@${CONTROLLER} sudo pcs resource cleanup --all --force    
    sleep 60 # give the cleanup some time
    info "Updated HA proxy settings"
}


create_nova_keys() {
    # TODO - not integrated yet, if at all - from RH docs
    completed nova_keys_created && return
    source ~/${STACKNAME}rc  # addressing the overcloud
    ssh-keygen -f ~/nova_rsa -t rsa -N ''
    ALLCOMPUTES=$(openstack server list --name ".*compute.*" \
	-c Networks -f csv --quote none | \
	tail -n+2 | awk -F '=' '{ print $2 }')
    for COMPUTE in $ALLCOMPUTES
    do
	ssh heat-admin@$COMPUTE "sudo usermod -s /bin/bash nova"
	ssh heat-admin@$COMPUTE "sudo mkdir -p /var/lib/nova/.ssh"
	scp nova* heat-admin@$COMPUTE:~/
	ssh heat-admin@$COMPUTE "sudo cp ~/nova_rsa /var/lib/nova/.ssh/id_rsa"
	ssh heat-admin@$COMPUTE "sudo cp ~/nova_rsa.pub /var/lib/nova/.ssh/id_rsa.pub"
	ssh heat-admin@$COMPUTE "sudo rm ~/nova_rsa*"
	ssh heat-admin@$COMPUTE "echo 'StrictHostKeyChecking no'|sudo tee -a /var/lib/nova/.ssh/config"
	ssh heat-admin@$COMPUTE "sudo cat /var/lib/nova/.ssh/id_rsa.pub|sudo tee -a /var/lib/nova/.ssh/authorized_keys"
	ssh heat-admin@$COMPUTE "sudo chown -R nova: /var/lib/nova/.ssh"
	ssh heat-admin@$COMPUTE "sudo su -c 'chmod 600 /var/lib/nova/.ssh/*' nova"
	ssh heat-admin@$COMPUTE "sudo chmod 700 /var/lib/nova/.ssh"
    done
    
    rm ~/nova_rsa*
    source ~/stackrc
    set_completed nova_keys_created
}


upgrade_scripts() {
    completed scripts_upgraded && return
    overcloud_deploy ~/pilot/templates/overcloud/environments/major-upgrade-pacemaker-init.yaml  || fatal "Scripts upgrade failed $GUIDANCE"
    # *** sanity test should run at this point
    set_completed scripts_upgraded
}


upgrade_controllers() {
    completed controllers_upgraded && return
    # **** insert in controller ceph.comf?  mon_pg_warn_max_per_osd = 0
    # check again
    local health=$(ssh heat-admin@$CONTROLLER 'sudo ceph health')
    [[ $health != "HEALTH_OK" ]] && fatal "Ceph health check failed: $health - should be HEALTH_OK - $GUIDANCE"

    # create 'metrics' ceph pool that gnocchi needs for upgrade if needed
    [[ $(ssh heat-admin@$CONTROLLER 'sudo ceph osd lspools' | grep metrics) ]] || ssh heat-admin@$CONTROLLER 'sudo ceph osd pool create metrics 128'

    overcloud_deploy ~/pilot/templates/overcloud/environments/major-upgrade-pacemaker.yaml  || fatal "Controllers upgrade failed $GUIDANCE"
    # if failure do sudo pcs cluster start and re-run.
    # *** verify services are back
    # pcs resource cleanup if not
    # *** sanity test will fail? Unclear (neutron server disabled during this step)
    set_completed controllers_upgraded
}


upgrade_remove_sahara() {
    # optional operation, not called by default
    completed sahara_removed && return
    overcloud_deploy ~/pilot/templates/overcloud/environments/major-upgrade-remove-sahara.yaml  || fatal "Remove sahara failed $GUIDANCE"
    set_completed sahara_removed
}


upgrade_computes() {
    completed computes_upgraded && return

    for NODE_UUID in `nova list | grep ACTIVE | grep compute | awk -F '|' '{ print $2 }'`
    do
	upgrade-non-controller.sh --upgrade $NODE_UUID || fatal "Compute upgrade failed $GUIDANCE"
	# *** wait for node to come up  ??
    done
    # *** validate that all nodes are up
    check_overcloud_status || fatal "Compute upgrade failed $GUIDANCE"
    # *** sudo systemctl restart neutron-openvswitch-agent?
    for C in $COMPUTES
    do
        ssh heat-admin@${C} 'sudo systemctl restart neutron-openvswitch-agent'
    done

    set_completed computes_upgraded
}


upgrade_storage() {
    completed storage_upgraded && return

    for NODE_UUID in `nova list | grep ACTIVE | grep ceph | awk -F '|' '{ print $2 }'`
    do
	upgrade-non-controller.sh --upgrade $NODE_UUID || fatal "Storage upgrade failed $GUIDANCE"
	# *** wait for node to come up  ??
    done
    # *** validate that all nodes are up
    # sudo heat-admin@$CONTROLLER "sudo ceph osd tree | grep down"
    check_overcloud_status || fatal "Storage upgrade failed $GUIDANCE"

    set_completed storage_upgraded
}

finalize_upgrade() {
    completed upgrade_finalized && return
    
    #overcloud_deploy ~/pilot/templates/overcloud/environments/major-upgrade-pacemaker-converge.yaml --force-postconfig || fatal "Finalize upgrade failed $GUIDANCE"
    overcloud_deploy ~/pilot/templates/overcloud/environments/major-upgrade-pacemaker-converge.yaml  || fatal "Finalize upgrade failed $GUIDANCE"

    # check for unmanged, repeatedly! set:
    #  ssh heat-admin@$CONTROLLER "sudo pcs property set maintenance-mode=false"
    #    and then sleep 30 sec try again

    # sanity test should succeed here
    set_completed upgrade_finalized
}


upgrade_aodh_migration() {
    completed aodh_migrated && return

    overcloud_deploy ~/pilot/templates/overcloud/environments/major-upgrade-aodh-migration.yaml  || fatal "upgrade aodh_migration failed $GUIDANCE"

    # sanity test should succeed here
    set_completed aodh_migrated
}



# --------------- main
cd ~  

deploy_subscription_json
prepare_upgrade
upgrade_undercloud
check_undercloud_upgrade

patch_ceph_conf_for_health

upgrade_overcloud_images
subscribe_overcloud # should already be subscribed - making sure
upgrade_telemetry
#patch_ha_proxy     # deprecated
upgrade_scripts
upgrade_controllers
#upgrade_storage
#upgrade_computes
#finalize_upgrade
#upgrade_aodh_migration

# OpenStack Platform 10 includes a migration script
# (aodh-data-migration) to move to composite alarms. This guide contains
# instructions for migrating this data in Section 3.4.10, “Migrating the
# OpenStack Telemetry Alarming Database”. Make sure to run this script
# and convert your alarms to composite.
