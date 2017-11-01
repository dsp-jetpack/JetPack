#!/bin/bash
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
# TODO:
#   - patch clock skew info: https://blog.headup.ws/node/36 into ceph health

# to exit on failure:
#set -e
shopt -s nullglob  # pathname expansion which match no files returns null string

exec > >(tee -a ~/update_upgrade/upgrade-js6.0.1.log)
exec 2>&1

CONTROL_SCALE="$1"
COMPUTE_SCALE="$2"
CEPH_SCALE="$3"
VLAN_RANGE="$4"
SUBSCRIPTION_MGR_USER="$5"
SUBSCRIPTION_MGR_PASSWORD="$6"
OPENSTACK_POOL_ID="$7"
CEPH_POOL_ID="$8"
SAH_IP="$9"

if [ "$#" -lt 9 ]; then
    echo "Usage: $0 <control_scale> <compute_scale> <ceph_scale> <vlan_range> \
<subscription_mgr_user> <subscription_mgr_password> <openstack_pool_id> <ceph_pool_id> <sah_ip_address>"
    exit 1
fi

source ~/stackrc

DEPLOY_CMD_PATH=~/pilot/overcloud_deploy_cmd.log
SUBSCRIPTION_JSON="$HOME/pilot/subscription.json"
CONTROLLERS=$(openstack server list  -c Name -c Networks -f value | grep 'control' | awk -F "=" '{ print $2 }')
CONTROLLER=($CONTROLLERS)
COMPUTES=$(openstack server list  -c Name -c Networks -f value | grep 'compute' | awk -F "=" '{ print $2 }')
STORAGE=$(openstack server list  -c Name -c Networks -f value | grep 'storage' | awk -F "=" '{ print $2 }')
OVERCLOUD=$(openstack server list  -c Name -c Networks -f value | awk -F "=" '{ print $2 }')
STACKNAME=$(openstack stack list -f value -c "Stack Name")
GUIDANCE="- please fix issue and re-run upgrade-script"

mkdir -p ~/update_upgrade/upgrade-lockfiles

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

info "Log file is: $HOME/update_upgrade/upgrade-js6.0.log"

# Generally following Chapter 3 of the Red Hat Openstack Platform 10
# document:
# https://access.redhat.com/documentation/en/red-hat-openstack-platform/10/paged/upgrading-red-hat-openstack-platform/chapter-3-director-based-environments-performing-upgrades-to-major-versions

# 3.1. IMPORTANT PRE-UPGRADE NOTES
# update the customized yamls in the ~/pilot/templates directory by comparing with JS-10.0 versions.


deploy_subscription_json() {
    # deploy this file fresh every time so one can change pool_id's if need be
    completed subscription_json_deployed && return
    info "updating subscription.json with needed repositories"
    cd ~/pilot
    cat >"subscription.json" <<EOF
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
                       "rhel-7-server-rhceph-2-tools-rpms",
                       "rhel-7-server-rhscon-2-agent-rpms"  ]
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
    # insert "unset" loop to protect against OS_<attrs> defined elsewhere
    grep 'unset $key' ~/stackrc >/dev/null 2>&1
    if [ $? -ne 0 ]
    then
      sed -i '1ifor key in $( set | awk '"'"'{FS="="}  /^OS_/ {print $1}'"'"' ); do unset $key ; done' ~/stackrc
    fi
}


patch_bzs() {
    # https://bugzilla.redhat.com/show_bug.cgi?id=1482172
    ! grep "pcs config show --full"  ~/pilot/templates/overcloud/extraconfig/tasks/major_upgrade_pacemaker_migrations.sh &&  cat ~/update_upgrade/1476711.patch | sudo patch -f -d ~/pilot/templates/overcloud -p1
}


patch_network_environment_yaml() {
    ! grep -q "NovaColdMigrationNetwork: internal_api" ~/pilot/templates/network-environment.yaml && \
    sed -i.bak 's/^  ServiceNetMap:/  ServiceNetMap:\
    NovaColdMigrationNetwork: internal_api\
    NovaLibvirtNetwork: internal_api/' ~/pilot/templates/network-environment.yaml

    # https://bugzilla.redhat.com/show_bug.cgi?id=1482172
    ! grep -q "NeutronTunnelTypes"  ~/pilot/templates/network-environment.yaml && \
    sed -i.bak "s/^parameter_defaults:/parameter_defaults:\\
  # The tunnel type for the tenant network (vxlan or gre). Set to empty string to disable tunneling.\\
  NeutronTunnelTypes: '' \\
  /"  ~/pilot/templates/network-environment.yaml
}


