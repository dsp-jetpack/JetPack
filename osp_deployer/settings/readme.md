
[//]: # ((c) 2015-2016 Dell)
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

##Change Log

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

#####settings.properties
* 6.0.0.a - Initial 6.0 version
* 6.0.0.b - Added optional static ip propertis for the overcloud nodes (to be used in conjunction with .ini overcloud_static_ips)
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


