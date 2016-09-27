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
