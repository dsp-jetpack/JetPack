#!/usr/bin/env python

# OpenStack - A set of software tools for building and managing cloud
# computing platforms for public and private clouds.
# Copyright (C) 2015 Dell, Inc.
#
# This file is part of OpenStack.
#
# OpenStack is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenStack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.


import abc
import six
import sys

from tempest.openstack.common import log as logging

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class DbBase(object):

    def __init__(self, config, service):
        self.sqls = []
        self.ids = []
        self.host = config.get(service, 'host')
        self.user = config.get(service, 'user')
        self.passwd = config.get(service, 'passwd')
        self.db_name = config.get(service, 'db')
        self.db = self.get_connection()

    @abc.abstractmethod
    def __get_connection__(self):
        while False:
            yield None

    def get_connection(self):
        """Get database connection."""
        try:
            conn = self.__get_connection__()
            return conn
        except Exception as ex:
            LOG.error("Failed getting database connection, exception: %s" % ex)
            sys.exit(ex)

    def execute(self):
        """Run sqls based on array of ids."""
        try:
            if self.ids == []:
                raise Exception("Cleaner has no records to delete.")
            for sql in self.sqls:
                self.execute_sql(sql)
        except Exception as ex:
            LOG.error("execution failed, exception: %s" % ex)
            pass

    def execute_sql(self, sql):
        """Run single sql statement."""
        LOG.debug("Executing sql: %s" % sql)
        try:
            cursor = self.db.cursor()
            cursor.execute(sql, self.ids)
            self.db.commit()
            cursor.close()
        except Exception as ex:
            LOG.error("sql: %s failed, exception: %s" % (sql, ex))
            self.db.rollback()
            pass

    def build_sql(self, sql):
        """Build sql string based on query and id."""
        ids = self.ids
        if ids is not None and ids != []:
            in_p = ', '.join(list(map(lambda x: '%s', ids)))
            sql = sql % in_p
        return sql