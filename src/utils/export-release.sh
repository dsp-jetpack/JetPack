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

checksum_file=CHECKSUMS.sha256

if [ -z "$1" ]; then
  echo "Usage: export-release.sh <version> [<directory>]"
  exit
fi

dir=$(pwd)
if [ ! -d $dir/data -o ! -d $dir/src ];
then
  echo "This script must be run from the root directory of the cloud_repo"
  exit 1
fi

if [ ! $(echo "$1" | grep -e "^[0-9]\+\(\.[0-9]\+\)\{1,3\}$") ];
then
  echo \"$1\" is not a legal release number
  exit 1 
fi

if [ -n "$2" ];
then
  dest="${2}/releases/jetpack-${1}"
else
  dest="$(pwd)/releases/jetpack-${1}"
fi

rm -rf ${dest}
mkdir -p $dest

mk_bundle() {
  local archive_name=$1
  local root_dir=$2
  shift
  shift
  first_dir=$1
  local src_dirs="$@"

  local target_root_dir="$dest/stage"
  local target_dir="$target_root_dir/$root_dir"

  echo "Creating $root_dir bundle"
  mkdir -p ${target_dir}
  cp LICENSE ${target_dir}
  for src_dir in ${src_dirs}; do
    if [[ $src_dir =~ "vlock" ]]; then
      cp data/vlock_files/$src_dir ${target_dir}/${first_dir}
    else
      cp -r src/${src_dir} ${target_dir}
    fi
  done
  (cd $target_dir; sha256sum $(find . -type f -print) >${target_dir}/${checksum_file})
  (cd $target_dir; tar zcvf $dest/${archive_name}.tgz $src_dirs LICENSE ${checksum_file}; zip -r $dest/${archive_name} $src_dirs LICENSE ${checksum_file})
  rm -rf ${target_root_dir}
}


# make bundles
# mk_bundle <tar-file-name> <tar-root-dir-name> <src-dirs> <vlock-files>
mk_bundle dell-mgmt-node sah mgmt rhscon_vm.vlock director_vm.vlock
mk_bundle dell-pilot manual pilot common
mk_bundle dell-deploy automated deploy common

# checksum the base directory files
(cd $dest; sha256sum * > ${checksum_file})

echo "Done! - release bundles and files are in ${dest}."
echo "  Use 'sha256sum -c ${checksum_file}' to verify."
