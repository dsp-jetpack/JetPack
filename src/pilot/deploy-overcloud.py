#!/usr/bin/python

# (c) 2016 Dell
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

import argparse
import distutils.dir_util
import os
import re
import subprocess
import sys
import time

from credential_helper import CredentialHelper
from subprocess import check_output

# Dell utilities
from identify_nodes import main as identify_nodes
from update_ssh_config import main as update_ssh_config

home_dir = os.path.expanduser('~')


def subst_home(relative_path):
    in_file_name = os.path.join(home_dir, relative_path)
    out_file_name = in_file_name + '.out'

    in_file = open(in_file_name, 'r')
    out_file = open(out_file_name, 'w')

    for line in in_file:
        line = re.sub("HOME", home_dir, line)
        out_file.write(line)

    in_file.close()
    out_file.close()

    os.rename(in_file_name, in_file_name + '.bak')
    os.rename(out_file_name, in_file_name)


def create_volume_types():
    print 'Creating cinder volume types...'
    # Add ceph by default
    types = [["rbd_backend", "tripleo_ceph"]]

    if args.enable_eqlx or args.enable_dellsc:
        cinder_file = open(home_dir +
                           '/pilot/templates/dell-cinder-backends.yaml', 'r')
        for line in cinder_file:
            line = line.strip()
            try:
                found = re.search('cinder_user_enabled_backends: \[(.+?)\]',
                                  line).group(1)
                backends = found.split(",")
                for backend in backends:
                    types.append([backend + "_backend", backend])
            except AttributeError:
                found = ''

    overcloudrc_name = CredentialHelper.get_overcloudrc_name()

    for type in types:
        cmd = "source {} && " \
              "cinder type-create {} && " \
              "cinder type-key {} set volume_backend_name={}" \
              "".format(overcloudrc_name, type[0], type[0], type[1])
        os.system(cmd)

    os.system("source {} && "
              "cinder extra-specs-list".format(overcloudrc_name))


def update_swift_endpoint(keystone_client):
    swift_service = keystone_client.services.find(**{'name': 'swift'})
    swift_endpoint = keystone_client.endpoints.find(
        **{'service_id': swift_service.id})

    # The radosgw uses this suffix for all Swift endpoint URLs
    radosgw_url_suffix = '/swift/v1'

    if swift_endpoint.publicurl.endswith(radosgw_url_suffix):
        print 'Swift endpoint is already configured for Ceph radosgw.'
        return

    # Delete the current Swift endpoint, and recreate it with with URLs for the
    # Ceph radosgw.
    print 'Updating Swift endpoint for Ceph radosgw...'
    keystone_client.endpoints.delete(swift_endpoint.id)

    # Convert the Swift URLs to a Ceph radogw URLs. Trim everything after "/v1"
    # (including any "/AUTH_%(tenant_id)s" suffix), and append the radosgw
    # suffix.

    url = swift_endpoint.publicurl
    swift_endpoint.publicurl = url[:url.rfind('/v1'):] + radosgw_url_suffix

    url = swift_endpoint.adminurl
    swift_endpoint.adminurl = url[:url.rfind('/v1'):] + radosgw_url_suffix

    url = swift_endpoint.internalurl
    swift_endpoint.internalurl = url[:url.rfind('/v1'):] + radosgw_url_suffix

    keystone_client.endpoints.create(region=swift_endpoint.region,
                                     service_id=swift_service.id,
                                     publicurl=swift_endpoint.publicurl,
                                     adminurl=swift_endpoint.adminurl,
                                     internalurl=swift_endpoint.internalurl)


def finalize_overcloud():
    from credential_helper import CredentialHelper
    from os_cloud_config.utils import clients

    os_auth_url, os_tenant_name, os_username, os_password = \
        CredentialHelper.get_overcloud_creds()

    try:
        keystone_client = clients.get_keystone_client(os_username,
                                                      os_password,
                                                      os_tenant_name,
                                                      os_auth_url)
    except:
        return None

    create_volume_types()
    update_swift_endpoint(keystone_client)

    horizon_service = keystone_client.services.find(**{'name': 'horizon'})
    horizon_endpoint = keystone_client.endpoints.find(
        **{'service_id': horizon_service.id})
    return horizon_endpoint.publicurl


