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
