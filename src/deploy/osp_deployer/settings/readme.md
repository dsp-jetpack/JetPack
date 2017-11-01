
[//]: # ((c) 2015-2017 Dell)
[//]: # ( )
[//]: # (Licensed under the Apache License, Version 2.0 (the "License");)
[//]: # (you may not use this file except in compliance with the License.)
[//]: # (You may obtain a copy of the License at)
[//]: # ( )
[//]: # (    http://www.apache.org/licenses/LICENSE-2.0)
[//]: # ( )
[//]: # (Unless required by applicable law or agreed to in writing, software)
[//]: # (distributed under the License is distributed on an "AS IS" BASIS,)
[//]: # (WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.)
[//]: # (See the License for the specific language governing permissions and)
[//]: # (limitations under the License.)

#####Change Log

#####This is a change log for the settings.ini and settings.properties file


#####settings.ini:
* 6.0.0.a - Initial 6.0 version
* 6.0.0.b - Added tenant network related settings :
               . tenant_network
	       . tenant_network_allocation_pool_start
	       . tenant_network_allocation_pool_end
               * note : Not used unless you wish to configure Generic Routing Encapsulation (GRE) networks
            Added overcloud_static_ips - true/false to enable the use of static ips on the overcloud nodes. false will use dhcp
* 6.0.0.c - Added settings for static VIPs support : 
	       . use_static_vips - true/false to enable the use of static VIPs
	       . redis_vip        - VIP for redis on the private api network
               . provisioning_vip - VIP for the provisioning network
               . private_api_vip  - VIP for the private api network
               . public_api_vip   - VIP for the public api network
               . storage_vip      - VIP for the storage network
               . storage_cluster_vip - VIP for the storage cluster network (must be set on the provisioning network)
	       * see sample file comments for valid ips in the above networks
* 6.0.0.d - Removed settings :
               . sah_kickstart
               . rhel_install_location
* 10.0.0.a - Initial 10.0 version
* 10.0.0.a - removed external_netmask & external_gateway settings (removed)
          - added hardware -  Hardware type, valid options are poweredge, fx

#####settings.properties
* 6.0.0.a - Initial 6.0 version
* 6.0.0.b - Added optional static ip properties for the overcloud nodes (to be used in conjunction with .ini overcloud_static_ips)
	    . Controllers nodes:
        	public_api_ip
	        private_api_ip
        	storage_ip
	        storage_cluster_ip
        	tenant_ip
	    . Computes nodes
		private_api_ip
		storage_ip
		tenant_ip
	    . Storage nodes
        	storage_ip
	        storage_cluster_ip
* 6.0.0.c - Removed provisioning_mac_address properties on all overcloud nodes - no longer required
	    Removed hostname from overcloud nodes - not in use anymore (nodes get named controller-x, compute-x, cephstorage-x)
* 10.0.0.a - Initial 7.0 version : Rename is_ceph node to is_rhscon, and change its hostname to "rhscon
* 10.0.0.b - Added overcloud_nodes_pwd to allow setting a root password on the overcloud nodes
* 10.0.0.c - removed storage_cluster_ip from controller nodes
          - removed external ips
* 10.0.1.a - renamned tenant_ip to tenant_tunnel_ip
* 10.0.1.b - Added enable_rbd_nova_backend to support nova rbd/ceph as ephemeral backend independent of 
             enable_rbd_backend which is used for cinder
* 10.0.1.c - Added deploy_overcloud_debug to allow optionally running
             deploy_overcloud script in debug mode
* 10.0.1.c - Renamed external_bond to public_bond & external_slaves to public_slaves
* 10.0.1.d - Added sanity test parameters:
             floating_ip_network
             floating_ip_network_start_ip
             floating_ip_network_end_ip
             floating_ip_network_gateway
             floating_ip_network_vlan
             sanity_tenant_network
             sanity_user_password
             sanity_user_email
             sanity_key_name
* 10.0.1.e - Renamed tenant network parameters as follows:
             tenant_network -> tenant_tunnel_network
             tenant_network_allocation_pool_start ->
                 tenant_tunnel_network_allocation_pool_start
             tenant_network_allocation_pool_end ->
                 tenant_tunnel_network_allocation_pool_end
             tenant_network_vlanid -> tenant_tunnel_network_vlanid
"
