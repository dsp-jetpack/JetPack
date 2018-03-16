# Copyright (c) 2018 Dell Inc. or its subsidiaries.
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

#class: dellnfv::hugepages
#
# Configure Dell NFV Hugepages feature on Dell-NFV nodes via composable services.
#

class dellnfv::hugepages (
        $step = hiera('step'),
        $state = hiera('dellnfv::hugepages::enable'),
        $hpg_size = hiera('dellnfv::hugepages::hugepagesize'),
        $hpg_number = hiera('dellnfv::hugepages::hugepagecount')

) {
  if ($step >= 4){
    if ($state == true) {

        #update the kernel using hugepages details, hugepage default size is equal to hugepage size
        exec {'update_kernel_hugepages':
                path => ['/bin/', '/sbin/', '/usr/bin/', '/usr/sbin/'],
                command => "sudo grubby --update-kernel=ALL --args=\"default_hugepagesz=$hpg_size hugepagesz=$hpg_size hugepages=$hpg_number\"",
        }

    }
  }
}
