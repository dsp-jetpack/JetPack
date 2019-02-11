
<img src="media/dc99730255437cdd115b74c45cc6c19d.jpg" alt="drawing" width="200px"/>

# Dell EMC Red Hat Ready Architecture Deployment Guide Notes
### Version 13.0
##### Dell EMC Service Provider Solutions





















<br><br><br><br><br><br><br><br><br>
<div style="page-break-after: always;"></div>

# Trademarks
Copyright © 2014-2018 Dell Inc. or its subsidiaries. All rights reserved.

Microsoft® and Windows® are registered trademarks of Microsoft Corporation in the United States and/or other countries.

Red Hat®, Red Hat Enterprise Linux®, and Ceph are trademarks or registered trademarks of Red Hat, Inc., registered in the U.S. and other countries. Linux® is the registered trademark of Linus Torvalds in the U.S. and other countries. Oracle® and Java® are registered trademarks of Oracle Corporation and/or its affiliates.

DISCLAIMER: The OpenStack® Word Mark and OpenStack Logo are either registered trademarks/ service marks or trademarks/service marks of the OpenStack Foundation, in the United States and other countries, and are used with the OpenStack Foundation's permission. We are not affiliated with, endorsed or sponsored by the OpenStack Foundation or the OpenStack community.

























<div style="page-break-after: always;"></div>

# Contents:

