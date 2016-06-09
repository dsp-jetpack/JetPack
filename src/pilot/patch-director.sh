#!/bin/bash

# (c) 2016 Dell
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

###
### This script is responsible for applying patches to the OSP Director. The
### patches provide an interim workaround until bug(s) are resolved upstream.
###
### It's possible that updating the Director (via yum) will affect files in
### a way that a patch is no longer relevant, or no longer cleanly applies.
### If this situation arises, the patch data in this file will need to be
### updated to work with the new Director code.
###

# The following file needs to be patched in order to enable the Ceph radosgw.
# Use absence of "::ceph::profile::rgw" to indicate whether the file needs
# to be patched.

file="/usr/share/openstack-tripleo-heat-templates/puppet/manifests/overcloud_controller_pacemaker.pp"

if ! grep -q "::ceph::profile::rgw" ${file}; then
    echo "Applying patches for Ceph radosgw..."
    # Quote the 'EOF' to prevent bash from doing any parameter expansion
    sudo patch -V t -d $(dirname ${file}) <<'EOF'
--- overcloud_controller_pacemaker.pp.orig	2016-04-07 16:08:52.793376909 -0400
+++ overcloud_controller_pacemaker.pp	2016-04-07 16:13:27.531762180 -0400
@@ -537,6 +537,7 @@
     }
     include ::ceph::conf
     include ::ceph::profile::mon
+    include ::ceph::profile::rgw
   }
 
   if str2bool(hiera('enable_ceph_storage', false)) {
@@ -977,7 +978,8 @@
   # swift proxy
   class { '::swift::proxy' :
     manage_service => $non_pcmk_start,
-    enabled        => $non_pcmk_start,
+    # enabled        => $non_pcmk_start,
+    enabled        => false,
   }
   include ::swift::proxy::proxy_logging
   include ::swift::proxy::healthcheck
@@ -1842,6 +1844,13 @@
 
   }
 
+  if $ceph::profile::params::enable_rgw
+  {
+    exec { 'create_radosgw_keyring':
+      command => "/usr/bin/ceph auth get-or-create client.radosgw.gateway mon 'allow rwx' osd 'allow rwx' -o /etc/ceph/ceph.client.radosgw.gateway.keyring" ,
+      creates => "/etc/ceph/ceph.client.radosgw.gateway.keyring" ,
+    }
+  }
 } #END STEP 4
 
 if hiera('step') >= 5 {
EOF
    status=$?
    [ ${status} -eq 0 ] || exit ${status}
fi
