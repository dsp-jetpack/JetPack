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

class Node_Conf():
    '''
    holds the network etc. related settings for the nodes (content of cluster.properties)
    '''


    def __init__(self , json):
        self.is_sah = None
        self.is_foreman  = None
        self.is_ceph = None
        self.hostname = None
        self.idrac_ip = None
        self.root_password = None
        self.public_ip = None
        self.public_gateway = None
        self.public_bond = None
        self.public_netmask = None
        self.public_slaves = None
        self.provisioning_ip    = None
        self.provisioning_ip    = None
        self.provisioning_gateway    = None
        self.provisioning_bond    = None
        self.provisioning_netmask    = None
        self.provisioning_slaves    = None
        self.name_server    = None

        self.__dict__ = json
        
        
        
