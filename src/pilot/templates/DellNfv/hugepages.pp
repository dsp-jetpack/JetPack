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
        #Create log file for hugepage
        file {'/tmp/dellnfv_hpg_config.log':
                ensure => 'present',
                content => 'FAIL : HugePages configuration failed',
                owner => 'heat-admin',
                group => 'heat-admin',
                mode => 0777,
        }

        #update the kernel using hugepages details, hugepage default size is equal to hugepage size
        exec {'update_kernel_hugepages':
                path => ['/bin/', '/sbin/', '/usr/bin/', '/usr/sbin/'],
                command => "sudo grubby --update-kernel=ALL --args=\"default_hugepagesz=$hpg_size hugepagesz=$hpg_size hugepages=$hpg_number\"",
        }

        #Update in-built log file for SUCCESS
        file_line {'edit_success_hugepage':
                path => '/tmp/dellnfv_hpg_config.log',
                line => 'SUCCESS : HugePages configuration successful',
                match => "FAIL : HugePages configuration failed",
                replace => true,
                require => Exec['update_kernel_hugepages'],
        }
    }
  }
}