def main():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument("--controllers", dest="num_controllers", type=int,
                        default=3, help="The number of controller nodes")
    parser.add_argument("--computes", dest="num_computes", type=int,
                        required=True, help="The number of compute nodes")
    parser.add_argument("--storage", dest="num_storage", type=int,
                        required=True, help="The number of storage nodes")
    parser.add_argument("--vlans", dest="vlan_range", required=True,
                        help="The VLAN range to use for Neutron in xxx:yyy "
                             "format")
    parser.add_argument("--ntp", dest="ntp_server_fqdn",
                        default="0.centos.pool.ntp.org",
                        help="The FQDN of the ntp server to use")
    parser.add_argument("--timeout", default="120",
                        help="The amount of time in minutes to allow the "
                             "overcloud to deploy")
    parser.add_argument("--overcloud_name", default=None,
                        help="The name of the overcloud")
    parser.add_argument('--enable_eqlx', action='store_true', default=False,
                        help="Enable cinder Dell Eqlx backend")
    parser.add_argument('--enable_dellsc', action='store_true', default=False,
                        help="Enable cinder Dell Storage Center backend")
    # parser.add_argument('--static_ips', action='store_true', default=False,
    #  help="Specify the IPs and VIPs on the controller nodes")
    args = parser.parse_args()
    p = re.compile('\d+:\d+')
    if not p.match(args.vlan_range):
        print("Error: The VLAN range must be a number followed by a colon, "
              "followed by another number")
        sys.exit(1)

    os_auth_url, os_tenant_name, os_username, os_password = \
        CredentialHelper.get_undercloud_creds()

    # Replace HOME with the actual home directory in a few files
    subst_home('pilot/templates/dell-environment.yaml')
    subst_home('pilot/templates/static-ip-environment.yaml')
    subst_home('pilot/templates/network-environment.yaml')

    # Apply any patches required on the Director itself. This is done each time
    # the overcloud is deployed (instead of once, after the Director is
    # installed) in order to ensure an update to the Director doesn't overwrite
    # the patch.
    cmd = os.path.join(home_dir, 'pilot', 'patch-director.sh')
    status = os.system(cmd)
    if status != 0:
        print("\nError: {} failed, unable to continue".format(cmd))
        print("See the comments in that file for additional information")
        sys.exit(1)

    # Recursively copy pilot/templates/overrides to pilot/templates/overcloud
    overrides_dir = os.path.join(home_dir, 'pilot/templates/overrides')
    overcloud_dir = os.path.join(home_dir, 'pilot/templates/overcloud')
    distutils.dir_util.copy_tree(overrides_dir, overcloud_dir)

    # Launch the deployment

    overcloud_name_opt = ""
    if args.overcloud_name is not None:
        overcloud_name_opt = "--stack " + args.overcloud_name

    # The order of the environment files is important as a later inclusion
    # overrides resources defined in prior inclusions.

    # The network-environment.yaml must be included after the
    # network-isolation.yaml
    env_opts = "-e ~/pilot/templates/overcloud/environments/network-isolation.yaml" \
               " -e ~/pilot/templates/network-environment.yaml"

    # The static-ip-environment.yaml must be included after the
    # network-environment.yaml
    # if args.static_ips:
    #   env_opts += " -e ~/pilot/templates/static-ip-environment.yaml"

    # The dell-environment.yaml must be included after the
    # storage-environment.yaml
    env_opts += " -e ~/pilot/templates/overcloud/environments/storage-environment.yaml" \
                " -e ~/pilot/templates/dell-environment.yaml" \
                " -e /usr/share/openstack-tripleo-heat-templates/" \
                "environments/puppet-pacemaker.yaml"

    if args.enable_dellsc | args.enable_eqlx:
        env_opts += " -e ~/pilot/templates/dell-cinder-backends.yaml"

    cmd = "cd ; openstack overcloud deploy" \
          " --log-file ~/pilot/overcloud_deployment.log" \
          " -t {}" \
          " {}" \
          " --templates ~/pilot/templates/overcloud" \
          " {}" \
          " --control-flavor control" \
          " --compute-flavor compute" \
          " --ceph-storage-flavor ceph-storage" \
          " --swift-storage-flavor swift-storage" \
          " --block-storage-flavor block-storage" \
          " --neutron-public-interface bond1" \
          " --neutron-network-type vlan" \
          " --neutron-disable-tunneling" \
          " --os-auth-url {}" \
          " --os-project-name {}" \
          " --os-user-id {}" \
          " --os-password {}" \
          " --control-scale {}" \
          " --compute-scale {}" \
          " --ceph-storage-scale {}" \
          " --ntp-server {}" \
          " --neutron-network-vlan-ranges physint:{},physext" \
          " --neutron-bridge-mappings physint:br-tenant,physext:br-ex" \
          "".format(args.timeout,
                    overcloud_name_opt,
                    env_opts,
                    os_auth_url,
                    os_tenant_name,
                    os_username,
                    os_password,
                    args.num_controllers,
                    args.num_computes,
                    args.num_storage,
                    args.ntp_server_fqdn,
                    args.vlan_range)

    print cmd
    start = time.time()
    status = os.system(cmd)
    end = time.time()
    print '\nExecution time: {} (hh:mm:ss)'.format(time.strftime('%H:%M:%S',
                                                   time.gmtime(end - start)))
    if status == 0:
        horizon_url = finalize_overcloud()
    else:
        horizon_url = None

    print 'Fetching SSH keys...'
    update_ssh_config()
    print 'Overcloud nodes:'
    identify_nodes()

    if horizon_url:
        print '\nHorizon Dashboard URL: {}\n'.format(horizon_url)

if __name__ == "__main__":
    main()
