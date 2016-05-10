#!/bin/bash

# (c) 2016 Dell
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

cd /tmp

# Obtain and install the Extra Packages for Enterprise Linux (EPEL) repository.
# That repo contains the python-pip package, which is required by this script.
wget https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
sudo yum -y install ./epel-release-latest-7.noarch.rpm

# Ensure that packages that are offered by both EPEL and a Red Hat Enterprise
# Linux (RHEL) repository are obtained from the RHEL repo.  This is accomplished
# by setting the priority of the EPEL repository to be a greater value than the
# priorities of the RHEL repositories.
sudo yum-config-manager --enable epel --setopt="epel.priority=2"

# Install the python-pip package.
sudo yum install -y python-pip

cd ~/pilot/probe_idrac

# Install the Python packages on which probe_idrac depends.
sudo pip install -r ./requirements.txt

# Create a pip installable package in tarball format.
export PBR_VERSION=0.0.1
python ./setup.py sdist

# Copy the tarball to /tmp.
cp -p dist/probe-idrac-${PBR_VERSION}.tar.gz /tmp

cd /tmp

# Install the probe_idrac Python package.
sudo pip install ./probe-idrac-${PBR_VERSION}.tar.gz
sudo yum -y remove python-pip epel-release
