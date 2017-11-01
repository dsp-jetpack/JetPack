#!/bin/bash

# Copyright (c) 2016 Dell Inc. or its subsidiaries.
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

domain_name=$(grep CloudDomain ~/pilot/templates/dell-environment.yaml | awk -F: '{print$2}' | tr -d '[:space:]')

sudo grep -q ^dhcp_domain=${domain_name}\$ /etc/nova/nova.conf
if [ $? -ne 0  ] ; then
    echo "Patching CloudDomain (${domain_name}) into nova.conf and restarting nova..."
    sudo sed -i.bak "s/^dhcp_domain=.*/dhcp_domain=${domain_name}/" /etc/nova/nova.conf || exit 1

    # Restart all of nova
    sudo systemctl restart openstack-nova-api.service || exit 1
    sudo systemctl restart openstack-nova-cert.service || exit 1
    sudo systemctl restart openstack-nova-compute.service || exit 1
    sudo systemctl restart openstack-nova-conductor.service || exit 1
    sudo systemctl restart openstack-nova-scheduler.service || exit 1
fi
