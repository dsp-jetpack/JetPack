##Change Log
### Layout
Command to execute

python deployer.py -s "PATH to the Settings file"

The structure is each directory represents a site and rack designation

* Please add your spreadsheets for your installs
* Please name your files

** MHT_RackName.properties
** MHT_RackName_settings.ini

or

** AUS_RackName.properties
** AUS_RackName_settings.ini



#####This is a change log for the settings.ini and settings.properties file


#####settings.ini:
* 5.0.0.a - Initial 5.0 version - some settings left over from 4.x might go away as this is still work in progress
* 5.0.0.b - Added new setting use_ipmi_driver
* 5.0.0.c - removed legacy settings.
* 5.0.0.d - added management_network & provisioning_gateway settings
* 5.0.0.e - added user_custom_instack_json & custom_instack_json settings to allow nodes scanning bypass
* 5.0.0.f - renamed rhl71_iso to rhl72_iso
* 5.0.0.g - added overcloud_deploy_timeout
* 5.0.0.h - added sanity_test & run_sanity
* 5.0.0.i - added eqlx backend settings
* 5.0.0.j - added run_tempest & tempest_smoke_only
* 5.0.0.k - added dellsc backend settings
* 5.0.0.l - removed ipmi_discovery_range_start & ipmi_discovery_range_end
* 5.0.0.m - removed deploy_ram_disk_image & sanity_test
* 5.0.0.n - added enable_rbd_backend
* 5.0.0.o - added overcloud_name
* 5.0.0.p - added enable_instance_ha
* 5.0.0.q - removed nova_public_network - added enable_fencing

#####settings.properties
* 5.0.0.a - Initial 5.0 version - some settings left over from 4.x might go away as this is still work in progress
* 5.0.0.b - removed legacy settings.
* 5.0.0.c - removed "journal_disks" on storage nodes
* 5.0.0.d - removed is_730 on storage nodes





