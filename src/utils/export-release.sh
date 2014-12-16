#!/bin/bash

if [ ! -d releases ]; then
  echo "Not in repo directory?" ; exit 
fi

if [ -z "$1" ]; then
  echo "Usage: export-release.sh <version> [<directory>]"
  exit
else
  if [ ! $(echo "$1" | grep -e "^[0-9]\+\(\.[0-9]\+\)\{1,2\}$") ]; then
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
            mkdir -p ${dest}/${target_dir}/vlock_files
	    cp data/vlock_files/$src_dir ${dest}/${target_dir}/vlock_files
        else
	    cp src/${src_dir}/* ${dest}/${target_dir}
        fi
    done
    (cd $dest; sha256sum ${target_dir}/* ${target_dir}/vlock_files/* >${target_dir}/CHECKSUMS.sha256)
    (cd $dest; tar zcvf ${target_dir}.tgz ${target_dir}/*; zip -r ${target_dir} ${target_dir})
    rm -rf ${dest}/${target_dir}
}

echo "Copying PDF's"
cp doc/*.pdf $dest

echo "Copying hardware configuration spreadsheets"
cp doc/*.xlsx $dest

# checksum the base directory files
(cd $dest; sha256sum * > CHECKSUMS.sha256)

# make bundles
mk_bundle dell-mgmt-node    mgmt         ceph_vm.vlock foreman_vm.vlock
mk_bundle dell-pilot-deploy pilot common controller.vlock compute.vlock ceph.vlock
mk_bundle dell-poc-deploy   poc common   controller.vlock compute.vlock

echo "Done! - release bundles and files are in ${dest}."
echo "  Use 'sha256sum -c <checksums_file>' to verify."
