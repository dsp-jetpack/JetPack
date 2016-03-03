#!/usr/bin/env python

from datetime import datetime
import logging
from pprint import pprint
import sys, os
import yaml
import ConfigParser
from dciclient.v1.logger import DciHandler
import osp_deployer.deployer
from dciclient.v1.api import file as dcifile
from dciclient.v1.api import context as dcicontext
from dciclient.v1.api import job as dcijob
from dciclient.v1.api import jobstate as dcijobstate
from dciclient.v1.api import topic as dcitopic
from dciclient.v1 import helper as dcihelper

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

def upload_configuration_files(dci_context, jetstream_ini_file):
     jetstream_settings = ConfigParser.RawConfigParser()
     jetstream_settings.read(jetstream_ini_file)
     #properties_file = jetstream_settings.get('Cluster Settings', 'cluster_nodes_configuration_file')
 
     dcihelper.upload_file(dci_context, jetstream_ini_file, dci_context.last_job_id)
     #dcihelper.upload_file(dci_context, properties_file, dci_context.last_job_id)

parser_dci = argparse.ArgumentParser(description='dci only, nothing to see here')
parser_dci.add_argument('-dci','--dci_conf', help='dci configuration yaml file', required=True)
parser_dci.add_argument('-s','--settings', help='ini settings file, e.g settings/acme.ini', required=True)
parser_dci.add_argument('-skip_sah','--skip_sah', help='Do not reinstall the SAH node',action='store_true', required=False)
parser_dci.add_argument('-skip_undercloud','--skip_undercloud', help='Do not reinstall the SAH or Undercloud',action='store_true', required=False)
parser_dci.add_argument('-skip_ceph_vm','--skip_ceph_vm', help='Do not reinstall the ceph vm',action='store_true', required=False)
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
topic = dcitopic.get(dci_context, dci_conf.get('topic', 'default')).json()['topic']
job = dcijob.schedule(dci_context, remoteci_id=dci_conf['remoteci_id'], topic_id=topic['id']).json()
print(job)
job_full_data = dcijob.get_full_data(dci_context, dci_context.last_job_id)
upload_configuration_files(dci_context, nspace.settings)

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
dcijobstate.create(dci_context, 'running', 'running', dci_context.last_job_id)

try:
   osp_deployer.deployer.deploy()
   dcijobstate.create(dci_context, 'post-run','todo :: tempest etc.', dci_context.last_job_id)
   dcijobstate.create(dci_context, 'success', 'All done', dci_context.last_job_id)
except:
   print " somebody set us up the bomb "
   dcijobstate.create(dci_context, 'failure', 'failure', dci_context.last_job_id)







