# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
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

from libcloud.compute.providers import Provider
from libcloud.compute.base import Node
from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver

class CloudComNodeDriver(CloudStackNodeDriver):
    "Driver for Ninefold's Compute platform."

    host = '72.52.126.24'
    path = '/client/api'

    type = Provider.CLOUDCOM
    name = 'CloudCom'
    
    def __init__(self, key, secret=None, secure=False, host=None, port=None):
        host = host or self.host
        super(CloudComNodeDriver, self).__init__(key, secret, secure, host, port)


    def create_node(self, name, size, image, location=None, **kwargs):
        if location is None:
            location = self.list_locations()[0]
        network_id = kwargs.pop('network_id', None)
        if network_id is None:
            networks = self._sync_request('listNetworks')
            network_id = networks['network'][0]['id']
        result = self._async_request('deployVirtualMachine',
                                     name=name,
                                     displayname=name,
                                     serviceOfferingId=size.id,
                                     templateId=image.id,
                                     zoneId=location.id,
                                     networkIds=network_id,
                                    )

        node = result['virtualmachine']

        return Node(
            id=node['id'],
            name=node['displayname'],
            state=self.NODE_STATE_MAP[node['state']],
            public_ip=[],
            private_ip=[x['ipaddress'] for x in node['nic']],
            driver=self,
            extra={
                   'zoneid': location.id,
                   'ip_addresses': [],
                   'forwarding_rules': [],
                   'password': node['password'],
                   }
                )
