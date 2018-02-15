# == Class: dellnfv::numa
#
# Configure Dell NFV NUMA feature on Dell-NFV nodes via composable services.
#

class dellnfv::numa (
                        $step         = hiera('step'),
                        $state        = hiera('dellnfv::numa::enable'),
                        $vcpu_pin_set = hiera('dellnfv::numa::vcpu_pin_set')
) {
  if ($step>=4) {
        if ($state == true){

        #Create log file for NUMA
        file {'/tmp/dellnfv_numa_config.log':
                ensure => 'present',
                content => 'FAIL : CPU Pinning configuration failed',
                owner => 'heat-admin',
                group => 'heat-admin',
                mode => 0777,
        }

        #update the kernel using isolcpus
        exec {'update_kernel_numa':
				path => ['/bin/', '/sbin/', '/usr/bin/', '/usr/sbin/'],
				command => "sudo grubby --update-kernel=ALL --args=\"isolcpus=$vcpu_pin_set\"",
        }

        #update vcpu_pin_set in nova.conf
        exec {'set_vcpu_in_nova_conf':
				require => Exec['update_kernel_numa'],
				path => ['/bin/', '/sbin/', '/usr/bin/', '/usr/sbin/'],
				command => "sudo crudini --set /etc/nova/nova.conf DEFAULT vcpu_pin_set \"${vcpu_pin_set}\"",

        }

        #Update in-built puppet log for SUCCESS
        file_line {'edit_success_numa':
				path => '/tmp/dellnfv_numa_config.log',
				line => 'SUCCESS : CPU Pinning configuration successful',
				match => "FAIL : CPU Pinning configuration failed",
				replace => true,
				require => Exec['set_vcpu_in_nova_conf'],
        }
     }
  }
}
