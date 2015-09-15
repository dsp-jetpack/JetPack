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


class DeleteVolume(MySqlDb):

    def __init__(self, config):
        super(DeleteVolume, self).__init__(config, "cinder")

        self.get_volume_ids()
        sqls = self.sqls

        # backups
        sql = self.build_sql('delete from ' +
                             'backups where ' +
                             'volume_id in (%s)')
        sqls.append(sql)

        # iscsi_targets
        sql = self.build_sql('delete from ' +
                             'iscsi_targets where ' +
                             'volume_id in (%s)')
        sqls.append(sql)

        # snapshots
        sql = self.build_sql('delete from ' +
                             'snapshots where ' +
                             'volume_id in (%s)')
        sqls.append(sql)

        # transfers
        sql = self.build_sql('delete from ' +
                             'transfers where ' +
                             'volume_id in (%s)')
        sqls.append(sql)

        # volume_admin_metadata
        sql = self.build_sql('delete from ' +
                             'volume_admin_metadata where ' +
                             'volume_id in (%s)')
        sqls.append(sql)

        # volume_glance_metadata
        sql = self.build_sql('delete from ' +
                             'volume_glance_metadata where ' +
                             'volume_id in (%s)')
        sqls.append(sql)

        # volume_metadata
        sql = self.build_sql('delete from ' +
                             'volume_metadata where ' +
                             'volume_id in (%s)')
        sqls.append(sql)

        # volumes
        sql = self.build_sql('delete from ' +
                             'volumes where id in (%s)')
        sqls.append(sql)

    def get_volume_ids(self):
        ids = []
        cur = self.db.cursor()
        cur.execute('select id from ' +
                    'volumes where ' +
                    'status != "deleted";')
        res = cur.fetchall()
        for rec in res:
            ids.append(rec[0])
        self.ids = ids