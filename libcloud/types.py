# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
class Provider(object):
    """ Defines for each of the supported providers """
    DUMMY = 0 # Example provider
    EC2 = 1 # Amazon AWS
    EC2_EU = 2 # Amazon AWS EU
    RACKSPACE = 3 # Cloud Servers
    SLICEHOST = 4 # Cloud Servers
    GOGRID = 5 # GoGrid 
    VPSNET = 6 # VPS.net
    LINODE = 7 # Linode.com
    VCLOUD = 8 # vCloud
    RIMUHOSTING = 9 #RimuHosting.com

class NodeState(object):
    """ Standard states for a node """
    RUNNING = 0
    REBOOTING = 1
    TERMINATED = 2
    PENDING = 3
    UNKNOWN = 4

class InvalidCredsException(Exception):
    def __init__(self, value='Invalid credentials with the provider'):
        self.value = value
    def __str__(self):
        return repr(self.value)
