#!/usr/bin/python

# Copyright (c) 2017 Dell Inc. or its subsidiaries.
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

from constants import Constants


class ArgHelper:
    @staticmethod
    def add_ip_service_tag(parser):
        parser.add_argument("ip_service_tag",
                            help="""IP address of the iDRAC
                                    or service tag of the node""",
                            metavar="ADDRESS")

    @staticmethod
    def add_model_properties_arg(parser):
        parser.add_argument("-m",
                            "--model-properties",
                            default=Constants.MODEL_PROPERTIES_FILENAME,
                            help="""file that defines Dell system model
                                    properties, including FQDD of network
                                    interface to PXE boot from""",
                            metavar="FILENAME")

    @staticmethod
    def add_instack_arg(parser):
        parser.add_argument("-n",
                            "--node-definition",
                            default=Constants.INSTACKENV_FILENAME,
                            help="""node definition template file that defines the
                                    nodes being configured""",
                            metavar="FILENAME")
