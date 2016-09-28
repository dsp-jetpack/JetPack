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


class ResetQuotas(MySqlDb):

    def __init__(self, config):
        super(ResetQuotas, self).__init__(config, "nova")
        self.ids = None
        # Reset the quotas to 0, this is nec because there are several
        # openstack bugs where in_use is not updated when an object is
        # deleted through api.
        sql = self.build_sql('update quota_usages ' +
                             'set in_use = 0 where in_use != -1')
        self.sqls.append(sql)
