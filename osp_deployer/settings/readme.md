##Change Log
#####This is a change log for the settings.ini and settings.properties file


#####settings.ini:
* 1.0: - Initial version.
* 2.0.x: - Icehouse , RH-OSP5
* 3.0 - 2/24 - Juno, RH-OSP6 A1
* 3.0.a - 3/20/2015 - Added ceph_user_password
* 3.0.1 - 04/07/2015 - Initial version of Juno, RH-OSP6 A2
* 3.0.1.a - 04/10/2015 - Added cloud_repo_dir, clone and use git repo cloud-repo
* 3.0.1.b - 04/24/2015 - Added rhl71_iso and ceph_iso to the Bastion Settings, removed rhl7_iso
* 3.0.1.c - 04/28/2015 - Added partition table variables
  controller_nodes_are_730,compute_nodes_are_730,storage_nodes_are_730=false       
* 3.0.1.d - 04/28/2015 - Removing bonding options bond_mode_*
* 3.0.1.e - 04/30/2015 - Added new pool ID settings for node types : subscription_manager_pool_sah, subscription_manager_pool_vm_rhel, subscription_manager_pool_phyical_openstack_nodes, subscription_manager_pool_vm_openstack_nodes, subscription_manager_vm_ceph, subscription_manager_pool_physical_ceph; removed subscription_manager_pool
* 3.0.1.f - 05/05/2015 - Removed nodes_root_password   openstack_services_password, replaced with cluster_password
* 3.0.1.g - 05/08/2015 - subscription_check_retries property.  New subscription retries setting to allow calls to subscription manager to be retried in case temporary failure is expected (initially, checking subscription status)

#####settings.properties
* 1.0: - Initial version.
* 2.0.x: - Icehouse , RH-OSP5
* 3.0 - 2/24 - Juno, RH-OSP6 A1
* 3.0.a - 03/06 Added private_bond and private_slaves
* 3.0.b - 03/13 Added anaconda_ip and anaconda_iface to sah node
* 3.0.c - 03/06 ceph vm move to storage network(provisioning out)
**Removed: provisioning_ip, provisioning_gateway, provisioning_bond, provisioning_netmask
**Added: storage_ip, storage_gateway , storage_bond, storage_netmask
* 3.0.d - 03/09 Added is_730 ( true,false) to ceph storage nodes
* 3.0.e -  Added anaconda_ip and anaconda_iface to the sah node
* 3.0.f - added root_password to ceph node
* 3.0.g - 04/03/2015 ceph related , changed irdrac_secondary_ip and idrac_secondary_gateway
* 3.0.1 -04/07/2015 - Initial version of Juno, RH-OSP6 A2
* 3.0.1.a - 04/10/2015 - Added is_730 ( true or false) to ceph storage nodes
* 3.0.1.b - 04/30/2015 - Remove public_ip from compute nodes
* 3.0.1.c - 05/05/2015 - Added tempest vm properties
* 3.0.1.d  - 05/05/2015 - New external_vlanid private_api_vlanid vlan properties on the sah to support tempest vm.







