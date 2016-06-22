#!/usr/bin/python

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

import argparse
import distutils.dir_util
import distutils.file_util
import os
import re
import subprocess
import sys
import time

home_dir = os.path.expanduser('~')

def subst_bkup (relative_path):
  in_file_name = os.path.join(home_dir, relative_path)
  os.rename (in_file_name, in_file_name + '.mido.bak')
 
subst_bkup('pilot/templates/nic-configs/compute.yaml')
subst_bkup('pilot/templates/nic-configs/controller.yaml')
subst_bkup('pilot/templates/nic-configs/ceph-storage.yaml')
subst_bkup ('pilot/templastes/network-environment.yaml')
subst_bkup('pilot/deploy-overcloud.py')
#copy midonet files into the right dir
nic_dir = os.path.join(home_dir, 'pilot/templates/nic-configs')
pilot_dir = os.path.join(home_dir,'pilot')
templates_dir = os.path.join (hume_dir,'pilot/templates')
distutils.dir_util.copy_tree('./templates/nic-configs', nic_dir)
distutils.file_util.copy_file('./deploy-overcloud.py',pilot_dir)
distutils.file_util.copy_file('./templates/network_environment.yaml',templates_dir)
