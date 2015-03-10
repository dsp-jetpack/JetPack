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
# Author:  Chris Dearborn
# Version: 1.7
#

shopt -s nullglob

NETWORK_CONFIG_DIR=/etc/sysconfig/network-scripts

# Default bonding mode
DEFAULT_MODE="balance-tlb"

# Logging levels
FATAL=0
ERROR=1
WARN=2
INFO=3
DEBUG=4

# Default logging level
LOG_LEVEL=$INFO

# Logging functions
log() { echo -e "$(date '+%F %T'): $@" >&2; }
fatal() { log "FATAL: $@" >&2; exit 1; }
error() { [[ $ERROR -le $LOG_LEVEL ]] && log "ERROR: $@"; }
warn() { [[ $WARN -le $LOG_LEVEL ]] && log "WARN: $@"; }
info() { [[ $INFO -le $LOG_LEVEL ]] && log "INFO: $@"; }
debug() { [[ $DEBUG -le $LOG_LEVEL ]] && log "DEBUG: $@"; }

# Commands
ADD_BOND="add_bond"
ADD_VLAN="add_vlan"
UPDATE_DEVICE="update_device"
UPDATE_BOND="update_bond"
UPDATE_VLAN="update_vlan"
REMOVE_BOND="remove_bond"
REMOVE_VLAN="remove_vlan"
DEFAULT_ROUTE="default_route"

set_command() {
  [ $command ] && fatal "Only one of -ab, -av, -ud, -ub, -uv, -rb, -rv, -dr may be specified"
  command="$1"
  debug "Setting command=$command"
}

parse_args() {
  if [[ $# = 0 ]]
  then
    usage
    exit 1
  fi

  while [[ $# > 0 ]]
  do
    local key="$1"
    debug "Processing key \"$key\""
    shift

    case $key in
      -ab|--add-bond)
        set_command $ADD_BOND
        bond_name="$1"
        debug "Setting bond_name=$bond_name"
        shift
        ;;
      -av|--add-vlan)
        set_command $ADD_VLAN
        vlan_name="$1"
        debug "Setting vlan_name=$vlan_name"
        shift
        ;;
      -d|--dns)
        dns="$1"
        dns_passed=true
        debug "Setting dns=$dns"
        debug "Setting dns_passed=$dns_passed"
        shift
        ;;
      -g|--gateway)
        gateway="$1"
        debug "Setting gateway=$gateway"
        shift
        ;;
      -h|--help)
        usage
        exit 1
        ;;
      -i|--ip)
        ip="${1,,}"
        ip_passed=true
        debug "Setting ip=$ip"
        debug "Setting ip_passed=$ip_passed"
        shift
        ;;
      -l|--log_level)
        local logging_level="$1"
        case $logging_level in
          fatal)
            LOG_LEVEL=$FATAL
            ;;
          error)
            LOG_LEVEL=$ERROR
            ;;
          warn)
            LOG_LEVEL=$WARN
            ;;
          info)
            LOG_LEVEL=$INFO
            ;;
          debug)
            LOG_LEVEL=$DEBUG
            ;;
          *)
            fatal "Unknown logging level \"$logging_level\""
            ;;
        esac

        shift
        ;;
      -m|--mode)
        mode="$1"
        # Note that the valid modes are taken from the nmcli man page
        case $mode in
          balance-rr|active-backup|balance-xor|broadcast|802.3ad|balance-tlb|balance-alb)
            ;;
          *)
            fatal "Invalid bonding mode \"$mode\""
            ;;
        esac
        debug "Setting mode=$mode"
        shift
        ;;
      -n|--netmask)
        netmask="$1"
        debug "Setting netmask=$netmask"
        shift
        ;;
      -p|--prefix)
        prefix="$1"
        debug "Setting prefix=$prefix"
        shift
        ;;
      -pr|--promisc)
        promisc=$1
	debug "Setting promisc=$promisc"
        shift
        ;;
      -rb|--remove-bond)
        set_command $REMOVE_BOND
        bond_name="$1"
        debug "Setting bond_name=$bond_name"
        shift
        ;;
      -rv|--remove-vlan)
        set_command $REMOVE_VLAN
        vlan_name="$1"
        debug "Setting vlan_name=$vlan_name"
        shift
        ;;
      -s|--slaves)
        local raw_slaves="$1"

        # Convert a comma separated slave list to an array
        slave_names=(${raw_slaves//,/ })

        debug "Setting slave_names=${slave_names[@]}"
        shift
        ;;
      -ud|--update-device)
        set_command $UPDATE_DEVICE
        device_name="$1"
        debug "Setting device_name=$device_name"
        shift
        ;;
      -ub|--update-bond)
        set_command $UPDATE_BOND
        bond_name="$1"
        debug "Setting bond_name=$bond_name"
        shift
        ;;
      -uv|--update-vlan)
        set_command $UPDATE_VLAN
        vlan_name="$1"
        debug "Setting vlan_name=$vlan_name"
        shift
        ;;
      -dr|--default-route)
        set_command $DEFAULT_ROUTE
        default_route_device="$1"
        debug "Setting default route on device $default_route_device"
        shift
        ;;
      *)
        fatal "Unknown option \"$key\""
        break
        ;;
    esac
  done

  # Dump the result of parsing
  debug "command=$command"
  debug "device_name=$device_name"
  debug "bond_name=$bond_name"
  debug "ip=$ip"
  debug "ip_passed=$ip_passed"
  debug "prefix=$prefix"
  debug "gateway=$gateway"
  debug "dns=$dns"
  debug "dns_passed=$dns_passed"
  debug "mode=$mode"
  debug "promisc=$promisc"
  debug "slave_names: ${slave_names[@]}"
  debug "default_route: $default_route_device"
  debug "LOG_LEVEL: $LOG_LEVEL"
}

