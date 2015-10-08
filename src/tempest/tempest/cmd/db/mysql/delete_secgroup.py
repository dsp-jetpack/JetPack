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


from tempest.cmd.db.mysql.mysql_db import MySqlDb


class DeleteSecGroup(MySqlDb):

    def __init__(self, config):
        super(DeleteSecGroup, self).__init__(config, "nova")

        self.get_instance_ids()
        sqls = self.sqls
        # delete security_group_rules
        sql = self.build_sql('delete from ' +
                             'security_group_rules where ' +
                             'parent_group_id in (%s)')
        sqls.append(sql)

        # delete from security_group_instance_association
        sql = self.build_sql('delete from ' +
                             'security_group_instance_association where ' +
                             'parent_group_id in (%s)')
        sqls.append(sql)

        # delete from security_groups
        sql = self.build_sql('delete from ' +
                             'security_groups where ' +
                             'id in (%s)')
        sqls.append(sql)

    def get_instance_ids(self):
        ids = []
        cur = self.db.cursor()
        cur.execute('select id from ' +
                    'security_groups where ' +
                    'name !="default"')

        res = cur.fetchall()
        for rec in res:
            ids.append(rec[0])
        self.ids = ids