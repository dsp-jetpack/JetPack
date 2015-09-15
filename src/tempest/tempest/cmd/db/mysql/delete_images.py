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


class DeleteImages(MySqlDb):

    def __init__(self, config):
        super(DeleteImages, self).__init__(config, "glance")

        self.get_image_ids()
        sqls = self.sqls

        # delete from image_locations
        sql = self.build_sql('delete from ' +
                             'image_locations where ' +
                             'image_id in (%s)')
        sqls.append(sql)

        # delete from image_members
        sql = self.build_sql('delete from ' +
                             'image_members where ' +
                             'image_id in (%s)')
        sqls.append(sql)

        # delete from image_properties
        sql = self.build_sql('delete from ' +
                             'image_properties where ' +
                             'image_id in (%s)')
        sqls.append(sql)

        # delete from image_tags
        sql = self.build_sql('delete from ' +
                             'image_tags where ' +
                             'image_id in (%s)')
        sqls.append(sql)

        # delete from security_groups
        sql = self.build_sql('delete from ' +
                             'images where ' +
                             'id in (%s)')
        sqls.append(sql)

    def get_image_ids(self):
        ids = []
        cur = self.db.cursor()
        cur.execute('select id from ' +
                    'images')

        res = cur.fetchall()
        for rec in res:
            ids.append(rec[0])
        self.ids = ids