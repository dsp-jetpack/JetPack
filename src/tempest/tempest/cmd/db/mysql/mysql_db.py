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


from tempest.cmd.db import db_base
# from tempest.openstack.common import log as logging

import MySQLdb


class MySqlDb(db_base.DbBase):
    '''
    classdocs
    '''
    def __get_connection__(self):
        return MySQLdb.connect(self.host, self.user,
                               self.passwd, self.db_name)