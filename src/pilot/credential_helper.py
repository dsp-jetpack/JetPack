import os
import json
from subprocess import check_output
from misc_helper import MiscHelper


class CredentialHelper:
    @staticmethod
    def get_creds(filename):
        creds_file = open(filename, 'r')

        for line in creds_file:
            prefix = "export"
            if line.startswith(prefix):
                line = line[len(prefix):]

            line = line.strip()
            key, val = line.split('=', 2)
            key = key.lower()

            if key == 'os_username':
                os_username = val
            elif key == 'os_auth_url':
                os_auth_url = val
            elif key == 'os_tenant_name':
                os_tenant_name = val
            elif key == 'os_password':
                os_password = val

        if 'hiera' in os_password:
            os_password = check_output(['sudo', 'hiera', 'admin_password']).strip()

        return os_auth_url, os_tenant_name, os_username, os_password

    @staticmethod
    def get_undercloud_creds():
        return CredentialHelper.get_creds(os.path.join(os.path.expanduser('~'),
                                                       'stackrc'))

    @staticmethod
    def get_overcloud_creds():
        rc_name = "{}rc".format(MiscHelper.get_stack_name())
        return CredentialHelper.get_creds(os.path.join(os.path.expanduser('~'),
                                                       rc_name))

    @staticmethod
    def get_drac_creds(ironic_client, node_uuid,
                       instackenv_file="instackenv.json"):
        # Get the DRAC IP, username, and password
        node = ironic_client.node.get(node_uuid, ["driver_info"])

        return CredentialHelper.get_drac_creds_from_node(node)

    @staticmethod
    def get_drac_creds_from_node(node, instackenv_file="instackenv.json"):
        drac_ip, drac_user = CredentialHelper.get_drac_ip_and_user(node)

        # Can't get the password out of ironic, so dig it out of the
        # instackenv.json file
        drac_password = CredentialHelper.get_drac_password(
            drac_ip, instackenv_file)

        return drac_ip, drac_user, drac_password

    @staticmethod
    def get_drac_ip_and_user(node):
        driver_info = node.driver_info
        if "drac_host" in driver_info:
            drac_ip = driver_info["drac_host"]
            drac_user = driver_info["drac_username"]
        else:
            drac_ip = driver_info["ipmi_address"]
            drac_user = driver_info["ipmi_username"]

        return drac_ip, drac_user

    @staticmethod
    def get_drac_ip(node):
        drac_ip, drac_user = CredentialHelper.get_drac_ip_and_user(node)

        return drac_ip

    @staticmethod
    def get_drac_password(ip, instackenv_file):
        json_file = os.path.join(os.path.expanduser('~'), instackenv_file)
        instackenv_json = open(json_file, 'r')
        instackenv = json.load(instackenv_json)

        nodes = instackenv["nodes"]

        for node in nodes:
            if node["pm_addr"] == ip:
                return node["pm_password"]

        return None
