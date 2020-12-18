#!/usr/bin/python3

# Copyright (c) 2017-2021 Dell Inc. or its subsidiaries.
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


class Constants:
    HOME = os.path.expanduser('~')
    MODEL_PROPERTIES_FILENAME = os.path.join(HOME,
                                             "pilot",
                                             "dell_systems.json")
    INSTACKENV_FILENAME = os.path.join(HOME,
                                       'instackenv.json')
    TEMPLATES = os.path.join(HOME, "pilot", "templates")
    UNDERCLOUD_CONF = (os.path.join(os.path.expanduser('~'),
                                    'undercloud.conf'))