[Chapter 1 : Overview](#Chapter-1-:-Overview)

[Chapter 2 : Red Hat Subscriptions](#Chapter-2-:-Red-Hat-Subscriptions)

[Chapter 3 : Automation Configuration Files](#Chapter-3-:-Automation-Configuration-Files)

[Chapter 4   Preparing and Deploying the Solution Admin Host](#Chapter-4-Preparing-and-Deploying-the-Solution-Admin-Host)

[Chapter 5 : Deploying the Undercloud and the OpenStack Cluster](#Chapter-5-:-Deploying-the-Undercloud-and-the-OpenStack-Cluster)

[Appendix A : Files References](#Appendix-A-:-Files-References)

[Appendix B : Updating RPMs on Version Locked Nodes](#Appendix-B-:-Updating-RPMs-on-Version-Locked-Nodes)

[Appendix C : OpenStack Operations Functional Test](#Appendix-C-:-OpenStack-Operations-Functional-Test)
























<div style="page-break-after: always;"></div>

# Chapter 1 : Overview
This guide provides information necessary to deploy the Dell EMC Ready Architecture for Red Hat OpenStack platform v13.0 using an automation framework developed by Dell EMC and validated by Red Hat.

**Servers**

This document describes the procedure for solution validation using Dell EMC PowerEdge R640 with the Dell EMC PowerEdge H740 disk controller and S4048T switches for networking and other possible hardware configurations.

The base validated Solution supports the Dell EMC PowerEdge R640 and Dell EMC PowerEdge R740xd Server lines

> Note: Please contact your Dell EMC sales representative for Detailed parts lists.

**Networking**

The Dell EMC Ready Architecture for Red Hat OpenStack Platform uses the S5248-ON as the Top of Rack switches and the S3048-ON switch (S4048-ON optional) as the management switch. 



## Before You Begin

> Note: This guide assumes that you have racked the servers and networking hardware, and completed power and network cabling, as per the *Dell EMC Ready Architecture_for_Red_Hat OpenStack Platform Reference Guide – Version 13.*

The high-level steps required to install the Dell EMC Ready Architecture for Red Hat OpenStack Platform v13 using the automated installation procedures include:

1.  Ensuring that your environment meets the [Prerequisites](#Prerequisites)
2.  Ensuring that the [Dependencies](#Dependencies) on are met.
3.  *Determining Pool IDs*.
4.  [Downloading and Extracting Automation Files](#page12).
5.  [Preparing the Solution Admin Host Deployment](#page14).
6.  [Deploying the SAH Node](#page16).
7.  [Deploying the Undercloud and the OpenStack Cluster](#page18).

## Prerequisites
The following prerequisites must be satisfied before proceeding with a Dell EMC Ready Architecture for Red Hat OpenStack platform v13.0 deployment:

> Note: All nodes in the same roles must be of the same server models, with identical HDD, RAM, and NIC configurations. So, all Controller nodes must be identical to each other; all Compute nodes must be identical to each other; and so on. See the Dell EMC Ready Architecture for Red Hat OpenStack Platform - Version 13 for configuration options for each node role.

* Hardware racked and wired per the [Dell EMC Ready Architecture for Red Hat OpenStack Platform Architecture Guide Version 13](https://www.dellemc.com/resources/en-us/asset/technical-guides-support-information/solutions/dell_emc_ready_architecture_for_red_hat_openstack_platform_architecture_guide.pdf).
* Hardware configured as per the [Dell EMC Ready Architecture for Red Hat OpenStack Platform Architecture Guide Version 13](https://www.dellemc.com/resources/en-us/asset/technical-guides-support-information/solutions/dell_emc_ready_architecture_for_red_hat_openstack_platform_architecture_guide.pdf).
* Hardware is powered off after the hardware is configured per the [Dell EMC Ready Architecture for Red Hat OpenStack Platform Architecture Guide Version 13](https://www.dellemc.com/resources/en-us/asset/technical-guides-support-information/solutions/dell_emc_ready_architecture_for_red_hat_openstack_platform_architecture_guide.pdf).
* Internet access, including but not limited to, Red Hat’s subscription manager service and repositories
* Valid Red Hat subscriptions
* Workstation used to extract the JetPack-automation-13.0.tgz file and begin building the collateral for the SAH node.Workstation must be a RHEL7.6 host.

## Dependencies
For customers performing a self-installation, these files are available upon request from Dell EMC. Please contact your account representative, or email <a href="malito: openstack@dell.com" target="_blank">openstack@dell.com</a> for instructions.

> NOTE: The files are also open sourced and can be obtained from <a href="https://github.com/dsp-jetpack/JetPack." target="_blank">https://github.com/dsp-jetpack/JetPack.</a> The Dell EMC Ready Architecture for Red Hat OpenStack Platform v13 deployment dependencies include


> NOTE: The automated install also requires that you have the ISO file “Red Hat Enterprise Linux 7.6 Binary DVD”. It can be downloaded from the Red Hat Customer Portal here: https://access.redhat.com/downloads/content/69/ver=/rhel---7/7.2/x86_64/product-software

























<div style="page-break-after: always;"></div>

# Chapter 2 : Red Hat Subscriptions
Once all prerequisites have been met, you must determine the Appropriate Red Hat subscription entitlements for each cluster node.

## Red Hat Subscription Manager Pool IDs
You must determine the pool ID to use for the Solution Admin Host (SAH) and each node in the cluster before proceeding with the installation. To determine the pool IDs, you must have an existing server that is registered to the Red Hat Hosted Services. This server must also be registered using the same credentials as the ones being used in this environment.


1. Once the server is correctly registered, execute the following command to see the available subscription pools.

```bash
$ subscription-manager list --all --available
```

> Note: The command will output a list of available pools. Each section of information lists what the subscription provides, its pool ID, how many are available, the type of system it is for, as well as other information.


2. Determine the correct pool ID needed for this environment and take note of it.
> Note: Pay close attention to the System Type. The System Type can be Virtual or Physical. If necessary you can use a physical license for a virtual node. However, you cannot use a virtual subscription for a physical node.

```bash
$ subscription-manager list --all --available

[OUTPUT ABBREVIATED]

Subscription Name:	Red Hat	Ceph Storage, Standard Support(8 Nodes,NFR)
Provides:	Red Hat   	OpenStack Director Deployment Tools Beta
	Red Hat	Software Collections (for RHEL server)
SKU:	Red Hat Ansible Engine
Red Hat Ceph Storage
Red Hat Enterprise Linux Scalable File System (for RHEL Server)
Red Hat OpenStack Director Deployment Tools for IBM Power LE
Red Hat OpenStack Director Deployment Tools Beta for IBM Power LE
Red Hat Storage Console Node
Red Hat Storage Console
Red Hat Enterprise Linux Server
Red Hat Ceph Storage OSD
Red Hat Ceph Storage MON
Red Hat Ceph Storage Calamari
Red Hat OpenStack Director Deployment Tools
RS00019
Contract:	11699983	
Pool ID:	Aaaa111	Bbb222ccc333ddd444eee5556
Provides Management: 	No
Available:	69	
Suggested:	1	
Service Level:	Standard	
Service Type:	L1-L3	
Subscription Type:     	Standard	
Ends:	06/22/2019	
System Type:	Physical	
		
		
[OUTPUT  ABBREVIATED]
```

> Note: The above output shows a subscription that contains the Red Hat OpenStack entitlement. The required entitlement types for each node are shown the following table.

| **Node Role**                     | **Entitlement**                 | **System Type**                   |
|-----------------------------------|---------------------------------|-----------------------------------|
| Solution Admin Host               | Red Hat Enterprise Linux Server | Physical                          |
| Director Node                     | Red Hat OpenStack               | Virtual                           |
| Red Hat Ceph Storage Dashboard VM | Red Hat Ceph Storage Dashboard  | physical (no virtual available at this time |
| Controller Node                   | Red Hat OpenStack               | Physical                          |
| Compute Node                      | Red Hat OpenStack               | Physical                          |
| Storage Node                      | Red Hat Ceph Storage            | Physical                          |


<div style="page-break-after: always;"></div>

# Chapter 3 : Automation Configuration Files
This chapter details obtaining the required configuration files.

### Downloading and Extracting Automation Files

The following procedure installs the required configuration files and scripts used to build the collateral (osp_ks.img) to begin deploying the solution. This system must be a RHEL 7.6 system and is only used to build up the initial kickstart file. It will not be used again as it is a one-time use, and will not be allocated permanently in the customer's OpenStack deployment.

1.	Log into your RHEL 7.6 system as user root.
2.	Download the JetPack-automation-13.0.tgz to the /root directory.
3.	Change the working directory to /root.
4.	Extract the tar file contents:
    ``` bash
    $ tar -xvf JetPack-automation-13.0.tgz
    ```
5.	Download or copy the ISO of the Red Hat Enterprise Linux Server 7.6 installation DVD to /root/ rhel76.iso.































<div style="page-break-after: always;"></div>

# Chapter 4: Preparing and Deploying the Solution Admin Host
This topic describes preparing for, and performing, the Solution Admin Host (SAH) deployment.

The Dell EMC PowerEdge R-Series servers require the Open Source Hardware Configuration Toolkit (OS-HCTK) **to be run only on the SAH**.

## Preparing the Solution Admin Host Deployment
> ***CAUTION:*** This operation will destroy all data on the SAH, with no option for recovery.

> ***Note:*** This release uses the feature of profiles to determine the use case for a deployment. There are 2 different pre-defined profiles, CSP or xSP that can be used for a deployment. The CSP profile is designed for Telecommunications Providers, Cable TV Operators, Satellite TV, Internet Service Providers, etc. whereas the xSP profile is designed for Business & IT Services Providers such as Hosting Service Providers, Cloud Service Providers, Software-as-a-Service/Platform-as-a-Service Providers, Application Hosting Service Providers and Private Managed Cloud Service Providers.
> 

1.	Log into your RHEL 7.6 system as the root user.
2.	Change the working directory to 
    ```bash
    /root/JetPack/src/deploy/osp_deployer/settings
    ```
    Then, 
    ```bash
    $ cd ~/JetPack/src/deploy/osp_deployer/settings
    ```

    > Note: Pick the right sample configuration files for your deployment. There are 3
    > sample configuration files available, sample_csp_profile.ini, sample_xsp_profile.ini and
    > sample_properties. Make sure you review Appendix D-F for additional information for the sample_csp_profile.ini file.
    > .

3.	Copy the sample settings files to the ~/ directory and rename them for your deployment
    
    ```bash
    $ cp ~/JetStream/src/deploy/osp_deployer/settings/sample.properties ~/acme.properties
    ```
    and
    
    ```bash
    $ cp ~/JetPack/src/deploy/osp_deployer/settings/sample_csp_profile.ini ~/acme.ini
    ```
    or
    ```bash
    $ cp ~/JetPack/src/deploy/osp_deployer/settings/sample_xsp_profile.ini ~/acme.ini
    ```

4.	Edit your hardware stamp’s .ini and .properties files to match your hardware stamp documentation (i.e., a Solution Workbook). Use a text editor of your choice; our example uses vi:
    
    ```bash
    $ vi ~/acme.ini
    ```
    
    a. Change the pre-populated values in your stamp-specific .ini file to match your specific environment. In addition, the IP addresses and the Subscription Manager Pool IDs must be changed to match your deployment. Each section will have a brief description of the attributes.
    
    b. The nic_env_file parameter must be set to the NIC configuration to use. The default value of 5_port/nic_environment.yaml is appropriate for 10GbE or 25GbE  Intel NICs with DPDK disabled.The deployment can be done with only 4NICs too, where in you need to use the value of 4_port/nic_environment.yaml
        
    > Note: The overcloud deployment is validated with R630 servers is the normal compute nodes [standard deployment] without any NFV features. Also validated with R740 servers. Although the additional information for the settings within the CSP profile can be found in the [Appendix D-F](#Appendix-D). 
    
    c. The Dell EMC Ready Architecture for Red Hat OpenStack Platform v13optimizes the performance of the deployed overcloud. See [Appendix G](#Appendix-G) for instructions on how to further tune the performance Optimization parameters.

5. With CSP profile, hugepages is enabled. With XSP profile, hugepages are disabled on the deployed compute nodes for XSP profile. 
    > To enable hugepages, see [Appendix D](#Appendix-D). 

6.	Edit the stamp-specific .properties file:
    
    ```bash
    $ vi ~/acme.properties
    ```

7.	Change the values in your .properties file to match your specific environment. You must supply a value for IP addresses, host names, passwords, interfaces, and storage OSDs/journals.

    **The storage OSDs/journals configuration is not specified if the storage nodes are 14G servers with HBA330 controllers, but must be specified for all other storage node configurations.**

    > Note: Additional nodes can be added to your stamp-specific .properties file if your environment contains more than that supported by the base architecture, as described in the Dell EMC Ready Architecture for Red Hat OpenStack Platform Reference Guide Version 13.


    The examples in this file are based on the Dell EMC Ready Architecture for Red Hat OpenStack Platform Reference Guide Version 13, and the installation scripts rely on the VLAN IDs as specified in this file. For example, the Private API VLAN ID is 140. So, all addresses on the Private API network must have 140 as the third octet (e.g., 192.168.140.114). Table 2: VLAN IDs on page 15 below lists the VLAN IDs.
    
    | **VLAN ID**           | **Name**                                                 |
    |-----------------------|----------------------------------------------------------|
    | 110                   | Management/Out of Band (OOB) Network (iDRAC)             |
    | 120                   | Provisioning Network                                     |
    | 130                   | Tenant Tunnel Network                                    |
    | 140                   | Private API Network                                      |
    | 170                   | Storage Network                                          |
    | 180                   | Storage Clustering Network                               |
    | 190                   | Public API Network                                       |
    | 191                   | External Tenant Network (Used for floating IP addresses) |
    | 201-250               | Internal Tenant Network                                  |

    > ***Note:*** The anaconda_ip is used for the initial installation of the SAH node, and requires an address that can access the Internet to obtain Red Hat software. When possible, the anaconda_iface must be a dedicated interface using 1GbE that is only used for this purpose, and is not used in any other part of the configuration. For 10GbE or 25GbE Intel NICs, "em4" (the fourth nic on the motherboard) should be used. For Intel XXV710 DP 25GbE DA/SFP NICs, "em2.<public_api_network_vlan_id>" (usually "em2.190") should be used.

    a.	Configure the Overcloud nodes' iDRACs to use either DHCP or statically-assigned IP addresses. A mix of these two choices is supported.
    
        a.	Determine the service tag of the Overcloud nodes whose iDRAC is configured to use DHCP.
        
        b.	Determine the IP addresses of the Overcloud nodes whose iDRAC is configured to use static IP addresses.
        
        c.	When creating the automation .properties file:
            * Add the following line to each node using DHCP, substituting the service tag for the node:
                ```yaml
                "service_tag": "<serviceTagHere>",
                ```
            * Add the following line to each node using static IP addressing, substituting IP address:
                ```yaml
                "idrac_ip": "<idracIpHere>",
                ```
                Only service_tag or idrac_ip should be specified for each Overcloud node, not both.
                
                The iDRACs using DHCP will be assigned an IP address from the management allocation pool specified in the .ini file. The parameters that specify the pool range are:
        
                * management_allocation_pool_start
                
                * management_allocation_pool_end
        
                During deployment, the iDRACs using DHCP will be automatically assigned an IP address and discovered. The IP addresses assigned to the nodes can be seen after the undercloud is deployed:
        
                * In /var/lib/dhcpd/dhcpd.leases on the SAH Node
                * In ~/instackenv.json on the Director Node
                * By executing the following commands on the Director Node:
                
                    ```bash
                    $ ironic node-list
                    $ ironic node-show <node_guid>
                    ```
                    
    b. When using Mellanox 25GbE NICs, add the following to each Overcloud node in the .properties file:
        ```yaml
        "pxe_nic": "NIC.Integrated.1-1-1",
        ```
8. Update your python path:
    ```bash
    $ export PYTHONPATH=/usr/bin/python:/lib/python2.7:/lib/python2.7/\ site-packages:~/JetPack/src/deploy
    ```

9.	You can install the SAH node using either of the following methods:
    * **Using a physical USB key (key must have 8GBs minimum of capacity):**
        1. Plug your USB key into your RHEL 7.6 system.
        2. Run the setup script to prepare your USB key, passing in the USB device ID (/dev/sdb in the example below). This process can take up to 10 minutes to complete.
        
            > Note:  Use full paths.
    
            ```bash
            $ cd ~/JetPack/src/deploy/setup
            $ python setup_usb_idrac.py -s /root/acme.ini -usb_key /dev/sdb
            ```

    * **Using an iDRAC virtual media image file. This requires your RHEL 7.6 system to have access to the iDRAC consoles to attach the image.**
        1.	Run the setup script to generate an image file that can later be attached to the SAH node.
            > Note:  Use full paths.
            
            ```bash
            $ cd ~/JetPack/src/deploy/setup
            $ python setup_usb_idrac.py -s /root/acme.ini -idrac_vmedia_img
            ```
        2.	The output will be an image file generated in ~/ named osp_ks.img.


<br><br><br>

## Deploying the SAH Node

**You can deploy the SAH node by one of two methods:**
* Using a physical USB key generated above, plugged into the SAH node, or
* Using an iDRAC virtual media image generated above, made available using the **Map Removable Media** option on the iDRAC.

    > Note: Proceed to [Presenting the Image to the RHEL OS Installation Process](#Presenting-the-Image-to-the-RHEL-OS-Installation-Process)
 

### Presenting the Image to the RHEL OS Installation Process

1.	Attach the Red Hat Enterprise Linux Server 7.6 ISO as a virtual CD/DVD using the Virtual Media -> Map CD/DVD option.

2.	Attach the ~/osp_ks.img created above by using either of the following methods:

    * As a removable disk using the Virtual Media -> Map Removable Disk option, or
    * Plug in the USB key created above into the SAH.

3.	Set the SAH node to boot from the virtual CD/DVD using the Next Boot -> Virtual CD/DVD/ISO option.

4.	Boot the SAH node.

    a. At the installation menu, select the Install option. Do not press the [Enter] key. b. Press the Tab key.
    
    c. Move the cursor to the end of the line that begins with vmlinuz. d. Append the following to the end of the line:

        ```bash
        ks=hd:sdb:/osp-sah.ks
        ```
        
    > Note: The device sdb can change, depending upon the quantity of disks being presented to the installation environment. These instructions assume that a single disk is presented. If otherwise, adjust accordingly.
 
5.	Press the [Enter] key to start the installation.
    > Note: It may take a few minutes before progress is seen on the screen. Press the [ESC] key at the memory check to speed up the process.
 
<br><br><br>






























<div style="page-break-after: always;"></div>

# Chapter 5: Deploying the Undercloud and the OpenStack Cluster
> ***Topics:*** Deploying and Validating the Cluster

Now that the SAH node is installed you can deploy and validate the rest of the Dell EMC Ready Architecture for Red Hat OpenStack Platform v13

> ***CAUTION:*** This operation will destroy all data on the identified servers, with no option for recovery.

**To deploy and validate the rest of the cluster:**

1.	Log in through the iDRAC console as root, or ssh into the SAH node.

2.	Mount the USB media:

    ```bash
    $ mount /dev/sdb /mnt
    ```

3.	Copy all the files locally:

    ```bash
    $ cp -rfv /mnt/* /root
    ```

4.	Start a tmux session to avoid losing progress if the connection drops:

    ```bash
    $ tmux
    ```

5.	There are some post-deployment validation options in the [Sanity Test Settings] group and [Tempest Settings] group of the stamp-specific initialization file you should consider prior to deployment:
    
    * **run_sanity** - If set to true the sanity_test.sh script will be executed that will verify the basic functionality of your overcloud deployment.
    * **run_tempest** - If set to true the Tempest integration test suite will be executed against your overcloud deployment.

    > ***Note:*** Tempest requires that the sanity test must be run first so run_sanity, above, must also be set to true. For some details on tempest results notes, please refer to Dell_EMC_Red_Hat_Ready_Architecture_Release_Notes_v13.0

    * **tempest_smoke_only** - If run_tempest, above, is set to true this option, which is set to true by default, will cause Tempest to run only a small subset of the test suite, where the tests are tagged as "smoke". If set to false the entire Tempest suite will be run, which can take an hour or more to complete.

6.	Run the deployment by executing the deployer.py command:

    ```bash
    $ cd /root/JetPack/src/deploy/osp_deployer
    $ python deployer.py -s <path_to_settings_ini_file> [-undercloud_only] [-overcloud_only] [-skip_dashboard_vm]
    ```

    Optional arguments include:
    * -undercloud_only = Reinstall only the Undercloud
    * -overcloud_only = Reinstall only the Overcloud
    * -skip_dashboard_vm = Do not reinstall the Red Hat Ceph Storage Dashobard VM

7.	For installation details, execute a tail command on the /auto_results/deployer.log.xxx file on the SAH node. For example:

    ```bash
    $ tail -f /auto_results/ deployer.log.2018.09.09-07.32
    ```

8.	If issues are discovered during the installation process:
    a. Identify the issue in the deployer.log 
    b. Address the issue.
    c. Rerun the python deployer.py command above.

9.	If the installation is successful, the deployment_summary.log file will display some useful information for accessing the Dell EMC Ready Architecture for Red Hat OpenStack platform v13.
    
    ```bash
    $ cd /auto_results
    $ cat deployment_summary.log
    ```
    
    The output will appear similar to this:

    ```bash
    ====================================
    ### nodes ip information ###
    ### Controllers ###
     overcloud-controller-0   :
         - provisioning ip  : 192.168.120.128
         - nova private ip  : 192.168.140.110
         - nova public ip   : 10.118.135.20
         - storage ip       : 192.168.170.110
     overcloud-controller-1   :
         - provisioning ip  : 192.168.120.129
         - nova private ip  : 192.168.140.109
         - nova public ip   : 10.118.135.21
         - storage ip       : 192.168.170.109
     overcloud-controller-2   :
         - provisioning ip  : 192.168.120.127
         - nova private ip  : 192.168.140.117
         - nova public ip   : 10.118.135.22
         - storage ip       : 192.168.170.117
    ### Compute  ###
     overcloud-dell-compute-0 :
         - provisioning ip  : 192.168.120.131
         - nova private ip  : 192.168.140.112
         - storage ip       : 192.168.170.112
     overcloud-dell-compute-1 :
         - provisioning ip  : 192.168.120.122
         - nova private ip  : 192.168.140.113
         - storage ip       : 192.168.170.113
    ### Storage  ###
     overcloud-cephstorage-0  :
         - provisioning ip    : 192.168.120.133
         - storage cluster ip : 192.168.180.115
         - storage ip         : 192.168.170.115
     overcloud-cephstorage-1  :
         - provisioning ip    : 192.168.120.124
         - storage cluster ip : 192.168.180.108
         - storage ip         : 192.168.170.108
     overcloud-cephstorage-2  :
         - provisioning ip    : 192.168.120.132
         - storage cluster ip : 192.168.180.116
         - storage ip         : 192.168.170.116
    ====================================
    OverCloud Horizon        : http://10.118.135.10:5000//v3
    
    OverCloud admin password : AdZ3re629WZuYKMkRRpNMQPft
    
    ====================================
    ```






























<div style="page-break-after: always;"></div>

# Appendix A : Files References
> ***Topics:*** Solution Files This appendix lists documents and script archives that are required to install and deploy the Dell EMC Ready Architecture for Red Hat OpenStack Plaftform v13. Please contact your Dell EMC representative for copies if required.
 

**Solution Files**

<u>**Dell EMC Ready Architecture for Red Hat OpenStack Platform v13 includes:**</u>

* https://github.com/dsp-jetpack/JetPack - Contains all automation deployment solution scripts
* Dell_EMC_Red_Hat_Ready_Architecture_Cumulus_Switch_Configurations_v13.0.pdf
* Dell_EMC_Red_Hat_Ready_Architecture_Guide_v13.0.pdf
* Dell_EMC_Red_Hat_Ready_Architecture_Release_Notes_v13.0.pdf
* Dell_EMC_Red_Hat_Ready_Architecture_Deployment_Guide_Notes¬_v13.0 (github doc folder)






























<div style="page-break-after: always;"></div>

# Appendix B : Updating RPMs on Version Locked Nodes
At a high level, updating RPMs on a version locked node (Red Hat OpenStack Platform Director Node or Red Hat Ceph Storage Dashboard VM):
1. Identifies the RPMs that need to be updated.
2. Updated RPMs removed from the version lock list for that node.
3. Updates RPMs.
4. Adds the updated RPMs back into the version lock list.

### Updating the RPMs

To update the RPMs:

> ***Note:*** All of the following commands should be run as the root user.
 

1.	Produce a list of RPMs that are version locked on a node:

	a. Login to a node.

	b. Execute the following command to produce a list of RPMs that are version locked:

	```bash
    $ yum versionlock list
    ```


2.	Identify the RPMs to be updated from the output of the above command.

3.	Remove the selected RPMs from the version lock list:

    a.	Execute the following command, substituting VLockListEntry with an RPM name from the output of the versionlock list command above:
    
    > ***Note:*** The VLockListEntry must exactly match an RPM name in the output of the yum versionlock list command.
 

	```bash
    $ yum versionlock delete VLockListEntry
    ```

    b. Repeat for each RPM.

4.	Update each of the selected RPMs:

	a. Execute the following command for an RPM, substituting RPMNameWithoutVersion with the name of the RPM without the version number:

    	```bash
        $ yum update RPMNameWithoutVersion
        ```

	b. Repeat for each subsequent RPM

5.	Add each of the selected RPMs back into the version lock list:
    Execute the following command, again substituting RPMNameWithoutVersion with the name of the RPM without the version number:

    ```bash
    $ yum versionlock add RPMNameWithoutVersion
    ```

> Note: The deployment option “enable_version_locking=true” in the [Advanced Settings] of .ini file for both csp and xsp profiles enforces version lock on the packages. Typically developers should set to false.






























<div style="page-break-after: always;"></div>

# Appendix C : OpenStack Operations Functional Test

> **Topics:** Creating Neutron Networks in the Overcloud, Manual RHOSP Test, Scripted RHOSP Sanity Test

This optional section includes instructions for creating the networks and testing a majority of your RHOSP environment using Glance configured with Red Hat Ceph Storage, SC Series, or any backend. These command line instructions are working examples that you may found on the OpenStack website. 


### Creating Neutron Networks in the Overcloud

The following example commands create the required tenant and public networks, and their network interfaces. You must complete them prior to creating instances and volumes, and testing of the functional operations of OpenStack.

> Note: The following commands and those in the following section should be executed on the Director Node.
> 

1.	Log into the Director Node using the user name and password specified when creating the node and source the overcloudrc file, or the name of the stack defined when deploying the overcloud :

    ```bash
    $ cd ~/
    $ source overcloudrc
    ```

2.	Create the tenant network by executing the following commands:

    >  	Note: Replace tenant_network_name with your desired values. (e.g., openstack network create tenant_net1 --share).

    ```bash
    $ openstack network create <tenant_network_name> --share
    ```

3.	Create the tenant subnet on the tenant network:

 	> Note: Replace tenant_network_name, vlan_network, vlan_name and vlan_gateway with your desired values (e.g., openstack subnet create tenant_2011 --network tenant_net1 --subnet-range 192.168.201.0/24).

    ```bash
    $ openstack subnet create <tenant_subnet_name> --network <tenant_network_name> --subnet-range <vlan_network>
    ```

4.	Create the router:

    >  	Note: Replace tenant_router with your desired values (e.g., openstack router create tenant_201_router).
    
    ```bash
    $ openstack router create <tenant_router>
    ```

5.	Before you add the tenant network interface, you will need the subnets ID. Execute the following command to display them:

    ```bash
    $ openstack network list
    ```

    **The displayed output will be similar to the following (example truncated for brevity):**
    
    | id	|	name	| subnets
    |--------------------------------------|--------------------|---|
    | 52411536-ec43-402f-9736-4cabdc8c875d |	tenant_net		| 7329d413 | 
    | 0af01763-539e-41c7-ac32-abbaa62ee575 |	HA network tenant | bdae0b72 |


6.	Add the tenant network interface between the router and the tenant network:

    >  	Note: Replace tenant_router and subnets_id with your desired values (e.g.,
     
    
    ```bash
    $ openstack router add subnet tenant_201_router 7329d413-ac23-56cf-8867-133b5ff8fc12).
    $ openstack router add subnet <tenant_router> <subnets_id>
    ```


7.	Create the external network by executing the following commands:

    > Note: Replace external_network_name and external_vlan_id with your desired value. (e.g.,
 
    ```bash
    $ openstack network create public --external --provider-network-type vlan --provider-physical-network physext --provider-segment 45).
    $ openstack network create <external_network_name> --external \ --provider:network_type vlan –provider-physical-network physext \ --provider-segment <external_vlan_id>
    ```

8.	Create the external subnet with floating IP addresses on the external network:

 	> Note: Replace external_subnet_name, start_ip, end_ip, external_network_name, external_vlan_network and external_gateway with your desired values (e.g.,

    ```bash
    $ openstack subnet create external_sub --network public --subnet-range 10.118.135.0/25 --allocation-pool start=10.118.135.39,end=10.118.135.49 --gateway 10.118.135.1 --no-dhcp).
    
    $ openstack subnet create <external_subnet_name> \
    --network <external_network_name> --subnet-range <external_vlan_network>\
    --allocation-pool start=<start_ip>,end=<end_ip> \
    --gateway <gateway_ip> --no-dhcp
    
    ```


    
9.	Set the external network gateway for the router:

 	> Note: Replace tenant_router_name with the router name external_nework_name with the external network name (e.g., openstack router set --external-gateway public tenant_201_router).


    ```bash
    $ openstack router set –-external-gateway <external_network_name> <tenant_router_name>
    ```







### Manual RHOSP Test

This example uses the Cirros image to test high-level functional operations of OpenStack.

1.	Log into the Director Node using the user name and password specified when creating the node.

2.	Download the Cirros image:

    ```bash
    $ wget http://download.cirros-cloud.net/0.3.3/cirros-0.3.3-x86_64-disk.img
    ```

3.	Source your Overcloud credentials:

    ```bash
    $ cd ~/
    $ source <overcloud_name>rc
    ```


4.	Create and upload the Glance image:

    ```bash
    $ openstack image create --disk-format <format> \
    --container-format <format> --file <file_path> <IMAGE_NAME> --public
    ```

For example:

    ```bash
    $ openstack image create --disk-format qcow2 \
        --container-format bare --file cirros-0.3.3-x86_64-disk.img cirros --public
    ```

5.	List available images to verify that your image uploaded Successfully: 

    ```bash
    $ openstack image list
    ```

 
6.	To view more detailed information about an image, use the identifier of the image from the output of the openstack image list command above:

    ```bash
    $ openstack image show <id>
    ```

7.	Launch an instance using the boot image that uploaded: 
    a. Get the ID of the flavor you will use:
    
        ```bash
        $ openstack flavor list
        ```

    b.	Get the image ID:
    
        ```bash
        $ openstack image list
        ```
    
    c.	Get the tenant network ID:

        ```bash
        $ openstack network list
        ```

    d.	Generate a key pair. The command below generates a new key pair; if you try using an existing key pair in the command, it fails.
    
        >  	Note: MY_KEY.pem is an output file created by the nova keypair-add command, and will be used later.
    
        ```bash
        $ openstack keypair create --public-key <path to public key>  MY_KEY > MY_KEY.pem
        ```
    
    e.	Create an instance using the nova boot command. 
    
        >  	Note: Change the IDs to your IDs from Steps 7a-c, and the nameofinstance and the key_name from Step 7c:
        
        
        ```bash
        $ openstack server create --flavor <flavor_id> --key-name <key_name> \
        --image <imageid>	--nic net-id=<tenantNetID> <nameofinstance>
        ```
        
        For example:
        
        ```bash
        $ openstack server create --flavor 2 --key_name key_name \ --image 0bde34f6-fba6-4174-a3ea-ff2a7918de2e \
        --nic net-id=52411536-ec43-402f-9736-4cabdc8c875d	cirros-test
        ```
    
    f.	List the instance you created:
    
        ```bash
        $ openstack server list
        ```

8.	If you have multiple backends, create a Cinder volume type for each backend. Get the <volume_backend_name> from the /etc/cinder/cinder.conf file on the Controller node.

    ```bash
    $ openstack volume type create <type_name>
    $ openstack volume type set <type_name> \
    --property volume_backend_name=<volume_backend_name>
    ```

    For example:
    
    ```bash
    $ openstack volume type create rbd_backend
    $ openstack volume type set rbd_backend --property volume_backend_name=tripleo_ceph
    
    $ openstack volume type create dellsc_backend
    $ openstack volume type set dellsc_backend  --property volume_backend_name=dellsc
    ```

9. Create a new volume to test the Cinder volumes:

    > Note: If you have multiple backends defined, you must append the optional arguments --type <type-name> from Step 8 to the command below.

    ```bash
    $ openstack volume create –-size <sizeinGB> <volume_name>
    ```

    For example:
    
    ```bash
    $ openstack volume create –-size 1 vol_test1
    ```

    a.	List the Cinder volumes:
        
        ```bash
        $ openstack volume list
        ```
        
        b.	Attach the volume to the instance, specifying the server ID and the volume ID.
        
        > Note: Replace the server_id with the ID returned from the nova list command, and replace the volume_id with the ID returned from the cinder list command, from the previous steps.
 
        ```bash
        $ openstack server add volume <server_id> <volume_id> <device>
        ```
        
        For example:
        
        ```bash
        $ openstack server add volume 84c6e57d-a6b1-44b6-81eb-fcb36afd31b5 \ 573e024d-5235-49ce-8332-be1576d323f8 /dev/vdb
        ```

10. Access the instance.

    a.	Find the active Controller by executing the following commands from the Director Node:

        ```bash
        $ cd ~/
        $ source stackrc
        $ openstack server list (make note of the controllers ips)
        $ ssh heat-admin@<controller ip>
        $ sudo -i
        # pcs cluster status
        ```
        
        The displayed output will be similar to the following:

        ```bash
        Cluster name: tripleo_cluster
        Last updated: Wed Apr 6 20:48:10 2016
        Last change: Mon Apr 4 18:49:20 2016 by root via cibadmin on overcloud-
        controller-1
        Stack: corosync
        
        Current DC: overcloud-controller-1 (version 1.1.13-10.el7_2.2-44eb2dd) - partition with quorum        3	nodes and 112 resources configured
        ```


    b.	Initiate an SSH session to the active Controller, as heat-admin.
    
    c.	Find the instances by executing the following command:
    
        ```bash
        $ sudo -i
        # ip netns
        ```

    
        The displayed output will be similar to the following:
        
        ```bash
        qrouter-21eba0b0-b849-4083-ac40-44b794744e9f
        qdhcp-f4a2c88f-1bc9-4785-b070-cc82d7c334f4
        ```


    d.	Access an instance namespace by executing the following command:
    
        ```bash
        $ ip netns exec <namespace> bash
        ```

        For example:
        
        ```bash
        $ ip netns exec qdhcp-f4a2c88f-1bc9-4785-b070-cc82d7c334f4 bash
        ```

    
    e. Verify that the namespace is the desired tenant network, by executing the following command:
    
        ```bash
        ip a
        ```

    
        The displayed output will be similar to the following:
    
        ```bash
        1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
        link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
        inet 127.0.0.1/8 scope host lo
        valid_lft forever preferred_lft forever
        inet6 ::1/128 scope host
        valid_lft forever preferred_lft forever
        19: tap05a22fb4-4f: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc
        noqueue state UNKNOWN
        link/ether fa:16:3e:99:b9:88 brd ff:ff:ff:ff:ff:ff
        inet 192.168.201.2/24 brd 192.168.201.255 scope global tap05a22fb4-4f ->
        Tenant network
        valid_lft forever preferred_lft forever
        inet6 fe80::f816:3eff:fe99:b988/64 scope link
        valid_lft forever preferred_lft forever
        ```
  
    
    f.	Ping the IP address of the instance.
    
    g.	SSH into the instance, as cirros, using the keypair generated above:
    
        ```bash
        $ ssh -i MY_KEY.pem cirros@<ip>
        ```



11. Format the drive and access it.

    a. List storage devices:
        ```bash
        $ sudo -i
        $ fdisk –l
        ```


    b. Format the drive:
        ```bash
        $ mkfs.ext3 /dev/vdb
        ```


c. Mount the device, access it, and then unmount it:
        ```bash
        $ mkdir ~/mydrive
        $ mount /dev/vdb ~/mydrive
        $ cd ~/mydrive
        $ touch helloworld.txt
        $ ls
        $ umount ~/mydrive
        ```


### Scripted RHOSP Sanity Test

As an alternative to manually testing your deployment script, we provide sanity_test.sh, which tests all of the basic functionality.

**To run the sanity test script:**

1.	Log into the Director Node using the user name and password specified when creating the node.

2.	Review the pilot/deployment-validation/sanity.ini file, and modify the parameters as appropriate for your environment. If using OVS-DPDK, set the value for        
    ```bash
    ovs_dpdk_enabled= to True.
    ```
    > Note: The sanity test generates the public/private SSH key pair using the name specified in sanity.ini in the sanity_key_name parameter. The public key is named ~/ <sanity_key_name>.pub, and the private key is named ~/<sanity_key_name>.
 

3.	From your home directory, execute the sanity_test.sh script:

    ```bash
    $ cd ~/
    $ ./pilot/deployment-validation/sanity_test.sh
    ```

4.	If you wish to clean the environment once the sanity_test.sh script has run successfully:

    ```bash
    $ cd ~/
    $ ./pilot/deployment-validation/sanity_test.sh clean
    ```

> Note: There are deployment options [Sanity Test Settings], in the sample files which may be configured initially to run the sanity tests automatically after the overcloud deployment is successful. The relevant sanity logs will be generated in the director VM at the directory of pilot/deployment-validation/
 







------------------- Pending Huge Pages Appendix D -------------------------
