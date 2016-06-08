#!/usr/bin/bash
#
# Requires:
#   - libguestfs-tools,
#   - Red Hat subscription to;
#       rhel-7-server-extras-rpms,
#       rhel-7-server-optional-rpms,
#       rhel-7-server-openstack-8-rpms,
#   - qemu-kvm-tun-rhosp.pp
#
# Invoke example: ./customize_image.sh /home/stack/overcloud-full.qcow2 rh_user rh_pass \
#                                      1234567890abcdef1234567890abcdef mido_user mido_pass
#

TARGET_IMG="$1"
SUBSCR_USER="$2"
SUBSCR_PASS="$3"
SUBSCR_POOL="$4"
MIDO_REPO_USER="$5"
MIDO_REPO_PASS="$6"
ENABLE_REPOS="rhel-7-server-extras-rpms rhel-7-server-optional-rpms rhel-7-server-openstack-8-rpms"
INSTALL_PCKGS=augeas,augeas-devel,deltarpm,dsc20,tomcat,midonet-api,python-networking-midonet,midolman,ruby-devel,zookeeper

export LIBGUESTFS_BACKEND=direct

if [ "$#" -ne 6 ]; then
  echo "Usage: $0 <target image> <subscription manager user> <subscription manager password> <subscription pool id> <MidoNet repo user> <MidoNet repo pass>"
  exit 1
fi

if ! [ -x /usr/bin/virt-customize ]; then
  echo "This script requires libguestfs-tools"
  exit 1
fi

cat > /tmp/datastax.repo << THEEND
# DataStax (Apache Cassandra)
[datastax]
name = DataStax Repo for Apache Cassandra
baseurl = http://rpm.datastax.com/community
enabled = 1
gpgcheck = 1
gpgkey = https://rpm.datastax.com/rpm/repo_key
THEEND

cat > /tmp/midokura.repo << THEEND
[mem]
name=MEM
baseurl=http://${MIDO_REPO_USER}:${MIDO_REPO_PASS}@yum.midokura.com/repo/v1.9/stable/RHEL/7/
enabled=1
gpgcheck=1
gpgkey=https://${MIDO_REPO_USER}:${MIDO_REPO_PASS}@yum.midokura.com/repo/RPM-GPG-KEY-midokura

[mem-openstack-integration]
name=MEM OpenStack Integration
baseurl=http://${MIDO_REPO_USER}:${MIDO_REPO_PASS}@yum.midokura.com/repo/openstack-liberty/stable/RHEL/7/
enabled=1
gpgcheck=1
gpgkey=https://${MIDO_REPO_USER}:${MIDO_REPO_PASS}@yum.midokura.com/repo/RPM-GPG-KEY-midokura
THEEND

echo "## Add MidoNet & Datastax repos"
virt-customize -a ${TARGET_IMG} --upload /tmp/datastax.repo:/etc/yum.repos.d/datastax.repo
virt-customize -a ${TARGET_IMG} --upload /tmp/midokura.repo:/etc/yum.repos.d/midokura.repo
rm -rf /tmp/datastax.repo /tmp/midokura.repo

echo "## Register the image with subscription manager & enable repos"
virt-customize -a ${TARGET_IMG} --run-command "subscription-manager register --username=${SUBSCR_USER} --password=${SUBSCR_PASS} --auto-attach"
virt-customize -a ${TARGET_IMG} --run-command "subscription-manager attach --pool=${SUBSCR_POOL}"
for repo in $ENABLE_REPOS; do
  virt-customize -a ${TARGET_IMG} --run-command "subscription-manager repos --enable=${repo}"
done

echo "## Installing packages"
virt-customize -a ${TARGET_IMG} --install ${INSTALL_PCKGS}

echo "## Adding SELinux workaround"
virt-customize -a ${TARGET_IMG} --upload qemu-kvm-tun.pp:/tmp/qemu-kvm-tun.pp
virt-customize -a ${TARGET_IMG} --run-command "semodule -i /tmp/qemu-kvm-tun.pp"

echo "## Applying puppet module workaround"
virt-customize -a ${TARGET_IMG} --run-command "puppet module upgrade deric-zookeeper --version 0.4.1"

echo "## Installing some Ruby Gems"
virt-customize -a ${TARGET_IMG} --run-command "gem install faraday"
virt-customize -a ${TARGET_IMG} --run-command "gem install url"

echo "## Unregister from subscription manager & cleaning-up"
virt-customize -a ${TARGET_IMG} --run-command 'subscription-manager remove --all'
virt-customize -a ${TARGET_IMG} --run-command 'subscription-manager unregister'
virt-customize -a ${TARGET_IMG} --delete /etc/yum.repos.d/midokura.repo

echo "## Done preparing MidoNet overcloud image"

# upload the image to the overcloud
#openstack overcloud image upload --update-existing --image-path $HOME/pilot/images

