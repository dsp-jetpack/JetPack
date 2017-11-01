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

import json
import os
from constants import Constants


class Utils:
    @staticmethod
    def get_model_properties(
            json_filename=Constants.MODEL_PROPERTIES_FILENAME):
        model_properties = None
        expanded_filename = os.path.expanduser(json_filename)

        try:
            with open(expanded_filename, 'r') as f:
                try:
                    model_properties = json.load(f)
                except ValueError as ex:
                    ex.message = "Could not deserialize model properties " \
                        "file {}: {}".format(expanded_filename, ex.message)
                    raise
        except IOError as ex:
            ex.message = "Could not open model properties file {}: {}".format(
                expanded_filename, ex.message)
            raise

        return model_properties
