#!/usr/bin/env python

# Copyright (c) 2015-2016 Dell Inc. or its subsidiaries.
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

import re
import codecs


# noinspection PyClassHasNoInit
class FileHelper():
    @staticmethod
    def replace_expression(fileref, search_exp, replace_exp):
        fh = open(fileref, 'rU')
        content = fh.readlines()
        fh.close()
        updated = []
        for line in content:
            line = re.sub(search_exp, replace_exp, line)
            updated.append(line)

        with codecs.open(fileref, 'wbU', encoding='utf8') as f:
            for line in updated:
                f.write(line)
        f.close()

    @staticmethod
    def replace_expression_txt(fileref, search_exp, replace_exp):
        fh = open(fileref, 'r')
        content = fh.readlines()  # Dont try this on large files..
        fh.close()
        updated = []

        for line in content:
            line = re.sub(search_exp, replace_exp, line)
            updated.append(line)

        f_out = file(fileref, 'w')
        f_out.writelines(updated)
        f_out.close()
