#!/bin/bash
#
# OpenStack - A set of software tools for building and managing cloud
# computing platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.
#
RADOSGW_PUBLIC_VIP=${1}
KEYSTONE_PRIVATE_VIP=${2}
KEYSTONE_ADMIN_PASS=${3}
CEPH_CONF=ceph.conf

####################
# Function usage
####################
usage( ) {
cat <<EOF
Usage: $0 <RADOSGW_PUBLIC_VIP> <KEYSTONE_PRIVATE_VIP> <KEYSTONE_ADMIN_TOKEN>
EOF
exit -1
}

####################
# Function is_file_exits
####################
is_file_exits(){
        [[ -f "$CEPH_CONF" ]] && return 0 || return 1
}

####################
# Main
####################
[[ $# -ne  3  ]] && usage

if ( ! is_file_exits "$CEPH_CONF" )
then
 echo "File: $CEPH_CONF, not found!"
 exit -1
fi

cat << EOF > /tmp/swift.tmp
rgw swift url = http://${RADOSGW_PUBLIC_VIP}:8087
rgw swift url prefix = swift
rgw keystone url = http://${KEYSTONE_PRIVATE_VIP}:35357
rgw keystone admin token = ${KEYSTONE_ADMIN_PASS}
rgw keystone accepted roles = _member_, Member, admin
rgw keystone token cache size = 500
rgw keystone revocation interval = 600
rgw s3 auth use keystone = true
EOF

EXISTING_LINE=`grep -n "rgw swift url" ${CEPH_CONF} | grep -Eo '^[^:]+'`
if [ ! "$EXISTING_LINE" ]
then
  LINE_NUM=`grep -n "filestore_xattr_use_omap" ${CEPH_CONF} | grep -Eo '^[^:]+'`
    sed "${LINE_NUM}r /tmp/swift.tmp" < ${CEPH_CONF} > /tmp/ceph.tmp
    mv /tmp/ceph.tmp ${CEPH_CONF}
else 
  echo "Nothing to do -- swift integration already found."
fi