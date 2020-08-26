#!/usr/bin/python3

# Copyright (c) 2018-2020 Dell Inc. or its subsidiaries.
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

# IMPORTS
import csv
import json
import sys
import io

from collections import defaultdict


class parse_key_components:
    role_type = None
    node_id = None

    def setKey(self, key):
        key_tokens = key.split('_')
        key_token_count = len(key_tokens)
        if key_token_count > 2:
            self.node_id = key_tokens[1]
            self.role_type = key_tokens[0]
        else:
            self.role_type = key_tokens[0]

    def getNodeId(self):
        if unicode(self.node_id).isnumeric():
            return self.node_id
        else:
            return 'false'

    def getRoleType(self):
        return self.role_type


def read_input_file(input_file):
    inputFile = open("exported_name_value.csv", 'r')
    csvIn = csv.DictReader(inputFile, fieldnames=("Key", "Value"),
                           delimiter='|')

    settings = {}
    keys = []
    value = []

    for row in csvIn:
        if row["Key"] not in keys:
            key = row["Key"]
            value = row["Value"]
            if key.startswith("sah_"):
                node_setting_key = key.split("sah_")[1]
                p = parse_key_components()
                p.setKey(key)
                role_type = p.getRoleType()
                node_id = p.getNodeId()
            elif key.startswith("director_"):
                node_setting_key = key.split("director_")[1]
                p = parse_key_components()
                p.setKey(key)
                role_type = p.getRoleType()
                node_id = p.getNodeId()
            elif key.startswith("powerflexgw_"):
                node_setting_key = key.split("powerflexgw_")[1]
                p = parse_key_components()
                p.setKey(key)
                role_type = p.getRoleType()
                node_id = p.getNodeId()
            elif key.startswith("controller_"):
                p = parse_key_components()
                p.setKey(key)
                role_type = p.getRoleType()
                node_id = p.getNodeId()
                if node_id.isdigit():
                    node_setting_key = key.split("controller_" +
                                                 node_id + "_")[1]
                else:
                    continue
            elif key.startswith("compute_"):
                p = parse_key_components()
                p.setKey(key)
                role_type = p.getRoleType()
                node_id = p.getNodeId()
                if node_id.isdigit():
                    node_setting_key = key.split("compute_" +
                                                 node_id + "_")[1]
                else:
                    continue
            elif key.startswith("storage_"):
                p = parse_key_components()
                p.setKey(key)
                role_type = p.getRoleType()
                node_id = p.getNodeId()
                if node_id.isdigit():
                    node_setting_key = key.split("storage_" +
                                                 node_id + "_")[1]
                else:
                    continue
            else:
                continue

        if role_type in settings:
            node_settings = settings[role_type]
        else:
            node_settings = {}

        if node_id in node_settings:
            node_id_settings = node_settings[node_id]
        else:
            node_id_settings = {}

        if role_type.startswith("sah"):
            node_id_settings['is_sah'] = 'true'
        elif role_type.startswith("director"):
            node_id_settings['is_director'] = 'true'
        elif role_type.startswith("powerflexgw"):
            node_id_settings['is_powerflexgw'] = 'true'
        elif role_type.startswith("compute"):
            node_id_settings['is_compute'] = 'true'
        elif role_type.startswith("controller"):
            node_id_settings['is_controller'] = 'true'
        elif role_type.startswith("storage"):
            node_id_settings['is_ceph_storage'] = 'true'
        else:
            continue

        node_id_settings[node_setting_key] = value
        node_settings[node_id] = node_id_settings
        settings[role_type] = node_settings
    return settings


def generate_output_file(in_data, output_file,
                         excluded_keys, use_service_tags):
    i = 0
    outputFile = open(output_file, 'w')
    sections = []

    top_level_keys = in_data.keys()
    key_count = len(top_level_keys)
    for tlkey in top_level_keys:
        nexlevel_keys = in_data.get(tlkey).keys()
        i = i+1
        for nexkey in nexlevel_keys:
            odata = in_data.get(tlkey).get(nexkey)

            if use_service_tags and "idrac_ip" in odata:
                del odata["idrac_ip"]
            elif "service_tag" in odata:
                del odata["service_tag"]

            if "is_director" in odata:
                del odata["storage_ip"]

            if "is_controller" in odata:
                del odata["storage_cluster_ip"]
                del odata["provisioning_ip"]

            if "is_compute" in odata:
                del odata["storage_cluster_ip"]
                del odata["provisioning_ip"]
                del odata["public_api_ip"]

            if "is_ceph_storage" in odata:
                del odata["tenant_tunnel_ip"]
                del odata["private_api_ip"]
                del odata["provisioning_ip"]
                del odata["public_api_ip"]

            if excluded_keys is not None:
                for exclude_key in excluded_keys:
                    if exclude_key in odata:
                        del odata[exclude_key]
            sections.append(odata)
    outputFile.write(json.dumps(sections, indent=4, sort_keys=True))
    outputFile.close()


def main():
    num_args = len(sys.argv) - 1
    use_service_tag = False

    if num_args < 2:
        print("error: missing required arguments")
        print("usage: python %s <kvp_input_file> <output_file> \
              [-use_service_tag]" % sys.argv[0])
        sys.exit(1)

    kvp_in_file = sys.argv[1]
    output_file = sys.argv[2]
    if num_args == 3:
        mode = sys.argv[3]
        if mode == '-use_service_tag':
            use_service_tag = True

    if kvp_in_file == output_file:
        print("error: all file arguments must be unique")
        sys.exit(1)

    in_data = read_input_file(kvp_in_file)

    if len(in_data) > 0:
        excluded_keys = ["bonding_opts",
                         "bond_opts",
                         "bond_0_interface_0",
                         "bond_0_interface_1",
                         "bond_1_interface_0",
                         "bond_1_interface_1",
                         "public_ip",
                         "os_oob_management_ip",
                         "provisioning_interface",
                         "install_user",
                         "install_user_password",
                         "ipmi_user",
                         "ipmi_password"]
        generate_output_file(in_data, output_file,
                             excluded_keys, use_service_tag)
    else:
        print("no input data. not populating output ini file")
        sys.exit(1)


if __name__ == '__main__':
    main()
