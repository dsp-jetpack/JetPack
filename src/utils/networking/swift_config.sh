#!/bin/bash
# Copyright 2015, Dell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Version: 1.0
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
