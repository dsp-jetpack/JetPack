#!/usr/bin/python

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
