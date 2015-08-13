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