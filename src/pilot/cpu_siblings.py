# It is a dictionary of the form {'total number of cpu cores' : {'number_of_host_os_cpu' : {'vcpu_pin_set' : 'Range of corresponding cpus', 'host_os_cpu' : 'Range of corresponding cpus'} } }
# If 'total number of cpu cores' = 48 & 'number_of_host_os_cpu' = 4 then you can get 'vcpu_pin_set' by using sibling_info[48][4]['vcpu_pin_set']
sibling_info = {
    40:
    {8: {'vcpu_pin_set': '4-19,24-39', 'host_os_cpu': '0-3,20-23'},
     2: {'vcpu_pin_set': '1-19,21-39', 'host_os_cpu': '0,20'},
     4: {'vcpu_pin_set': '2-19,22-39', 'host_os_cpu': '0-1,20-21'},
     6: {'vcpu_pin_set': '3-19,23-39', 'host_os_cpu': '0-2,20-22'}},
\
    48: {
        8: {'vcpu_pin_set': '4-23,28-47', 'host_os_cpu': '0-3,24-27'},
        2: {'vcpu_pin_set': '1-23,25-47', 'host_os_cpu': '0,24'},
        4: {'vcpu_pin_set': '2-23,26-47', 'host_os_cpu': '0-1,24-25'},
        6: {'vcpu_pin_set': '3-23,27-47', 'host_os_cpu': '0-2,24-26'}},
\
    128: {
        8: {'vcpu_pin_set': '4-63,68-127', 'host_os_cpu': '0-3,64-67'},
        2: {'vcpu_pin_set': '1-63,65-127', 'host_os_cpu': '0,64'},
        4: {'vcpu_pin_set': '2-63,66-127', 'host_os_cpu': '0-1,64-65'},
        6: {'vcpu_pin_set': '3-63,67-127', 'host_os_cpu': '0-2,64-66'}},
\
    64: {
        8: {'vcpu_pin_set': '4-31,36-63', 'host_os_cpu': '0-3,32-35'},
        2: {'vcpu_pin_set': '1-31,33-63', 'host_os_cpu': '0,32'},
        4: {'vcpu_pin_set': '2-31,34-63', 'host_os_cpu': '0-1,32-33'},
        6: {'vcpu_pin_set': '3-31,35-63', 'host_os_cpu': '0-2,32-34'}},
\
    72: {
        8: {'vcpu_pin_set': '4-35,40-71', 'host_os_cpu': '0-3,36-39'},
        2: {'vcpu_pin_set': '1-35,37-71', 'host_os_cpu': '0,36'},
        4: {'vcpu_pin_set': '2-35,38-71', 'host_os_cpu': '0-1,36-37'},
        6: {'vcpu_pin_set': '3-35,39-71', 'host_os_cpu': '0-2,36-38'}}}
