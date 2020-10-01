#!/usr/bin/env python3

# Copyright (c) 2015-2020 Dell Inc. or its subsidiaries.
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

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import yaml
from jinja2 import Environment
from jinja2 import FileSystemLoader
from osp_deployer.settings.config import Settings
from checkpoints import Checkpoints
from collections import defaultdict
from collections import OrderedDict
from infra_host import InfraHost
from infra_host import directory_check
from auto_common import Scp
from auto_common.yaml_utils import OrderedDumper
from auto_common.yaml_utils import OrderedLoader

logger = logging.getLogger("osp_deployer")
# TODO after testing delete two logging config lines below
# logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
# logger = logging.getLogger()

exitFlag = 0

# Ceph pools present in a default install
HEAVY_POOLS = ['images',
               'vms',
               'volumes']
OTHER_POOLS = ['.rgw.buckets',
               '.rgw.root',
               'backups',
               'default.rgw.buckets.data',
               'default.rgw.buckets.index',
               'default.rgw.control',
               'default.rgw.log',
               'default.rgw.meta',
               'metrics']

TEMPEST_CONF = 'tempest.conf'
UNDERCLOUD_LOCAL_INTERFACE = 'enp2s0'
OVERCLOUD_PATH = 'overcloud'
OVERCLOUD_ENVS_PATH = OVERCLOUD_PATH + '/environments'

STAGING_PATH = '/deployment_staging'
STAGING_TEMPLATES_PATH = STAGING_PATH + '/templates'
NIC_CONFIGS = 'nic-configs'
STAGING_NIC_CONFIGS = STAGING_TEMPLATES_PATH + '/' + NIC_CONFIGS
NIC_ENV = 'nic_environment'
NODE_PLACEMENT = 'node-placement'
DELL_ENV = 'dell-environment'
NET_ENV = 'network-environment'
INSTACK = 'instackenv'
STATIC_IP_ENV = 'static-ip-environment'
STATIC_VIP_ENV = 'static-vip-environment'
ROLES_DATA = 'roles_data'
NET_DATA = 'network_data'
NET_ISO = 'network-isolation'
CONTROLLER = 'controller'
DEF_COMPUTE_ROLE_FILE = 'Compute.yaml'
DEF_COMPUTE_REMOTE_PATH = ('/usr/share/openstack-tripleo-heat-templates/'
                           'roles/{}'.format(DEF_COMPUTE_ROLE_FILE))
CONTROL_PLANE_NET = ('ControlPlane', "ctlplane")
INTERNAL_API_NET = ('InternalApi', 'internal_api')
STORAGE_NET = ('Storage', 'storage')
TENANT_NET = ('Tenant', 'tenant')
EXTERNAL_NET = ('External', 'external')

EDGE_NETWORKS = (INTERNAL_API_NET, STORAGE_NET,
                 TENANT_NET, EXTERNAL_NET)
EDGE_VLANS = ["TenantNetworkVlanID", "InternalApiNetworkVlanID",
              "StorageNetworkVlanID"]

# Jinja2 template constants
J2_EXT = '.j2.yaml'
NIC_ENV_EDGE_J2 = NIC_ENV + "_edge" + J2_EXT
EDGE_COMPUTE_J2 = 'compute_edge' + J2_EXT
CONTROLLER_J2 = CONTROLLER + J2_EXT
NETWORK_DATA_J2 = NET_DATA + J2_EXT
NETWORK_ENV_EDGE_J2 = NET_ENV + "-edge" + J2_EXT
DELL_ENV_EDGE_J2 = DELL_ENV + "-edge" + J2_EXT
STATIC_IP_ENV_EDGE_J2 = STATIC_IP_ENV + "-edge" + J2_EXT
NODE_PLACEMENT_EDGE_J2 = NODE_PLACEMENT + "-edge" + J2_EXT
ROLES_DATA_EDGE_J2 = ROLES_DATA + "_edge" + J2_EXT
NET_ISO_EDGE_J2 = NET_ISO + "-edge" + J2_EXT
# TODO: dpaterson: migrating dell-environment template involves a bit of
# rework for ceph osd stuff, wait for now
# DELL_ENV_J2 = DELL_ENV + J2_EXT

EC2_IPCIDR = '169.254.169.254/32'
EC2_PUBLIC_IPCIDR_PARAM = 'EC2MetadataPublicIpCidr'