patch_migration_timeouts() {
    grep -q NovaComputeExtraConfig ~/pilot/templates/dell-environment.yaml && return
    cat >>~/pilot/templates/dell-environment.yaml <<EOF

  NovaComputeExtraConfig:
    nova::migration::libvirt::live_migration_completion_timeout: 800
    nova::migration::libvirt::live_migration_progress_timeout: 150
EOF
    for C in $COMPUTES
    do
        [[ $(ssh heat-admin@${C} 'sudo egrep "^live_migration_progress_timeout" /etc/nova/nova.conf') ]] || ssh heat-admin@${C} 'sudo sed -i "s|\[libvirt\]|\[libvirt\]\nlive_migration_progress_timeout=150\nlive_migration_completion_timeout=800|" /etc/nova/nova.conf'
    done
}


patch_ceph_disk_timeout() {
    for S in $STORAGE
    do
        ssh heat-admin@${S} 'sudo sed -i "s/timeout 120/timeout 10000/" /usr/lib/systemd/system/ceph-disk\@.service'
    done
}


patch_ironic() {
    completed ironic-patched && return
    ~/update_upgrade/patch_ironic.sh || fatal "ironic patch failed. $GUIDANCE"
    set_completed ironic-patched

}

subscribe_overcloud() {
    # subscribe the overcloud nodes
    completed overcloud-registered && return
    info "Registering overcloud nodes with Red Hat Subscription Manger"
    patch_stack_rc_format
    cd ~/update_upgrade
    # The updated subscription.json should have been deployed already
    if ! ~/update_upgrade/register_overcloud.py -u ${SUBSCRIPTION_MGR_USER} -p ${SUBSCRIPTION_MGR_PASSWORD} ; then
        fatal "Could not successfully register overcloud - please fix issue and re-run update script"
    fi
    set_completed overcloud-registered
}


restart_ceph_mon_services() {
    for C in $CONTROLLERS
    do
        local service=$(ssh heat-admin@${C} 'sudo systemctl | grep ceph-mon\..*\.service')
        local regexp='(ceph-mon\.[a-z0-9-]+\.[0-9]+\.[0-9]+)\.service'
        local host=$(ssh heat-admin@${C} hostname)
        if [[ $service =~ $regexp ]] && \
            ssh heat-admin@${C} sudo systemctl restart ${BASH_REMATCH[1]} ;
        then
            info "restarting ceph-mon service ${BASH_REMATCH[1]} on ${host} ($C)"
        else
            fatal "failed to find or restart ceph-mon service ${BASH_REMATCH[1]} on ${host} ($C)"
        fi
    done
}


patch_ceph_conf_for_health() {
    info "Checking Ceph heath"
    local health=$(ssh heat-admin@$CONTROLLER 'sudo ceph health')

    local regexp='skew'
    if [[ $health =~ $regexp ]] ;
    then
        fatal "Ceph monitor clock skew detected, please sync controller nodes and rerun script"
    fi

    # patch up two common warnings

    info "Suppressing Ceph PG to OSG ratio warning"
    for C in $CONTROLLERS
    do
        [[ $(ssh heat-admin@${C} 'grep mon_pg_warn_max_per_osd /etc/ceph/ceph.conf') ]] || ssh heat-admin@${C} 'sudo sed -i "s|\[global\]|\[global\]\nmon_pg_warn_max_per_osd = 0\nmon_warn_on_legacy_crush_tunables = false|" /etc/ceph/ceph.conf'
    done

    restart_ceph_mon_services
}


unpatch_ceph_conf_for_health() {
    completed unpatch_ceph_conf_for_health && return
    for C in $CONTROLLERS
    do
        ssh heat-admin@${C} 'sudo sed -i "s/^mon_pg_warn_max_per_osd.*$//" /etc/ceph/ceph.conf'
        ssh heat-admin@${C} 'sudo sed -i "s/^mon_warn_on_legacy_crush_tunables.*$//" /etc/ceph/ceph.conf'
    done
    restart_ceph_mon_services
    set_completed unpatch_ceph_conf_for_health
}


