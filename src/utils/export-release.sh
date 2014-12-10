#!/bin/bash

mkdir -p /tmp/jetstream-release; rm -rf /tmp/jetstream-release/*
dest=/tmp/jetstream-release

if [ ! -d releases ]; then
  echo "Not in repo directory?" ; exit 
fi

mk_bundle() {
    local target_dir="$1"; shift
    local src_dirs="$@"

    echo "Creating $target_dir node bundles"
    mkdir -p /tmp/jetstream-release/${target_dir}
    for src_dir in ${src_dirs}; do
	if [[ $src_dir =~ "versionlock" ]]; then
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
mk_bundle dell-mgmt-node    mgmt         versionlock.list_cephvm versionlock.list_foreman
mk_bundle dell-pilot-deploy pilot common versionlock.list_cntl versionlock.list_nova
mk_bundle dell-poc-deploy   poc common   versionlock.list_cntl versionlock.list_nova

echo "Done! - release bundles and files are in /tmp/jetstream-release directory. Use 'sha256sum -c <checksums_file>' to verify"