class Director(InfraHost):

    def __init__(self):

        self.settings = Settings.settings
        logger.info("Settings.settings: %s", str(Settings.settings))
        self.user = self.settings.director_install_account_user
        self.ip = self.settings.director_node.public_api_ip
        self.provisioning_ip = self.settings.director_node.provisioning_ip
        self.pwd = self.settings.director_install_account_pwd
        self.root_pwd = self.settings.director_node.root_password

        self.home_dir = "/home/" + self.user
        self.pilot_dir = os.path.join(self.home_dir, "pilot")
        self.sanity_dir = os.path.join(self.pilot_dir, "deployment-validation")
        self.images_dir = os.path.join(self.pilot_dir, "images")
        self.templates_dir = os.path.join(self.pilot_dir, "templates")
        self.nic_configs_dir = os.path.join(self.templates_dir,
                                            NIC_CONFIGS)
        self.validation_dir = os.path.join(self.pilot_dir,
                                           "deployment-validation")
        self.source_stackrc = 'source ' + self.home_dir + "/stackrc;"

        self.tempest_directory = os.path.join(self.home_dir,
                                              self.settings.tempest_workspace)
        self.tempest_conf = os.path.join(self.tempest_directory,
                                         "etc", TEMPEST_CONF)
        self.default_compute_services = []

        self.jinja2_env = Environment(
            loader=FileSystemLoader(self.settings.jinja2_templates))
         
        cmd = "mkdir -p " + self.pilot_dir
        self.run(cmd)

    def apply_internal_repos(self):
        # Add the internal repo. if going down that road,
        # Pull the target rpm's
        if self.settings.internal_repos is True:
            logger.debug(
                "Applying internal repo's to the "
                "director vm & reinstall rdo manager")
            count = 1
            for repo in self.settings.internal_repos_urls:
                cmd = 'curl ' + \
                      repo + \
                      " > /etc/yum.repos.d/internal_" + \
                      str(count) + \
                      ".repo"
                self.run_as_root(cmd)
                self.run_as_root("sed -i '/enabled=1/a priority=1' "
                                 "/etc/yum.repos.d/internal_" +
                                 str(count) + ".repo")
                count += 1
        else:
            for repo in self.settings.rhsm_repos:
                _, std_err, _ = self.run_as_root('subscription-manager repos '
                                                 '--enable=' + repo)
                if std_err:
                    logger.error("Unable to enable repo {}: {}".format(
                        repo, std_err))
                    sys.exit(1)

    def upload_update_conf_files(self):

        logger.debug("tar up the required pilot files")
        os.system("cd " +
                  self.settings.foreman_configuration_scripts +
                  ";tar -zcvf /root/pilot.tar.gz pilot common")
        self.upload_file("/root/pilot.tar.gz",
                         self.home_dir + "/pilot.tar.gz")

        self.run('cd;tar zxvf pilot.tar.gz')
        self.render_and_upload_undercloud_conf()

        #Configure containers-prepare-parameter.yaml to retrieve container images
        cmd = 'sed -i "s|[[:space:]]\+username: password|      ' + \
              self.settings.subscription_manager_user + ': ' + "'" + self.settings.subscription_manager_password + "'" + \
              '|" pilot/containers-prepare-parameter.yaml'
        self.run(cmd)

        if self.settings.version_locking_enabled is True:
            yaml = "/overcloud_images.yaml"
            source_file = self.settings.lock_files_dir + yaml
            dest_file = self.home_dir + yaml
            self.upload_file(source_file, dest_file)

            lock_file = "/unity_container_vlock.ini"
            source_file = self.settings.lock_files_dir + lock_file
            dest_file = self.home_dir + lock_file
            self.upload_file(source_file, dest_file)

            unity_lock_file = dest_file
            if self.settings.enable_unity_backend is True:
                cmd = "sudo grep cinder_unity_container_version " + \
                      unity_lock_file + \
                      " | awk -F '=' '{print $2}'"
                self.settings.cinder_unity_container_version = \
                    self.run_tty(cmd)[0].replace('\r', '').rstrip()
            if self.settings.enable_unity_manila_backend is True:
                cmd = "sudo grep manila_unity_container_version " + \
                      unity_lock_file + \
                      " | awk -F '=' '{print $2}'"
                self.settings.manila_unity_container_version = \
                    self.run_tty(cmd)[0].replace('\r', '').rstrip()


    def install_director(self):
        logger.info("Installing the undercloud")
        if self.settings.use_satellite:
            cmd = '~/pilot/install-director.sh --dns ' + \
                  self.settings.name_server + ' --director_ip ' + \
                  self.ip + ' --satellite_hostname ' + \
                  self.settings.satellite_hostname + ' --satellite_org ' + \
                  self.settings.satellite_org + ' --satellite_key ' + \
                  self.settings.satellite_activation_key
            if self.settings.pull_containers_from_satellite is True:
                cmd += " --containers_prefix " + \
                       self.settings.containers_prefix
        else:
            cmd = '~/pilot/install-director.sh --dns ' + \
                  self.settings.name_server + \
                  " --director_ip " + \
                  self.ip 

        if len(self.settings.overcloud_nodes_pwd) > 0:
            cmd += " --nodes_pwd " + self.settings.overcloud_nodes_pwd
        if self.settings.enable_powerflex_backend is True:
            cmd += " --enable_powerflex"
        stdout, stderr, exit_status = self.run(cmd)
        if exit_status:
            raise AssertionError("Director/Undercloud did not " +
                                 "install properly - see " +
                                 "/pilot/install-director.log" +
                                 " for details")

        # TODO: believe this was moved to deployer.py
        # tester = Checkpoints()
        # tester.verify_undercloud_installed()

    def upload_cloud_images(self):
        if self.settings.pull_images_from_cdn is False:
            logger.debug("Uploading cloud images to the Director vm")
            self.run("mkdir -p " + self.images_dir)

            self.upload_file(self.settings.discovery_ram_disk_image,
                             self.images_dir + "/discovery-ramdisk.tar")

            self.upload_file(self.settings.overcloud_image,
                             self.images_dir + "/overcloud-full.tar")
        else:
            pass

    def node_discovery(self):
        setts = self.settings
        if setts.use_custom_instack_json is True:
            logger.debug(
                "Using custom instack.json file - NOT scannings nodes")
            cmd = "rm " + self.home_dir + "/instackenv.json -f"
            self.run_tty(cmd)

            remote_file = self.home_dir + "/instackenv.json"
            self.upload_file(setts.custom_instack_json,
                             remote_file)
            cmd = "sudo chown " + setts.director_install_account_user + ":" + \
                setts.director_install_account_user + " " + remote_file
            self.run_tty(cmd)
        else:

            # In 13g servers, the iDRAC sends out a DHCP req every 3 seconds
            # for 1 minute.  If it still hasn't received a response, it sleeps
            # for 20 seconds and then repeats.  As a result, we sleep for 30
            # seconds here to make sure that every iDRAC has had a chance to
            # get a DHCP address prior to launching node discovery.
            time.sleep(30)

            setts = self.settings
            cmd = "cd ~/pilot/discover_nodes;./discover_nodes.py  -u " + \
                  setts.ipmi_user + \
                  " -p '" + setts.ipmi_password + "'"

            # Discover the nodes using DHCP for the iDRAC
            cmd += ' ' + setts.management_allocation_pool_start + "-" + \
                setts.management_allocation_pool_end

            # Discover the nodes using static IPs for the iDRAC
            for node in (self.settings.controller_nodes +
                         self.settings.compute_nodes +
                         self.settings.ceph_nodes +
                         self.settings.computehci_nodes +
                         self.settings.powerflex_nodes ):
                if hasattr(node, "idrac_ip"):
                    cmd += ' ' + node.idrac_ip
            # Add edge nodes if there are any defined
            for node_type, edge_site_nodes in setts.node_types_map.items():
                for edge_node in edge_site_nodes:
                    if hasattr(edge_node, "idrac_ip"):
                        cmd += ' ' + edge_node.idrac_ip

            cmd += '> ~/instackenv.json'

            self.run_tty(cmd)

            cmd = "ls -la ~/instackenv.json | awk '{print $5;}'"
            size = \
                self.run_tty(cmd)[0]
            if int(size) <= 50:
                logger.fatal("did not manage to pick up the nodes..")
                raise AssertionError(
                    "Unable to scan all the nodes ... need to go & pull "
                    "the plug(s) - " +
                    size + " - " +
                    size[0])

            else:
                logger.debug("nodes appear to have been picked up")

        logger.debug("Verify the number of nodes picked match up to settings")
        expected_nodes = (len(self.settings.controller_nodes)
                          + len(self.settings.compute_nodes)
                          + len(self.settings.ceph_nodes)
                          + len(self.settings.computehci_nodes)
                          + len(self.settings.powerflex_nodes))
        for node_type, nodes in setts.node_types_map.items():
            expected_nodes += len(nodes)

        found = self.run_tty(
            "grep pm_addr ~/instackenv.json | wc -l")[0].rstrip()
        logger.debug("Found " + found + " Expected : " + str(expected_nodes))
        if int(found) == expected_nodes:
            pass
        else:
            raise AssertionError(
                "Number of nodes in instackenv.json does not add up"
                " to the number of nodes defined in .properties file")

        if setts.use_ipmi_driver is True:
            logger.debug("Using pxe_ipmi driver")
            cmd = 'sed -i "s|pxe_drac|pxe_ipmitool|" ~/instackenv.json'
            self.run_tty(cmd)
        if self._has_edge_sites():
            self.update_instack_env_subnets_edge()

    def configure_idracs(self):
        setts = self.settings
        nodes = list(self.settings.controller_nodes)
        nodes.extend(self.settings.compute_nodes)
        nodes.extend(self.settings.computehci_nodes)
        nodes.extend(self.settings.ceph_nodes)
        nodes.extend(self.settings.powerflex_nodes)
        cmd = "~/pilot/config_idracs.py "

        for node_type, edge_site_nodes in setts.node_types_map.items():
            nodes.extend(edge_site_nodes)

        json_config = defaultdict(dict)
        for node in nodes:
            if hasattr(node, 'idrac_ip'):
                node_id = node.idrac_ip
            else:
                node_id = node.service_tag

            if hasattr(node, 'pxe_nic'):
                json_config[node_id]["pxe_nic"] = node.pxe_nic

            new_ipmi_password = setts.new_ipmi_password
            if new_ipmi_password:
                json_config[node_id]["password"] = new_ipmi_password
            if node.skip_nic_config:
                json_config[node_id]["skip_nic_config"] = node.skip_nic_config
        if json_config.items():
            cmd += "-j '{}'".format(json.dumps(json_config))

        stdout, stderr, exit_status = self.run(cmd)
        if exit_status:
            raise AssertionError("An error occurred while running "
                                 "config_idracs.  exit_status: {}, "
                                 "error: {}, stdout: {}".format(exit_status,
                                                                stderr,
                                                                stdout))

    def import_nodes(self):
        stdout, stderr, exit_status = self.run(self.source_stackrc
                                               + "~/pilot/import_nodes.py")
        if exit_status:
            raise AssertionError("Unable to import nodes into Ironic.  "
                                 "exit_status: {}, error: {}, "
                                 "stdout: {}".format(
                                     exit_status, stderr, stdout))

        tester = Checkpoints()
        tester.verify_nodes_registered_in_ironic()

    def node_introspection(self):
        setts = self.settings

        stdout, stderr, exit_status = self.run(
            self.source_stackrc + "~/pilot/prep_overcloud_nodes.py")
        if exit_status:
            raise AssertionError("An error occurred while running "
                                 "prep_overcloud_nodes.  exit_status: {}, "
                                 "error: {}, stdout: {}".format(exit_status,
                                                                stderr,
                                                                stdout))
        # Turning LLDP off before introspection
        lldp_off_cmd = "sudo sed -i 's/ipa-collect-lldp=1/ipa-collect-lldp=0/g' /var/lib/ironic/httpboot/inspector.ipxe"  # noqa
        self.run(lldp_off_cmd)

        introspection_cmd = self.source_stackrc + "~/pilot/introspect_nodes.py"
        if setts.use_in_band_introspection is True:
            introspection_cmd += " -i"

        stdout, stderr, exit_status = self.run(introspection_cmd)
        if exit_status:
            raise AssertionError("Unable to introspect nodes.  "
                                 "exit_status: {}, error: {}, "
                                 "stdout: {}".format(
                                     exit_status, stderr, stdout))

        tester = Checkpoints()
        tester.verify_introspection_sucessfull()

    def assign_role(self, node, role, index):
        assign_role_command = self._create_assign_role_command(
            node, role, index)
        stdout, stderr, exit_status = self.run(self.source_stackrc +
                                               "cd ~/pilot;" +
                                               assign_role_command)
        if exit_status:
            if hasattr(node, 'service_tag'):
                node_identifier = "service tag " + node.service_tag
            else:
                node_identifier = "ip " + node.idrac_ip
            raise AssertionError("Failed to assign {} role to {}: stdout={}, "
                                 "stderr={}, exit_status={}".format(
                                     role,
                                     node_identifier,
                                     stdout,
                                     stderr,
                                     exit_status))

    def assign_node_roles(self):
        setts = self.settings
        logger.debug("Assigning roles to nodes")
        osd_yaml = os.path.join(self.templates_dir, "ceph-osd-config.yaml")
        self.run("/bin/cp -rf " + osd_yaml + ".orig " + osd_yaml)
        common_path = os.path.join(os.path.expanduser(
            setts.cloud_repo_dir + '/src'), 'common')
        sys.path.append(common_path)
        from thread_helper import ThreadWithExHandling  # noqa

        roles_to_nodes = {}
        roles_to_nodes["controller"] = setts.controller_nodes
        roles_to_nodes["compute"] = setts.compute_nodes
        roles_to_nodes["storage"] = setts.ceph_nodes
        roles_to_nodes["computehci"] = setts.computehci_nodes
        roles_to_nodes["powerflex"] = setts.powerflex_nodes
        # Add edge nodes if there are any defined
        for node_type, edge_site_nodes in setts.node_types_map.items():
            roles_to_nodes[node_type] = edge_site_nodes

        threads = []
        for role in roles_to_nodes.keys():
            index = 0
            for node in roles_to_nodes[role]:

                thread = ThreadWithExHandling(logger,
                                              target=self.assign_role,
                                              args=(node, role, index))
                threads.append(thread)
                thread.start()
                index += 1

        for thread in threads:
            thread.join()

        failed_threads = 0
        for thread in threads:
            if thread.ex is not None:
                failed_threads += 1

        if failed_threads == 0:
            logger.info("Successfully assigned roles to all nodes")
        else:
            logger.info("assign_role failed on {} out of {} nodes".format(
                failed_threads, len(threads)))
            sys.exit(1)

    def update_sshd_conf(self):
        setts = self.settings
        # Update sshd_config to allow for more than 10 ssh sessions
        # Required for assign_role to run threaded if stamp has > 10 nodes
        non_sah_nodes = (setts.controller_nodes
                         + setts.compute_nodes
                         + setts.computehci_nodes
                         + setts.ceph_nodes
                         + setts.powerflex_nodes)

        for node_type, edge_site_nodes in setts.node_types_map.items():
            non_sah_nodes.extend(edge_site_nodes)
        # Allow for the number of nodes + a few extra sessions
        maxSessions = len(non_sah_nodes) + 10

        setts = ['MaxStartups', 'MaxSessions']
        for each in setts:
            re = self.run("sudo grep " + each +
                          " /etc/ssh/sshd_config")[0].rstrip()
            if re != each + " " + str(maxSessions):
                self.run_as_root('sed -i -e "\$a' + each + ' ' +
                                 str(maxSessions) +
                                 '" /etc/ssh/sshd_config')
        self.run_as_root("systemctl restart sshd")

    def revert_sshd_conf(self):
        # Revert sshd_config to its default
        cmds = [
            "sed -i '/MaxStartups/d' /etc/ssh/sshd_config",
            "sed -i '/MaxSessions/d' /etc/ssh/sshd_config",
            "systemctl restart sshd"
        ]
        for cmd in cmds:
            self.run_as_root(cmd)

    def setup_templates(self):
        """Re-upload the yaml files in the case where
        the undercloud is left intact but want to redeploy the overcloud
        with a different config.
        """

        self.setup_networking()
        if self._has_edge_sites():
            self.render_and_upload_roles_data_edge()
        self.setup_dell_storage()
        self.setup_manila()
        if self.settings.enable_powerflex_backend == False:
            self.setup_environment()
        self.setup_sanity_ini()

    def clamp_min_pgs(self, num_pgs):
        if num_pgs < 1:
            return 0

        pg_options = [8192, 4096, 2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4,
                      2, 1]

        option_index = 0
        finding_pg_value = True
        while finding_pg_value:
            if num_pgs >= pg_options[option_index]:
                num_pgs = pg_options[option_index]
                finding_pg_value = False
            else:
                option_index += 1

        return num_pgs

    def calc_pgs(self, num_osds, num_heavy_pools, num_other_pools):
        if num_osds == 0:
            return 0, 0
        replication_factor = 3
        max_pgs = num_osds * 200 / replication_factor
        total_pgs = max_pgs * 0.8
        total_heavy_pgs = total_pgs / 2
        heavy_pgs = total_heavy_pgs / num_heavy_pools
        heavy_pgs = self.clamp_min_pgs(heavy_pgs)

        heavy_pools_pgs = num_heavy_pools * heavy_pgs
        remaining_pgs = total_pgs - heavy_pools_pgs
        other_pgs = remaining_pgs / num_other_pools
        other_pgs = self.clamp_min_pgs(other_pgs)

        return heavy_pgs, other_pgs

    def calc_num_osds(self, default_osds_per_node):
        # Pull down the auto-generated OSD config file from the director
        local_file = self.settings.ceph_osd_config_yaml + '.director'
        remote_file = os.path.join('/home',
                                   self.settings.director_install_account_user,
                                   Settings.CEPH_OSD_CONFIG_FILE)
        self.download_file(local_file, remote_file)

        # Calculate the number of OSDs across the entire cluster
        total_osds = 0

        with open(local_file, 'r') as stream:
            osd_configs_yaml = yaml.load(stream)

        node_data_lookup_str = osd_configs_yaml["parameter_defaults"][
            "NodeDataLookup"]
        uuid_to_osd_configs = json.loads(json.dumps(node_data_lookup_str))
        for uuid in uuid_to_osd_configs:
            osd_config = uuid_to_osd_configs[uuid]
            num_osds = len(osd_config["devices"])
            total_osds = total_osds + num_osds

        num_storage_nodes = len(self.settings.ceph_nodes) + len(self.settings.computehci_nodes)
        num_unaccounted = num_storage_nodes - len(uuid_to_osd_configs)
        if num_unaccounted < 0:
            raise AssertionError("There are extraneous servers listed in {}. "
                                 "Unable to calculate the number of OSDs in "
                                 "the cluster.  Remove the bad entries from "
                                 "the file or discard the current generated "
                                 "OSD configration by copying {}.orig to "
                                 "{}.".format(
                                     self.settings.ceph_osd_config_yaml,
                                     self.settings.ceph_osd_config_yaml,
                                     self.settings.ceph_osd_config_yaml))

        total_osds = total_osds + (num_unaccounted * default_osds_per_node)

        return total_osds

    def setup_environment(self):
        logger.debug("Configuring Ceph storage settings for overcloud")

        # If the osd_disks were not specified then just return
        osd_disks = None
        if len(self.settings.computehci_nodes) > 0 and hasattr(self.settings.computehci_nodes[0], 'osd_disks'):
            if len(self.settings.ceph_nodes) > 0 and hasattr(self.settings.ceph_nodes[0], 'osd_disks'):
                # If the OSD disks are specified on the first storage node, then
                # use them.  This is the best we can do until the OSP Director
                # supports more than a single, global OSD configuration.
               osd_disks = self.settings.ceph_nodes[0].osd_disks
        src_file = open(self.settings.dell_env_yaml, 'r')

        # Temporary local file used to stage the modified environment file
        tmp_fd, tmp_name = tempfile.mkstemp()
        tmp_file = os.fdopen(tmp_fd, 'w')

        # Leading whitespace for these variables is critical !!!
        osds_param = "  CephAnsibleDisksConfig:"
        osd_scenario_param = "    osd_scenario:"
        osd_scenario = "lvm"
        osd_devices = "    devices:\n"
        ceph_pools = "  CephPools:"
        domain_param = "  CloudDomain:"
        rbd_backend_param = "  NovaEnableRbdBackend:"
        glance_backend_param = "  GlanceBackend:"
        rbd_cinder_backend_param = "  CinderEnableRbdBackend:"
        osds_per_node = 0

        if osd_disks:
            for osd in osd_disks:
                # Format is ":OSD_DRIVE",
                # so split on the ':'
                tokens = osd.split(':')

                # Make sure OSD_DRIVE begins with "/dev/"
                if not tokens[1].startswith("/dev/"):
                    tokens[1] += "/dev/"

                if len(tokens) == 2:
                    # Set all devices
                    osd_devices = "{}      - {}\n".format(
                        osd_devices, tokens[1])
                    osds_per_node += 1
                else:
                    logger.warning(
                        "Bad entry in osd_disks: {}".format(osd))

        total_osds = self.calc_num_osds(osds_per_node)
        if total_osds == 0:
            logger.info("Either the OSD configuration is not specified in "
                        "the .properties file or the storage nodes have "
                        "no available storage to dedicate to OSDs. Exiting")
            sys.exit(1)

        heavy_pgs, other_pgs = self.calc_pgs(total_osds,
                                             len(HEAVY_POOLS),
                                             len(OTHER_POOLS))

        found_osds_param = False
        for line in src_file:
            if osd_disks and line.startswith(osds_param):
                found_osds_param = True

            elif found_osds_param:
                # Discard lines that begin with "#", "osd_scenario",
                # "devices:" or "-" because these lines
                # represent the original ceph.yaml file's OSD configuration.
                tokens = line.split()
                if len(tokens) > 0 and (tokens[0].startswith("#") or
                                        tokens[0].startswith("osd_scenario") or
                                        tokens[0].startswith("devices") or
                                        tokens[0].startswith("-")):
                    continue

                # End of original Ceph OSD configuration: now write the new one
                tmp_file.write("{}\n".format(osds_param))
                tmp_file.write("{} {}\n".format(
                    osd_scenario_param, osd_scenario))
                tmp_file.write(osd_devices)

                # This is the line that follows the original Ceph OSD config
                tmp_file.write(line)
                found_osds_param = False

            elif line.startswith(domain_param):
                value = str(self.settings.domain).lower()
                tmp_file.write("{} {}\n".format(domain_param, value))

            elif line.startswith(rbd_backend_param):
                value = str(self.settings.enable_rbd_nova_backend).lower()
                tmp_file.write("{} {}\n".format(rbd_backend_param, value))

            elif line.startswith(glance_backend_param):
                value = str(self.settings.glance_backend).lower()
                tmp_file.write("{} {}\n".format(glance_backend_param, value))

            elif line.startswith(rbd_cinder_backend_param):
                value = str(self.settings.enable_rbd_backend).lower()
                tmp_file.write("{} {}\n".
                               format(rbd_cinder_backend_param, value))
            elif line.startswith(ceph_pools):
                pool_str = line[len(ceph_pools):]
                pools = json.loads(pool_str)
                for pool in pools:
                    if "rgw" in pool["name"]:
                        pool["application"] = "rgw"
                    elif "metric" in pool["name"]:
                        pool["application"] = "openstack_gnocchi"
                    else:
                        pool["application"] = "rbd"
                    if pool["name"] in HEAVY_POOLS:
                        pool["pg_num"] = heavy_pgs
                        pool["pgp_num"] = heavy_pgs
                    else:
                        pool["pg_num"] = other_pgs
                        pool["pgp_num"] = other_pgs

                tmp_file.write("{} {}\n".format(ceph_pools, json.dumps(pools)))
            else:
                tmp_file.write(line)

        src_file.close()
        tmp_file.close()

        env_name = os.path.join(self.templates_dir, DELL_ENV + ".yaml")
        self.upload_file(tmp_name, env_name)
        os.remove(tmp_name)
        # If we have edge sites we need to make another round trip
        # downloading and uploading dell-environment.yaml
        # TODO: Refactor above code so we can do all this work in one pass,
        # out of scope for JS 13.3, address in 16.1
        if self._has_edge_sites():
            self.render_and_upload_dell_environment_edge()

    # TODO: dpaterson, refactor to use ini parser like was done
    # in undercloud.conf
    def setup_sanity_ini(self):
        sanity_ini = self.sanity_dir + "/sanity.ini"
        self.upload_file(self.settings.sanity_ini,
                         sanity_ini)
        # Update the remote sanity ini file with the given settings
        cmds = [
            'sed -i "s|floating_ip_network=.*|floating_ip_network=' +
            self.settings.floating_ip_network +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|floating_ip_network_start_ip=.*|' +
            'floating_ip_network_start_ip=' +
            self.settings.floating_ip_network_start_ip +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|floating_ip_network_end_ip=.*|' +
            'floating_ip_network_end_ip=' +
            self.settings.floating_ip_network_end_ip +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|floating_ip_network_gateway=.*|'
            'floating_ip_network_gateway=' +
            self.settings.floating_ip_network_gateway +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|floating_ip_network_vlan=.*|floating_ip_network_vlan=' +
            self.settings.floating_ip_network_vlan +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|numa_enabled=.*|numa_enabled=' +
            str(self.settings.numa_enable) +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|hugepages_enabled=.*|hugepages_enabled=' +
            str(self.settings.hpg_enable) +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|ovs_dpdk_enabled=.*|ovs_dpdk_enabled=' +
            str(self.settings.enable_ovs_dpdk) +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|sriov_enabled=.*|sriov_enabled=' +
            str(self.settings.enable_sriov) +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|smart_nic_enabled=.*|smart_nic_enabled=' +
            str(self.settings.enable_smart_nic) +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|dvr_enabled=.*|dvr_enabled=' +
            str(self.settings.dvr_enable) +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|sanity_tenant_network=.*|sanity_tenant_network=' +
            self.settings.sanity_tenant_network +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|sanity_user_password=.*|sanity_user_password=' +
            self.settings.sanity_user_password +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|sanity_user_email=.*|sanity_user_email=' +
            self.settings.sanity_user_email +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|sanity_key_name=.*|sanity_key_name=' +
            self.settings.sanity_key_name +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|sanity_number_instances=.*|sanity_number_instances=' +
            str(self.settings.sanity_number_instances) +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|vlan_aware_sanity=.*|vlan_aware_sanity=' +
            self.settings.vlan_aware_sanity +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|sanity_image_url=.*|sanity_image_url=' +
            self.settings.sanity_image_url +
            '|" pilot/deployment-validation/sanity.ini',
            'sed -i "s|sanity_vlantest_network=.*|sanity_vlantest_network=' +
            self.settings.sanity_vlantest_network +
            '|" pilot/deployment-validation/sanity.ini'
        ]
        for cmd in cmds:
            self.run(cmd)

    def setup_dell_storage(self):

        # Re - Upload the yaml files in case we're trying to
        # leave the undercloud intact but want to redeploy with
        # a different config
        dell_storage_yaml = self.templates_dir + "/dell-cinder-backends.yaml"
        self.upload_file(self.settings.dell_storage_yaml,
                         dell_storage_yaml)
        # Backup before modifying
        self.run_tty("cp " + dell_storage_yaml +
                     " " + dell_storage_yaml + ".bak")

        self.setup_dellsc(dell_storage_yaml)

        # Dell Sc file
        dellsc_cinder_yaml = self.templates_dir + "/dellsc-cinder-config.yaml"
        self.upload_file(self.settings.dellsc_cinder_yaml,
                         dellsc_cinder_yaml)
        self.run_tty("cp " + dellsc_cinder_yaml +
                     " " + dellsc_cinder_yaml + ".bak")
        self.setup_dellsc(dellsc_cinder_yaml)

        # Unity is in a separate yaml file
        dell_unity_cinder_yaml = self.templates_dir + \
            "/dellemc-unity-cinder-backend.yaml"
        self.upload_file(self.settings.dell_unity_cinder_yaml,
                         dell_unity_cinder_yaml)

        dell_unity_cinder_container_yaml = self.templates_dir + \
            "/dellemc-unity-cinder-container.yaml"
        self.upload_file(self.settings.dell_unity_cinder_container_yaml,
                         dell_unity_cinder_container_yaml)

        # Backup before modifying
        self.run_tty("cp " + dell_unity_cinder_yaml +
                     " " + dell_unity_cinder_yaml + ".bak")
        self.run_tty("cp " + dell_unity_cinder_container_yaml +
                     " " + dell_unity_cinder_container_yaml + ".bak")

        self.setup_unity_cinder(dell_unity_cinder_yaml, \
                                dell_unity_cinder_container_yaml )

        # Powermax
        dell_powermax_iscsi_cinder_yaml = self.templates_dir + \
            "/dellemc-powermax-iscsi-cinder-backend.yaml"
        self.upload_file(self.settings.dell_powermax_iscsi_cinder_yaml,
                         dell_powermax_iscsi_cinder_yaml)
        dell_powermax_fc_cinder_yaml = self.templates_dir + \
            "/dellemc-powermax-fc-cinder-backend.yaml"
        self.upload_file(self.settings.dell_powermax_fc_cinder_yaml,
                         dell_powermax_fc_cinder_yaml)

       # Backup before modifying
        self.run_tty("cp " + dell_powermax_iscsi_cinder_yaml +
                     " " + dell_powermax_iscsi_cinder_yaml + ".bak")
        self.run_tty("cp " + dell_powermax_fc_cinder_yaml +
                     " " + dell_powermax_fc_cinder_yaml + ".bak")

        if self.settings.powermax_protocol == 'iSCSI':
            self.setup_powermax_cinder(dell_powermax_iscsi_cinder_yaml)
        else:
            self.setup_powermax_cinder(dell_powermax_fc_cinder_yaml)

        # PowerFlex
        dell_powerflex_cinder_yaml = self.templates_dir + \
            "/dellemc-powerflex-cinder-backend.yaml"
        self.upload_file(self.settings.dell_powerflex_cinder_yaml,
                         dell_powerflex_cinder_yaml)
        self.run_tty("cp " + dell_powerflex_cinder_yaml +
                     " " + dell_powerflex_cinder_yaml + ".bak")

        dell_powerflex_ansible_yaml = self.templates_dir  + \
            "/overcloud/environments/powerflex-ansible/powerflex-ansible.yaml"
        self.setup_powerflex(dell_powerflex_cinder_yaml,dell_powerflex_ansible_yaml)


        # Enable multiple backends now
        enabled_backends = "["

        if self.settings.enable_dellsc_backend is True:
            enabled_backends += "'tripleo_dellsc'"

        if self.settings.enable_unity_backend is True:
            enabled_backends += ",'tripleo_dellemc_unity'"

        if self.settings.enable_powermax_backend is True:
            enabled_backends += ",'tripleo_dellemc_powermax'"


        enabled_backends += "]"

        cmd = 'sed -i "s|<enable_rbd_backend>|' + \
            str(self.settings.enable_rbd_backend) + \
            '|" ' + dell_storage_yaml
        self.run_tty(cmd)

    def setup_manila(self):
        # Re - Upload the yaml files in case we're trying to
        # leave the undercloud intact but want to redeploy with
        # a different config
        unity_manila_yaml = self.templates_dir + "/unity-manila-config.yaml"
        self.upload_file(self.settings.unity_manila_yaml,
                         unity_manila_yaml)
        unity_manila_container_yaml = self.templates_dir + "/unity-manila-container.yaml"
        self.upload_file(self.settings.unity_manila_container_yaml,
                         unity_manila_container_yaml)

        # Backup before modifying
        self.run_tty("cp " + unity_manila_yaml +
                     " " + unity_manila_yaml + ".bak")
        self.run_tty("cp " + unity_manila_container_yaml +
                     " " + unity_manila_container_yaml + ".bak")

        self.setup_unity_manila(unity_manila_yaml, unity_manila_container_yaml)

        #  Now powermax
        powermax_manila_yaml = self.templates_dir + "/powermax-manila-config.yaml"
        self.upload_file(self.settings.powermax_manila_yaml,
                         powermax_manila_yaml)
        # Backup before modifying
        self.run_tty("cp " + powermax_manila_yaml +
                     " " + powermax_manila_yaml + ".bak")

        self.setup_powermax_manila(powermax_manila_yaml)

    def setup_dellsc(self, dellsc_cinder_yaml):

        if self.settings.enable_dellsc_backend is False:
            logger.debug("not setting up dellsc backend")
            return

        logger.debug("configuring dell sc backend")

        cmds = [
            'sed -i "s|<enable_dellsc_backend>|' +
            'True' + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_san_ip>|' +
            self.settings.dellsc_san_ip + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_san_login>|' +
            self.settings.dellsc_san_login + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_san_password>|' +
            self.settings.dellsc_san_password + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_ssn>|' +
            self.settings.dellsc_ssn + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_iscsi_ip_address>|' +
            self.settings.dellsc_iscsi_ip_address + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_iscsi_port>|' +
            self.settings.dellsc_iscsi_port + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_api_port>|' +
            self.settings.dellsc_api_port + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_server_folder>|' +
            self.settings.dellsc_server_folder + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_volume_folder>|' +
            self.settings.dellsc_volume_folder + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_second_san_ip>|' +
            self.settings.dellsc_second_san_ip + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_second_san_login>|' +
            self.settings.dellsc_second_san_login + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_second_san_password>|' +
            self.settings.dellsc_second_san_password + '|" ' +
            dellsc_cinder_yaml,
            'sed -i "s|<dellsc_second_api_port>|' +
            self.settings.dellsc_second_api_port + '|" ' + dellsc_cinder_yaml,
            'sed -i "s|<dellsc_excluded_domain_ip>|' +
            self.settings.dellsc_excluded_domain_ip + '|" ' +
            dellsc_cinder_yaml,
            'sed -i "s|<dellsc_multipath_xref>|' +
            self.settings.dellsc_multipath_xref + '|" ' + dellsc_cinder_yaml,
        ]
        for cmd in cmds:
            self.run_tty(cmd)
    def setup_unity_cinder(self, dell_unity_cinder_yaml, \
                           dell_unity_cinder_container_yaml):

        if self.settings.enable_unity_backend is False:
            logger.debug("Not setting up unity cinder backend.")
            return

        logger.debug("Configuring dell emc unity backend.")

        overcloud_images_file = self.home_dir + "/overcloud_images.yaml"

        cmds = [
            'sed -i "s|<unity_san_ip>|' +
            self.settings.unity_san_ip + '|" ' + dell_unity_cinder_yaml,
            'sed -i "s|<unity_san_login>|' +
            self.settings.unity_san_login + '|" ' + dell_unity_cinder_yaml,
            'sed -i "s|<unity_san_password>|' +
            self.settings.unity_san_password + '|" ' + dell_unity_cinder_yaml,
            'sed -i "s|<unity_storage_protocol>|' +
            self.settings.unity_storage_protocol + '|" ' +
            dell_unity_cinder_yaml,
            'sed -i "s|<unity_io_ports>|' +
            self.settings.unity_io_ports + '|" ' + dell_unity_cinder_yaml,
            'sed -i "s|<unity_storage_pool_names>|' +
            self.settings.unity_storage_pool_names + '|" ' +
            dell_unity_cinder_yaml,
        ]

        if self.settings.use_satellite:
            cinder_container = "openstack-cinder-volume-dellemc-rhosp16:" + \
                str(self.settings.cinder_unity_container_version) 
            remote_registry = self.settings.satellite_hostname + \
                ":5000/" 
            local_url = remote_registry + self.settings.containers_prefix + \
                cinder_container
            cmds.append('sed -i "s|ContainerCinderVolumeImage.*|' +
                        'ContainerCinderVolumeImage: ' + local_url +
                        '|" ' + dell_unity_cinder_container_yaml)
            cmds.append('sed -i "s|<dellemc_container_registry>|' + remote_registry +
                        '|" ' + dell_unity_cinder_container_yaml)             
        else:
            undercloud_domain_name = self.settings.director_node.hostname + \
                                 ".ctlplane.localdomain"
            cinder_container = "/dellemc/openstack-cinder-volume-dellemc-rhosp16:" + \
                str(self.settings.cinder_unity_container_version)
            remote_registry = "registry.connect.redhat.com"
            remote_url = remote_registry + cinder_container
            local_registry = self.provisioning_ip + ":8787"
            local_registry_domain = undercloud_domain_name + ":8787"
            local_url = local_registry_domain + cinder_container

            cmds.extend([
                'sudo podman login -u ' + self.settings.subscription_manager_user +
                ' -p ' + self.settings.subscription_manager_password +
                ' ' + remote_registry,
                'sudo podman pull ' + remote_url,
                'sudo openstack tripleo container image push --local ' + remote_url,
                'sudo podman tag ' + remote_url + ' ' + local_url,
                'sed -i "s|ContainerCinderVolumeImage.*|' +
                'ContainerCinderVolumeImage: ' + local_url +
                '|" ' + dell_unity_cinder_container_yaml,
                'sed -i "s|<dellemc_container_registry>|' + local_registry +
                '|" ' + dell_unity_cinder_container_yaml,
                'sed -i "s|<dellemc_container_registry_domain>|' + local_registry_domain +
                        '|" ' + dell_unity_cinder_container_yaml,
                'sudo podman logout ' + remote_registry,
            ])
        for cmd in cmds:
            self.run_tty(cmd)

    def setup_unity_manila(self, unity_manila_yaml, unity_manila_container_yaml):

        if self.settings.enable_unity_manila_backend is False:
            logger.debug("Not setting up unity manila backend.")
            return

        logger.debug("Configuring dell emc unity manila backend.")

        overcloud_images_file = self.home_dir + "/overcloud_images.yaml"

        cmds = ['sed -i "s|<manila_unity_driver_handles_share_servers>|' +
                self.settings.manila_unity_driver_handles_share_servers +
                '|" ' + unity_manila_yaml,
                'sed -i "s|<manila_unity_nas_login>|' +
                self.settings.manila_unity_nas_login + '|" ' +
                unity_manila_yaml,
                'sed -i "s|<manila_unity_nas_password>|' +
                self.settings.manila_unity_nas_password + '|" ' +
                unity_manila_yaml,
                'sed -i "s|<manila_unity_nas_server>|' +
                self.settings.manila_unity_nas_server + '|" ' +
                unity_manila_yaml,
                'sed -i "s|<manila_unity_server_meta_pool>|' +
                self.settings.manila_unity_server_meta_pool + '|" ' +
                unity_manila_yaml,
                'sed -i "s|<manila_unity_share_data_pools>|' +
                self.settings.manila_unity_share_data_pools + '|" ' +
                unity_manila_yaml,
                'sed -i "s|<manila_unity_ethernet_ports>|' +
                self.settings.manila_unity_ethernet_ports + '|" ' +
                unity_manila_yaml,
                'sed -i "s|<manila_unity_ssl_cert_verify>|' +
                self.settings.manila_unity_ssl_cert_verify + '|" ' +
                unity_manila_yaml,
                'sed -i "s|<manila_unity_ssl_cert_path>|' +
                self.settings.manila_unity_ssl_cert_path + '|" ' +
                unity_manila_yaml,
                ]

        if self.settings.use_satellite:
            manila_container = "openstack-manila-share-dellemc-rhosp16" + \
                ':' + str(self.settings.manila_unity_container_version)
            remote_registry = self.settings.satellite_hostname + \
                ":5000/"
            local_url = remote_registry + self.settings.containers_prefix + \
                manila_container
            cmds.append('sed -i "s|ContainerManilaShareImage.*|' +
                        'ContainerManilaShareImage: ' + local_url +
                        '|" ' + unity_manila_container_yaml)
            cmds.append('sed -i "s|<undercloud_registry>|' + remote_registry +
                        '|" ' + unity_manila_container_yaml)

        else:
            undercloud_domain_name = self.settings.director_node.hostname + \
                                ".ctlplane.localdomain"
            manila_container = "/dellemc/openstack-manila-share-dellemc-rhosp16:" + \
                               str(self.settings.manila_unity_container_version)
            remote_registry = "registry.connect.redhat.com"
            remote_url = remote_registry + manila_container
            local_registry = self.provisioning_ip + ":8787"
            local_registry_domain = undercloud_domain_name + ":8787"
            local_url = local_registry_domain + manila_container

            cmds.extend([
                'sudo podman login -u ' + self.settings.subscription_manager_user +
                ' -p ' + self.settings.subscription_manager_password +
                ' ' + remote_registry,
                'sudo podman pull ' + remote_url,
                'sudo openstack tripleo container image push --local ' + remote_url,
                'sudo podman tag ' + remote_url + ' ' + local_url,
                'sed -i "s|ContainerManilaShareImage.*|' +
                'ContainerManilaShareImage: ' + local_url +
                '|" ' + unity_manila_container_yaml,
                'sed -i "s|<dellemc_container_registry>|' + local_registry +
                '|" ' + unity_manila_container_yaml,
                'sed -i "s|<dellemc_container_registry_domain>|' + local_registry_domain +
                        '|" ' + unity_manila_container_yaml,
                'sudo podman logout ' + remote_registry,
            ])

        for cmd in cmds:
            self.run_tty(cmd)


    def setup_powermax_cinder(self, powermax_cinder_yaml):

        if self.settings.enable_powermax_backend is False:
            logger.debug("not setting up powermax backend")
            return

        logger.debug("configuring powermax backend")

        cmds = [
            'sed -i "s|<enable_powermax_backend>|' +
            'True' + '|" ' + powermax_cinder_yaml,
            'sed -i "s|<powermax_san_ip>|' +
            self.settings.powermax_san_ip + '|" ' + powermax_cinder_yaml,
            'sed -i "s|<powermax_san_login>|' +
            self.settings.powermax_san_login + '|" ' + powermax_cinder_yaml,
            'sed -i "s|<powermax_san_password>|' +
            self.settings.powermax_san_password + '|" ' + powermax_cinder_yaml,
            'sed -i "s|<powermax_array>|' +
            self.settings.powermax_array + '|" ' + powermax_cinder_yaml,
            'sed -i "s|<powermax_port_groups>|' +
            self.settings.powermax_port_groups + '|" ' + powermax_cinder_yaml,
            'sed -i "s|<powermax_srp>|' +
            self.settings.powermax_srp + '|" ' + powermax_cinder_yaml,
        ]
        for cmd in cmds:
            self.run_tty(cmd)

    def setup_powermax_manila(self, powermax_manila_yaml):

        if self.settings.enable_powermax_manila_backend is False:
            logger.debug("Not setting up powermax manila backend.")
            return

        logger.debug("Configuring dell emc powermax manila backend.")

        cmds = ['sed -i "s|<manila_powermax_driver_handles_share_servers>|' +
                self.settings.manila_powermax_driver_handles_share_servers +
                '|" ' + powermax_manila_yaml,
                'sed -i "s|<manila_powermax_nas_login>|' +
                self.settings.manila_powermax_nas_login + '|" ' +
                powermax_manila_yaml,
                'sed -i "s|<manila_powermax_nas_password>|' +
                self.settings.manila_powermax_nas_password + '|" ' +
                powermax_manila_yaml,
                'sed -i "s|<manila_powermax_nas_server>|' +
                self.settings.manila_powermax_nas_server + '|" ' +
                powermax_manila_yaml,
                'sed -i "s|<manila_powermax_server_container>|' +
                self.settings.manila_powermax_server_container + '|" ' +
                powermax_manila_yaml,
                'sed -i "s|<manila_powermax_share_data_pools>|' +
                self.settings.manila_powermax_share_data_pools + '|" ' +
                powermax_manila_yaml,
                'sed -i "s|<manila_powermax_ethernet_ports>|' +
                self.settings.manila_powermax_ethernet_ports + '|" ' +
                powermax_manila_yaml,
                ]
        for cmd in cmds:
            self.run_tty(cmd)

    def setup_powerflex(self, powerflex_cinder_yaml, powerflex_ansible_yaml):

        if self.settings.enable_powerflex_backend is False:
            logger.debug("Not setting up powerflex backend.")
            return

        logger.debug("Configuring dell emc powerflex backend.")

        cmds = [ 'sed -i "s|<powerflex_san_ip>|' +
                self.settings.powerflexgw_vm.storage_ip +
                '|" ' + powerflex_cinder_yaml,
                'sed -i "s|<powerflex_san_login>|' +
                self.settings.powerflex_san_login +
                '|" ' + powerflex_cinder_yaml,
                'sed -i "s|<powerflex_san_password>|' +
                self.settings.powerflex_san_password +
                '|" ' + powerflex_cinder_yaml,
                'sed -i "s|<powerflex_storage_pools>|' +
                self.settings.powerflex_storage_pools +
                '|" ' + powerflex_cinder_yaml,
                ]
        for cmd in cmds:
            self.run_tty(cmd)

        logger.debug("Configuring ansible playbook for powerflex deployment.")

        cmds = ['sed -i "s|<powerflex_rpms_method>|' +
                self.settings.powerflex_rpms_method +
                '|" ' + powerflex_ansible_yaml,
                'sed -i "s|<powerflex_rpms_path>|' +
                self.settings.powerflex_rpms_path +
                '|" ' + powerflex_ansible_yaml,
                'sed -i "s|<powerflex_cluster_name>|' +
                self.settings.powerflex_cluster_name +
                '|" ' + powerflex_ansible_yaml,
                'sed -i "s|<powerflex_protection_domain>|' +
                self.settings.powerflex_protection_domain +
                '|" ' + powerflex_ansible_yaml,
                'sed -i "s|<powerflex_storage_pool>|' +
                self.settings.powerflex_storage_pool +
                '|" ' + powerflex_ansible_yaml,
                'sed -i "s|<powerflex_cluster_config>|' +
                self.settings.powerflex_cluster_config +
                '|" ' + powerflex_ansible_yaml,
                'sed -i "s|<powerflex_mgmt_interface>|' +
                self.settings.powerflex_mgmt_interface +
                '|" ' + powerflex_ansible_yaml,
                'sed -i "s|<powerflex_cluster_interface>|' +
                self.settings.powerflex_cluster_interface +
                '|" ' + powerflex_ansible_yaml,
                'sed -i "s|<powerflex_cluster_vip>|' +
                self.settings.powerflex_cluster_vip +
                '|" ' + powerflex_ansible_yaml,
                'sed -i "s|<powerflex_rebuild_interface>|' +
                self.settings.powerflex_rebuild_interface +
                '|" ' + powerflex_ansible_yaml,
                'sed -i "s|<powerflex_password>|' +
                self.settings.powerflex_password +
                '|" ' + powerflex_ansible_yaml,
                'sed -i "s|<powerflex_lia_token>|' +
                self.settings.powerflex_lia_token +
                '|" ' + powerflex_ansible_yaml,
                ]
        for cmd in cmds:
            self.run_tty(cmd)


    def setup_net_envt(self):

        logger.debug("Configuring network-environment.yaml for overcloud")

        network_yaml = self.templates_dir + "/network-environment.yaml"
        octavia_yaml = self.templates_dir + "/octavia.yaml"

        self.upload_file(self.settings.network_env_yaml,
                         network_yaml)

        if self.settings.octavia_user_certs_keys is True:
            self.upload_file(self.settings.certificate_keys_path,
                             self.templates_dir + "/cert_keys.yaml")
            self.run_tty('sed -i "s|OctaviaGenerateCerts:.*|' +
                         'OctaviaGenerateCerts: ' +
                         'false' + '|" ' +
                         str(octavia_yaml))

        if self.settings.octavia_user_certs_keys is False:
            self.run_tty('sed -i "s|OctaviaGenerateCerts:.*|' +
                         'OctaviaGenerateCerts: ' +
                         'true' + '|" ' +
                         str(octavia_yaml))

        cmds = [
            'sed -i "s|ControlPlaneDefaultRoute:.*|' +
            'ControlPlaneDefaultRoute: ' +
            self.settings.director_node.provisioning_ip + '|" ' +
            network_yaml,
            'sed -i "s|EC2MetadataIp:.*|EC2MetadataIp: ' +
            self.settings.director_node.provisioning_ip + '|" ' +
            network_yaml,
            'sed -i "s|InternalApiNetCidr:.*|InternalApiNetCidr: ' +
            self.settings.private_api_network + '|" ' + network_yaml,
            'sed -i "s|StorageNetCidr:.*|StorageNetCidr: ' +
            self.settings.storage_network + '|" ' + network_yaml,
            'sed -i "s|StorageMgmtNetCidr:.*|StorageMgmtNetCidr: ' +
            self.settings.storage_cluster_network + '|" ' + network_yaml,
            'sed -i "s|ExternalNetCidr:.*|ExternalNetCidr: ' +
            self.settings.public_api_network + '|" ' + network_yaml,
            'sed -i "s|ManagementAllocationPools:.*|'
            'ManagementAllocationPools: ' +
            "[{'start': '" + self.settings.management_allocation_pool_start +
            "', 'end': '" + self.settings.management_allocation_pool_end +
            "'}]"   '|" ' + network_yaml,
            'sed -i "s|InternalApiAllocationPools:.*|'
            'InternalApiAllocationPools: ' +
            "[{'start': '" + self.settings.private_api_allocation_pool_start +
            "', 'end': '" + self.settings.private_api_allocation_pool_end +
            "'}]"   '|" ' + network_yaml,
            'sed -i "s|StorageAllocationPools:.*|StorageAllocationPools: ' +
            "[{'start': '" + self.settings.storage_allocation_pool_start +
            "', 'end': '" +
            self.settings.storage_allocation_pool_end + "'}]"   '|" ' +
            network_yaml,
            'sed -i "s|StorageMgmtAllocationPools:.*|'
            'StorageMgmtAllocationPools: ' +
            "[{'start': '" +
            self.settings.storage_cluster_allocation_pool_start +
            "', 'end': '" +
            self.settings.storage_cluster_allocation_pool_end + "'}]"   '|" ' +
            network_yaml,
            'sed -i "s|ExternalAllocationPools:.*|ExternalAllocationPools: ' +
            "[{'start': '" + self.settings.public_api_allocation_pool_start +
            "', 'end': '" +
            self.settings.public_api_allocation_pool_end + "'}]"   '|" ' +
            network_yaml,
            'sed -i "s|ExternalInterfaceDefaultRoute:.*|'
            'ExternalInterfaceDefaultRoute: ' +
            self.settings.public_api_gateway + '|" ' + network_yaml,
            'sed -i "s|ManagementNetworkGateway:.*|'
            'ManagementNetworkGateway: ' +
            self.settings.management_gateway + '|" ' + network_yaml,
            'sed -i "s|ManagementNetCidr:.*|ManagementNetCidr: ' +
            self.settings.management_network + '|" ' + network_yaml,
            'sed -i "s|ProvisioningNetworkGateway:.*|'
            'ProvisioningNetworkGateway: ' +
            self.settings.provisioning_gateway + '|" ' + network_yaml,
            'sed -i "s|ControlPlaneDefaultRoute:.*|' +
            'ControlPlaneDefaultRoute: ' +
            self.settings.director_node.provisioning_ip +
            '|" ' + network_yaml,
            "sed -i 's|ControlPlaneSubnetCidr:.*|ControlPlaneSubnetCidr: " +
            '"' +
            self.settings.provisioning_network.split("/")[
                1] + '"' + "|' " + network_yaml,
            'sed -i "s|ControlPlaneNetCidr:.*|' +
            'ControlPlaneNetCidr: ' +
            self.settings.provisioning_network +
            '|" ' + network_yaml,
            'sed -i "s|EC2MetadataIp:.*|EC2MetadataIp: ' +
            self.settings.director_node.provisioning_ip + '|" ' + network_yaml,
            "sed -i 's|DnsServers:.*|DnsServers: " + '["' +
            self.settings.name_server + '"]|' + "' " + network_yaml,
            'sed -i "s|InternalApiNetworkVlanID:.*|' +
            'InternalApiNetworkVlanID: ' +
            self.settings.private_api_vlanid + '|" ' + network_yaml,
            'sed -i "s|StorageNetworkVlanID:.*|StorageNetworkVlanID: ' +
            self.settings.storage_vlanid + '|" ' + network_yaml,
            'sed -i "s|StorageMgmtNetworkVlanID:.*|' +
            'StorageMgmtNetworkVlanID: ' +
            self.settings.storage_cluster_vlanid + '|" ' + network_yaml,
            'sed -i "s|ExternalNetworkVlanID:.*|ExternalNetworkVlanID: ' +
            self.settings.public_api_vlanid + '|" ' + network_yaml,
            'sed -i "s|TenantNetworkVlanID:.*|TenantNetworkVlanID: ' +
            self.settings.tenant_tunnel_vlanid + '|" ' + network_yaml,
            'sed -i "s|ExternalMtu:.*|ExternalMtu: ' +
            self.settings.public_api_network_mtu + '|" ' + network_yaml,
            'sed -i "s|InternalApiMtu:.*|InternalApiMtu: ' +
            self.settings.private_api_network_mtu + '|" ' + network_yaml,
            'sed -i "s|StorageMtu:.*|StorageMtu: ' +
            self.settings.storage_network_mtu + '|" ' + network_yaml,
            'sed -i "s|StorageMgmtMtu:.*|StorageMgmtMtu: ' +
            self.settings.storage_cluster_network_mtu + '|" ' + network_yaml,
            'sed -i "s|TenantMtu:.*|TenantMtu: ' +
            self.settings.tenant_tunnel_network_mtu + '|" ' + network_yaml,
            'sed -i "s|ProvisioningMtu:.*|ProvisioningMtu: ' +
            self.settings.provisioning_network_mtu + '|" ' + network_yaml,
            'sed -i "s|ManagementMtu:.*|ManagementMtu: ' +
            self.settings.management_network_mtu + '|" ' + network_yaml,
            'sed -i "s|DefaultBondMtu:.*|DefaultBondMtu: ' +
            self.settings.default_bond_mtu + '|" ' + network_yaml,
            'sed -i "s|NeutronGlobalPhysnetMtu:.*|NeutronGlobalPhysnetMtu: ' +
            self.settings.tenant_network_mtu + '|" ' + network_yaml,
            'sed -i "s|neutron::plugins::ml2::physical_network_mtus:.*|neutron'
            '::plugins::ml2::physical_network_mtus: [\'physext:' +
            self.settings.floating_ip_network_mtu + '\']|" ' + network_yaml,
        ]

        if self.settings.tenant_tunnel_network:
            cmds += [
                'sed -i "s|TenantNetCidr:.*|TenantNetCidr: ' +
                self.settings.tenant_tunnel_network + '|" ' + network_yaml,
                'sed -i "s|TenantAllocationPools:.*|TenantAllocationPools: ' +
                "[{'start': '" +
                self.settings.tenant_tunnel_network_allocation_pool_start +
                "', 'end': '" +
                self.settings.tenant_tunnel_network_allocation_pool_end +
                "'}]"   '|" ' + network_yaml,
            ]
        for cmd in cmds:
            self.run_tty(cmd)

        if self._has_edge_sites():
            self.render_and_upload_network_environment_edge()

    def configure_dhcp_server(self):
        cmd = 'cd ' + self.pilot_dir + ';./config_idrac_dhcp.py ' + \
            self.settings.sah_node.provisioning_ip + \
            ' -p ' + self.settings.sah_node.root_password
        stdout, stderr, exit_status = self.run(cmd)
        if exit_status:
            raise AssertionError(
                "Failed to configure DHCP on the SAH node.  exit_status: {}, "
                "error: {}, stdout: {}".format(exit_status, stderr, stdout))

    def setup_networking(self):
        logger.debug("Configuring network settings for overcloud")

        static_ips_yaml = self.templates_dir + "/static-ip-environment.yaml"
        static_vip_yaml = self.templates_dir + "/static-vip-environment.yaml"
        neutron_ovs_dpdk_yaml = self.templates_dir + "/neutron-ovs-dpdk.yaml"
        neutron_sriov_yaml = self.templates_dir + "/neutron-sriov.yaml"

        if self.settings.enable_ovs_dpdk is True:
            self.set_ovs_dpdk_driver(self.settings.neutron_ovs_dpdk_yaml)

        # Re - Upload the yaml files in case we're trying to
        # leave the undercloud intact but want to redeploy
        # with a different config
        self.upload_file(self.settings.static_ips_yaml, static_ips_yaml)
        self.upload_file(self.settings.static_vip_yaml, static_vip_yaml)
        self.upload_file(self.settings.neutron_ovs_dpdk_yaml,
                         neutron_ovs_dpdk_yaml)
        self.upload_file(self.settings.neutron_sriov_yaml, neutron_sriov_yaml)

        self.setup_nic_configuration()

        if self.settings.enable_sriov is True:
            self.setup_sriov_nic_configuration()

        if self.settings.overcloud_static_ips is True:
            logger.debug("Updating static_ips yaml for the overcloud nodes")
            # static_ips_yaml
            control_external_ips = ''
            control_private_ips = ''
            control_storage_ips = ''
            control_tenant_tunnel_ips = ''
            for node in self.settings.controller_nodes:
                control_external_ips += "    - " + node.public_api_ip
                control_private_ips += "    - " + node.private_api_ip
                control_storage_ips += "    - " + node.storage_ip
                control_tenant_tunnel_ips += "    - " + node.tenant_tunnel_ip
                if node != self.settings.controller_nodes[-1]:
                    control_external_ips += "\\n"
                    control_private_ips += "\\n"
                    control_storage_ips += "\\n"
                    control_tenant_tunnel_ips += "\\n"

            compute_tenant_tunnel_ips = ''
            compute_private_ips = ''
            compute_storage_ips = ''
            compute_storage_cluster_ip = ''

            for node in self.settings.compute_nodes:
                compute_tenant_tunnel_ips += "    - " + node.tenant_tunnel_ip
                compute_private_ips += "    - " + node.private_api_ip
                compute_storage_ips += "    - " + node.storage_ip
                if node != self.settings.compute_nodes[-1]:
                    compute_tenant_tunnel_ips += "\\n"
                    compute_private_ips += "\\n"
                    compute_storage_ips += "\\n"

            computehci_tenant_tunnel_ips =''
            computehci_private_ips = ''
            computehci_storage_ips = ''
            computehci_cluster_ips = ''

            for node in self.settings.computehci_nodes:
                computehci_tenant_tunnel_ips += "    - " + node.tenant_tunnel_ip
                computehci_private_ips += "    - " + node.private_api_ip
                computehci_storage_ips += "    - " + node.storage_ip
                computehci_cluster_ips += "    - " + node.storage_cluster_ip
                if node != self.settings.computehci_nodes[-1]:
                    computehci_tenant_tunnel_ips += "\\n"
                    computehci_private_ips += "\\n"
                    computehci_storage_ips += "\\n"
                    computehci_cluster_ips += "\\n"

            powerflex_private_ips = ''
            powerflex_storage_ips = ''
            powerflex_cluster_ips = ''

            for node in self.settings.powerflex_nodes:
                powerflex_private_ips += "    - " + node.private_api_ip
                powerflex_storage_ips += "    - " + node.storage_ip
                powerflex_cluster_ips += "    - " + node.storage_cluster_ip
                if node != self.settings.powerflex_nodes[-1]:
                    powerflex_private_ips += "\\n"
                    powerflex_storage_ips += "\\n"
                    powerflex_cluster_ips += "\\n"


            storage_storgage_ip = ''
            storage_cluster_ip = ''
            for node in self.settings.ceph_nodes:
                storage_storgage_ip += "    - " + node.storage_ip
                storage_cluster_ip += "    - " + node.storage_cluster_ip
                if node != self.settings.ceph_nodes[-1]:
                    storage_storgage_ip += "\\n"
                    storage_cluster_ip += "\\n"

            cmds = ['sed -i "/192.168/d" ' + static_ips_yaml,
                    'sed -i "/ControllerIPs:/,/NovaComputeIPs:/ \
                    s/tenant:/tenant: \\n' +
                    control_tenant_tunnel_ips + "/\" " + static_ips_yaml,
                    'sed -i "/ControllerIPs:/,/NovaComputeIPs:/ \
                    s/external:/external: \\n' +
                    control_external_ips + "/\" " + static_ips_yaml,
                    'sed -i "/ControllerIPs:/,/NovaComputeIPs:/ \
                    s/internal_api:/internal_api: \\n' +
                    control_private_ips + "/\" " + static_ips_yaml,
                    'sed -i "/ControllerIPs:/,/NovaComputeIPs:/ \
                    s/storage:/storage: \\n' +
                    control_storage_ips + "/\" " + static_ips_yaml,
                    'sed -i "/DellComputeIPs:/,/CephStorageIPs:/ \
                    s/tenant:/tenant: \\n' +
                    compute_tenant_tunnel_ips + "/\" " + static_ips_yaml,
                    'sed -i "/DellComputeIPs:/,/CephStorageIPs:/ \
                    s/internal_api:/internal_api: \\n' +
                    compute_private_ips + "/\" " + static_ips_yaml,
                    'sed -i "/DellComputeIPs:/,/CephStorageIPs:/ \
                    s/storage:/storage: \\n' +
                    compute_storage_ips + "/\" " + static_ips_yaml,
                    'sed -i "/CephStorageIPs:/,/$p/ s/storage:/storage: \\n' +
                    storage_storgage_ip + "/\" " + static_ips_yaml,
                    'sed -i "/CephStorageIPs:/,/$p/ \
                    s/storage_mgmt:/storage_mgmt: \\n' +
                    storage_cluster_ip + "/\" " + static_ips_yaml
                    ]
            if len(self.settings.computehci_nodes) > 0:
                cmds.extend(['sed -i "/DellComputeHCIIPs:/,/tenant:/s/tenant:/tenant: \\n' +
                           computehci_tenant_tunnel_ips + "/\" " + static_ips_yaml,
                           'sed -i "/DellComputeHCIIPs:/,/internal_api:/s/internal_api:/internal_api: \\n' +
                           computehci_private_ips + "/\" " + static_ips_yaml,
                           'sed -i "/DellComputeHCIIPs:/,/storage:/s/storage:/storage: \\n' +
                           computehci_storage_ips + "/\" " + static_ips_yaml,
                           'sed -i "/DellComputeHCIIPs:/,/storage_mgmt:/s/storage_mgmt:/storage_mgmt: \\n' +
                           computehci_cluster_ips + "/\" " + static_ips_yaml
                          ])
            if len(self.settings.powerflex_nodes) > 0:
                cmds.extend(['sed -i "/PowerflexStorageIPs:/,/internal_api:/s/internal_api:/internal_api: \\n' +
                           powerflex_private_ips + "/\" " + static_ips_yaml,
                           'sed -i "/PowerflexStorageIPs:/,/storage:/s/storage:/storage: \\n' +
                           powerflex_storage_ips + "/\" " + static_ips_yaml,
                           'sed -i "/PowerflexStorageIPs:/,/storage_mgmt:/s/storage_mgmt:/storage_mgmt: \\n' +
                           powerflex_cluster_ips + "/\" " + static_ips_yaml
                           ])

            for cmd in cmds:
                self.run_tty(cmd)

        if self.settings.use_static_vips is True:
            logger.debug("Updating static vip yaml")
            cmds = ["""sed -i "s/RedisVirtualFixedIPs: .*/RedisVirtualFixedIPs: [{'ip_address':'""" +
                    self.settings.redis_vip + """'}]/" """ + static_vip_yaml,
                    """sed -i "s/ControlFixedIPs: .*/ControlFixedIPs: [{'ip_address':'""" +
                    self.settings.provisioning_vip + """'}]/" """ + static_vip_yaml,
                    """sed -i "s/InternalApiVirtualFixedIPs: .*/InternalApiVirtualFixedIPs: [{'ip_address':'""" +
                    self.settings.private_api_vip + """'}]/" """ + static_vip_yaml,
                    """sed -i "s/PublicVirtualFixedIPs: .*/PublicVirtualFixedIPs: [{'ip_address':'""" +
                    self.settings.public_api_vip + """'}]/" """ + static_vip_yaml,
                    """sed -i "s/StorageVirtualFixedIPs: .*/StorageVirtualFixedIPs: [{'ip_address':'""" +
                    self.settings.storage_vip + """'}]/" """ + static_vip_yaml,
                    """sed -i "s/StorageMgmtVirtualFixedIPs: .*/StorageMgmtVirtualFixedIPs: [{'ip_address':'""" +
                    self.settings.storage_cluster_vip + """'}]/" """ + static_vip_yaml
                    # 'sed -i "s/redis: .*/redis: ' +
                    # self.settings.redis_vip + '/" ' + static_vip_yaml,
                    # 'sed -i "s/ControlPlaneIP: .*/ControlPlaneIP: ' +
                    # self.settings.provisioning_vip + '/" ' + static_vip_yaml,
                    # 'sed -i "s/InternalApiNetworkVip: ' +
                    # '.*/InternalApiNetworkVip: ' +
                    # self.settings.private_api_vip + '/" ' + static_vip_yaml,
                    # 'sed -i "s/ExternalNetworkVip: ' +
                    # '.*/ExternalNetworkVip: ' +
                    # self.settings.public_api_vip + '/" ' + static_vip_yaml,
                    # 'sed -i "s/StorageNetworkVip: ' +
                    # '.*/StorageNetworkVip: ' +
                    # self.settings.storage_vip + '/" ' + static_vip_yaml,
                    # 'sed -i "s/StorageMgmtNetworkVip: ' +
                    # '.*/StorageMgmtNetworkVip: ' +
                    # self.settings.storage_cluster_vip + '/" ' + static_vip_yaml
                    ]
            for cmd in cmds:
                self.run_tty(cmd)

        if self._has_edge_sites():
            self.render_and_upload_network_data()
            self.render_and_upload_network_data_edge()
            self.render_and_upload_network_environment_edge()
            self.render_and_upload_network_isolation_edge()
            self.render_and_upload_node_placement_edge()
            self.render_and_upload_nic_env_edge()
            self.render_and_upload_compute_templates_edge()

            if self.settings.overcloud_static_ips is True:
                self.render_and_upload_static_ips_edge()

    def setup_nic_configuration(self):
        # Upload all yaml files in the NIC config directory
        local_nic_env_file_path = self.settings.nic_env_file_path
        local_nic_configs_dir = os.path.dirname(local_nic_env_file_path)
        nic_config_dirname = os.path.dirname(self.settings.nic_env_file)
        for nic_config_file in os.listdir(local_nic_configs_dir):
            if nic_config_file.endswith(".yaml"):
                local_file_path = os.path.join(local_nic_configs_dir,
                                               nic_config_file)
                remote_file_path = os.path.join(self.nic_configs_dir,
                                                nic_config_dirname,
                                                nic_config_file)
                logger.info("Uploading {} to {} on the director node".format(
                    local_file_path, remote_file_path))
                self.upload_file(local_file_path, remote_file_path)

        # Get the user supplied NIC settings from the .ini
        ini_nics_settings = self.settings.get_curated_nics_settings()

        # Build up a series of sed commands to perform variable substitution
        # in the NIC environment file
        cmds = []
        remote_file = os.path.join(self.nic_configs_dir,
                                   self.settings.nic_env_file)
        for setting_name, setting_value in ini_nics_settings.items():
            # The following is executing a sed command of the following format:
            # sed -i -r 's/(^\s*StorageBond0Interface1:\s*).*/\1p1p2/'
            cmds.append('sed -i -r \'s/(^\s*' + setting_name +    # noqa: W605
                        ':\s*).*/\\1' + setting_value + '/\' ' + remote_file)

        # Execute the commands
        for cmd in cmds:
            self.run(cmd)

    def setup_sriov_nic_configuration(self):
        logger.debug("setting SR-IOV environment")
        # Get settings from .ini file
        ini_nics_settings = self.settings.get_curated_nics_settings()

        cmds = []
        env_file = os.path.join(self.templates_dir, "neutron-sriov.yaml")

        # Get and sort the SR-IOV interfaces that user provided
        sriov_interfaces = self.get_sriov_compute_interfaces()
        interfaces = "'" + ",".join(sriov_interfaces) + "'"

        # Build up the sed command to perform variable substitution
        # in the neutron-sriov.yaml (sriov environment file)

        # Specify number of VFs for sriov mentioned interfaces
        sriov_map_setting = []
        sriov_pci_passthrough = []
        physical_network = ["physint", "physint1", "physint2", "physint3"]
        check = 0
        for interface in sriov_interfaces:
            devname = interface
            if (self.settings.enable_smart_nic is True):
                mapping = physical_network[check] + ':' + interface
                nova_pci = '{devname: ' + \
                           '"' + interface + '",' + \
                           'physical_network: ' + \
                           '"' + physical_network[check] + '"}'
                check = check + 1

            else:
                mapping = physical_network[0] + ':' + interface
                nova_pci = '{devname: ' + \
                           '"' + interface + '",' + \
                           'physical_network: ' + \
                           '"' + physical_network[0] + '"}'

            sriov_map_setting.append(mapping)

            sriov_pci_passthrough.append(nova_pci)

        sriov_map_setting = "'" + ",".join(sriov_map_setting) + "'"
        sriov_pci_passthrough = "[" + ",".join(sriov_pci_passthrough) + "]"

        cmds.append('sed -i "s|NumSriovVfs:.*|' +
                    'NumSriovVfs: ' +
                    self.settings.sriov_vf_count + '|" ' + env_file)
        cmds.append('sed -i "s|NeutronPhysicalDevMappings:.*|' +
                    'NeutronPhysicalDevMappings: ' +
                    sriov_map_setting + '|" ' + env_file)
        cmds.append('sed -i "s|NovaPCIPassthrough:.*|' +
                    'NovaPCIPassthrough: ' +
                    sriov_pci_passthrough + '|" ' + env_file)

        # Execute the command related to sriov configuration
        for cmd in cmds:
            self.run(cmd)

    def deploy_overcloud(self):

        logger.debug("Configuring network settings for overcloud")
        cmd = "rm -f " + self.home_dir + '/.ssh/known_hosts'
        self.run_tty(cmd)
        cmd = self.source_stackrc + "cd" \
                                    " ~/pilot;./deploy-overcloud.py" \
                                    " --dell-computes " + \
                                    str(len(self.settings.compute_nodes)) + \
                                    " --controllers " + \
                                    str(len(self.settings.controller_nodes)) + \
                                    " --dell-computeshci " + \
                                    str(len(self.settings.computehci_nodes)) + \
                                    " --storage " + \
                                    str(len(self.settings.ceph_nodes)) + \
                                    " --powerflex " + \
                                    str(len(self.settings.powerflex_nodes)) + \
                                    " --vlan " + \
                                    self.settings.tenant_vlan_range + \
                                    " --nic_env_file " + \
                                    self.settings.nic_env_file + \
                                    " --overcloud_name " + \
                                    self.settings.overcloud_name + \
                                    " --ntp " + \
                                    self.settings.sah_node.provisioning_ip + \
                                    " --mtu " + \
                                    self.settings.default_bond_mtu

        if self.settings.hpg_enable is True:
            cmd += " --enable_hugepages "
            cmd += " --hugepages_size " + self.settings.hpg_size

        if self.settings.numa_enable is True:
            cmd += " --enable_numa "
            cmd += " --hostos_cpu_count " + self.settings.hostos_cpu_count

        if self.settings.overcloud_deploy_timeout != "120":
            cmd += " --timeout " \
                   + self.settings.overcloud_deploy_timeout
        if self.settings.enable_dellsc_backend is True:
            cmd += " --enable_dellsc"
        if self.settings.enable_unity_backend is True:
            cmd += " --enable_unity"
        if self.settings.enable_unity_manila_backend is True:
            cmd += " --enable_unity_manila"
        if self.settings.enable_powermax_backend is True:
            cmd += " --enable_powermax"
            cmd += " --powermax_protocol "
            cmd += self.settings.powermax_protocol
        if self.settings.enable_powermax_backend is True:
            cmd += " --enable_powermax"
        if self.settings.enable_powermax_manila_backend is True:
            cmd += " --enable_powermax_manila"
        if self.settings.enable_rbd_backend is False:
            cmd += " --disable_rbd"
        if self.settings.overcloud_static_ips is True:
            cmd += " --static_ips"
        if self.settings.use_static_vips is True:
            cmd += " --static_vips"
        if self.settings.enable_ovs_dpdk is True:
            cmd += " --ovs_dpdk"
        if self.settings.enable_sriov is True:
            cmd += " --sriov"
        if self.settings.enable_smart_nic is True:
            cmd += " --hw_offload"
            cmd += " --sriov_interfaces " + \
                str(len(self.get_sriov_compute_interfaces()))
        if self.settings.dvr_enable is True:
            cmd += " --dvr_enable"
        if self.settings.barbican_enable is True:
            cmd += " --barbican_enable"
        if self.settings.octavia_enable is True:
            cmd += " --octavia_enable"
        if self.settings.octavia_user_certs_keys is True:
            cmd += " --octavia_user_certs_keys"
        # Node placement is required in an automated install.  The index order
        # of the nodes is the order in which they are defined in the
        # .properties file
        cmd += " --node_placement"
        if self.settings.deploy_overcloud_debug:
            cmd += " --debug"
        if self._has_edge_sites():
            cmd += " --network_data"
        if self.settings.enable_dashboard is True and self.settings.enable_powerflex_backend is False:
            cmd += " --dashboard_enable"

        cmd += " > overcloud_deploy_out.log 2>&1"
        self.run_tty(cmd)

    def delete_overcloud(self):

        logger.info("Deleting the overcloud stack")
        self.run_tty(self.source_stackrc +
                     "openstack stack delete --yes --wait " +
                     self.settings.overcloud_name)
        # Unregister the nodes from Ironic
        re = self.run_tty(self.source_stackrc +
                          "openstack baremetal node list | grep None")
        ls_nodes = re[0].split("\n")
        ls_nodes.pop()
        for node in ls_nodes:
            node_state = node.split("|")[5]
            node_id = node.split("|")[1]
            if "ERROR" or "inspect failed" in node_state:
                self.run_tty(self.source_stackrc +
                             "openstack baremetal node maintenance set" +
                             node_id)
            if "clean failed" in node_state:
                self.run_tty(self.source_stackrc +
                             "openstack baremetal node maintenance unset" +
                             node_id)
                self.run_tty(self.source_stackrc +
                             "openstack baremetal node manage " +
                             node_id)
            self.run_tty(self.source_stackrc +
                         "openstack baremetal node delete " +
                         node_id)

    def summarize_deployment(self):
        logger.info("**** Retrieving nodes information ")
        deployment_log = '/auto_results/deployment_summary.log'
        ip_info = []
        fi = open(deployment_log, "wb")
        try:
            logger.debug("retrieving node ip details ..")
            ip_info.append("====================================")
            ip_info.append("### nodes ip information ###")

            priv_ = self.settings.private_api_network.rsplit(".", 1)[0]
            priv_.replace(".", '\.')  # noqa: W605
            pub_ = self.settings.public_api_network.rsplit(".", 1)[0]
            pub_.replace(".", '\.')  # noqa: W605
            stor_ = self.settings.storage_network.rsplit(".", 1)[0]
            stor_.replace(".", '\.')  # noqa: W605
            clus_ = self.settings.storage_cluster_network.rsplit(".", 1)[0]
            clus_.replace(".", '\.')  # noqa: W605

            re = self.run_tty(self.source_stackrc +
                              "nova list | grep controller")
            ip_info.append("### Controllers ###")
            ls_nodes = re[0].split("\n")
            ls_nodes.pop()

            for each in ls_nodes:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]

                ssh_opts = (
                    "-o StrictHostKeyChecking=no "
                    "-o UserKnownHostsFile=/dev/null "
                    "-o KbdInteractiveDevices=no")
                re = self.run_tty("ssh " + ssh_opts + " heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  priv_ +
                                  ".*netmask " +
                                  self.settings.private_api_netmask +
                                  ".*\" | awk '{print $2}'")
                private_api = re[0].split("\n")[1]

                re = self.run_tty("ssh " + ssh_opts + " heat-admin@" +
                                  provisioning_ip +
                                  "/sbin/ifconfig | grep \"inet.*" +
                                  pub_ +
                                  ".*netmask " +
                                  self.settings.public_api_netmask +
                                  ".*\" | awk '{print $2}'")
                nova_public_ip = re[0].split("\n")[1]

                re = self.run_tty("ssh " + ssh_opts + " heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  stor_ +
                                  ".*netmask " +
                                  self.settings.storage_netmask +
                                  ".*\" | awk '{print $2}'")
                storage_ip = re[0].split("\n")[1]

                ip_info.append(hostname + ":")
                ip_info.append("     - provisioning ip  : " + provisioning_ip)
                ip_info.append("     - nova private ip  : " + private_api)
                ip_info.append("     - nova public ip   : " + nova_public_ip)
                ip_info.append("     - storage ip       : " + storage_ip)

            re = self.run_tty(self.source_stackrc + "nova list | grep compute")

            ip_info.append("### Compute  ###")
            ls_nodes = re[0].split("\n")
            ls_nodes.pop()
            for each in ls_nodes:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]

                ssh_opts = (
                    "-o StrictHostKeyChecking=no "
                    "-o UserKnownHostsFile=/dev/null "
                    "-o KbdInteractiveDevices=no")
                re = self.run_tty("ssh " + ssh_opts + " heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  priv_ +
                                  ".*netmask " +
                                  self.settings.private_api_netmask +
                                  ".*\" | awk '{print $2}'")
                private_api = re[0].split("\n")[1]

                re = self.run_tty("ssh " + ssh_opts + " heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  stor_ +
                                  ".*netmask " +
                                  self.settings.storage_netmask +
                                  ".*\" | awk '{print $2}'")
                storage_ip = re[0].split("\n")[1]

                ip_info.append(hostname + ":")
                ip_info.append("     - provisioning ip  : " + provisioning_ip)
                ip_info.append("     - nova private ip  : " + private_api)
                ip_info.append("     - storage ip       : " + storage_ip)

            re = self.run_tty(self.source_stackrc + "nova list | grep storage")

            ip_info.append("### Storage  ###")
            ls_nodes = re[0].split("\n")
            ls_nodes.pop()
            for each in ls_nodes:
                hostname = each.split("|")[2]
                provisioning_ip = each.split("|")[6].split("=")[1]

                ssh_opts = (
                    "-o StrictHostKeyChecking=no "
                    "-o UserKnownHostsFile=/dev/null "
                    "-o KbdInteractiveDevices=no")
                re = self.run_tty("ssh " + ssh_opts + " heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  clus_ +
                                  ".*netmask 255.255.255.0.*\""
                                  " | awk '{print $2}'")
                cluster_ip = re[0].split("\n")[1]

                re = self.run_tty("ssh " + ssh_opts + " heat-admin@" +
                                  provisioning_ip +
                                  " /sbin/ifconfig | grep \"inet.*" +
                                  stor_ +
                                  ".*netmask " +
                                  self.settings.storage_netmask +
                                  ".*\" | awk '{print $2}'")
                storage_ip = re[0].split("\n")[1]

                ip_info.append(hostname + ":")
                ip_info.append(
                    "     - provisioning ip    : " + provisioning_ip)
                ip_info.append("     - storage cluster ip : " + cluster_ip)
                ip_info.append("     - storage ip         : " + storage_ip)

            if (self.settings.hpg_enable is True or
                    self.settings.numa_enable is True):
                ip_info.append("### NFV features details... ###")
                ip_info.append("====================================")
                if self.settings.hpg_enable is True:
                    ip_info.append("### Hugepages ###")
                    ip_info.append("Feature enabled : " +
                                   str(self.settings.hpg_enable))
                    ip_info.append("Hugepage size : " +
                                   self.settings.hpg_size)
                if self.settings.numa_enable is True:
                    ip_info.append("### NUMA ###")
                    ip_info.append("Feature enabled : " +
                                   str(self.settings.numa_enable))

            ip_info.append("====================================")

            # noinspection PyBroadException
            try:
                overcloud_endpoint = self.run_tty(
                    'grep "OS_AUTH_URL=" ~/' + self.settings.overcloud_name +
                    'rc')[0].split('=')[1].replace(':5000/v2.0/', '')
                overcloud_pass = self.run('grep "OS_PASSWORD=" ~/' +
                                          self.settings.overcloud_name +
                                          'rc')[0].split('=')[1]
                if self.settings.enable_dashboard is True:
                    dashboard_pwd = self.run_tty('sudo grep dashboard_admin_password /var/lib/mistral/' +
                                                 self.settings.overcloud_name +
                                                 '/ceph-ansible/group_vars/all.yml')[0].split(' ')[1]
                    dashboard_ip = self.run_tty('sudo grep dashboard_frontend /var/lib/mistral/' +
                                                self.settings.overcloud_name +
                                                '/ceph-ansible/group_vars/mgrs.yml')[0].split(' ')[1]
                ip_info.append("OverCloud Horizon        : " +
                               overcloud_endpoint)
                ip_info.append("OverCloud admin password : " +
                               overcloud_pass)
                if self.settings.enable_dashboard is True:
                    ip_info.append("Ceph Dashboard           : " +
                                   "http://" + dashboard_ip.rstrip()+ ":8444")
                    ip_info.append("Dashboard admin password : " +
                                   dashboard_pwd)
                ip_info.append("cloud_repo # " +
                               self.settings.cloud_repo_version)
                ip_info.append("deploy-auto # " +
                               self.settings.deploy_auto_version)
            except:  # noqa: E722
                pass
            ip_info.append("====================================")
        except:  # noqa: E722
            logger.debug(" Failed to retrieve the nodes ip information ")
        finally:
            for each in ip_info:
                logger.debug(each)
                fi.write((each + "\n").encode('utf-8'))
            fi.close()

    def inject_ssh_key(self):
        if not os.path.exists('/root/.ssh/id_rsa.pub'):
            subprocess.call('ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ""',
                            shell=True)
        self.run_tty("mkdir /home/" + self.user + "/.ssh")
        self.upload_file("/root/.ssh/id_rsa.pub",
                         "/home/" + self.user + "/.ssh/authorized_keys")
        self.run_tty("sudo chown %s:%s /home/%s/.ssh/authorized_keys" %
                     (self.user, self.user, self.user))
        self.run_tty("chmod 700 /home/" + self.user + "/.ssh")
        self.run_tty("chmod 600 /home/" + self.user + "/.ssh/authorized_keys")
        self.run_tty("sudo cp -Rv /home/" + self.user + "/.ssh /root")
        self.run_tty("sudo chmod 700 /root/.ssh")
        self.run_tty("sudo chmod 600 /root/.ssh/authorized_keys")

    def run_sanity_test(self):
        if self.settings.run_sanity is True:
            logger.info("Running sanity test")
            cmd = 'rm -f ~/{}.pub'.format(self.settings.sanity_key_name)
            self.run_tty(cmd)
            cmd = 'rm -f ~/{}'.format(self.settings.sanity_key_name)
            self.run_tty(cmd)
            self.run_tty("cd " + self.validation_dir +
                         ';chmod ugo+x sanity_test.sh')
            re = self.run_tty("cd " + self.validation_dir +
                              ';./sanity_test.sh')
            if "VALIDATION SUCCESS" in re[0]:
                logger.info("Sanity Test Passed")
            else:
                logger.fatal("Sanity Test failed")
                raise AssertionError(
                    "Sanity test failed - see log for details")
        else:
            logger.info("NOT running sanity test")
            pass

    def configure_tempest(self):
        """Attemtps to create tempest.conf

        If there is an existing tempest.conf it is backed up, the we try
        to create a new one.  If the correct networks are not there it means
        sanity test most likely wasn't run, in that case we raise exception
        informing the user to run sanity test and try again.

        :raises: AssertionException Could not find right subnet to discover
        networks and configure tempest.
        """
        logger.info("Configuring tempest")
        setts = self.settings
        external_sub_guid = self.get_sanity_subnet()
        if not external_sub_guid:
            err = ("Could not find public network, please run the " +
                   "sanity test to create the appropriate networks " +
                   "and re-run this script with the " +
                   "--tempest_config_only flag.")
            raise AssertionError(err)

        self._backup_tempest_conf()

        cmd_route = ("source ~/" + setts.overcloud_name + "rc;" +
                     "sudo ip route add " + setts.floating_ip_network +
                     " dev enp1s0")
        cmd_config = ("source ~/" + setts.overcloud_name + "rc;" +

                      "if [ ! -d " + self.tempest_directory +
                      " -o -z '$(ls -A " + self.tempest_directory +
                      " 2>/dev/null)' ]; then tempest init " +
                      self.tempest_directory + ";fi;cd " +
                      self.tempest_directory +
                      ";discover-tempest-config --deployer-input " +
                      "~/tempest-deployer-input.conf --debug --create " +
                      "--network-id " + external_sub_guid +
                      " object-storage-feature-enabled.discoverability False" +
                      " object-storage-feature-enabled.discoverable_apis" +
                      " container_quotas")
        cmd_roles = ("sed -i 's|tempest_roles =.*|tempest_roles "
                     "= _member_,Member|' " + self.tempest_conf)
        cmds = [cmd_route, cmd_config, cmd_roles]
        for cmd in cmds:
            logger.info("Configuring tempest, cmd: %s" % cmd)
            self.run_tty(cmd)

    def run_tempest(self):
        logger.info("Running tempest")

        if not self.is_tempest_conf():
            self.configure_tempest()

        setts = self.settings
        cmd = ("source ~/" + setts.overcloud_name + "rc;cd " +
               self.tempest_directory +
               ";tempest cleanup --init-saved-state")

        self.run_tty(cmd)

        if setts.tempest_smoke_only is True:
            logger.info("Running tempest - smoke tests only.")
            cmd = ("source ~/" + setts.overcloud_name + "rc;cd " +
                   self.tempest_directory +
                   ";ostestr '.*smoke' --concurrency=4")
        else:
            logger.info("Running tempest - full tempest run.")
            cmd = ("source ~/" + setts.overcloud_name +
                   "rc;cd " + self.tempest_directory +
                   ";ostestr --concurrency=4")

        self.run_tty(cmd)
        tempest_log_file = (self.tempest_directory + "/tempest.log")

        Scp.get_file(self.ip, self.user, self.pwd,
                     "/auto_results/tempest.log",
                     tempest_log_file)
        logger.debug("Finished running tempest, cleanup next.")
        cmds = ['source ~/' + self.settings.overcloud_name + 'rc;cd ' +
                self.tempest_directory + ';tempest cleanup --dry-run',
                'source ~/' + self.settings.overcloud_name + 'rc;cd ' +
                self.tempest_directory + ';tempest cleanup']

        for cmd in cmds:
            self.run_tty(cmd)

    def is_tempest_conf(self):
        logger.info("Checking to see if tempest.conf exists.")
        cmd = "test -f " + self.tempest_conf + "; echo $?;"
        resp = self.run_tty(cmd)[0].rstrip()
        is_conf = not bool(int(resp))
        return is_conf

    def get_sanity_subnet(self):
        logger.debug("Retrieving sanity test subnet.")
        setts = self.settings
        external_sub_cmd = ("source ~/" + setts.overcloud_name + "rc;" +
                            "openstack subnet list  | grep external_sub " +
                            "| awk '{print $6;}'")
        external_sub_guid = self.run_tty(external_sub_cmd)[0].rstrip()
        return external_sub_guid

    def _backup_tempest_conf(self):
        logger.info("Backing up tempest.conf")
        if self.is_tempest_conf():
            timestamp = int(round(time.time() * 1000))
            new_conf = (self.tempest_conf + "." + str(timestamp))
            logger.debug("Backing up tempest.conf, new file is: %s "
                         % new_conf)
            cmd = ("mv " + self.tempest_conf + " " + new_conf + " 2>/dev/null")
            self.run_tty(cmd)

    def enable_fencing(self):
        if self.settings.enable_fencing is True:
            logger.info("enabling fencing")
            new_ipmi_password = self.settings.new_ipmi_password
            if new_ipmi_password:
                passwd = new_ipmi_password
            else:
                passwd = self.settings.ipmi_password
            cmd = 'cd ' + \
                  self.pilot_dir + \
                  ';./agent_fencing.sh ' + \
                  self.settings.ipmi_user + \
                  ' ' + \
                  passwd + \
                  ' enable'
            self.run_tty(cmd)

    def _create_assign_role_command(self, node, role, index):
        node_identifier = ""
        if hasattr(node, 'service_tag'):
            node_identifier = node.service_tag
        else:
            node_identifier = node.idrac_ip

        skip_raid_config = ""
        if node.skip_raid_config:
            skip_raid_config = "-s"

        skip_bios_config = ""
        if node.skip_bios_config:
            skip_bios_config = "-b"

        os_volume_size_gb = ""
        if hasattr(node, 'os_volume_size_gb'):
            os_volume_size_gb = "-o {}".format(node.os_volume_size_gb)

        return './assign_role.py {} {} {} {} {}-{}'.format(
            os_volume_size_gb,
            skip_raid_config,
            skip_bios_config,
            node_identifier,
            role,
            str(index))

    def set_ovs_dpdk_driver(self, neutron_ovs_dpdk_yaml):
        cmds = []
        HostNicDriver = self.settings.HostNicDriver
        if HostNicDriver == 'mlx5_core':
            nic_driver = 'mlx5_core'
        else:
            nic_driver = 'vfio-pci'
        cmds.append(
            'sed -i "s|OvsDpdkDriverType:.*|OvsDpdkDriverType: \\"' +
            nic_driver +
            '\\" |" ' +
            neutron_ovs_dpdk_yaml)
        for cmd in cmds:
            status = os.system(cmd)
            if status != 0:
                raise Exception(
                    "Failed to execute the command {}"
                    " with error code {}".format(
                        cmd, status))
            logger.debug("cmd: {}".format(cmd))

    def get_sriov_compute_interfaces(self):
        # Get settings from .ini file
        ini_nics_settings = self.settings.get_curated_nics_settings()
        sriov_conf = {}

        # Get and sort the SR-IOV interfaces that user provided
        for int_name, int_value in ini_nics_settings.items():
            if int_name.find('ComputeSriov') != -1:
                sriov_conf.update({int_name: int_value})
        sriov_interfaces = [x[1] for x in sorted(sriov_conf.items())]
        return sriov_interfaces

    @directory_check(STAGING_TEMPLATES_PATH)
    def render_and_upload_undercloud_conf(self):
        """Updadate and upload undercloud.conf to director vm

        Note: if there are any edge sites defined in the .ini and .properties
        enable_routed_networks must be set to True in order for edge sites to
        function as DCN depends on Neutron's routed L3 networks feature.

        Also if there are defined edge sites the provisioning subnets must be
        added to undercloud.conf prior to deploying the undercloud."""

        logger.info("Updating undercloud.conf")
        setts = self.settings
        uconf = setts.undercloud_conf
        hostname = (setts.director_node.hostname + '.'
                    + setts.domain)
        subnets = ['ctlplane-subnet']

        uconf.set('DEFAULT', 'undercloud_hostname', hostname)
        uconf.set('DEFAULT', 'local_ip',
                  setts.director_node.provisioning_ip + '/24')
        uconf.set('DEFAULT', 'local_interface', UNDERCLOUD_LOCAL_INTERFACE)
        uconf.set('DEFAULT', 'image_path', self.images_dir)

        _cnt_images_file = self.home_dir + '/containers-prepare-parameter.yaml'
        uconf.set('DEFAULT', 'container_images_file', _cnt_images_file)

        uconf.set('DEFAULT', 'undercloud_nameservers',
                  setts.name_server)
        uconf.set('DEFAULT', 'undercloud_ntp_servers',
                  setts.sah_node.provisioning_ip)
        uconf.set('DEFAULT', 'undercloud_public_host',
                  setts.undercloud_public_host)
        uconf.set('DEFAULT', 'undercloud_admin_host',
                  setts.undercloud_admin_host)

        # Always need control plane subnet
        uconf.set('ctlplane-subnet', 'cidr',
                  setts.provisioning_network)
        uconf.set('ctlplane-subnet', 'dhcp_start',
                  setts.provisioning_net_dhcp_start)
        uconf.set('ctlplane-subnet', 'dhcp_end',
                  setts.provisioning_net_dhcp_end)
        uconf.set('ctlplane-subnet', 'inspection_iprange',
                  setts.discovery_ip_range)
        uconf.set('ctlplane-subnet', 'gateway',
                  setts.director_node.provisioning_ip)
        uconf.set('DEFAULT', 'enable_routed_networks',
                  str(True))

        for node_type, node_type_data in setts.node_type_data_map.items():
            subnet_name = self._generate_subnet_name(node_type)
            subnets.append(subnet_name)
            if uconf.has_section(subnet_name):
                uconf.remove_section(subnet_name)
            uconf.add_section(subnet_name)
            for opt, val in node_type_data.items():
                uconf.set(subnet_name, opt, val)

        uconf.set('DEFAULT', 'subnets', ','.join(subnets))

        stg_undercloud_conf_path = self.get_timestamped_path(STAGING_PATH,
                                                             "undercloud")
        with open(stg_undercloud_conf_path, 'w+') as undercloud_conf_fp:
            uconf.write(undercloud_conf_fp)
            undercloud_conf_fp.flush()
            undercloud_conf_fp.seek(0)
            logger.debug("Staging undercloud.conf path: %s, contents:\n%s",
                         stg_undercloud_conf_path,
                         undercloud_conf_fp.read())
        undercloud_conf_dst = os.path.join(self.home_dir,
                                           setts.UNDERCLOUD_CONFIG_FILE)
        self.upload_file(stg_undercloud_conf_path, undercloud_conf_dst)

    @directory_check(STAGING_TEMPLATES_PATH)
    def render_and_upload_roles_data_edge(self):
        """Add generated edge site roles to roles_data.yaml and upload it.
        """
        setts = self.settings

        logger.debug("render_and_upload_roles_data_edge called!")
        setts = self.settings
        tmplt = self.jinja2_env.get_template(ROLES_DATA_EDGE_J2)

        for node_type, node_type_data in setts.node_type_data_map.items():
            tmplt_data = {}
            _nt_lower = self._generate_node_type_lower(node_type)
            _roles_name = ROLES_DATA + "_" + _nt_lower
            roles_file = os.path.join(self.templates_dir,
                                      _roles_name + '.yaml')
            oc_roles_file = os.path.join(self.templates_dir,
                                         'overcloud',
                                         _roles_name + ".yaml")

            stg_roles_file = self.get_timestamped_path(STAGING_TEMPLATES_PATH,
                                                       _roles_name,
                                                       "yaml")

            tmplt_data["roles"] = [self._generate_role_dict(node_type)]
            logger.debug("template data: %s", str(tmplt_data))
            rendered_tmplt = tmplt.render(**tmplt_data)
            with open(stg_roles_file, 'w') as stg_roles_fp:
                stg_roles_fp.write(rendered_tmplt)

            self.upload_file(stg_roles_file, roles_file)
            # Need to copy to pilot/templates/overcloud as
            # we copy the roles_data file there during undercloud
            # installation and it is used during overcloud deployment
            self.upload_file(stg_roles_file, oc_roles_file)

    ''' TODO: dpaterson, DELETE ME if unused
    @directory_check(STAGING_NIC_CONFIGS)
    def update_stamp_nic_config_routes(self):
        """Loop through node_types, grouped by the number of nics, and
        the overcloud nic config templates, where appropriate, settting the
        correct routes enabling communication between the control plane and
        edge sites. Upload the stagged templete to the appropriate
        template director.

        For example, if num_nics is 5 the modified controller template will be
        uploaded to: ~/pilot/templates/nic_configs/5_port/controller.yaml
        """
        logger.debug("update_stamp_nic_config_routes!")
        self.render_and_upload_stamp_controller_nic()
        nic_dict_by_port_num = self._group_node_types_by_num_nics()
        for num_nics, node_type_tuples in nic_dict_by_port_num.items():
            logger.debug("Number of nics: %s", num_nics)
            port_dir = "{}_port".format(num_nics)
            _tmplt_path = os.path.join(NIC_CONFIGS, port_dir, CONTROLLER_J2)
            tmplt = self.jinja2_env.get_template(_tmplt_path)
            tmplt_data = {}
            _params = tmplt_data['parameters'] = {}
            cntl_file = os.path.join(self.nic_configs_dir,
                                     port_dir,
                                     CONTROLLER + ".yaml")

            stg_nic_template_path = os.path.join(STAGING_TEMPLATES_PATH,
                                                 NIC_CONFIGS, port_dir)

            if not os.path.exists(stg_nic_template_path):
                os.makedirs(stg_nic_template_path)

            stg_cntl_path = self.get_timestamped_path(stg_nic_template_path,
                                                      CONTROLLER, "yaml")
            _edge_routes = tmplt_data['routes'] = {}
            for nt_tup in node_type_tuples:
                node_type = nt_tup[0]
                _nt_params = self._generate_stamp_controller_nic_params(
                    node_type)
                _params.update(_nt_params)
                self._update_stamp_controller_nic_net_cfg(_edge_routes,
                                                          node_type, num_nics)
                logger.info("_edge_routes: %s", str(_edge_routes))
            # tmplt_data.update(_edge_routes)

            logger.info("template data: %s", str(tmplt_data))
            rendered_tmplt = tmplt.render(**tmplt_data)
            with open(stg_cntl_path, 'w') as stg_cntl_fp:
                stg_cntl_fp.write(rendered_tmplt)
            self.upload_file(stg_cntl_path, cntl_file)
    '''

    @directory_check(STAGING_NIC_CONFIGS)
    def render_and_upload_compute_templates_edge(self):
        """Loop through settings.node_type_data_map, generate the nic config
        template for each node_type, and upload the template to the director
        vm.

        Based on the number of nics for a site the corresponding
        edge_compute.yaml is used as a baseline for creating the edge node
        nic configs.

        For example, if num_nics is 5 and the node_type is compute-boston, the
        generated file will be uploaded to:
        ~/pilot/templates/nic_configs/5_port/computeboston.yaml

        Once all the nic configuration files are uploaded for each site
        nic_environment.yaml for each site is also updated and uploaded,
        see: render_and_upload_nic_env_edge()
        """
        logger.debug("render_and_upload_compute_templates_edge called!")
        setts = self.settings
        for node_type, node_type_data in setts.node_type_data_map.items():
            num_nics = node_type_data['nic_port_count']
            port_dir = "{}_port".format(num_nics)
            _tmplt_path = os.path.join(NIC_CONFIGS, port_dir, EDGE_COMPUTE_J2)
            tmplt = self.jinja2_env.get_template(_tmplt_path)
            tmplt_data = {}
            tmplt_data["parameters"] = self._generate_nic_params(node_type)
            tmplt_data["network_config"] = self._generate_nic_network_config(
                node_type,
                node_type_data)
            stg_nic_template_path = os.path.join(STAGING_TEMPLATES_PATH,
                                                 NIC_CONFIGS, port_dir)

            if not os.path.exists(stg_nic_template_path):
                os.makedirs(stg_nic_template_path)

            nic_config_name = self._generate_node_type_lower(node_type)
            stg_nic_path = self.get_timestamped_path(stg_nic_template_path,
                                                     nic_config_name,
                                                     "yaml")
            dst_nic_yaml = nic_config_name + ".yaml"
            dst_nic_path = os.path.join(self.nic_configs_dir, port_dir,
                                        dst_nic_yaml)

            logger.info("tmplt_data: %s", str(tmplt_data))
            rendered_tmplt = tmplt.render(**tmplt_data)
            with open(stg_nic_path, 'w') as stg_nic_fp:
                stg_nic_fp.write(rendered_tmplt)

            self.upload_file(stg_nic_path, dst_nic_path)

    @directory_check(STAGING_NIC_CONFIGS)
    def render_and_upload_nic_env_edge(self):
        """Update and upload nic_environment_*.yaml templates for edge sites

        Loop through the node_types, grouped by number of nics, and update
        the template resource_registry and parameter_defaults with
        site-specific parameters contained in the .ini file.

        This results in a file that corresoponds to the node type,
        which is uploaded to the correct nic-configs sub-directory based on the
        number of ports declared in node_type_data.nic_port_count

        For example if num_nics is 5 and node_type is boston-compute
        the modified file will be uploaded to:
        to:
        ~/pilot/templates/nic_configs/5_port/nic_environement_bostoncompute.yaml
        """
        logger.debug("render_and_upload_nic_env_edge called!")

        nic_dict_by_port_num = self._group_node_types_by_num_nics()

        for num_nics, node_type_tuples in nic_dict_by_port_num.items():
            port_dir = "{}_port".format(num_nics)

            _tmplt_path = os.path.join(NIC_CONFIGS, port_dir, NIC_ENV_EDGE_J2)
            tmplt = self.jinja2_env.get_template(_tmplt_path)
            stg_nic_tmplt_path = os.path.join(STAGING_TEMPLATES_PATH,
                                              NIC_CONFIGS, port_dir)

            if not os.path.exists(stg_nic_tmplt_path):
                os.makedirs(stg_nic_tmplt_path)

            for node_type_tuple in node_type_tuples:
                node_type = node_type_tuple[0]
                node_type_data = node_type_tuple[1]
                _nt_lower = self._generate_node_type_lower(node_type)
                _nic_env_name = NIC_ENV + "_" + _nt_lower
                _rel_nic_env_path = os.path.join(port_dir,
                                                 _nic_env_name + ".yaml")
                # nic_env_file=5_port/nic_environment_edgecomputeboston.yaml
                nic_env_file = os.path.join(self.nic_configs_dir,
                                            _rel_nic_env_path)
                tmplt_data = {}
                _res_reg = tmplt_data['resource_registry'] = {}
                _params = tmplt_data['parameter_defaults'] = {}

                stg_nic_env_path = self.get_timestamped_path(
                    stg_nic_tmplt_path,
                    _nic_env_name,
                    "yaml")

                ne_params = self._generate_nic_environment_edge(tmplt_data,
                                                                node_type,
                                                                node_type_data)
                _params.update(ne_params)
                role = self._generate_cc_role(node_type)
                role_nic_key = ("OS::TripleO::"
                                + role + "::Net::SoftwareConfig")
                nic_config_name = ("./" + _nt_lower + ".yaml")
                _res_reg[role_nic_key] = nic_config_name
                logger.info("template data: %s", str(tmplt_data))
                rendered_tmplt = tmplt.render(**tmplt_data)
                with open(stg_nic_env_path, 'w') as stg_nic_env_fp:
                    stg_nic_env_fp.write(rendered_tmplt)
                self.upload_file(stg_nic_env_path, nic_env_file)

    @directory_check(STAGING_TEMPLATES_PATH)
    def render_and_upload_node_placement_edge(self):
        logger.debug("render_and_upload_node_placement_edge called!")
        self.render_and_upload_stamp_node_placement()
        setts = self.settings
        tmplt = self.jinja2_env.get_template(NODE_PLACEMENT_EDGE_J2)

        for node_type in setts.node_types:
            tmplt_data = {'scheduler_hints': {}}
            _sched_hints = tmplt_data['scheduler_hints']
            exp = self._generate_node_placement_exp(node_type)
            role = self._generate_cc_role(node_type)
            edge_name = self._generate_node_type_lower(node_type)
            node_plcmnt_name = NODE_PLACEMENT + "_" + edge_name
            _role_hints = role + 'SchedulerHints'
            _sched_hints[_role_hints] = exp

            rendered_tmplt = tmplt.render(**tmplt_data)

            stg_plcmnt_path = self.get_timestamped_path(STAGING_TEMPLATES_PATH,
                                                        node_plcmnt_name,
                                                        "yaml")
            with open(stg_plcmnt_path, 'w') as stg_plcmnt_fp:
                stg_plcmnt_fp.write(rendered_tmplt)

            remote_plcmnt_file = os.path.join(self.templates_dir,
                                              node_plcmnt_name + ".yaml")
            self.upload_file(stg_plcmnt_path, remote_plcmnt_file)

    @directory_check(STAGING_TEMPLATES_PATH)
    def render_and_upload_static_ips_edge(self):
        logger.debug("render_and_upload_static_ips_edge called!")
        setts = self.settings
        tmplt = self.jinja2_env.get_template(STATIC_IP_ENV_EDGE_J2)

        for node_type, nodes in setts.node_types_map.items():
            tmplt_data = {}
            nt_lower = self._generate_node_type_lower(node_type)
            static_ip_env_edge = STATIC_IP_ENV + "_" + nt_lower
            stg_static_ip_env_path = self.get_timestamped_path(
                STAGING_TEMPLATES_PATH,
                static_ip_env_edge, "yaml")
            remote_static_ip_env_file = os.path.join(self.templates_dir,
                                                     static_ip_env_edge
                                                     + ".yaml")
            tmplt_data['resource_registry'] = self._generate_static_ip_ports(
                node_type)
            tmplt_data['parameter_defaults'] = self._generate_static_ip_params(
                node_type,
                nodes)

            logger.debug("tmplt_data: %s", str(tmplt_data))
            rendered_tmplt = tmplt.render(**tmplt_data)

            with open(stg_static_ip_env_path, 'w') as stg_static_ip_env_fp:
                stg_static_ip_env_fp.write(rendered_tmplt)

            self.upload_file(stg_static_ip_env_path, remote_static_ip_env_file)

    @directory_check(STAGING_TEMPLATES_PATH)
    def render_and_upload_network_isolation_edge(self):
        """Update and upload network-isolation.yaml based on
        node types
        """
        logger.debug("Updating network isolation for edge sites.")
        setts = self.settings

        tmplt = self.jinja2_env.get_template(NET_ISO_EDGE_J2)

        for nt, nt_data in setts.node_type_data_map.items():
            _edge_name = "_" + self._generate_node_type_lower(nt)
            edge_net_iso_fn = NET_ISO + _edge_name
            tmplt_data = {}
            res_reg = tmplt_data["resource_registry"] = {}
            res_reg.update(self._generate_network_isolation(nt))
            logger.debug("tmplt_data: %s", str(tmplt_data))

            rendered_tmplt = tmplt.render(**tmplt_data)
            net_iso_file = os.path.join(self.templates_dir,
                                        edge_net_iso_fn + ".yaml")
            oc_net_iso_file = os.path.join(self.templates_dir,
                                           'overcloud',
                                           'environments',
                                           edge_net_iso_fn + ".yaml")

            stg_n_iso_path = self.get_timestamped_path(STAGING_TEMPLATES_PATH,
                                                       edge_net_iso_fn,
                                                       "yaml")

            with open(stg_n_iso_path, 'w') as stg_net_iso_fp:
                stg_net_iso_fp.write(rendered_tmplt)

            self.upload_file(stg_n_iso_path, net_iso_file)
            # have to upload twice as we specify overcloud/environments/
            # when deploying overcloud
            self.upload_file(stg_n_iso_path, oc_net_iso_file)

    @directory_check(STAGING_TEMPLATES_PATH)
    def render_and_upload_dell_environment_edge(self):
        logger.debug("Updating dell environment for edge sites.")
        setts = self.settings
        tmplt = self.jinja2_env.get_template(DELL_ENV_EDGE_J2)

        for nt, nt_data in setts.node_type_data_map.items():
            _nt_lower = self._generate_node_type_lower(nt)
            _dell_env_name = DELL_ENV + "_" + _nt_lower
            dell_env_file = os.path.join(self.templates_dir,
                                         _dell_env_name + ".yaml")
            stg_dell_env_path = self.get_timestamped_path(
                STAGING_TEMPLATES_PATH,
                dell_env_file, "yaml")
            tmplt_data = {}
            param_def = tmplt_data["parameter_defaults"] = {}
            role = self._generate_cc_role(nt)
            edge_subnet = self._generate_subnet_name(nt)
            role_subnet_key = role + 'ControlPlaneSubnet'
            param_def[role_subnet_key] = edge_subnet
            xtra_cfg_key = role + 'ExtraConfig'
            param_def[xtra_cfg_key] = self._generate_extra_config(nt)
            role_count_key = role + 'Count'
            nodes = setts.node_types_map[nt]
            param_def[role_count_key] = len(nodes)
            rendered_tmplt = tmplt.render(**tmplt_data)
            with open(stg_dell_env_path, 'w') as stg_dell_env_fp:
                stg_dell_env_fp.write(rendered_tmplt)
            self.upload_file(stg_dell_env_path, dell_env_file)

    @directory_check(STAGING_TEMPLATES_PATH)
    def render_and_upload_network_data(self):
        """Generate and upload network_data.yaml for default overcloud networks
        and edge site specific networks"""
        logger.debug("Creating network_data.yaml")
        net_data_path = self.templates_dir
        net_data_file = os.path.join(net_data_path, NET_DATA + ".yaml")

        stg_net_data_file = self.get_timestamped_path(STAGING_TEMPLATES_PATH,
                                                      NET_DATA, "yaml")
        stg_net_data_lst = self._generate_default_networks_data()
        tmplt = self.jinja2_env.get_template(NETWORK_DATA_J2)

        logger.info("Network data dump: %s", str(stg_net_data_lst))
        tmplt_data = {'networks': stg_net_data_lst}
        rendered_tmplt = tmplt.render(**tmplt_data)

        with open(stg_net_data_file, 'w') as stg_net_data_fp:
            stg_net_data_fp.write(rendered_tmplt)

        self.upload_file(stg_net_data_file, net_data_file)

    @directory_check(STAGING_TEMPLATES_PATH)
    def render_and_upload_network_data_edge(self):
        """Generate and upload network_data.yaml for edge site networks"""
        logger.debug("render_and_upload_network_data_edge called!")
        setts = self.settings
        tmplt = self.jinja2_env.get_template(NETWORK_DATA_J2)

        for node_type, node_type_data in setts.node_type_data_map.items():
            _nt_lower = self._generate_node_type_lower(node_type)
            _nd_name = NET_DATA + "_" + _nt_lower
            nd_file = os.path.join(self.templates_dir, _nd_name + ".yaml")

            stg_nd_file = self.get_timestamped_path(STAGING_TEMPLATES_PATH,
                                                    _nd_name, "yaml")
            nd = self._generate_network_data(node_type, node_type_data)
            logger.info("Network data dump: %s", str(nd))
            tmplt_data = {'networks': nd}
            rendered_tmplt = tmplt.render(**tmplt_data)

            with open(stg_nd_file, 'w') as stg_nd_fp:
                stg_nd_fp.write(rendered_tmplt)

            self.upload_file(stg_nd_file, nd_file)

    @directory_check(STAGING_TEMPLATES_PATH)
    def render_and_upload_network_environment_edge(self):
        """Update and upload network-environment-*.yaml for
        edge site specific networks
        """
        logger.debug("render_and_upload_network_environment_edge called")
        setts = self.settings
        tmplt = self.jinja2_env.get_template(NETWORK_ENV_EDGE_J2)
        for nt, nt_data in setts.node_type_data_map.items():
            _nt_lower = self._generate_node_type_lower(nt)
            _net_env_name = NET_ENV + "_" + _nt_lower
            net_env_file = os.path.join(self.templates_dir,
                                        _net_env_name + ".yaml")

            stg_net_env_path = self.get_timestamped_path(
                STAGING_TEMPLATES_PATH,
                _net_env_name, "yaml")
            params = self._generate_network_environment_params_edge(nt,
                                                                    nt_data)
            tmplt_data = {"parameter_defaults": params}
            rendered_tmplt = tmplt.render(**tmplt_data)
            with open(stg_net_env_path, 'w') as stg_net_env_fp:
                stg_net_env_fp.write(rendered_tmplt)
            self.upload_file(stg_net_env_path, net_env_file)

    def create_subnet_routes_edge(self):
        """Create routes for Director VM and reboot it, which is required
        for routes to take effect
        """
        logger.info('Setting routes for edge subnets on Director VM and '
                    'restarting VM, as it is required to get the routes to '
                    'register with virsh properly')
        setts = self.settings
        mgmt_gw = setts.management_gateway
        route_file = (" > /etc/sysconfig/network-scripts/route-"
                      + UNDERCLOUD_LOCAL_INTERFACE)
        mgmt_cmd = ""
        for node_type, node_type_data in setts.node_type_data_map.items():
            mgmt_cidr = node_type_data['mgmt_cidr']
            mgmt_cmd += "{} via {} dev {}\n".format(mgmt_cidr,
                                                    mgmt_gw,
                                                    UNDERCLOUD_LOCAL_INTERFACE)

        mgmt_cmd = "echo $'" + mgmt_cmd + "'" + route_file
        self.run_as_root(mgmt_cmd)
        logger.info('Restarting Director VM')
        self.run_as_root('init 6')
        dir_pub_ip = setts.director_node.public_api_ip
        dir_pw = setts.director_node.root_password
        self.wait_for_vm_to_go_down(dir_pub_ip,
                                    "root",
                                    dir_pw)

    @directory_check(STAGING_PATH)
    def update_instack_env_subnets_edge(self):
        instack_file = self.home_dir + "/" + INSTACK + ".json"
        mgmt_net = self.settings.management_network.rsplit(".", 1)[0]
        stg_instack_path = self.get_timestamped_path(STAGING_PATH,
                                                     INSTACK, "json")

        self.download_file(stg_instack_path, instack_file)
        instack = {}
        with open(stg_instack_path, 'r') as stg_instack_fp:
            instack = json.load(stg_instack_fp)
            nodes = instack['nodes']
            for node in nodes:
                node_mgmt_net = node['pm_addr'].rsplit('.', 1)[0]
                if node_mgmt_net != mgmt_net:
                    node['subnet'] = self._subnet_name_from_net(node_mgmt_net)

        with open(stg_instack_path, 'w') as stg_instack_fp:
            json.dump(instack, stg_instack_fp, indent=2)

        self.upload_file(stg_instack_path, instack_file)

    @directory_check(STAGING_TEMPLATES_PATH)
    def render_and_upload_stamp_controller_nic(self):
        setts = self.settings
        _tmplt_path = os.path.join(NIC_CONFIGS,
                                   setts.nic_dir, CONTROLLER_J2)
        tmplt = self.jinja2_env.get_template(_tmplt_path)
        cntl_file = os.path.join(self.nic_configs_dir,
                                 setts.nic_dir,
                                 CONTROLLER + ".yaml")

        stg_nic_template_path = os.path.join(STAGING_TEMPLATES_PATH,
                                             NIC_CONFIGS, setts.nic_dir)

        if not os.path.exists(stg_nic_template_path):
            os.makedirs(stg_nic_template_path)

        stg_cntl_path = self.get_timestamped_path(stg_nic_template_path,
                                                  CONTROLLER, "yaml")
        rendered_tmplt = tmplt.render(**{})
        logger.debug("template staging path: %s", stg_cntl_path)
        with open(stg_cntl_path, 'w') as stg_cntl_fp:
            stg_cntl_fp.write(rendered_tmplt)
        self.upload_file(stg_cntl_path, cntl_file)

    @directory_check(STAGING_TEMPLATES_PATH)
    def render_and_upload_stamp_node_placement(self):
        tmplt = self.jinja2_env.get_template(NODE_PLACEMENT_EDGE_J2)
        remote_plcmnt_file = os.path.join(self.templates_dir,
                                          NODE_PLACEMENT + ".yaml")

        stg_plcmnt_path = self.get_timestamped_path(STAGING_TEMPLATES_PATH,
                                                    NODE_PLACEMENT, "yaml")
        rendered_tmplt = tmplt.render(**{})
        logger.debug("template staging path: %s", stg_plcmnt_path)
        with open(stg_plcmnt_path, 'w') as stg_node_plcmnt_fp:
            stg_node_plcmnt_fp.write(rendered_tmplt)
        self.upload_file(stg_plcmnt_path, remote_plcmnt_file)

    def _has_edge_sites(self):
        return bool(self.settings.node_type_data_map)

    def _subnet_name_from_net(self, node_mgmt_net):
        setts = self.settings
        for node_type, node_type_data in setts.node_type_data_map.items():
            subnet_net = node_type_data['mgmt_cidr'].rsplit('.', 1)[0]
            if node_mgmt_net == subnet_net:
                return self._generate_subnet_name(node_type)

    def _generate_static_ip_ports(self, node_type):
        """Generate resource_resource registry port mapping dict for specific
        node type based on Tripleo heat template naming conventions
        :returns: dict of node type port mappings
        example: {
        'OS::TripleO::BostonCompute::Ports::InternalApiBostonComputePort':
        './overcloud/network/ports/internal_api_boston_compute_from_pool.yaml',
        ...
        }
        """
        port_dict = {}
        role = self._generate_cc_role(node_type)
        role_network = self._generate_role_network_lower(node_type)

        role_port = 'OS::TripleO::' + role + '::Ports::'
        int_api_port = role_port + 'InternalApi' + role + 'Port'
        storage_port = role_port + 'Storage' + role + 'Port'
        tenant_port = role_port + 'Tenant' + role + 'Port'
        external_port = role_port + 'External' + role + 'Port'
        int_api_yaml = ('./overcloud/network/ports/internal_api_'
                        + role_network + '_from_pool.yaml')
        storage_yaml = ('./overcloud/network/ports/storage_'
                        + role_network + '_from_pool.yaml')
        tenant_yaml = ('./overcloud/network/ports/tenant_'
                       + role_network + '_from_pool.yaml')
        external_yaml = ('./overcloud/network/ports/external_'
                         + role_network + '_from_pool.yaml')
        port_dict[int_api_port] = int_api_yaml
        port_dict[storage_port] = storage_yaml
        port_dict[tenant_port] = tenant_yaml
        port_dict[external_port] = external_yaml

        return port_dict

    def _generate_static_ip_params(self, node_type, nodes):
        """Generate resource_resource registry port mapping dict for specific
        node type based on Tripleo heat template naming conventions
        :returns: dict which maps node_type to a list of static ips
        example: {
        'BostonComputeIPs':
           'internal_api_boston_compute': ['192.168.142.40', '192.168.142.41'],
            ...,
        }
        """
        role = self._generate_cc_role(node_type)
        ip_params = {}
        role_ips = role + 'IPs'
        network_dict = {}
        int_api_ips = []
        storage_ips = []
        tenant_ips = []
        external_ips = []
        for node in nodes:
            int_api_ips.append(node.private_api_ip)
            storage_ips.append(node.storage_ip)
            tenant_ips.append(node.tenant_tunnel_ip)
            external_ips.append(node.external_ip)

        suffix = '_' + self._generate_role_network_lower(node_type)

        network_dict[INTERNAL_API_NET[1] + suffix] = int_api_ips
        network_dict[STORAGE_NET[1] + suffix] = storage_ips
        network_dict[TENANT_NET[1] + suffix] = tenant_ips
        network_dict[EXTERNAL_NET[1] + suffix] = external_ips
        ip_params[role_ips] = network_dict
        return ip_params

    def _generate_network_isolation(self, type):
        """Generate network isolation resource_registry network and port
        parameters using Tripleo heat template naming conventions
        example: {
            'OS::TripleO::BostonCompute::Ports::InternalApiBostonComputePort':
            '../network/ports/internal_api_boston_compute.yaml',
            ...
            'OS::TripleO::Network::InternalApiBostonCompute':
            '../network/internal_api_boston_compute.yaml',
            ...
        }
        """
        role = self._generate_cc_role(type)
        edge_net = self._generate_role_network_lower(type)
        _res_reg = {}
        for net_tuple in EDGE_NETWORKS:
            net_key = "OS::TripleO::Network::{}{}".format(net_tuple[0],
                                                          role)
            net_val = "../network/{}_{}.yaml".format(net_tuple[1],
                                                     edge_net)
            _res_reg[net_key] = net_val

        for net_tuple in EDGE_NETWORKS:
            port_key = "OS::TripleO::{}::Ports::{}{}Port".format(role,
                                                                 net_tuple[0],
                                                                 role)

            port_val = "../network/ports/{}_{}.yaml".format(net_tuple[1],
                                                            edge_net)
            _res_reg[port_key] = port_val
        return _res_reg

    def _generate_network_environment_params_edge(self, type, node_type_data):
        """Generate network-environment.yaml parameters for edge sites
        :returns: dict of edge site networks
        example:{
            'InternalApiBostonComputeIpSubnet': '192.168.141.0/24',
            'InternalApiBostonComputeNetCidr': '192.168.141.0/24',
            'InternalApiBostonComputeNetworkVlanID': 141,
            'InternalApiBostonComputeInterfaceDefaultRoute': '192.168.141.1',
            'InternalApiBostonComputeAllocationPools':
                [{'end': '192.168.141.60', 'start': '192.168.141.20'}],
            ...}
        """
        logger.debug("Generate network environment params for node type: %s",
                     type)
        params = {}
        role = self._generate_cc_role(type)
        edge_subnet = self._generate_subnet_name(type)

        cp_net_cidr = 'ControlPlane' + role + 'NetCidr'
        cp_subnet_cidr = 'ControlPlane' + role + 'SubnetCidr'
        cp_default_route = 'ControlPlane' + role + 'DefaultRoute'
        cp_subnet = role + 'ControlPlaneSubnet'
        params[cp_net_cidr] = node_type_data['cidr']
        params[cp_subnet] = edge_subnet
        _cp_subnet_cidr = node_type_data['cidr'].rsplit("/", 1)[1]
        params[cp_subnet_cidr] = _cp_subnet_cidr
        params[cp_net_cidr] = node_type_data['cidr']
        params[cp_default_route] = node_type_data['gateway']

        int_api_network = INTERNAL_API_NET[0] + role
        int_api_cidr = int_api_network + 'NetCidr'
        int_api_vlan = int_api_network + 'NetworkVlanID'
        int_api_subnet = int_api_network + 'IpSubnet'
        int_api_gateway = int_api_network + 'InterfaceDefaultRoute'
        int_api_pools = int_api_network + 'AllocationPools'
        int_def_route = "{}{}InterfaceDefaultRoute".format(INTERNAL_API_NET[0],
                                                           role)
        _int_api = node_type_data['private_api_network']
        params[int_api_subnet] = _int_api
        params[int_api_cidr] = _int_api
        _int_api_vlanid = int(node_type_data['private_api_vlanid'])
        params[int_api_vlan] = _int_api_vlanid
        params[int_api_gateway] = node_type_data['private_api_gateway']
        params[int_def_route] = node_type_data['private_api_gateway']
        _int_s = node_type_data['private_api_allocation_pool_start']
        _int_e = node_type_data['private_api_allocation_pool_end']
        params[int_api_pools] = [{'start': _int_s, 'end': _int_e}]

        tenant_network = TENANT_NET[0] + role
        tenant_net_cidr = tenant_network + 'NetCidr'
        tenant_vlan = tenant_network + 'NetworkVlanID'
        tenant_subnet = tenant_network + 'IpSubnet'
        tenant_gateway = tenant_network + 'InterfaceDefaultRoute'
        tenant_pools = tenant_network + 'AllocationPools'
        tenant_def_route = "{}{}InterfaceDefaultRoute".format(TENANT_NET[0],
                                                              role)
        _tenant_vlanid = int(node_type_data['tenant_vlanid'])
        params[tenant_vlan] = _tenant_vlanid
        _tenant_net = node_type_data['tenant_network']
        params[tenant_subnet] = _tenant_net
        params[tenant_net_cidr] = _tenant_net
        params[tenant_gateway] = node_type_data['tenant_gateway']
        params[tenant_def_route] = node_type_data['tenant_gateway']
        _ten_s = node_type_data['tenant_allocation_pool_start']
        _ten_e = node_type_data['tenant_allocation_pool_end']
        params[tenant_pools] = [{'start': _ten_s, 'end': _ten_e}]

        storage_network = STORAGE_NET[0] + role
        storage_net_cidr = storage_network + 'NetCidr'
        storage_vlan = storage_network + 'NetworkVlanID'
        storage_subnet = storage_network + 'IpSubnet'
        storage_gateway = storage_network + 'InterfaceDefaultRoute'
        storage_pools = storage_network + 'AllocationPools'
        storage_def_route = "{}{}InterfaceDefaultRoute".format(STORAGE_NET[0],
                                                               role)
        _storage_vlanid = int(node_type_data['storage_vlanid'])
        params[storage_vlan] = _storage_vlanid
        _storage_net = node_type_data['storage_network']
        params[storage_subnet] = _storage_net
        params[storage_net_cidr] = _storage_net
        params[storage_gateway] = node_type_data['storage_gateway']
        params[storage_def_route] = node_type_data['storage_gateway']
        _str_s = node_type_data['storage_allocation_pool_start']
        _str_e = node_type_data['storage_allocation_pool_end']
        params[storage_pools] = [{'start': _str_s, 'end': _str_e}]

        external_network = EXTERNAL_NET[0] + role
        external_net_cidr = external_network + 'NetCidr'
        external_vlan = external_network + 'NetworkVlanID'
        external_subnet = external_network + 'IpSubnet'
        external_gateway = external_network + 'InterfaceDefaultRoute'
        external_pools = external_network + 'AllocationPools'
        external_def_route = "{}{}InterfaceDefaultRoute".format(
            EXTERNAL_NET[0], role)
        _external_vlanid = int(node_type_data['external_vlanid'])
        params[external_vlan] = _external_vlanid
        _external_net = node_type_data['external_network']
        params[external_subnet] = _external_net
        params[external_net_cidr] = _external_net
        params[external_gateway] = node_type_data['external_gateway']
        params[external_def_route] = node_type_data['external_gateway']
        _ext_s = node_type_data['external_allocation_pool_start']
        _ext_e = node_type_data['external_allocation_pool_end']
        params[external_pools] = [{'start': _ext_s, 'end': _ext_e}]

        return params

    def _generate_role_dict(self, node_type):
        role_name = self._generate_cc_role(node_type)
        role_d = {}
        role_d['name'] = role_name
        role_d['description'] = role_name + " compute node role."
        role_d['CountDefault'] = 0

        _int_api_name = INTERNAL_API_NET[0] + role_name
        _int_api_subnet = self._generate_subnet_name(INTERNAL_API_NET[1]
                                                     + "_" + role_name)
        _int_api = {'name': _int_api_name,
                    'subnet': _int_api_subnet}

        _tenant_name = TENANT_NET[0] + role_name
        _tenant_subnet = self._generate_subnet_name(TENANT_NET[1]
                                                    + "_" + role_name)
        _tenant = {'name': _tenant_name,
                   'subnet': _tenant_subnet}

        _storage_name = STORAGE_NET[0] + role_name
        _storage_subnet = self._generate_subnet_name(STORAGE_NET[1]
                                                     + "_" + role_name)
        _storage = {'name': _storage_name,
                    'subnet': _storage_subnet}

        _external_name = EXTERNAL_NET[0] + role_name
        _external_subnet = self._generate_subnet_name(EXTERNAL_NET[1]
                                                      + "_" + role_name)
        _external = {'name': _external_name,
                     'subnet': _external_subnet}

        role_d['networks'] = [_int_api, _tenant, _storage, _external]
        role_d['HostnameFormatDefault'] = ("%stackname%-"
                                           + node_type + "-%index%")
        role_params = {}
        role_params['TunedProfileName'] = "virtual-host"
        role_d['RoleParametersDefault'] = role_params
        role_d['disable_upgrade_deployment'] = True
        role_d['uses_deprecated_params'] = False
        role_d['ServicesDefault'] = self._get_default_compute_services()
        return role_d

    ''' TODO: dpaterson DELETE ME if unused
    def _update_stamp_controller_nic_net_cfg(self, r_map, node_type, num_nics):
        role = self._generate_cc_role(node_type)

        # TODO: dpaterson, we should probably break this out into seperate
        # functions based on num_nics, hard coding to 5 for now to reach
        # parity with 13.3
        if num_nics == 5:
            prov_if = r_map["prov_if"] = r_map.get("prov_if", [])

            br_tenant = r_map["br_tenant"] = r_map.get("br_tenant", {})

            prov_edge_route = {"ip_netmask":
                               "{}{}NetCidr".format(CONTROL_PLANE_NET[0],
                                                    role),
                               "next_hop": "ProvisioningNetworkGateway"}

            prov_if.append(prov_edge_route)

            for vlan_id in EDGE_VLANS:
                if vlan_id == "TenantNetworkVlanID":
                    br_tenant["tenant_vlan"] = br_tenant.get("tenant_vlan", [])
                    tenant_route = {"ip_netmask":
                                    "Tenant{}NetCidr".format(role),
                                    "next_hop": "TenantInterfaceDefaultRoute"}
                    br_tenant["tenant_vlan"].append(tenant_route)
                elif vlan_id == "InternalApiNetworkVlanID":
                    br_tenant["internal_api_vlan"] = br_tenant.get(
                        "internal_api_vlan", [])
                    int_api_route = {"ip_netmask":
                                     "InternalApi{}NetCidr".format(role),
                                     "next_hop":
                                     "InternalApiInterfaceDefaultRoute"}
                    br_tenant["internal_api_vlan"].append(int_api_route)
                else:
                    br_tenant["storage_vlan"] = br_tenant.get(
                        "storage_vlan", [])
                    storage_route = {"ip_netmask":
                                     "Storage{}NetCidr".format(role),
                                     "next_hop":
                                     "StorageInterfaceDefaultRoute"}
                    br_tenant["storage_vlan"].append(storage_route)
    '''

    ''' TODO: dpaterson DELETE ME if unused
    def _generate_stamp_controller_nic_params(self, node_type):
        """
        For each node type and network we need to route the edge subnet to
        the local gateway
        ip route add 192.168.142.0/24 via 192.168.140.1
        """
        role = self._generate_cc_role(node_type)
        params = {}
        for net_tup in EDGE_NETWORKS:
            net_cidr = "{}{}NetCidr".format(net_tup[0], role)
            if_def_route = "{}InterfaceDefaultRoute".format(net_tup[0])
            params[net_cidr] = {"default": '', "type": "string"}
            params[if_def_route] = {"default": '', "type": "string"}
        _cp_edge_key = "{}{}NetCidr".format(CONTROL_PLANE_NET[0], role)
        params[_cp_edge_key] = {"default": '', "type": "string"}
        return params
    '''

    def _generate_nic_params(self, node_type):
        role = self._generate_cc_role(node_type)

        cp_default_route = "{}{}DefaultRoute".format(CONTROL_PLANE_NET[0],
                                                     role)
        cp_subnet_cidr = "{}{}SubnetCidr".format(CONTROL_PLANE_NET[0],
                                                 role)
        cp_net_cidr = "{}{}NetCidr".format(CONTROL_PLANE_NET[0], role)
        # TODO: this one is backwards, typically it's suppsed to  be
        # [NetWorkName][Role]SomeKey, but role comes first for CP subet
        # for some reason, try to refactor at some point so it's consistant
        cp_subnet = "{}{}Subnet".format(role, CONTROL_PLANE_NET[0])

        params = {}

        int_api_network = INTERNAL_API_NET[0] + role
        tenant_network = TENANT_NET[0] + role
        storage_network = STORAGE_NET[0] + role
        external_network = EXTERNAL_NET[0] + role
        int_api_cidr = int_api_network + 'NetCidr'
        int_api_vlan = int_api_network + 'NetworkVlanID'
        int_api_subnet = int_api_network + 'IpSubnet'
        int_api_gateway = int_api_network + 'InterfaceDefaultRoute'
        tenant_net_cidr = tenant_network + 'NetCidr'
        tenant_vlan = tenant_network + 'NetworkVlanID'
        tenant_subnet = tenant_network + 'IpSubnet'
        tenant_gateway = tenant_network + 'InterfaceDefaultRoute'
        storage_net_cidr = storage_network + 'NetCidr'
        storage_vlan = storage_network + 'NetworkVlanID'
        storage_subnet = storage_network + 'IpSubnet'
        storage_gateway = storage_network + 'InterfaceDefaultRoute'

        external_net_cidr = external_network + 'NetCidr'
        external_vlan = external_network + 'NetworkVlanID'
        external_subnet = external_network + 'IpSubnet'
        external_gateway = external_network + 'InterfaceDefaultRoute'

        prov_if = role + 'ProvisioningInterface'
        bond_0_if_1 = role + 'Bond0Interface1'
        bond_0_if_2 = role + 'Bond0Interface2'
        bond_1_if_1 = role + 'Bond1Interface1'
        bond_1_if_2 = role + 'Bond1Interface2'
        # InternalApi, Storage and Tenant for routes.
        for network_tup in EDGE_NETWORKS:
            _key = network_tup[0] + 'NetCidr'
            params[_key] = {"default": '', "type": "string"}
        params[EC2_PUBLIC_IPCIDR_PARAM] = {"default": EC2_IPCIDR,
                                             "type": "string"}
        params[cp_subnet_cidr] = {"default": '', "type": "string"}
        params[cp_subnet] = {"default": '', "type": "string"}
        params[cp_default_route] = {"default": '', "type": "string"}
        params[cp_net_cidr] = {"default": '', "type": "string"}
        params[int_api_subnet] = {"default": '', "type": "string"}
        params[int_api_cidr] = {"default": '', "type": "string"}
        params[int_api_vlan] = {"default": 0, "type": "number"}
        params[int_api_gateway] = {"default": '', "type": "string"}
        params[tenant_net_cidr] = {"default": '', "type": "string"}
        params[tenant_vlan] = {"default": 0, "type": "number"}
        params[tenant_subnet] = {"default": '', "type": "string"}
        params[tenant_gateway] = {"default": '', "type": "string"}
        params[storage_net_cidr] = {"default": '', "type": "string"}
        params[storage_vlan] = {"default": 0, "type": "number"}
        params[storage_subnet] = {"default": '', "type": "string"}
        params[storage_gateway] = {"default": '', "type": "string"}
        params[external_net_cidr] = {"default": '', "type": "string"}
        params[external_vlan] = {"default": 0, "type": "number"}
        params[external_subnet] = {"default": '', "type": "string"}
        params[external_gateway] = {"default": '', "type": "string"}
        params[prov_if] = {"default": '', "type": "string"}
        params[bond_0_if_1] = {"default": '', "type": "string"}
        params[bond_0_if_2] = {"default": '', "type": "string"}
        params[bond_1_if_1] = {"default": '', "type": "string"}
        params[bond_1_if_2] = {"default": '', "type": "string"}
        return params

    def _generate_nic_environment_edge(self, node_type, node_type_data):
        """Generate default_parameters subsequently injected into
        nic_environment.yaml for a specific edge site.

        :param node_type: one of the node types defined in .ini file
        :param node_type_data: node type data from node_type stanza in ini.
        For edge sites node_type_data contains all the networking
        params a site requires.
        :returns: OrderedDict of params added to the template's
        parameter_defaults map.
        """
        logger.debug("_generate_nic_environment_edge called!")
        role = self._generate_cc_role(node_type)
        params = {}
        # ControlPlane[ROLE]DefaultRoute: 192.168.120.126
        cp_default_route = 'ControlPlane' + role + 'DefaultRoute'
        # ControlPlane[ROLE]SubnetCidr: '26'
        cp_subnet_cidr = 'ControlPlane' + role + 'SubnetCidr'
        # [ROLE]ControlPlaneSubnet: [subnet]
        cp_subnet = role + 'ControlPlaneSubnet'
        prov_if = role + 'ProvisioningInterface'
        bond_0_if_1 = role + 'Bond0Interface1'
        bond_0_if_2 = role + 'Bond0Interface2'
        bond_1_if_1 = role + 'Bond1Interface1'
        bond_1_if_2 = role + 'Bond1Interface2'
        # cidr = 192.168.122.0/24
        cc_cidr = node_type_data['cidr'].rsplit("/", 1)[1]
        params[cp_default_route] = node_type_data['gateway']
        params[cp_subnet_cidr] = cc_cidr
        params[cp_subnet] = self._generate_subnet_name(node_type)
        params[prov_if] = node_type_data['ProvisioningInterface']
        params[bond_0_if_1] = node_type_data['Bond0Interface1']
        params[bond_0_if_2] = node_type_data['Bond0Interface2']
        params[bond_1_if_1] = node_type_data['Bond1Interface1']
        params[bond_1_if_2] = node_type_data['Bond1Interface2']
        return params

    def _generate_nic_network_config(self, node_type, node_type_data):
        """Generate nic configuration template for a node type and network data
        provided.  This results in a file that corresoponds to the node type,
        which is uploaded to the correct nic_configs sub-directory based on the
        number of ports declared in node_type_data.

        For example if node_type is boston-compute and
        node_type_data.nic_port_count is 5, the resultant file will be uploaded
        to ~/pilot/templates/nic_configs/5_port/bostoncompute.yaml

        Nic configs contain nic bonding, ovs bridges, vlans and
        L3 routing between an edge site and central cloud networks.

        :param node_type: one of the node types defined in .ini file
        :param node_type_data: node type data from node_type stanza in ini.
        For edge sites node_type_data contains all the networking
        params a site requires.
        :returns: list of nic configuration dicts
        """
        role = self._generate_cc_role(node_type)
        cp_default_route = 'ControlPlane' + role + 'DefaultRoute'
        cp_subnet_cidr = 'ControlPlane' + role + 'SubnetCidr'
        cp_subnet = role + 'ControlPlaneSubnet'
        prov_if_param = role + 'ProvisioningInterface'
        bond_0_if_1_param = role + 'Bond0Interface1'
        bond_0_if_2_param = role + 'Bond0Interface2'
        bond_1_if_1_param = role + 'Bond1Interface1'
        bond_1_if_2_param = role + 'Bond1Interface2'
        prov_if = {"type": "interface"}
        tenant_br = {"type": "ovs_bridge"}
        ex_br = {"type": "ovs_bridge"}
        int_api_network = INTERNAL_API_NET[0] + role
        tenant_network = TENANT_NET[0] + role
        storage_network = STORAGE_NET[0] + role
        external_network = EXTERNAL_NET[0] + role
        int_api_subnet = int_api_network + 'IpSubnet'
        int_api_gateway = int_api_network + 'InterfaceDefaultRoute'
        int_api_vlan_id = int_api_network + 'NetworkVlanID'

        tenant_subnet = tenant_network + 'IpSubnet'
        tenant_gateway = tenant_network + 'InterfaceDefaultRoute'
        tenant_vlan_id = tenant_network + 'NetworkVlanID'

        storage_subnet = storage_network + 'IpSubnet'
        storage_gateway = storage_network + 'InterfaceDefaultRoute'
        storage_vlan_id = storage_network + 'NetworkVlanID'

        external_subnet = external_network + 'IpSubnet'
        external_gateway = external_network + 'InterfaceDefaultRoute'
        external_vlan_id = external_network + 'NetworkVlanID'

        prov_if["name"] = prov_if_param
        prov_if["mtu"] = "ProvisioningNetworkMTU"
        prov_if["use_dhcp"] = False
        prov_if["dns_servers"] = "DnsServers"
        _cp_add = [{"ip": "ControlPlaneIp",
                    "cidr": "ControlPlaneSubnetCidr"}]
        prov_if["addresses"] = _cp_add

        ec2_route = {"ip_netmask": EC2_PUBLIC_IPCIDR_PARAM,
                     "next_hop": cp_default_route}
        default_route = {"default": True,
                         "next_hop": cp_default_route}
        prov_route = {"ip_netmask": "{}NetCidr".format(CONTROL_PLANE_NET[0]),
                      "next_hop": cp_default_route}
        prov_if["routes"] = [ec2_route, prov_route]

        tenant_br["name"] = "br-tenant"
        tenant_br["mtu"] = "DefaultBondMTU"
        bond_0 = {"type": "linux_bond"}
        bond_0["name"] = "bond0"
        bond_0["bonding_options"] = "ComputeBondInterfaceOptions"
        bond_0["mtu"] = "DefaultBondMTU"
        bond_0_if_1 = {"type": "interface"}
        bond_0_if_1["name"] = bond_0_if_1_param
        bond_0_if_1["mtu"] = "DefaultBondMTU"
        bond_0_if_1["primary"] = True
        bond_0_if_2 = {"type": "interface"}
        bond_0_if_2["name"] = bond_0_if_2_param
        bond_0_if_2["mtu"] = "DefaultBondMTU"
        bond_0["members"] = [bond_0_if_1, bond_0_if_2]

        internal_api_vlan = {"type": "vlan"}
        internal_api_vlan["device"] = "bond0"

        internal_api_vlan["vlan_id"] = int_api_vlan_id
        internal_api_vlan["mtu"] = "InternalApiMTU"
        internal_api_vlan["addresses"] = [{"ip_netmask":
                                           int_api_subnet}]

        int_api_route = {"ip_netmask": 'InternalApiNetCidr',
                         "next_hop":
                         int_api_gateway}
        internal_api_vlan['routes'] = [int_api_route]

        tenant_vlan = {"type": "vlan"}
        tenant_vlan["device"] = "bond0"
        tenant_vlan["vlan_id"] = tenant_vlan_id
        tenant_vlan["mtu"] = "DefaultBondMTU"
        tenant_vlan["addresses"] = [{"ip_netmask":
                                     tenant_subnet}]
        tenant_route = {"ip_netmask": 'TenantNetCidr',
                        "next_hop": tenant_gateway}
        tenant_vlan['routes'] = [tenant_route]

        storage_vlan = {"type": "vlan"}
        storage_vlan["device"] = "bond0"
        storage_vlan["vlan_id"] = storage_vlan_id
        storage_vlan["mtu"] = "DefaultBondMTU"
        storage_vlan["addresses"] = [{"ip_netmask":
                                      storage_subnet}]
        storage_route = {"ip_netmask": 'StorageNetCidr',
                         "next_hop": storage_gateway}
        storage_vlan['routes'] = [storage_route]

        tenant_br["members"] = [bond_0, internal_api_vlan,
                                tenant_vlan, storage_vlan]

        ex_br["name"] = "bridge_name"
        ex_br["mtu"] = "DefaultBondMTU"
        bond_1_if_1 = {"type": "interface"}
        bond_1_if_1["name"] = bond_1_if_1_param
        bond_1_if_1["mtu"] = "DefaultBondMTU"
        bond_1_if_1["primary"] = True
        bond_1_if_2 = {"type": "interface"}
        bond_1_if_2["name"] = bond_1_if_2_param
        bond_1_if_2["mtu"] = "DefaultBondMTU"
        bond_1 = {"type": "linux_bond"}
        bond_1["name"] = "bond1"
        bond_1["bonding_options"] = "ComputeBondInterfaceOptions"
        bond_1["mtu"] = "DefaultBondMTU"
        bond_1["members"] = [bond_1_if_1, bond_1_if_2]
        external_vlan = {"type": "vlan"}
        external_vlan["device"] = "bond0"
        external_vlan["vlan_id"] = external_vlan_id
        external_vlan["mtu"] = "DefaultBondMTU"
        external_vlan["addresses"] = [
            {"ip_netmask": external_subnet}]

        def_ex_route = {"default": True,
                        "next_hop": external_gateway}
        external_vlan["routes"] = [def_ex_route]
        ex_br["members"] = [bond_1, external_vlan]

        return [prov_if, tenant_br, ex_br]

    def _generate_default_networks_data(self):
        """Generate network_data.yaml file with default networks

        :returns: list of dicts for overcloud networks
        example:
            [{'name': InternalApi,
              'name_lower': internal_api_custom_name,
              # if name_lower is set to a custom name this should be set
              # to original default (optional).  This field is only necessary
              # when changing the default network names,
              # not when adding a new custom network.
              'service_net_map_replace': 'internal_api',
              # for existing stack you may need to override the default
              # transformation for the resource's name.
              'compat_name': DeprecatedInternalApiName,
              'vip': true,
              'enabled': true,
              'vlan': 140,
              'ip_subnet': '192.168.140.0/24',
              'allocation_pools': [{end: '192.168.110.20',
                                    start: '192.168.110.20'}],
              'routes': [{'destination':'10.0.0.0/16', 'nexthop':'10.0.0.1'}],
              'gateway_ip': '192.168.140.1',

              'ipv6': '{{network.ipv6}}',
              'ipv6_subnet': '{{network.ipv6_subnet}}',
              'ipv6_allocation_pools': [{'start': '2001:db8:fd00:1000::10',
                  'end': '2001:db8:fd00:1000:ffff:ffff:ffff:fffe'}],
              'gateway_ipv6': '2001:db8:fd00:1000::/64',
              'routes_ipv6': [{'destination':'fd00:fd00:fd00:3004::/64',
                               'nexthop':'fd00:fd00:fd00:3000::1'}],

               },
            ...
            ]
        """
        setts = self.settings
        default_network_data_list = []
        external = {'name': 'External'}
        external['name_lower'] = 'external'
        external['compat_name'] = "compat name"
        external['ip_subnet'] = setts.public_api_network
        external['vip'] = True
        external['enabled'] = True
        external['vlan'] = int(setts.public_api_vlanid)
        external['gateway_ip'] = setts.public_api_gateway
        _ex_s = setts.public_api_allocation_pool_start
        _ex_e = setts.public_api_allocation_pool_end
        external['allocation_pools'] = [{'start': _ex_s, 'end': _ex_e}]
        default_network_data_list.append(external)

        internal_api = {'name': INTERNAL_API_NET[0]}
        internal_api['name_lower'] = 'internal_api'
        _int_ip_subnet = setts.private_api_network
        internal_api['ip_subnet'] = _int_ip_subnet
        internal_api['vip'] = True
        internal_api['enabled'] = True
        internal_api['vlan'] = int(setts.private_api_vlanid)
        internal_api['gateway_ip'] = setts.private_api_gateway
        _int_s = setts.management_allocation_pool_start
        _int_e = setts.management_allocation_pool_end
        internal_api['allocation_pools'] = [{'start': _int_s, 'end': _int_e}]
        default_network_data_list.append(internal_api)

        storage = {'name': STORAGE_NET[0]}
        storage['name_lower'] = STORAGE_NET[1]
        storage['ip_subnet'] = setts.storage_network
        storage['vip'] = True
        storage['enabled'] = True
        storage['vlan'] = int(setts.storage_vlanid)
        storage['gateway_ip'] = setts.storage_gateway
        _st_s = setts.storage_allocation_pool_start
        _st_e = setts.storage_allocation_pool_end
        storage['allocation_pools'] = [{'start': _st_s, 'end': _st_e}]
        default_network_data_list.append(storage)

        storage_mgmt = {'name': 'StorageMgmt'}
        storage_mgmt['name_lower'] = 'storage_mgmt'
        storage_mgmt['ip_subnet'] = setts.storage_cluster_network
        storage_mgmt['vip'] = True
        storage_mgmt['enabled'] = True
        storage_mgmt['vlan'] = int(setts.storage_cluster_vlanid)
        _stmgmt_s = setts.storage_cluster_allocation_pool_start
        _stmgmt_e = setts.storage_cluster_allocation_pool_end
        storage_mgmt['allocation_pools'] = [{'start': _stmgmt_s,
                                             'end': _stmgmt_e}]
        default_network_data_list.append(storage_mgmt)

        tenant = {'name': TENANT_NET[0]}
        tenant['name_lower'] = TENANT_NET[1]
        _t_ip_subnet = setts.tenant_tunnel_network
        tenant['ip_subnet'] = _t_ip_subnet
        tenant['vip'] = False
        tenant['enabled'] = True
        tenant['vlan'] = int(setts.tenant_tunnel_vlanid)
        tenant['gateway_ip'] = setts.tenant_tunnel_gateway
        _t_s = setts.tenant_tunnel_network_allocation_pool_start
        _t_e = setts.tenant_tunnel_network_allocation_pool_end
        tenant['allocation_pools'] = [{'start': _t_s, 'end': _t_e}]
        default_network_data_list.append(tenant)

        return default_network_data_list

    def _generate_network_data(self, node_type, node_type_data):
        """Generate network_data.yaml networks based on node type network
        definitions

        :param node_type: The node type network data is being generated for
        :param node_type_data: dict containing all the site specific networking
        configuration data
        :returns: list of dicts for edge networks
        example:
            [{'name': InternalApiBostonCompute
              'name_lower': internal_api_boston_compute
              'ip_subnet': '192.168.141.0/24'
              'vip': true
              'vlan': 141
              'allocation_pools': [{end: '192.168.111.20',
                                    start: '192.168.111.20'}]
               },
            ...
            ]
        """
        role = self._generate_cc_role(node_type)
        networks_param_mapping = {}
        int_api = {}
        int_api['vlan'] = 'private_api_vlanid'
        int_api['lower'] = INTERNAL_API_NET[1]
        int_api['ip_subnet'] = 'private_api_network'
        int_api['allocation_pools'] = ('private_api_allocation_pool_start',
                                       'private_api_allocation_pool_end')
        int_api['gateway_ip'] = 'private_api_gateway'
        tenant = {}
        tenant['vlan'] = 'tenant_vlanid'
        tenant['lower'] = TENANT_NET[1]
        tenant['ip_subnet'] = 'tenant_network'
        tenant['allocation_pools'] = ('tenant_allocation_pool_start',
                                      'tenant_allocation_pool_end')
        tenant['gateway_ip'] = 'tenant_gateway'

        storage = {}
        storage['vlan'] = 'storage_vlanid'
        storage['lower'] = STORAGE_NET[1]
        storage['ip_subnet'] = 'storage_network'
        storage['allocation_pools'] = ('storage_allocation_pool_start',
                                       'storage_allocation_pool_end')
        storage['gateway_ip'] = 'storage_gateway'

        external = {}
        external['vlan'] = 'external_vlanid'
        external['lower'] = EXTERNAL_NET[1]
        external['ip_subnet'] = 'external_network'
        external['allocation_pools'] = ('external_allocation_pool_start',
                                        'external_allocation_pool_end')
        external['gateway_ip'] = 'external_gateway'

        networks_param_mapping[INTERNAL_API_NET[0]] = int_api
        networks_param_mapping[TENANT_NET[0]] = tenant
        networks_param_mapping[STORAGE_NET[0]] = storage
        networks_param_mapping[EXTERNAL_NET[0]] = external
        network_data_list = []
        suffix = '_' + self._generate_role_network_lower(node_type)
        for network, mapping in networks_param_mapping.items():
            nd = {'enabled': True}
            name_cc = network + role
            name_lower = mapping['lower']

            nd['name'] = name_cc
            nd['name_lower'] = name_lower + suffix
            nd['vip'] = False
            nd['vlan'] = int(node_type_data[mapping['vlan']])
            _ip_subnet = node_type_data[mapping['ip_subnet']]
            nd['ip_subnet'] = _ip_subnet
            _s = node_type_data[mapping['allocation_pools'][0]]
            _e = node_type_data[mapping['allocation_pools'][1]]
            nap = [{'start': _s, 'end': _e}]
            nd['allocation_pools'] = nap
            gw = node_type_data[mapping['gateway_ip']]
            nd['gateway_ip'] = gw
            network_data_list.append(nd)
        return network_data_list

    def _generate_extra_config(self, type):
        """Each edge site requires some overrides, for connecting to mysql for
        example.  Generate hiera data parameters puppet will consume at edge
        sites to provide overrrides.

        :param type: the node type the extra params are being generated for
        :returns: dict containing parameter overrides
        """
        net_suffix = '_' + self._generate_role_network_lower(type)
        api_net = INTERNAL_API_NET[1] + net_suffix
        tenant_net = TENANT_NET[1] + net_suffix

        xtra_cfg = {}
        xtra_cfg['nova::compute::libvirt::vncserver_listen'] = \
            '%{hiera("' + api_net + '")}'
        xtra_cfg['nova::compute::vncserver_proxyclient_address'] = \
            '%{hiera("' + api_net + '")}'
        xtra_cfg['neutron::agents::ml2::ovs::local_ip'] = \
            '%{hiera("' + tenant_net + '")}'
        xtra_cfg['cold_migration_ssh_inbound_addr'] = \
            '%{hiera("' + api_net + '")}'
        xtra_cfg['live_migration_ssh_inbound_addr'] = \
            '%{hiera("' + api_net + '")}'
        xtra_cfg['nova::migration::libvirt::live_migration_inbound_addr'] = \
            '%{hiera("' + api_net + '")}'
        xtra_cfg['nova::my_ip'] = '%{hiera("' + api_net + '")}'
        _mysql_key = 'tripleo::profile::base::database::mysql' \
            + '::client::mysql_client_bind_address'
        xtra_cfg[_mysql_key] = '%{hiera("' + api_net + '")}'
        # TODO not sure below are needed
        xtra_cfg['nova::cpu_allocation_ratio'] = 1
        xtra_cfg['nova::compute::resume_guests_state_on_host_boot'] = True
        xtra_cfg['nova::compute::libvirt::libvirt_cpu_model'] = \
            'host-passthrough'
        xtra_cfg['nova::compute::libvirt::libvirt_cpu_model_extra_flags'] = \
            'host-tsc-deadline'
        xtra_cfg['nova::compute::libvirt::mem_stats_period_seconds'] = 0
        return xtra_cfg

    def _generate_cc_role(self, type):
        """Find non-alphanumerics in node type and replace with space then
        camel-case that and strip spaces
        :returns:  CamelCaseRoleName from my-node_type
        """
        role_cc = (re.sub(r'[^a-z0-9]', " ",
                          type.lower()).title()).replace(" ", "")
        return role_cc

    def _generate_role_network_lower(self, type):
        _type_lwr = (re.sub(r'[^a-z0-9]', " ", type.lower()).replace(" ", "_"))
        return _type_lwr

    def _generate_subnet_name(self, type):
        return self._generate_role_network_lower(type) + '_subnet'

    def _generate_node_type_lower(self, type):
        # should look like denveredgecompute.yaml if following existing pattern
        nic_config_name = re.sub(r'[^a-z0-9]', "", type.lower())
        return nic_config_name

    def _generate_node_placement(self, tmplt_data, node_type):
        tmplt_data["parameter_defaults"] = (tmplt_data["parameter_defaults"]
                                            if "parameter_defaults"
                                            in tmplt_data else {})
        _param_def = tmplt_data["parameter_defaults"]
        _param_def["scheduler_hints"] = (_param_def["scheduler_hints"]
                                         if "scheduler_hints"
                                         in _param_def else {})
        _sched_hints = _param_def["scheduler_hints"]

        exp = self._generate_node_placement_exp(node_type)
        role = self._generate_cc_role(node_type)
        _role_hints = role + 'SchedulerHints'
        _sched_hints[_role_hints] = exp

    def _generate_node_placement_exp(self, type):
        placement_exp = ((re.sub(r'[^a-z0-9]', " ",
                                 type.lower())).replace(" ", "-") + "-%index%")
        return placement_exp

    def _group_node_types_by_num_nics(self):
        setts = self.settings
        nic_dict_by_port_num = {}
        for node_type, node_type_data in setts.node_type_data_map.items():
            num_nics = int(node_type_data['nic_port_count'])
            if num_nics not in nic_dict_by_port_num:
                nic_dict_by_port_num[num_nics] = []
            nic_dict_by_port_num[num_nics].append((node_type, node_type_data))
        return nic_dict_by_port_num

    @directory_check(STAGING_TEMPLATES_PATH)
    def _get_default_compute_services(self):
        """Lazy loading of default compute role services
        :returns: list of default compute services for edge role generation
        """
        if not self.default_compute_services:
            stg_compute_file = os.path.join(STAGING_TEMPLATES_PATH,
                                            DEF_COMPUTE_ROLE_FILE)
            self.download_file(stg_compute_file, DEF_COMPUTE_REMOTE_PATH)
            with open(stg_compute_file) as stg_compute_fp:
                compute_yaml = yaml.load(stg_compute_fp, Loader=OrderedLoader)
                # Role yamls are always list, even for single-role
                # template files
                _srv_defs = compute_yaml[0]['ServicesDefault']
                self.default_compute_services = _srv_defs
        return self.default_compute_services


if __name__ == "__main__":
    director = Director()
    # director.render_and_upload_compute_templates_edge()
    # director.render_and_upload_network_isolation_edge()
    # director.render_and_upload_node_placement_edge()
    # director.render_and_upload_roles_data_edge()
    # director.render_and_upload_static_ips_edge()
    # director.render_and_upload_network_data_edge()
    # director.render_and_upload_nic_env_edge()
    # director.render_and_upload_compute_templates_edge()
    # director.render_and_upload_network_environment_edge()
