#!/usr/bin/python

# Copyright (c) 2018-2019 Dell Inc. or its subsidiaries.
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


# It is a dictionary of the form {'total number of cpu cores' :
# {'number_of_host_os_cpu' : {
# 'mode2_rem_cores': 'Remaining cores after removing mode2_pmd_cores',
# 'mode1_rem_cores': 'Remaining cores after removing mode1_pmd_cores',
# 'vcpu_pin_set' : 'Range of corresponding CPUs available for nova',
# 'mode1_pmd_cores': 'Range of corresponding CPUs for pmd in Mode 1',
# 'mode2_pmd_cores': 'Range of corresponding CPUs for pmd in Mode 2',
# 'host_os_cpu' : 'Range of corresponding CPUSs available for Host OS'
# } } }
# If 'total number of cpu cores' = 48 & 'number_of_host_os_cpu' = 4
# you can get 'vcpu_pin_set' by using sibling_info[48][4]['vcpu_pin_set']


sibling_info = {
    128: {
        8: {
            'mode2_rem_cores': '5-63,69-127',
            'mode1_rem_cores': '6-63,70-127',
            'vcpu_pin_set': '4-63,68-127',
            'mode1_pmd_cores': '4,5,68,69',
            'mode2_pmd_cores': '4,68',
            'host_os_cpu': '0-3,64-67'
        },
        2: {
            'mode2_rem_cores': '2-63,66-127',
            'mode1_rem_cores': '3-63,67-127',
            'vcpu_pin_set': '1-63,65-127',
            'mode1_pmd_cores': '1,2,65,66',
            'mode2_pmd_cores': '1,65',
            'host_os_cpu': '0,64'
        },
        4: {
            'mode2_rem_cores': '3-63,67-127',
            'mode1_rem_cores': '4-63,68-127',
            'vcpu_pin_set': '2-63,66-127',
            'mode1_pmd_cores': '2,3,66,67',
            'mode2_pmd_cores': '2,66',
            'host_os_cpu': '0-1,64-65'
        },
        6: {
            'mode2_rem_cores': '4-63,68-127',
            'mode1_rem_cores': '5-63,69-127',
            'vcpu_pin_set': '3-63,67-127',
            'mode1_pmd_cores': '3,4,67,68',
            'mode2_pmd_cores': '3,67',
            'host_os_cpu': '0-2,64-66'
        }
    },
    64: {
        8: {
            'mode2_rem_cores': '5-31,37-63',
            'mode1_rem_cores': '6-31,38-63',
            'vcpu_pin_set': '4-31,36-63',
            'mode1_pmd_cores': '4,5,36,37',
            'mode2_pmd_cores': '4,36',
            'host_os_cpu': '0-3,32-35'
        },
        2: {
            'mode2_rem_cores': '2-31,34-63',
            'mode1_rem_cores': '3-31,35-63',
            'vcpu_pin_set': '1-31,33-63',
            'mode1_pmd_cores': '1,2,33,34',
            'mode2_pmd_cores': '1,33',
            'host_os_cpu': '0,32'
        },
        4: {
            'mode2_rem_cores': '3-31,35-63',
            'mode1_rem_cores': '4-31,36-63',
            'vcpu_pin_set': '2-31,34-63',
            'mode1_pmd_cores': '2,3,34,35',
            'mode2_pmd_cores': '2,34',
            'host_os_cpu': '0-1,32-33'
        },
        6: {
            'mode2_rem_cores': '4-31,36-63',
            'mode1_rem_cores': '5-31,37-63',
            'vcpu_pin_set': '3-31,35-63',
            'mode1_pmd_cores': '3,4,35,36',
            'mode2_pmd_cores': '3,35',
            'host_os_cpu': '0-2,32-34'
        }
    },
    40: {
        8: {
            'mode2_rem_cores': '5-19,25-39',
            'mode1_rem_cores': '6-19,26-39',
            'vcpu_pin_set': '4-19,24-39',
            'mode1_pmd_cores': '4,5,24,25',
            'mode2_pmd_cores': '4,24',
            'host_os_cpu': '0-3,20-23'
        },
        2: {
            'mode2_rem_cores': '2-19,22-39',
            'mode1_rem_cores': '3-19,23-39',
            'vcpu_pin_set': '1-19,21-39',
            'mode1_pmd_cores': '1,2,21,22',
            'mode2_pmd_cores': '1,21',
            'host_os_cpu': '0,20'
        },
        4: {
            'mode2_rem_cores': '3-19,23-39',
            'mode1_rem_cores': '4-19,24-39',
            'vcpu_pin_set': '2-19,22-39',
            'mode1_pmd_cores': '2,3,22,23',
            'mode2_pmd_cores': '2,22',
            'host_os_cpu': '0-1,20-21'
        },
        6: {
            'mode2_rem_cores': '4-19,24-39',
            'mode1_rem_cores': '5-19,25-39',
            'vcpu_pin_set': '3-19,23-39',
            'mode1_pmd_cores': '3,4,23,24',
            'mode2_pmd_cores': '3,23',
            'host_os_cpu': '0-2,20-22'
        }
    },
    48: {
        8: {
            'mode2_rem_cores': '5-23,29-47',
            'mode1_rem_cores': '6-23,30-47',
            'vcpu_pin_set': '4-23,28-47',
            'mode1_pmd_cores': '4,5,28,29',
            'mode2_pmd_cores': '4,28',
            'host_os_cpu': '0-3,24-27'
        },
        2: {
            'mode2_rem_cores': '2-23,26-47',
            'mode1_rem_cores': '3-23,27-47',
            'vcpu_pin_set': '1-23,25-47',
            'mode1_pmd_cores': '1,2,25,26',
            'mode2_pmd_cores': '1,25',
            'host_os_cpu': '0,24'
        },
        4: {
            'mode2_rem_cores': '3-23,27-47',
            'mode1_rem_cores': '4-23,28-47',
            'vcpu_pin_set': '2-23,26-47',
            'mode1_pmd_cores': '2,3,26,27',
            'mode2_pmd_cores': '2,26',
            'host_os_cpu': '0-1,24-25'
        },
        6: {
            'mode2_rem_cores': '4-23,28-47',
            'mode1_rem_cores': '5-23,29-47',
            'vcpu_pin_set': '3-23,27-47',
            'mode1_pmd_cores': '3,4,27,28',
            'mode2_pmd_cores': '3,27',
            'host_os_cpu': '0-2,24-26'
        }
    },
    72: {
        8: {
            'mode2_rem_cores': '5-35,41-71',
            'mode1_rem_cores': '6-35,42-71',
            'vcpu_pin_set': '4-35,40-71',
            'mode1_pmd_cores': '4,5,40,41',
            'mode2_pmd_cores': '4,40',
            'host_os_cpu': '0-3,36-39'
        },
        2: {
            'mode2_rem_cores': '2-35,38-71',
            'mode1_rem_cores': '3-35,39-71',
            'vcpu_pin_set': '1-35,37-71',
            'mode1_pmd_cores': '1,2,37,38',
            'mode2_pmd_cores': '1,37',
            'host_os_cpu': '0,36'
        },
        4: {
            'mode2_rem_cores': '3-35,39-71',
            'mode1_rem_cores': '4-35,40-71',
            'vcpu_pin_set': '2-35,38-71',
            'mode1_pmd_cores': '2,3,38,39',
            'mode2_pmd_cores': '2,38',
            'host_os_cpu': '0-1,36-37'
        },
        6: {
            'mode2_rem_cores': '4-35,40-71',
            'mode1_rem_cores': '5-35,41-71',
            'vcpu_pin_set': '3-35,39-71',
            'mode1_pmd_cores': '3,4,39,40',
            'mode2_pmd_cores': '3,39',
            'host_os_cpu': '0-2,36-38'
        }
    },
    56: {
        8: {
            'mode2_rem_cores': '5-27,33-55',
            'mode1_rem_cores': '6-27,34-55',
            'vcpu_pin_set': '4-27,32-55',
            'mode1_pmd_cores': '4,5,32,33',
            'mode2_pmd_cores': '4,32',
            'host_os_cpu': '0-3,28-31'
        },
        2: {
            'mode2_rem_cores': '2-27,30-55',
            'mode1_rem_cores': '3-27,31-55',
            'vcpu_pin_set': '1-27,29-55',
            'mode1_pmd_cores': '1,2,29,30',
            'mode2_pmd_cores': '1,29',
            'host_os_cpu': '0,28'
        },
        4: {
            'mode2_rem_cores': '3-27,31-55',
            'mode1_rem_cores': '4-27,32-55',
            'vcpu_pin_set': '2-27,30-55',
            'mode1_pmd_cores': '2,3,30,31',
            'mode2_pmd_cores': '2,30',
            'host_os_cpu': '0-1,28-29'
        },
        6: {
            'mode2_rem_cores': '4-27,32-55',
            'mode1_rem_cores': '5-27,33-55',
            'vcpu_pin_set': '3-27,31-55',
            'mode1_pmd_cores': '3,4,31,32',
            'mode2_pmd_cores': '3,31',
            'host_os_cpu': '0-2,28-30'
        }
    }
}
