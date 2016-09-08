#!/usr/bin/env python

# (c) 2015-2016 Dell
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

from datetime import datetime
import logging
from pprint import pprint
import os
import os.path
import traceback
import yaml
import ConfigParser
import osp_deployer
import osp_deployer.deployer
# noinspection PyUnresolvedReferences
from dciclient.v1.logger import DciHandler
# noinspection PyUnresolvedReferences
from dciclient.v1.api import file as dcifile
# noinspection PyUnresolvedReferences
from dciclient.v1.api import context as dcicontext
# noinspection PyUnresolvedReferences
from dciclient.v1.api import job as dcijob
# noinspection PyUnresolvedReferences
from dciclient.v1.api import jobstate as dcijobstate
# noinspection PyUnresolvedReferences
from dciclient.v1.api import topic as dcitopic
# noinspection PyUnresolvedReferences
from dciclient.v1 import helper as dcihelper
from dciclient.v1 import tripleo_helper as dci_tripleo_helper
import sys
import argparse

reload(sys)
# noinspection PyUnresolvedReferences
sys.setdefaultencoding("utf-8")


def setup_logging(dci_contxt):
    path = '/auto_results'
    if not os.path.exists(path):
        os.makedirs(path)
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    log_file_name = datetime.now().strftime(
        '/auto_results/deployment-%Y.%m.%d-%H.%M.log')
    file_handler = logging.FileHandler(log_file_name, mode='w')
    dci_handler = DciHandler(dci_contxt)

    for logger_name in ('osp_deployer', 'auto_common.ipmi',
                        'auto_common.ssh', 'tripleohelper'):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)
        logger.addHandler(dci_handler)
    return log_file_name


def upload_configuration_files(dci_contxt, jetstream_ini_file):
    r = dcihelper.upload_file(dci_contxt,
                              path=jetstream_ini_file,
                              job_id=dci_context.last_job_id)


def deploy_openstack(log_file_name):
    # noinspection PyBroadException
    try:
        osp_deployer.deployer.deploy()
        osp_deployer.deployer.inject_ssh_key()
    except:
        print " somebody set us up the bomb "
        dcijobstate.create(
            dci_context,
            'failure',
            'failure',
            dci_context.last_job_id)
        e = sys.exc_info()[0]
        error_msg = '%s\n%s' % (e, traceback.format_exc())
        dcifile.create(
            dci_context,
            'failure',
            error_msg,
            mime='text/plain',
            job_id=dci_context.last_job_id)
        print(error_msg)
    finally:
        with open(log_file_name, 'r') as f:
            dcifile.create(
                dci_context,
                'deployment.log',
                f.read(),
                mime='text/plain',
                job_id=dci_context.last_jobstate_id)


parser_dci = argparse.ArgumentParser(
    description='dci only, nothing to see here')
parser_dci.add_argument('-dci', '--dci_conf',
                        help='dci configuration yaml file',
                        required=True)
parser_dci.add_argument('-s', '--settings',
                        help='ini settings file, e.g settings/acme.ini',
                        required=True)
parser_dci.add_argument('-skip_sah', '--skip_sah',
                        help='Do not reinstall the SAH node',
                        action='store_true',
                        required=False)
parser_dci.add_argument('-skip_undercloud', '--skip_undercloud',
                        help='Do not reinstall the SAH or Undercloud',
                        action='store_true',
                        required=False)
parser_dci.add_argument('-skip_ceph_vm', '--skip_ceph_vm',
                        help='Do not reinstall the ceph vm',
                        action='store_true',
                        required=False)
nspace, others = parser_dci.parse_known_args()
dci_conf = yaml.load(open(nspace.dci_conf, 'r'))
dci_context = dcicontext.build_dci_context(
    'https://api.distributed-ci.io/',
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
topic = dcitopic.get(dci_context, dci_conf.get('topic', 'OSP8')).json()[
    'topic']
r = dcijob.schedule(dci_context, remoteci_id=dci_conf['remoteci_id'],
                    topic_id=topic['id'])
if r.status_code == 412:
    exit(0)
components = dcijob.get_components(
    dci_context, dci_context.last_job_id).json()['components']
upload_configuration_files(dci_context, nspace.settings)

with open('/var/www/html/RH7-RHOS-OSP-DCI.repo', 'w') as f:
    for component in components:
        f.write(repo_entry.format(
            rhos_mirror=dci_conf['rhos_mirror'],
            name=component['data']['repo_name'],
            path=component['data']['path']))

dcijobstate.create(dci_context, 'pre-run', 'initializing',
                   dci_context.last_job_id)
log_file_name = setup_logging(dci_context)
dcijobstate.create(dci_context,
                   'running',
                   'Running deployment',
                   dci_context.last_job_id)

deploy_openstack(log_file_name)
settings = osp_deployer.Settings.settings
dci_tripleo_helper.run_tests(
    dci_context,
    undercloud_ip=settings.director_node.external_ip,
    key_filename='/root/.ssh/id_rsa',
    remoteci_id=dci_conf['remoteci_id'])
