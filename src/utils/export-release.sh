#!/bin/bash

checksum_file=CHECKSUMS.sha256

if [ -z "$1" ]; then
  echo "Usage: export-release.sh <version> [<directory>]"
  exit
fi

dir=$(pwd)
if [ ! -d $dir/data -o ! -d $dir/doc -o ! -d $dir/src ];
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
  dest="${2}/releases/jetstream-${1}"
else
  dest="$(pwd)/releases/jetstream-${1}"
fi

rm -rf ${dest}
mkdir -p $dest

mk_bundle() {
  local archive_name=$1
  shift
  local src_dirs="$@"

  local target_root_dir="$dest/stage"
  local target_dir="$target_root_dir/pilot"

  echo "Creating $(echo $src_dirs|awk '{print $2}') node bundles"
  mkdir -p ${target_dir}
  for src_dir in ${src_dirs}; do
  if [[ $src_dir =~ "vlock" ]]; then
    cp data/vlock_files/$src_dir ${target_dir}
  else
    cp -r src/${src_dir}/* ${target_dir}
  fi
  done
  (cd $target_dir; sha256sum * >${target_dir}/${checksum_file})
  (cd $target_root_dir; tar zcvf $dest/${archive_name}.tgz pilot; zip -r $dest/${archive_name} pilot)
  rm -rf ${target_root_dir}
}

echo "Copying PDF's"
cp doc/*.pdf $dest

echo "Copying hardware configuration spreadsheets"
cp doc/*.xlsx $dest

# checksum the base directory files
(cd $dest; sha256sum * > ${checksum_file})

# make bundles
mk_bundle dell-mgmt-node mgmt ceph_vm.vlock director_vm.vlock
mk_bundle dell-pilot-deploy pilot common controller.vlock compute.vlock ceph.vlock utils/networking

echo "Done! - release bundles and files are in ${dest}."
echo "  Use 'sha256sum -c ${checksum_file}' to verify."
