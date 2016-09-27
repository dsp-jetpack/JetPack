#!/usr/bin/python

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

import argparse
import logging


class LoggingHelper():

    @staticmethod
    def add_argument(parser, default="INFO"):
        parser.add_argument("-l",
                            "--logging-level",
                            default=default,
                            type=LoggingHelper.logging_level,
                            help="""logging level defined by the logging
                                    module; choices include CRITICAL, ERROR,
                                    WARNING, INFO, and DEBUG""",
                            metavar="LEVEL")

    @staticmethod
    def logging_level(string):
        string_level = string

        try:
            # Convert to upper case to allow the user to specify
            # --logging-level=DEBUG or --logging-level=debug.
            numeric_level = getattr(logging, string_level.upper())
        except AttributeError:
            raise argparse.ArgumentTypeError(
                "Unknown logging level: {}".format(string_level))

        if not isinstance(numeric_level, (int, long)) or \
                int(numeric_level) < 0:
            raise argparse.ArgumentTypeError(
                "Logging level not a nonnegative integer: {!r}".format(
                    numeric_level))

        return numeric_level
