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