usage() {
  cat << EOF

Usage:
  bond.sh [command] [options]

Valid commands are:
  -ab|--add-bond <bond_name>
  -ub|--update-bond <bond_name>
  -rb|--remove-bond <bond_name>
  -av|--add-vlan <vlan_name>
  -uv|--update-vlan <vlan_name>
  -rv|--remove-vlan <vlan_name>
  -ud|--update-device <device_name>
  -dr|--default_route <device_name>
Valid options are:
  -h|--help
  [-i|--ip [<ip>|dhcp]]
  [-p|--prefix <prefix>]|[-n|--netmask <netmask>]
  [-pr|--promisc yes|no] 
  [-g|--gateway <gateway>]
  [-d|--dns <dns>]
  [-m|--mode balance-rr|active-backup|balance-xor|broadcast|802.3ad|balance-tlb|balance-alb]
    defaults to balance-tlb
  -s|--slaves <slave1>,<slave2>,...
  [-l|--log_level fatal|error|warn|info|debug]
    defaults to info

EOF
}

add_or_edit_key() {
  local file=$1
  local key=$2
  local value=$3

  if grep -q "^${key}=$value\$" $file; then
    debug "  Ignoring in ${file}: ${key}=${value}"
  elif grep -q "^${key}=" $file; then
    info "  Modifying ${file}: ${key}=${value}"
    sed -i "s/^${key}=.*/${key}=${value}/" $file
  else
    info "  Adding to ${file}:    ${key}=${value}"
    echo "${key}=${value}" >> $file
  fi
}

edit_key() {
  local file=$1
  local key=$2
  local value=$3

  if grep -q "^${key}=$value\$" $file; then
    debug "  Ignoring ${file}: ${key}=${value}"
  elif grep -q "^${key}=" $file; then
    info "  Modifying ${file}: ${key}=${value}"
    sed -i "s/^${key}=.*/${key}=${value}/" $file
  fi
}

remove_key() {
  local file=$1
  local key=$2
  local quiet=$3

  if grep -q "^${key}=" $file; then
    info "  Removing: ${key}=*"
    sed -i "/^${key}=.*/d" $file
  else
    [ $quiet ] || warn "  Key \"${key}\" does not exist"
  fi
}

get_key() {
  local file=$1
  local key=$2

  grep "^${key}=" $file | awk -F= '{print $2}'
}

has_key() {
  local file=$1
  local key=$2

  grep -q "^${key}=" $file
}

get_device_name() {
  local file=$1
  local device_name=$(get_key $file DEVICE)

  # If there was no DEVICE directive, then fall back to whatever is
  # in the NAME directive.  This is to make it work on RHEL 7
  [ $device_name ] || device_name=$(get_key $file NAME)

  echo $device_name
}

array_contains() {
  local value="$1"
  local -a array=${@:2}

  for element in ${array[@]}; do
    [ "$element" = "$value" ] && return 0
  done

  return 1
}

