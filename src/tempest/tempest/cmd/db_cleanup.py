#!/usr/bin/env python

# Copyright (c) 2016 Dell Inc. or its subsidiaries.
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

""" Database cleanup
@author: David Paterson


Running:
python db_cleanup.py [--init-db-conf] [--clean-db]

The first time you run db_cleanup you need to specify use the
--init-db-conf flag and edit db_cleanup.conf to suit your environment.

--clean-db will execute all sql contained in the cleaner subclasses.

Tip: ./cleanup_plugins/db/mysql/__init__.py can be modified to
explicitly specify what cleaners are executed. By default only
reset_quotas.py is in the list of subclasses that will execute.
"""
import argparse
import ConfigParser
import sys


from tempest.cmd.db import db_base
from tempest.cmd.db.mysql.mysql_db import MySqlDb
from tempest.cmd.db.mysql import *
from tempest import config
from tempest.openstack.common import log as logging

LOG = logging.getLogger(__name__)
CONF = config.CONF
CLEANUP_DB_CONF = "db_cleanup.conf"


class DbCleanup(object):

    def __init__(self):
        # Arbitrary getattr() call required to init config for logging.
        CONF.debug.enable
        self._init_options()
        self.config = ConfigParser.ConfigParser()
        self.config.read(CLEANUP_DB_CONF)

    def run(self):
        opts = self.options
        if opts.init_db_conf:
            self._init_db_conf()
        elif opts.clean_db:
            self._cleanup()
        else:
            LOG.info("No command provided please run with --help "
                     "flag for options")

    def _init_db_conf(self):
        """Create default db config file."""
        LOG.debug("Initialize database configuration")
        config = ConfigParser.RawConfigParser()

        secs = ['cinder', 'keystone', 'heat', 'nova', 'swift']
        for sec in secs:
            config.add_section(sec)
            config.set(sec, 'host', 'localhost')
            config.set(sec, 'db', sec)
            config.set(sec, 'user', sec)
            config.set(sec, 'passwd', 'foreman')

        with open(CLEANUP_DB_CONF, 'wb') as config_file:
            config.write(config_file)

    def _cleanup(self):
        try:
            if len(self.config.sections()) == 0:
                raise Exception("Empty database configuration file, "
                                "needs to be initialized. Please run again "
                                "using --init-db-conf and edit db_cleanup.conf"
                                "file to suit your environment")

            dbc = db_base.DbBase
            LOG.debug("DbBase subclasses : %s" % dbc.__subclasses__())
            for sub in dbc.__subclasses__():
                LOG.debug("Database type subclasses : %s"
                          % sub.__subclasses__())
                for cls in sub.__subclasses__():
                    LOG.debug("Cleaner class: %s " % cls)
                    cleaner = cls(self.config)
                    LOG.debug("Cleaner: %s " % cleaner)
                    cleaner.execute()
                    LOG.debug("Database cleaner: %s, executed!" % cls)

        except Exception as ex:
            LOG.error("Cleaner failed do to exception: %s" % ex)
            pass

    def _init_options(self):
        parser = argparse.ArgumentParser(
            description='Cleanup database after tempest run')
        parser.add_argument('--init-db-conf', action="store_true",
                            dest='init_db_conf', default=False,
                            help="Create default db_cleanup.conf, required " +
                            "for running with --clean-db switch")
        parser.add_argument('--clean-db', action="store_true", dest='clean_db',
                            default=False, help="Delete database " +
                            "records defined in ./db/*.py modules")
        self.options = parser.parse_args()


def main():
    db_cleanup = DbCleanup()
    db_cleanup.run()
    LOG.debug('Database Cleanup finished!')
    return 0

if __name__ == "__main__":
    sys.exit(main())
