#!/usr/bin/python

# (c) 2016 Dell
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

import os
import re
import subprocess


class MiscHelper:
    @staticmethod
    def get_overcloudrc_name():
        home_dir = os.path.expanduser('~')
        overcloudrc_name = "{}rc".format(MiscHelper.get_stack_name())

        return os.path.join(home_dir, overcloudrc_name)

    @staticmethod
    def get_stack_name():
        stack_name = None
        pattern = \
            re.compile('^\|\s+\S+\s+\|\s+(\S+)\s+\|\s+CREATE_\S+\s+\|.+$')
        stack_list = subprocess.check_output("heat stack-list".split())
        for line in stack_list.split("\n"):
            # Assume it's the first stack listed (there should be only 1)
            match = pattern.match(line)
            if match:
                stack_name = match.group(1)
                break

        return stack_name
