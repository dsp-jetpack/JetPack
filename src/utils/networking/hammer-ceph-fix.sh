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
HA_ID=`hammer hostgroup list | grep HA | cut -d" " -f1`
CN_ID=`hammer hostgroup list | grep "Compute (Neutron)" | cut -d" " -f1`

HA_CEPH_OSD_MNT_ID=`hammer sc-param list --search ceph_osd_mount_options_xfs --hostgroup-id $HA_ID | grep ceph_osd_mount| cut -d" " -f1`

CN_CEPH_OSD_MNT_ID=`hammer sc-param list --search ceph_osd_mount_options_xfs --hostgroup-id $CN_ID | grep ceph_osd_mount| cut -d" " -f1`

hammer sc-param update --id $HA_CEPH_OSD_MNT_ID --default-value "inode64,noatime,logbsize=256k" --override true

hammer sc-param update --id $CN_CEPH_OSD_MNT_ID --default-value "inode64,noatime,logbsize=256k" --override true