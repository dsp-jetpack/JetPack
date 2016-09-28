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


class DeleteInstance(MySqlDb):

    def __init__(self, config):
        super(DeleteInstance, self).__init__(config, "nova")

        self.get_instance_ids()
        sqls = self.sqls
        # delete security_group_instance_association
        sql = self.build_sql('delete from ' +
                             'security_group_instance_association ' +
                             'where instance_uuid in (%s)')
        sqls.append(sql)

        # delete from instance_info_caches
        sql = self.build_sql('delete from ' +
                             'instance_info_caches where ' +
                             'instance_uuid in (%s)')
        sqls.append(sql)

        # delete from block_device_mapping
        sql = self.build_sql('delete from ' +
                             'block_device_mapping ' +
                             'where instance_uuid in (%s)')
        sqls.append(sql)

        # delete instance_actions_event
        sql = self.build_sql('delete from ' +
                             'instance_actions_events where ' +
                             'action_id in (select id from instance_actions ' +
                             'where instance_uuid in (%s))')
        sqls.append(sql)

        # delete from instance_actions
        sql = self.build_sql('delete from ' +
                             'instance_actions where ' +
                             'instance_uuid in (%s)')
        sqls.append(sql)

        # delete from instance_faults
        sql = self.build_sql('delete from ' +
                             'instance_faults where ' +
                             'instance_uuid in (%s)')
        sqls.append(sql)

        # delete from instance_metadata
        sql = self.build_sql('delete from ' +
                             'instance_metadata where ' +
                             'instance_uuid in (%s)')
        sqls.append(sql)

        # delete from instance_system_metadata
        sql = self.build_sql('delete from ' +
                             'instance_system_metadata where ' +
                             'instance_uuid in (%s)')
        sqls.append(sql)

        # delete from virtual_interfaces
        sql = self.build_sql('delete from ' +
                             'virtual_interfaces where ' +
                             'instance_uuid in (%s)')
        sqls.append(sql)

        # delete from fixed_ips
        sql = self.build_sql('delete from ' +
                             'fixed_ips where ' +
                             'instance_uuid in (%s)')
        sqls.append(sql)

        # delete from instance_extra, instance_uuid
        sql = self.build_sql('delete from ' +
                             'instance_extra where ' +
                             'instance_uuid in (%s)')
        sqls.append(sql)

        # delete from instances
        sql = self.build_sql('delete from ' +
                             'instances where ' +
                             'uuid in (%s)')
        sqls.append(sql)

    def get_instance_ids(self):
        ids = []
        cur = self.db.cursor()
        cur.execute('select uuid from ' +
                    'instances where ' +
                    'deleted = 0;')
        res = cur.fetchall()
        for rec in res:
            ids.append(rec[0])
        self.ids = ids
