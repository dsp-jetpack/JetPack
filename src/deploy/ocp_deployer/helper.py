import ipaddress
import getpass
import hashlib
import json
import logging
import os
import re
import requests
import sys
import time

from urllib.request import urlopen
from urllib.error import HTTPError
from urllib3.exceptions import InsecureRequestWarning


def get_user_response(message=''):
    """
    User response invoked when error exists

    """
    valid_responses = ['y', 'NO']
    response = ''
    while response not in valid_responses:
        logging.error('{}'.format(message))
        response = input('Do you want to continue (y/NO): ')
        if response not in valid_responses:
            logging.info('Valid responses are \'y\' or \'NO\'')

    if response == 'NO':
        logging.info('QUITTING!!')
        sys.exit()

    
def create_dir(directory):
    """ 
    create directory recursively
 
    """
    try:
        os.makedirs(directory)
        logging.info('successfully created directory {}'.format(directory))
    except OSError:
        logging.error('creating directory {} failed'.format(directory))

def check_path(path, isfile=False, isdir=False):
    """ 
    returns if path given is a file or directory

    """
    
    return os.path.isfile(path) if isfile else os.path.isdir(path)

def set_values(user_input, default, check=''):
    """ 
    sets default value if user input is empty value.
    ensures integer value if necessary

    """
    if check == 'integer' and user_input != '':
        user_input = check_user_input_if_integer(user_input)
        
    return default if not user_input else user_input

def validate_url(url):
    """ 
    validates url and checks if any HTTP Errors

    """
    url_verify = ''

    try:
        url_verify = urlopen(url)
    except HTTPError:
        get_user_response(message='Error validating URL: {}'.format(url))

    return url_verify

def check_user_input_if_integer(user_input):
    """ 
    check if user input is integer and not any other data type

    """
    integer_input = ''
    while not integer_input:
         try:
             integer_input = int(user_input)
         except ValueError:
             logging.warn('only integer number accepted')
             user_input = input('enter a number: ')

    return integer_input

def get_ip(node_name='', ip_type=''):
    """ 
    get the ip address of a node

    """
    ip = ''
    
    while True:
        ip = input('ip address for {} in {} node: '.format(ip_type, node_name))
        ip_check = validate_ip(ip)
        if ip_check:
            break
        else:
            logging.warn('ip address should be in format: x.x.x.x')
    
    return ip  

def validate_file(directory, filename, url):
    re_hash = ''
    hash_value = False
    logging.info('validating file {} in {}'.format(filename, directory))

    with open('{}/{}'.format(directory, filename), 'rb') as f:
       bytes = f.read()
       re_hash = hashlib.sha256(bytes).hexdigest()
    logging.info('sha256 for file {} is {}'.format(filename, re_hash))
    
    with open('{}/rhcos.txt'.format(directory)) as f:
       if re_hash and re_hash in f.read():
           logging.info('sha256sum for file {} is validated in rhcos.txt'.format(filename))
           hash_value = True

    if not hash_value:
        with open('{}/client.txt'.format(directory)) as f:
            if re_hash and re_hash in f.read():
                logging.info('sha256sum for file {} is validated in client.txt'.format(filename))
                hash_value = True

    return hash_value

def validate_ip(ip):
    """    
    validates ip address format
    
    """
    valid_ip = ''
    try:
        valid_ip = str(ipaddress.ip_address(ip))
    except ValueError:
        logging.error('ip address \'{}\' is not valid: '.format(ip))
  
    return valid_ip

def validate_port(port):
    """
    validate ports to ensure HAProxy ports are not reused

    """
    invalid_ports = [80, 443, 6443, 22623]
    while True:
        try:
            check_for_string = port.isdigit()
            if not check_for_string:
                logging.warn('port has to be an integer')
            else:
                invalid_ports.index(int(port))
            logging.warn('ports {} are not allowed'.format(invalid_ports))
            port = input('enter a port: ')
        except AttributeError:
            break 
        except ValueError:
            break

    return port

def validate_network_cidr(network_cidr):
    """
    validate ip address with cidr format. defaults to /24 if only IP is given

    """
    compressed_network_cidr = ''
    while True:
        try:
            compressed_network_cidr = ipaddress.ip_network(network_cidr)
            break
        except ValueError:
            logging.warn('input should be in format x.x.x.x/x')
            network_cidr = input('enter the network cidr: ')

    return compressed_network_cidr.compressed
    

def validate_cidr(cidr):
    """ 
    validates subnet in cidr format.

    """
    check_integer = ''
    while not check_integer:
         check_integer = check_user_input_if_integer(cidr)     
         if check_integer and check_integer < 32:
             pass
         else:
             cidr = input('user input has to be an integer and less than 32: ')
             
    return cidr

def check_ip_ping(ip):

    command = 'ping -c 3 {} > /dev/null'.format(ip)
    response = os.system(command)
  
    return response           

def get_idrac_creds(ip):
    user = input('enter the idrac user for {}: '.format(ip))
    passwd = getpass.getpass('enter the idrac password for {}: '.format(ip))
  
    return user, passwd

def map_interfaces_network(network_devices):
    devices = []
    if network_devices:
        for network_device in network_devices:
            device = list(map(lambda interface: interface.encode('ascii'), network_device.values()))
            try:
                devices.append(device[0].decode("utf-8").split('/')[-1])
            except IndexError:
                logging.error('Did not find any network devices')

    return devices

