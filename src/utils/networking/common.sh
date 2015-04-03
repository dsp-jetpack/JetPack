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
# Author:  Chris Dearborn
# Version: 1.0
#

. ./osp_config.sh

PILOT_DIR=/root/pilot

die()
{
  echo "Exiting"
  exit 1
}

execute()
{
  if [[ $1 == *"username"* || $1 == *"password"* ]]
  then
    censored=$(echo $1 | sed "s/\".*\"/\"******\"/")
    echo "# $censored"
  else
    echo "# $1"
  fi

  eval $1 || die
  echo
}
