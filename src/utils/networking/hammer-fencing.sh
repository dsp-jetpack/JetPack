#!/bin/bash
# Copyright 2014, Dell
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
# Version: 1.1
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
    echo "hammer sc-param update --id $FT_ID --default-value $FENCE_MODE --override true"
    #hammer sc-param update --id $FT_ID --default-value $FENCE_MODE --override true
  else
    echo "Error: Unable to find parameter $FT_ID"
    exit 1
  fi
else
  echo "Usage: $0  < enabled || disabled >"
  exit 1
fi