patch_post_deploy_yaml() {
    grep -q "radosgw.gateway" ~/pilot/templates/post-deploy.yaml && return  # already patched

    perl -i -pe "undef $/; s/echo \"Restarting RGW...\".*\} \>\>/echo \"Restarting RGW...\"\n\
          sudo pkill radosgw
          sudo systemctl restart ceph-radosgw\@radosgw.gateway
        \} \>\>/ms"  ~/pilot/templates/post-deploy.yaml
}


completed() {
    info "~/update_upgrade/upgrade-lockfiles/${1}.lock"
    [ -e ~/update_upgrade/upgrade-lockfiles/${1}.lock ]
}


set_completed() {
    info "Stage $1 completed"
    touch ~/update_upgrade/upgrade-lockfiles/${1}.lock
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
    patch_network_environment_yaml
    patch_ironic
    patch_migration_timeouts
    patch_bzs

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
    ~/update_upgrade/customize_image.sh $SUBSCRIPTION_MGR_USER $SUBSCRIPTION_MGR_PASSWORD $CEPH_POOL_ID || fatal "overcloud images were not successfully customized $GUIDANCE"
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
        let counter=counter+1  # 5 minutes
        [[ $counter -lt 10 ]] || break
    done
    info "Waiting for software deployments to complete..."
    counter=0
    until ! openstack software deployment list | grep PROGRESS ; do
        sleep 30
        let counter=counter+1  # 2 min
        [[ $counter -lt 4 ]] || break
    done
    info "Checking stack status and pcs status for failures or stuck progress"
    # fail if any of these conditions are true..
        # removed this condition until we can refacter - halts progress un-necessarily
        # openstack software deployment list | egrep "(FAIL|PROGRESS)" || \
    ! (openstack stack list | grep FAIL || \
        openstack  stack resource list $STACKNAME | egrep "(FAIL|PROGRESS)" || \
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
        t_line=${line::-2}
        # switch to new dell-environment-upgrade
        # dellenv="-e ~/pilot/templates/dell-environment.yaml"
        # if [[ "$t_line" == "$dellenv" ]]; then
        #  t_line="-e ~/update_upgrade/templates/dell-environment-upgrade.yaml"
        # fi
        envs+=($t_line)
      fi
    done < "$DEPLOY_CMD_PATH"
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
    # from BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1467704
    # ceph osd pool create metrics 8 8
    # ceph auth get-or-create client.gnocchi mon "allow r" osd "allow rwx pool=metrics"
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

    overcloud_deploy ~/pilot/templates/overcloud/environments/major-upgrade-aodh-migration.yaml  || fatal "Upgrade aodh_migration failed $GUIDANCE"

    # sanity test should succeed here
    set_completed aodh_migrated
}


ceph_upgrade_sah() {
    completed ceph_upgraded_sah && return

    sudo scp -o StrictHostKeyChecking=no ~/update_upgrade/ceph_upgrade_sah.sh ~/update_upgrade/deploy-rhscon-vm-6.py root@${SAH_IP}:/tmp
    ceph_ip=$(sudo ssh root@${SAH_IP} grep eth0 ceph.cfg | awk -F ' ' '{ print $2 }')
    ceph_pw=$(sudo ssh root@${SAH_IP} grep rootpassword ceph.cfg | awk -F ' ' '{ print $2 }')
    [[ $ceph_ip == "" ]] || [[ $ceph_pw == "" ]] && \
        fatal "Could not retrieve Ceph VM IP address or password from SAH node. $GUIDANCE"
    sudo ssh root@${SAH_IP} 'cd /tmp ; /tmp/ceph_upgrade_sah.sh' || fatal "Ceph upgrade SAH failed - $GUIDANCE"
    sleep 30

    set_completed ceph_upgraded_sah
}


ceph_upgrade_director() {
    completed ceph_upgrade_director && return
    ceph_ip=$(sudo ssh root@${SAH_IP} grep eth0 ceph.cfg | awk -F ' ' '{ print $2 }')
    ceph_pw=$(sudo ssh root@${SAH_IP} grep rootpassword ceph.cfg | awk -F ' ' '{ print $2 }')
    [[ $ceph_ip == "" ]] || [[ $ceph_pw == "" ]] && \
        fatal "Could not retrieve Ceph VM IP address or password from SAH node. $GUIDANCE"
    info "Upgrading ceph on director node:  $ceph_ip  *******"
    cd ~/update_upgrade
    ./ceph_upgrade_director.sh "$ceph_ip" "$ceph_pw"  || fatal "Ceph upgrade Director failed - $GUIDANCE"

    set_completed ceph_upgrade_director
}


copy_auth_keys_to_sah() {
    completed auth_keys_copied && return
    info "Please provide root password for SAH node so allow authorized_keys info to be sent"
    info "This provide access for Ceph upgrade to the RH Ceph console. Control-C to exit."
    sudo scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o KbdInteractiveDevices=no  /root/.ssh/authorized_keys ${SAH_IP}:~/.ssh/  || fatal "Ceph copy auth keys to SAH failed - $GUIDANCE"

    set_completed auth_keys_copied
}

disable_swift_services(){
   services=( openstack-swift-proxy.service openstack-swift-object-expirer.service )
   for node in $OVERCLOUD
   do
     info "Node is: $node"
     for service in "${services[@]}"
     do
       # disable and stop swift proxy on all overcloud nodes,
	   # may be overkill as probably only running on controllers.
       info "Stop and disable ${service}"
       ssh heat-admin@${node} "sudo systemctl stop ${service}"
       ssh heat-admin@${node} "sudo systemctl disable ${service}"
     done
   done
}

update_ceph_config_for_rgw(){

  info "Update RGW and HAProxy configuration for OSP 10"
  source ~/${STACKNAME}rc
  # Check for rgw_frontends. Don't modify unless need be retart service either way
  KEYSTONE_URL_VALUE=$(openstack endpoint show keystone | grep adminurl | cut -d\| -f3 | sed 's%/[^/]*$%%')
  # Fetch a copy of ceph.conf and haproxy.cfg files from a controller node
  source ~/stackrc

  scp heat-admin@$CONTROLLER:/etc/haproxy/haproxy.cfg /tmp/haproxy.cfg

  INDEX=0
    for node in $CONTROLLERS
    do
      scp heat-admin@$node:/etc/ceph/ceph.conf /tmp/${INDEX}ceph.conf
      sed -i.bak -e 's/rgw_keystone_url =.*$/rgw_keystone_url =/' /tmp/${INDEX}ceph.conf
      OUTPUT=$(grep "rgw_frontends" /tmp/${INDEX}ceph.conf)
      if [[ "${OUTPUT}" =~ "rgw_frontends" ]]
      then
        info "rgw_frontends already set in ceph.conf"
      else
        sed -i '/^rgw_keystone_url =/ s%$%\nrgw_frontends =%' /tmp/${INDEX}ceph.conf
        CEPH_STOR_IP_PORT=$(grep "${INDEX}.storage" /tmp/haproxy.cfg | grep 8080 | cut -d" " -f5)
        sed -i 's%^rgw_frontends =%rgw_frontends = civetweb port='"${CEPH_STOR_IP_PORT}"'%' /tmp/${INDEX}ceph.conf
      fi
      sed -i 's%^rgw_keystone_url =%rgw_keystone_url ='"${KEYSTONE_URL_VALUE}"'%' /tmp/${INDEX}ceph.conf
      echo "Copying modified ceph.conf back to ${node}"
      scp /tmp/${INDEX}ceph.conf heat-admin@${node}:/tmp/ceph.conf
      ssh heat-admin@${node} "sudo mv /tmp/ceph.conf /etc/ceph/ceph.conf"
      let INDEX=${INDEX}+1
    done
  # restart the rgw services whether we touch ceph.conf or not
  for node in $CONTROLLERS
  do
    ssh heat-admin@${node} "sudo systemctl enable ceph-radosgw.target"
    ssh heat-admin@${node} "sudo systemctl restart ceph-radosgw.target"
    ssh heat-admin@${node} "sudo systemctl enable ceph-radosgw\@radosgw.gateway.service"
    ssh heat-admin@${node} "sudo systemctl restart ceph-radosgw\@radosgw.gateway.service"
    ssh heat-admin@${node} "sudo chown -R ceph:ceph /var/lib/ceph/radosgw"
	ssh heat-admin@${node} "sudo chown -R ceph:ceph /var/log/ceph"
  done

  # Check for rgw_frontends. If file does not need modification we still restart services
  OUTPUT=$(grep "listen ceph_rgw" /tmp/haproxy.cfg)
  if [[ "${OUTPUT}" =~ "listen ceph_rgw" ]]
  then
    info "listen ceph_rgw alredy set in haproxy"
  else
    # Modify the haproxy.conf's contents
    # Get Keystone URL value
    sed -i.bak 's%listen swift_proxy_server%listen ceph_rgw%' /tmp/haproxy.cfg
    for node in $CONTROLLERS
    do
      info "Copying modified haproxy.conf to ${node}"
      scp /tmp/haproxy.cfg heat-admin@${node}:/tmp/haproxy.cfg
      ssh heat-admin@${node} "sudo mv /tmp/haproxy.cfg /etc/haproxy/haproxy.cfg"
    done
  fi
  # restart haproxy whether cfg touched or not
  for node in $CONTROLLERS
  do
    ssh heat-admin@${node} "sudo systemctl restart haproxy"
  done

  info "Finished mods to haproxy and swift for rgw to function after upgrade."

}

recreate_swift_endpoint(){
  #Indentify swift endpoint UID and capture swift endpoint IPs and region data
  source ~/${STACKNAME}rc  # addressing the overcloud
  ENDPOINT_UID=$(openstack endpoint list | grep swift | cut -d\| -f2 | xargs echo -n)
  info "Existing Swift ENDPOINT_ID: $ENDPOINT_UID"
  ADMIN_URL_IP=$(openstack endpoint show swift | grep adminurl | cut -d\| -f3 | cut -d: -f2 | cut -d\/ -f3)
  info "Existing Swift ADMIN_URL_IP: $ADMIN_URL_IP"
  INTERNAL_URL_IP=$(openstack endpoint show swift | grep internalurl | cut -d\| -f3 | cut -d: -f2 | cut -d\/ -f3)
  info "Existing Swift INTERNAL_URL_IP: $INTERNAL_URL_IP"
  PUBLIC_URL_IP=$(openstack endpoint show swift | grep publicurl | cut -d\| -f3 | cut -d: -f2 | cut -d\/ -f3)
  info "Existing Swift PUBLIC_URL_IP: $PUBLIC_URL_IP"
  REGION=$(openstack endpoint show swift | grep region | cut -d\| -f3 | xargs echo -n)
  info "Existing Swift REGION: $REGION"
  #Delete swift endpoint
  openstack endpoint delete ${ENDPOINT_UID}
  info "Deleted existing swift endpoint."
  #Recreate new Swift endpoint using OSP10 format
  openstack endpoint create --region ${REGION} --publicurl "http://${PUBLIC_URL_IP}:8080/swift/v1" --adminurl "http://${ADMIN_URL_IP}:8080/swift/v1" --internalurl "http://${INTERNAL_URL_IP}:8080/swift/v1" swift
  info "New swift endpoint created for RGW."
  source ~/stackrc
}

restart_controllers_to_finalize_rgw_upgrade(){
  #Indentify swift endpoint UID and capture swift endpoint IPs and region data
  for node in $CONTROLLERS
  do
    info "Rebooting controller $node to finalize RGW upgrade."
    ssh heat-admin@${node} "sudo shutdown -r now"
  done
}

update_rgw() {
   completed rgw_configured && return
   disable_swift_services
   update_ceph_config_for_rgw
   recreate_swift_endpoint
   restart_controllers_to_finalize_rgw_upgrade
   set_completed rgw_configured
   info "Post-upgrade RGW configuration completed. You must wait for controllers to come back up and then run 'sudo pcs status' to verify cluster is in good health."
}

# --------------- main
cd ~
# most of these stages of upgrade have associated lock-files that indicate whether
# they have been sucessfully executed. See ~/update_upgrade/upgrade-lockfiles. To force a
# re-run of a stage, delete it's lock file.

copy_auth_keys_to_sah
deploy_subscription_json
prepare_upgrade
upgrade_undercloud
check_undercloud_upgrade
upgrade_overcloud_images
subscribe_overcloud # should already be subscribed - making sure
upgrade_telemetry
upgrade_scripts
upgrade_controllers
upgrade_storage
upgrade_computes
finalize_upgrade
upgrade_aodh_migration
unpatch_ceph_conf_for_health
patch_ceph_disk_timeout
ceph_upgrade_sah
### What upgrade vm we don't have running
ceph_upgrade_director
update_rgw

info "Upgrade complete!"
