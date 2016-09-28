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


class DeleteStack(MySqlDb):

    def __init__(self, config):

        super(DeleteStack, self).__init__(config, "heat")

        self.get_stack_ids()
        sqls = self.sqls

        # delete event
        sql = self.build_sql('delete from ' +
                             'event where ' +
                             'stack_id in (%s)')
        sqls.append(sql)

        # delete stack
        sql = self.build_sql('delete from ' +
                             'stack where ' +
                             'id in (%s)')
        sqls.append(sql)

    def get_stack_ids(self):
        ids = []
        cur = self.db.cursor()
        cur.execute('select id from ' +
                    'stack where ' +
                    'status in ("IN_PROGRESS","FAILED","ERROR_DELETE",' +
                    '"DELETE_IN_PROGRESS");')
        res = cur.fetchall()
        for rec in res:
            ids.append(rec[0])
        self.ids = ids