def connect_to_idrac(user, passwd, base_api_url):
    """ 
    establishes connection to idrac

    """
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    response = ''
    status_code = None
    try:
        response = requests.get(base_api_url, verify=False, auth=(user, passwd),
                                timeout=5) 
    except requests.exceptions.ConnectTimeout:
        logging.info('timeout')
        get_user_response(message='connecting to idrac timeout')
    except Exception as e:
        logging.error('{}'.format(e))  
        get_user_response(message='connecting to idrac unknown exception occurred')

    try:
        status_code = response.status_code
    except AttributeError:
        logging.error('could not get idrac response status code')
        
        return None

    return response if status_code == 200 else None


def get_server_model(user, passwd, api_url):
    """
    get server model using redfish API

    """
    server_model = None
    response = connect_to_idrac(user, passwd, api_url)
    output = response.json()
    if output:
        server_model = output['Model']

    return server_model

    
def get_network_devices(user, passwd, base_api_url):
    """ 
    get list of network devices from iDRAC 

    """
    network_devices = ''
    response = connect_to_idrac(user, passwd, base_api_url)
    if response and response.json():
        network_devices_info = response.json()
        try:
            network_devices = network_devices_info[u'Members']
        except KeyError:
            network_devices = ''
            get_user_response(message='could not get network devices info')
    else:
        get_user_response(message='idrac connection status code is 401')

    return network_devices
  
def generate_network_devices_menu(devices, purpose=''):
    """ 
    generate a list of network devices menu obtained from iDRAC 

    """
    menu = {}
    i = 1
    choice = ''
    devices.sort()
    for device in devices:
        menu[int(i)] = device
        i += 1
    while True:
        options = menu.keys()
        for entry in options:
            logging.info('{} -> {}'.format(entry, menu[entry]))
        choice = input('Select the interface used by {}: '.format(purpose))
        try:
            menu[int(choice)]
            break
        except KeyError:
            logging.warn('Invalid option')
            continue
        except ValueError:
            logging.warn('Input option should be integer and not string')
            continue

    selected_network_device = menu[int(choice)]
    logging.info('selected interface is: {}'.format(menu[int(choice)]))
    
    return selected_network_device
        
def get_mac_address(selected_network_device, base_api_url, user, passwd):
    """ 
    get mac address for a selected network device

    """   
    url = '{}/{}'.format(base_api_url, selected_network_device)
    device_mac_address = ''
    try:
        response = requests.get(url, verify=False, auth=(user, passwd),
                                timeout=5)
    except requests.exceptions.ConnectionTimeout:
        logging.error('failed to establish connection to get mac address')

    try:
        network_device_info = response.json()
    except ValueError:
        logging.error('check URL, iDRAC user and password may be invalid')
        logging.info('{}'.format(url))

    try:
        device_mac_address = network_device_info[u'MACAddress']
    except KeyError:
        logging.error('No MAC Address found for network devices')
        logging.info('{}'.format(selected_network_device))

    return device_mac_address

def get_network_device_mac(device, user, passwd, base_api_url):
    """ 
    lists available network devices from iDRAC
    generates a menu of network devices
    obtains mac address for the network device

    """
    network_device_mac_address = ''

    if device:
        selected_network_device = device
        network_device_mac_address = get_mac_address(selected_network_device, base_api_url, user, passwd)

    if network_device_mac_address:
        logging.info('device {} mac address is {}'.format(selected_network_device, network_device_mac_address))
    
    return network_device_mac_address

def get_device_enumeration(device, os='', server_model=''):
    """
    get device enumeration based on server model

    """

    integrated_nic_patterns = ['NIC.Integrated.1-', 'NIC.Embedded.']
    nic_slot_patterns = ['NIC.Slot.', 'NIC.Mezzanine.']
    enumeration = ''
    integrated_nic_pattern = [integrated_pattern for integrated_pattern in integrated_nic_patterns if integrated_pattern in device]
    nic_slot_pattern = [nic_slot for nic_slot in nic_slot_patterns if nic_slot in device]

    if integrated_nic_pattern and integrated_nic_pattern[0] in device:
        enumeration_postfix = device.split(integrated_nic_pattern[0])[1].split('-')[0]
        if 'XR11' in server_model or 'XR12' in server_model:
            enumeration = 'eno' + str(int(8203 + (int(enumeration_postfix) * 100))) + 'np' + str(int(enumeration_postfix) - 1)
            return enumeration

        elif '650' in server_model:
            enumeration = 'eno' + str(int(8203 + (int(enumeration_postfix) * 100)))
            return enumeration

        if os == 'rhcos':
            enumeration = 'eno' + enumeration_postfix
        if os == 'rhel':
            enumeration = 'em' + enumeration_postfix

    if nic_slot_pattern and nic_slot_pattern[0] in device:
        slot_number = device.split(nic_slot_pattern[0])[1].split('-')[0]
        port_number = device.split(nic_slot_pattern[0])[1].split('-')[1]
        if os == 'rhcos':
            enumeration = 'ens' + slot_number + 'f' + str(int(port_number)-1)
        if os == 'rhel':
            enumeration = 'p' + slot_number + 'p' + port_number

    return enumeration

        

def main():
    pass

if __name__ == "__main__":
    main()
