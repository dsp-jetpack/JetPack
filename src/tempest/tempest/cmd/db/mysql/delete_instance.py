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