#!/usr/bin/python3

# Copyright (c) 2016-2021 Dell Inc. or its subsidiaries.
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

import logging


class LoggingHelper:

    @staticmethod
    def add_argument(parser, default="INFO"):
        parser.add_argument("-l",
                            "--logging-level",
                            default=default,
                            choices=["CRITICAL", "ERROR", "WARNING",
                                     "INFO", "DEBUG"],
                            help="""logging level defined by the logging
                                    module; choices include CRITICAL, ERROR,
                                    WARNING, INFO, and DEBUG""",
                            metavar="LEVEL")

    @staticmethod
    def configure_logging(logging_level,
                          noisy_logger="requests.packages.urllib3"):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging_level)
        logger = logging.getLogger(noisy_logger)
        logger.setLevel(logging.WARN)
