#!/bin/bash
#
# OpenStack - A set of software tools for building and managing cloud computing
# platforms for public and private clouds.
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

if [ ! -d releases ]; then
  echo "Not in repo directory?" ; exit 
fi

if [ -z "$1" ]; then
  echo "Usage: export-release.sh <version> [<directory>]"
  exit
else
  if [ ! $(echo "$1" | grep -e "^[0-9]\+\(\.[0-9]\+\)\{1,3\}$") ]; then
    echo \"$1\" is not a legal release number
    exit 1 
  fi
  dest="releases/jetstream-${1}"
  [[ $2 ]] && dest=${2}/${dest}
fi
mkdir -p $dest; rm -rf ${dest}/*

mk_bundle() {
    local target_dir="$1"; shift
    local src_dirs="$@"

    echo "Creating $target_dir node bundles"
    mkdir -p ${dest}/${target_dir}
    for src_dir in ${src_dirs}; do
	if [[ $src_dir =~ "vlock" ]]; then
	    cp data/vlock_files/$src_dir ${dest}/${target_dir}
        else
	    cp src/${src_dir}/* ${dest}/${target_dir}
        fi
    done
    (cd $dest; sha256sum ${target_dir}/* >${target_dir}/CHECKSUMS.sha256)
    (cd $dest/${target_dir}; tar zcvf $dest/${target_dir}.tgz ./*; zip -r $dest/${target_dir} .)
    (cd $dest; rm -rf ${dest}/${target_dir})
}

echo "Copying PDF's"
cp doc/*.pdf $dest

echo "Copying hardware configuration spreadsheets"
cp doc/*.xlsx $dest

# checksum the base directory files
(cd $dest; sha256sum * > CHECKSUMS.sha256)

# make bundles
mk_bundle dell-mgmt-node    mgmt         ceph_vm.vlock foreman_vm.vlock
mk_bundle dell-pilot-deploy pilot common controller.vlock compute.vlock ceph.vlock utils/networking

echo "Done! - release bundles and files are in ${dest}."
echo "  Use 'sha256sum -c <checksums_file>' to verify."