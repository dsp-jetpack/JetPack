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

+# This hacks in a patch to fix correct querying WSMAN Enumerations that have
 +# more than 100 entries.  We will need to remove this after the fix appears
 +# in OSP10.  Note that this patch must be here because we use this code prior
 +# to deploying the director.
 +echo
 +echo "## Patching Ironic iDRAC driver WSMAN library..."
 +OUT=$(sudo patch -b -s /usr/lib/python2.7/site-packages/dracclient/wsman.py ~/pilot/wsman.patch)
 +sudo rm -f /usr/lib/python2.7/site-packages/dracclient/wsman.pyc
 +sudo rm -f /usr/lib/python2.7/site-packages/dracclient/wsman.pyo
 +echo "## Done." 

# This hacks in a patch to work around a known issue where RAID configuration
# fails because the iDRAC is busy running an export to XML job and is not
# ready. Note that this patch must be here because we use this code prior to
# deploying the director.
echo
echo "## Patching Ironic iDRAC driver is_ready check..."
OUT=$(sudo patch -b -s /usr/lib/python2.7/site-packages/dracclient/resources/lifecycle_controller.py ~/pilot/lifecycle_controller.patch)
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/lifecycle_controller.pyc
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/lifecycle_controller.pyo
OUT=$(sudo patch -b -s /usr/lib/python2.7/site-packages/dracclient/resources/uris.py ~/pilot/uris.patch)
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/uris.pyc
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/uris.pyo
OUT=$(sudo patch -b -s /usr/lib/python2.7/site-packages/dracclient/client.py ~/pilot/client.patch)
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/client.pyc
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/client.pyo
OUT=$(sudo patch -b -s /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/raid.py ~/pilot/raid.patch)
sudo rm -f /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/raid.pyc
sudo rm -f /usr/lib/python2.7/site-packages/ironic/drivers/modules/drac/raid.pyo
echo "## Done."

# This hacks in a patch to work around a known issue where a RAID-10 virtual
# disk cannot be created from more than 16 backing physical disks.  Note that
# this code must be here because we use this code prior to deploying the
# director.
echo
echo "## Patching Ironic iDRAC driver RAID library..."
OUT=$(sudo patch -b -s /usr/lib/python2.7/site-packages/dracclient/resources/raid.py ~/pilot/dracclient_raid.patch)
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/raid.pyc
sudo rm -f /usr/lib/python2.7/site-packages/dracclient/resources/raid.pyo
echo "## Done."

# This hacks in a patch to work around an issue where lock contention on the
# nodes in ironic can occur during RAID cleaning.
echo
echo "## Patching ironic.conf for locking..."
sudo sed -i 's/#node_locked_retry_attempts = 3/node_locked_retry_attempts = 15/' /etc/ironic/ironic.conf
echo "## Done."

echo
echo "## Restarting openstack-ironic-conductor.service..."
sudo systemctl restart openstack-ironic-conductor.service
echo "## Done."

# This hacks in a workaround to fix in-band introspection.  A fix has been
# made to NetworkManager upstream, but is not currently present in OSP10.
# We will need to remove this after the fix appears in OSP10.
echo
echo "## Patching Ironic in-band introspection..."
sudo sed -i 's/initrd=agent.ramdisk /initrd=agent.ramdisk net.ifnames=0 biosdevname=0 /' /httpboot/inspector.ipxe
echo "## Done."

network="ctlplane"
echo
echo "## Configuring neutron network ${network} as a cleaning network"
configure_cleaning_network $network
echo "## Done."