backup() {
  local file=$1
  local base_file=$(basename $file)

  local backup_dir=~/ifcfg-backup
  [ -d $backup_dir ] || mkdir $backup_dir

  info "Backing up $file to $backup_dir/$base_file"
  cp $file $backup_dir/$base_file
}

get_config_file_by_directive() {
  local directive=$1
  local value=$2

  for test_config_file in $NETWORK_CONFIG_DIR/*; do
    if grep -q "^$directive=$value\$" $test_config_file; then
      echo $test_config_file
      return
    fi
  done
}

get_config_file_by_device() {
  local device_name=$1
  local default_config_file=$2

  # Look for a file that references the device using the DEVICE directive
  local config_file=$(get_config_file_by_directive DEVICE $device_name)
  [ $config_file ] && echo $config_file && return

  # Look for a file that references the device using the NAME directive
  config_file=$(get_config_file_by_directive NAME $device_name)
  [ $config_file ] && echo $config_file && return

  # No file found so return the default file name
  echo $default_config_file
}

is_vlan_config() {
  local config_file=$1

  if ! grep -q "^VLAN=yes\$" $config_file; then
    debug "Config file $config_file does not specify a VLAN configuration"
    return 1
  fi
  debug "Config file $config_file specifies a VLAN configuration"
  return 0
}

down_interface() {
  local if_type=$1
  local if_name=$2

  case $if_type in
    bond)
      info "Shutting down bond $if_name"
      local slaves_file=/sys/class/net/$if_name/bonding/slaves
      if [ -f $slaves_file ]; then
        slave_ifs=$(cat $slaves_file)
        for device in $slave_ifs; do
          echo "-$device" > $slaves_file;
        done
      fi

      #[ -e /sys/class/net/bonding_masters ] && ( ip link delete $if_name )
      local masters_file=/sys/class/net/bonding_masters
      [ -e "$masters_file" ] && echo "-$if_name" > $masters_file
      ifdown $if_name
      rmmod bonding
      ;;
    device)
      info "Shutting down $if_type $if_name"
      ifdown $if_name
      ;;
    vlan)
      info "Shutting down $if_type $if_name"
      ifdown $if_name
      ;;
    *)
      fatal "Error: $if_type passed to down_interface() when only bond, vlan and device are supported"
      ;;
  esac
}

get_bond_config_file() {
  bond_config_file=$(get_config_file_by_device "$bond_name" "${NETWORK_CONFIG_DIR}/ifcfg-${bond_name}")

  # Do not check for contents of a file that does not exist
  if [ ! -f $bond_config_file ]; then
     debug "bond_config_file=$bond_config_file"
     return
  fi

  # A base bond configuration file should not specify a VLAN configuration
  if is_vlan_config $bond_config_file; then 
    fatal "Error: The config file $bond_config_file specifies a VLAN configuration"
  fi
  
  debug "bond_config_file=$bond_config_file"
}

get_vlan_config_file() {
  vlan_config_file=$(get_config_file_by_device "$vlan_name" "${NETWORK_CONFIG_DIR}/ifcfg-${vlan_name}")

  # If the file does not exist then do not check for VLAN config - it will fail!
  if [ ! -f $vlan_config_file ]; then
    debug "vlan_config_file=$vlan_config_file"
    return
  fi

  # Error out if an interface name given as a VLAN  does not specify the VLAN
  # configuration
  if ! is_vlan_config $vlan_config_file; then 
     fatal "Error: Config file $vlan_config_file does not specify a VLAN configuration"
  fi

  debug "vlan_config_file=$vlan_config_file"
}

get_slave_config_files() {
  declare -a slave_config_files

  # Slaves can reference the master bond by either bond name or UUID, so...
  # Get the UUID from the bond configuration file
  local bond_uuid=$(get_key $bond_config_file UUID)
  debug "bond_uuid=$bond_uuid"

  local pattern="^MASTER=${bond_name}\$"
  [ "$bond_uuid" ] && pattern="$pattern\|^MASTER=${bond_uuid}\$"
  debug "pattern=\"$pattern\""

  # Find all the slave files that reference the bond by name or UUID
  for slave_config_file in $NETWORK_CONFIG_DIR/*; do
    debug "Checking slave_config_file $slave_config_file"

    # If the slave config file contains a MASTER directive set to either the
    # bond name or UUID, then it's a slave of the given bond
    if grep -q "$pattern" $slave_config_file; then
      debug "slave_config_file $slave_config_file matches"
      slave_config_files=(${slave_config_files[@]} $slave_config_file)
    else
      debug "slave_config_file $slave_config_file does not match"
    fi
  done

  debug "Found slave_config_files ${slave_config_files[@]}"

  echo ${slave_config_files[@]}
}

get_vlans_by_bond() {
  local bond_name=$1
  local vlan_names=""

  for test_config_file in $NETWORK_CONFIG_DIR/*; do
    if grep -q "^DEVICE=$bond_name\.\|^NAME=$bond_name\." $test_config_file; then
      local vlan_name=$(get_device_name $test_config_file)
      vlan_names="$vlan_names\n\t${vlan_name}: $test_config_file"
    fi
  done

  echo $vlan_names
}

add_slave() {
  local slave_name=$1
  local slave_config_file=$(get_config_file_by_device "$slave_name" "${NETWORK_CONFIG_DIR}/ifcfg-${slave_name}")

  info "Adding slave $slave_name"

  # If the slave config file exists, then update it
  if [ -f "$slave_config_file" ]; then
    backup "$slave_config_file"

    info "Editing slave configuration file $slave_config_file"
    add_or_edit_key "$slave_config_file" NAME "$slave_name"
    add_or_edit_key "$slave_config_file" DEVICE "$slave_name"
    add_or_edit_key "$slave_config_file" NM_CONTROLLED no
    add_or_edit_key "$slave_config_file" ONBOOT yes
    add_or_edit_key "$slave_config_file" BOOTPROTO none
    add_or_edit_key "$slave_config_file" MASTER "$bond_name"
    add_or_edit_key "$slave_config_file" SLAVE yes

    # The network service will fail to start if a slave has an IP, so
    # remove it
    remove_key "$slave_config_file" IPADDR quiet
    remove_key "$slave_config_file" PREFIX quiet
    remove_key "$slave_config_file" NETMASK quiet
  else
    # The slave config file does not exist, so create it
    info "Creating slave configuration file $slave_config_file"
    cat > $slave_config_file << EOF
NAME=$slave_name
DEVICE=$slave_name
TYPE=Ethernet
NM_CONTROLLED=no
ONBOOT=yes
BOOTPROTO=none
MASTER=$bond_name
SLAVE=yes
EOF
  fi

  # If HWADDR is not specified, then populate it if possible
  local mac=$(get_key $slave_config_file HWADDR)
  if [ ! "$mac" ]; then
    mac_file="/sys/class/net/$slave_name/address"
    if [ -f "$mac_file" ]; then
      mac=$(cat $mac_file)
      mac=${mac^^}
      add_or_edit_key "$slave_config_file" HWADDR "$mac"
    else
      warn "Unable to populate HWADDR for $slave_name because $mac_file does not exist"
    fi
  fi

  # If UUID is not specified, then populate it
  local uuid=$(get_key $slave_config_file UUID)
  if [ ! "$uuid" ]; then
    uuid=$(uuidgen $slave_name)
    add_or_edit_key "$slave_config_file" UUID "$uuid"
  fi
}

remove_slave_by_config_file() {
  local slave_config_file=$1

  info "Removing slave $(get_device_name $slave_config_file)"

  backup $slave_config_file
  info "Editing slave configuration file $slave_config_file"
  remove_key $slave_config_file MASTER
  remove_key $slave_config_file SLAVE
}

parse_vlan_name() {
  bond_name=$(echo "$vlan_name" | awk -F. '{print $1}')
  local vlan_tag=$(echo "$vlan_name" | awk -F. '{print $2}')

  [ "$bond_name" ] && [ "$vlan_tag" ] || fatal "The vlan name must be of the format: <bond_name>.<vlan_tag>"
}

validate_ip_settings() {
  [ "$prefix" ] && [ "$netmask" ] && fatal "Either prefix or netmask may be specified, but not both"

  if [ "$ip" = "dhcp" ]; then
    [ "$prefix" ] || [ "$netmask" ] && fatal "Neither prefix nor netmask may be specified when using dhcp"
  else
    [ "$ip" ] && [ -z $prefix ] && [ -z $netmask ] && fatal "If IP is specified then prefix or netmask must be too"
    [ $prefix ] || [ $netmask ] && [ -z $ip ] && fatal "If prefix or netmask is specified then IP must be too"
  fi
}

convert_directive0() {
  local config_file=$1
  local directive=$2

  if has_key "$config_file" "$directive"; then
    local value=$(get_key "$config_file" "$directive")

    local short_directive=${directive%0}
    info "Converting $directive=$value to $short_directive=$value"

    remove_key "$config_file" $directive
    add_or_edit_key "$config_file" "$short_directive" "$value"
  fi
}

update_promisc() {
  local config_file="$1"
  case "$promisc" in 
    "yes")
      add_or_edit_key "$config_file" PROMISC yes
      ;;
    "no")
      remove_key "$config_file" PROMISC quiet
      ;;
    *)
      fatal "Unknown selector for promiscous mode setting: $promisc. Should be 'yes' or 'no'"
      break
      ;;
  esac
}

handle_ip_settings() {
  local operation="$1"
  local config_file="$2"

  if [ "$ip_passed" ] || [ "$netmask" ] || [ "$prefix" ] || [ "$gateway" ]; then
    # Convert existing values from 0 suffix to normal
    convert_directive0 "$config_file" IPADDR0
    convert_directive0 "$config_file" NETMASK0
    convert_directive0 "$config_file" PREFIX0
    convert_directive0 "$config_file" GATEWAY0
  fi

  # Disable IPV6 on device by default 
  edit_key "$config_file" IPV6_AUTOCONF no
  edit_key "$config_file" IPV6INIT no

  # Pick up the case where the user entered '-i ""'
  if [ "$operation" = "update" ] && [ "$ip_passed" = "true" ] && ([ ! "$ip" ] || [ "$ip" = "dhcp" ]); then
      remove_key "$config_file" IPADDR quiet
      [ "$prefix" ] && warn "Ignoring prefix of $prefix because IP was specified as empty"
      remove_key "$config_file" PREFIX quiet
      [ "$netmask" ] && warn "Ignoring netmask of $netmask because IP was specified as empty"
      remove_key "$config_file" NETMASK quiet
  fi
  if [ "$ip" = "dhcp" ]; then
    add_or_edit_key "$config_file" BOOTPROTO dhcp
  else
    add_or_edit_key "$config_file" BOOTPROTO none

    [ "$ip" ] && add_or_edit_key "$config_file" IPADDR "$ip"
  fi
  if [ "$netmask" ]; then
    remove_key "$config_file" PREFIX quiet
    add_or_edit_key "$config_file" NETMASK "$netmask"
  fi
  if [ "$prefix" ]; then
    remove_key "$config_file" NETMASK quiet
    add_or_edit_key "$config_file" PREFIX "$prefix"
  fi
  [ "$gateway" ] && add_or_edit_key "$config_file" GATEWAY "$gateway"
  if [ "$dns_passed" = "true" ] && [ ! "$dns" ]; then
      remove_key "$config_file" DNS1 quiet
  else
    [ "$dns" ] && add_or_edit_key "$config_file" DNS1 "$dns"
  fi
}

add_bond() {
  # When adding a bond, default bonding mode if it is not specified
  [ "$mode" ] || mode=$DEFAULT_MODE

  [ "$bond_name" ] || fatal "Bond name must be supplied"
  [ "${slave_names[0]}" ] || fatal "Slave list must be supplied"

  validate_ip_settings

  get_bond_config_file
  [ -f "$bond_config_file" ] && fatal "Bond $bond_name already exists: $bond_config_file"

  # As a safeguard, disable automatic creation of bond0 when bonding kernel
  # module is loaded
  echo "options bonding max_bonds=0" > /etc/modprobe.d/10-bonding.conf

  info "Creating bond configuration file $bond_config_file"

  # Create the bond config file
  cat > $bond_config_file << EOF
NAME=$bond_name
DEVICE=$bond_name
TYPE=Bond
NM_CONTROLLED=no
ONBOOT=yes
BONDING_OPTS="$BONDING_OPTS mode=$mode"
BONDING_MASTER=yes
DEFROUTE=no
EOF

  [[ $promisc ]] && update_promisc "$bond_config_file"
  handle_ip_settings add "$bond_config_file"

  # Create or edit the slave config files
  for slave_name in ${slave_names[@]}; do
    add_slave "$slave_name"
  done
}

add_vlan() {
  [ "$vlan_name" ] || fatal "Vlan name must be supplied"

  parse_vlan_name
  validate_ip_settings

  get_vlan_config_file
  [ -f "$vlan_config_file" ] && fatal "Vlan $vlan_name already exists: $vlan_config_file"

  info "Creating vlan configuration file $vlan_config_file"

  # Create the bond config file
  cat > $vlan_config_file << EOF
NAME=$vlan_name
DEVICE=$vlan_name
TYPE=Ethernet
NM_CONTROLLED=no
ONBOOT=yes
VLAN=yes
EOF

  [[ $promisc ]] && update_promisc "$vlan_config_file"
  handle_ip_settings add "$vlan_config_file"
}

update_device() {
  [ "$device_name" ] || fatal "Device name must be supplied"

  device_config_file="${NETWORK_CONFIG_DIR}/ifcfg-${device_name}"
  [ -f $device_config_file ] || fatal "Device $device_name does not exist"

  [ "$prefix" ] && [ "$netmask" ] && fatal "Either prefix or netmask may be specified, but not both"

  needs_device_update=false
  if ! grep -q "^DEVICE=$device_name\$" "$device_config_file"; then
    needs_device_update=true
  fi

  if [ $needs_device_update -o "$dns_passed" -o "$dns" -o "$gateway" -o "$ip" -o "$ip_passed" -o "$mode" -o "$netmask" -o "$prefix" ]; then
    backup $device_config_file

    down_interface device $device_name
    info "Updating device configuration file $device_config_file"

    if [ $needs_device_update ]; then
      add_or_edit_key "$device_config_file" DEVICE "$device_name"
    fi

    add_or_edit_key "$device_config_file" NM_CONTROLLED no
    add_or_edit_key "$device_config_file" ONBOOT yes
    [[ $promisc ]] && update_promisc "$device_config_file"
    handle_ip_settings update "$device_config_file"

  fi
}

update_bond() {
  [ "$bond_name" ] || fatal "Bond name must be supplied"

  get_bond_config_file
  [ -f $bond_config_file ] || fatal "Bond $bond_name does not exist"

  [ "$prefix" ] && [ "$netmask" ] && fatal "Either prefix or netmask may be specified, but not both"

  needs_device_update=false
  if ! grep -q "^DEVICE=$bond_name\$" "$bond_config_file"; then
    needs_device_update=true
  fi

  if [ $needs_device_update -o "$dns_passed" -o "$dns" -o "$gateway" -o "$ip" -o "$ip_passed" -o "$mode" -o "$netmask" -o "$prefix" -o "$bonding_opts_passed" = "true" ]; then
    backup $bond_config_file

    down_interface bond $bond_name
    info "Updating bond configuration file $bond_config_file"

    if [ $needs_device_update ]; then
      add_or_edit_key "$bond_config_file" DEVICE "$bond_name"
    fi

    [[ $promisc ]] && update_promisc "$bond_config_file"
    handle_ip_settings update "$bond_config_file"

    if [ "$mode" -o "$bonding_opts_passed" = "true" ]; then
      [ "$mode" ] || mode=$DEFAULT_MODE
      add_or_edit_key "$bond_config_file" BONDING_OPTS "\"$BONDING_OPTS mode=$mode\""
    fi
  fi

  if [ "${slave_names[0]}" ]; then
    # Get the slave config files for the given bond
    local -a slave_config_files=($(get_slave_config_files))

    # The slave config file names could be completely different from the slave
    # names, so build up an associative array that maps the slave name to the
    # slave config file
    local -A current_slaves
    for slave_config_file in ${slave_config_files[@]}; do
      current_slaves[$(get_device_name $slave_config_file)]="$slave_config_file"
    done

    debug "current_slaves:"
    for a_slave in "${!current_slaves[@]}"; do
      debug "$a_slave=>${current_slaves[$a_slave]}"
    done
    debug "proposed slave_names=${slave_names[@]}"

    # Add any new slaves
    for slave_name in ${slave_names[@]}; do
      if ! $(array_contains "$slave_name" ${!current_slaves[@]}); then
        add_slave $slave_name
      fi
    done

    # Remove any old slaves
    for current_slave in ${!current_slaves[@]}; do
      if ! $(array_contains "$current_slave" ${slave_names[@]}); then
        remove_slave_by_config_file "${current_slaves[$current_slave]}"
      fi
    done
  fi
}

update_vlan() {
  [ "$vlan_name" ] || fatal "Vlan name must be supplied"

  parse_vlan_name

  get_vlan_config_file
  [ -f "$vlan_config_file" ] || fatal "Vlan $vlan_name does not exist"

  [ "$prefix" ] && [ "$netmask" ] && fatal "Either prefix or netmask may be specified, but not both"

  backup $vlan_config_file

  down_interface vlan $vlan_name
  info "Updating vlan configuration file $vlan_config_file"

  [[ $promisc ]] && update_promisc "$vlan_config_file"
  handle_ip_settings update "$vlan_config_file"
}

remove_bond() {
  [ "$bond_name" ] || fatal "Bond name must be supplied"

  get_bond_config_file
  [ -f $bond_config_file ] || fatal "Bond $bond_name does not exist"

  # Check to see if there are any vlan subinterfaces that are using this bond
  local vlan_names=$(get_vlans_by_bond $bond_name)

  [ "$vlan_names" ] && fatal "The following vlan subinterfaces are using $bond_name: ${vlan_names}\n\nIf you still want to remove this bond, then remove the subinterfaces first using the -rv option."

  # Get the slave config files for the given bond
  local -a slave_config_files=($(get_slave_config_files))

  down_interface bond $bond_name
  # Remove the bond config file
  backup $bond_config_file
  info "Removing bond configuration file $bond_config_file"
  rm -f $bond_config_file

  # Remove the MASTER and SLAVE directives from the slave config files
  for slave_config_file in ${slave_config_files[@]}; do
    remove_slave_by_config_file "$slave_config_file"
  done
}

remove_vlan() {
  [ "$vlan_name" ] || fatal "Vlan name must be supplied"

  parse_vlan_name

  get_vlan_config_file
  [ -f "$vlan_config_file" ] || fatal "Vlan $vlan_name does not exist"

  backup $vlan_config_file
  down_interface vlan $vlan_name
  info "Removing vlan configuration file $vlan_config_file"
  rm -f "$vlan_config_file"
}

set_default_route() {
  [ "$default_route_device" ] || fatal "Default route device must be supplied"

  local device_config_file="${NETWORK_CONFIG_DIR}/ifcfg-${default_route_device}"
  [ -f "$device_config_file" ] || fatal "Default device configuration file does not exist: ${device_config_file}"

  local master=$(get_key $device_config_file MASTER)
  [ $master ] && fatal "$default_route_device is part of bond/vlan $master"
  (has_key ${device_config_file} IPADDR && \
   (has_key ${device_config_file} NETMASK || \
    has_key ${device_config_file} PREFIX) && \
   has_key ${device_config_file} GATEWAY) \
     || fatal "Default route device configuration must specify an IP address, a netmask or prefix, and a gateway"

  # set DEFROUTE, IPV6INIT, AND IPV6_AUTOCONF TO "no" in ALL CONFIG FILES
  for file in ${NETWORK_CONFIG_DIR}/ifcfg-*; do
    edit_key "$file" DEFROUTE no
    edit_key "$file" IPV6INIT no
    edit_key "$file" IPV6_AUTOCONF no
  done

  # set DEFROUTE=yes in default route device config file
  echo "setting default route to $default_route_device"
  add_or_edit_key "${device_config_file}" DEFROUTE yes
}

# Parse the incoming arguments
parse_args "$@"

# Use the bonding opts in the environment if specified, otherwise default to
# minimal opts (miimon is needed for failover)
if [ "$BONDING_OPTS" ]; then
  bonding_opts_passed=true
else
  bonding_opts_passed=false
  BONDING_OPTS="miimon=100"
fi
debug "BONDING_OPTS=$BONDING_OPTS"

case "$command" in
  $ADD_BOND)
    add_bond
    ;;
  $ADD_VLAN)
    add_vlan
    ;;
  $UPDATE_DEVICE)
    update_device
    ;;
  $UPDATE_BOND)
    update_bond
    ;;
  $UPDATE_VLAN)
    update_vlan
    ;;
  $REMOVE_BOND)
    remove_bond
    ;;
  $REMOVE_VLAN)
    remove_vlan
    ;;
  $DEFAULT_ROUTE)
    set_default_route
    ;;
  *)
    fatal "Unknown command.  One of -ab, -av, -ud, -ub, -uv, -rb, -rv, -dr must be specified"
    break
    ;;
esac
