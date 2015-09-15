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
FENCE_MODE="$1"
if [[ "$1" = "enabled" || "$1" = "disabled" ]]
then
  if [[ "$FENCE_MODE" = "enabled" ]]
  then
    FENCE_MODE="fence_ipmilan"
  fi

  HA_ID=`hammer hostgroup list | grep HA | cut -d" " -f1`
  FT_ID=`hammer sc-param list --search fencing_type --hostgroup-id $HA_ID | grep fencing_type | cut -d" " -f1`

  if [[ $FT_ID ]]
  then
    echo "Updating fencing_type value to: $1 for hostgroup: $HA_ID"
    hammer sc-param update --id $FT_ID --default-value $FENCE_MODE --override true
  else
    echo "Error: Unable to find parameter $FT_ID"
    exit 1
  fi
else
  echo "Usage: $0  < enabled || disabled >"
  exit 1
fi