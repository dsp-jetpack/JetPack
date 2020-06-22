#!/usr/bin/python3

# Copyright (c) 2018-2020 Dell Inc. or its subsidiaries.
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

# IMPORTS
from collections import defaultdict
import sys


def read_input_file(input_file):
    idata = {}
    with open(input_file, 'r') as f:
        next(f)  # skip first line
        for line in f:
            line = line.strip()
            if len(line) > 2:
                fields = line.split("|")
                if len(fields) == 2:
                    idata[fields[0]] = fields[1]
    return idata


def generate_output_file(idata, input_ini_file, output_ini_file):
    with open(input_ini_file, 'r') as f, open(output_ini_file, 'w') as fnew:
        for line in f:
            data = line.strip()
            if data.startswith("#") or data == "":
                fnew.write(line)
            else:
                if "=" in data:
                    okey, oval = data.split('=', 1)
                    if okey in idata:
                        oval = idata[okey]
                    fnew.write(okey + "=" + oval + "\n")
                else:
                    fnew.write(data + "\n")


def main():
    num_args = len(sys.argv) - 1
    if num_args < 3:
        print("error: missing required arguments")
        print("usage: python %s <kvp_input_file> \
              <input_ini_file> <output_ini_file>" % sys.argv[0])
        sys.exit(1)

    kvp_input_file = sys.argv[1]
    input_ini_file = sys.argv[2]
    output_ini_file = sys.argv[3]

    if kvp_input_file == input_ini_file or \
       kvp_input_file == output_ini_file or \
       input_ini_file == output_ini_file:
        print("error: all file arguments must be unique")
        sys.exit(1)

    in_data = read_input_file(kvp_input_file)
    if len(in_data) > 0:
        generate_output_file(in_data, input_ini_file, output_ini_file)
    else:
        print("no input data. not populating output ini file")
        sys.exit(1)


if __name__ == '__main__':
    main()
