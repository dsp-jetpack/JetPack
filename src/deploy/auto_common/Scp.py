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

try:
    import paramiko
except ImportError:
    pass


# noinspection PyClassHasNoInit
class Scp():

    @staticmethod
    def get_file(adress, user, passw, localfile, remotefile):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        trans = paramiko.Transport((adress, 22))
        trans.connect(username=user, password=passw)
        sftp = paramiko.SFTPClient.from_transport(trans)
        sftp.get(remotefile, localfile)
        sftp.close()
        trans.close()

    @staticmethod
    def put_file(adress, user, passw, localfile, remotefile):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        trans = paramiko.Transport((adress, 22))
        trans.connect(username=user, password=passw)
        sftp = paramiko.SFTPClient.from_transport(trans)
        sftp.put(localfile, remotefile)
        sftp.close()
        trans.close()
