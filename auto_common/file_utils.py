#!/usr/bin/env python

# OpenStack - A set of software tools for building and managing cloud computing
# platforms for public and private clouds.
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
