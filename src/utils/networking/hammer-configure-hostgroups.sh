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

find_param()
{
  param_name=$1

  param_id=0
  for i in $(hammer hostgroup sc-params  --search $1 --id 0 --per-page 1000 | awk "/$1/ {print \$1}"); do
    if [[ $(hammer sc-param info --id $i | awk '/class/ {print $NF}') == "quickstack::neutron::compute" ]]
    then
      param_id=$i
    fi
  done

  echo $param_id
}

update_param()
{
  param_name=$1
  value=$2

  param_id=$(find_param $1)
  if [[ $param_id ]]
  then
    hammer sc-param update --id $param_id --default-value $2 --override yes --parameter-type 'array'
  else
    echo "Error: Unable to find parameter $param_name"
    exit 1
  fi 
}

cd /usr/share/openstack-foreman-installer
bin/quickstack_defaults.rb -g config/hostgroups.yaml -d ~/pilot/dell-pilot.yaml.erb -v parameters

# Update ovs_bridge params on the Compute (Neutron) hostgroup
update_param ovs_bridge_uplinks '["br-tenant:bond0"]'
update_param ovs_bridge_mappings '["physint:br-tenant"]'
