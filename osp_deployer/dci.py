#!/usr/bin/env python

from datetime import datetime
import logging
from pprint import pprint
import sys, os
import yaml

from dciclient.v1.logger import DciHandler
import osp_deployer.deployer

from dciclient.v1.api import context as dcicontext
from dciclient.v1.api import job as dcijob
from dciclient.v1.api import jobstate as dcijobstate

import sys,argparse
reload(sys)
sys.setdefaultencoding("utf-8")

def setup_logging(dci_context):
    if sys.platform.startswith('linux'):
        isLinux = True
    path = '/auto_results'
    if not os.path.exists(path):
        os.makedirs(path)
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    log_file_name = datetime.now().strftime('/auto_results/deployment-%Y.%m.%d-%H.%M.log')
    file_handler = logging.FileHandler(log_file_name, mode='w')
    dci_handler = DciHandler(dci_context, info_as_jobstate=True)

    for logger_name in ('osp_deployer', 'auto_common.ipmi', 'auto_common.ssh'):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)
        logger.addHandler(dci_handler)

parser_dci = argparse.ArgumentParser(description='dci only, nothing to see here')
parser_dci.add_argument('-dci','--dci_conf', help='dci configuration yaml file', required=True)
nspace, others  = parser_dci.parse_known_args()
dci_conf = yaml.load(open(nspace.dci_conf, 'r'))
dci_context = dcicontext.build_dci_context(
    'http://46.231.133.44',
    dci_conf['login'],
    dci_conf['password'])

repo_entry = """
[{name}]
name={name}
baseurl={rhos_mirror}{path}
enable=1
gpgcheck=0
priority=0

"""

pprint(dci_conf)

if not dci_conf['rhos_mirror'].startswith('http'):
    print('RHOS mirror should be an URL')
    exit(1)

job = dcijob.schedule(dci_context, remoteci_id=dci_conf['remoteci_id']).json()
print(job)
job_full_data = dcijob.get_full_data(dci_context, dci_context.last_job_id)
pprint(job_full_data)
if job_full_data['test']['name'] != 'tempest':
    print('invalid test')
    exit(0)

with open('/var/www/html/RH7-RHOS-8.0.repo', 'w') as f:
    for component in job_full_data['components']:
        f.write(repo_entry.format(
            rhos_mirror=dci_conf['rhos_mirror'],
            name=component['data']['repo_name'],
            path=component['data']['path']))

dcijobstate.create(dci_context, 'pre-run', 'initializing', dci_context.last_job_id)
setup_logging(dci_context)
osp_deployer.deployer.deploy()
