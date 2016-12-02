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
"""
CLC Driver
"""

from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeImage, NodeLocation
from libcloud.compute.base import Node

from libcloud.common.clc import CLCBaseDriver

__all__ = [
    'CLCNodeDriver',
]

class CLCException(Exception): pass


class CLCNodeDriver(CLCBaseDriver):
    """
    CLC NodeDriver for API version 2.

    :keyword    key: Required for authentication. Login username
    :type       key: ``str``

    :keyword    password: Login password
    :type       password: ``str``

    :keyword    api_version: Specifies the API version to use. ``v1`` and
                             ``v2`` are the only valid options. Defaults to
                             using ``v2`` (optional)
    :type       api_version: ``str``

    """
    type = Provider.CLC

    POWER_STATES = {
        'queued': NodeState.PENDING,     # Brand New
        'started': NodeState.RUNNING,     # Running
        'powerOff': NodeState.TERMINATED,  # Powered Off
        'reboot': NodeState.REBOOTING,   # Shutting Down
    }

    COUNTRY_MAP = {
        'AU1': "Australia",
        'CA1': "Canada", 'CA2': "Canada", 'CA3': "Canada",
        'DE1': "Germany",
        'GB1': "England",
        'GB3': "England",
        'SG1': "Singapore",
        'IL1': "US", 'NY1': "US", 'UC1': "US",
        'UT1': "US", 'VA1': "US", 'WA1': "US",
    }

    def get_node(self, id):
        """
        @inherits: :class:`NodeDriver.get_node`
        :rtype: :class:`Node`
        """
        path = '/v2/servers/%s/%s' % (self.alias, id)
        resp = self.connection.request(path)
        return self._to_node(resp.object)

    def list_locations(self):
        path = '/v2/datacenters/%s' % (self.alias)
        resp = self.connection.request(path)
        return map(self._to_location, resp.object)

    def get_location(self, dc, groups=False):
        dc = self._get_dc(dc)
        return self._to_location(dc)

    def list_images(self, dc):
        # images == templates
        obj = self.ex_deployment_capabilities(dc)
        return map(self._to_image, obj['templates'])

    def list_nodes(self, gid):
        path = '/v2/groups/%s/%s' % (self.alias, gid)
        resp = self.connection.request(path)
        nodes = []
        def visit_group(g):
            for l in g['links']:
                rel = l['rel']
                if rel == 'server':
                    nodes.append(l['id'])
            for sg in g['groups']:
                visit_group(sg)
        visit_group(resp.object)
        return nodes

    def ex_list_groups(self, dc):
        dc = self._get_dc(dc, group=True)
        groups = []
        for l in dc['links']:
            if l['rel'] == 'group':
                groups.append(dict(id=l['id'], name=l['name']))
        return groups

    def ex_deployment_capabilities(self, dc):
        path = '/v2/datacenters/%s/%s/deploymentCapabilities' % \
               (self.alias, dc)
        resp = self.connection.request(path)
        return resp.object

    def ex_get_credentials(self, id):
        path = '/v2/servers/%s/%s/credentials' % (self.alias, id)
        resp = self.connection.request(path)
        return resp.object

    def _get_dc(self, dc, group=False):
        path = '/v2/datacenters/%s/%s' % (self.alias, dc)
        if group:
            path += '?groupLinks=true'
        resp = self.connection.request(path)
        return resp.object

    def _to_node(self, data):
        id = data['id']
        details = data['details']
        priv, pub = [], []
        for d in details['ipAddresses']:
            ip = d.get('internal')
            if ip: priv.append(ip)
            ip = d.get('public')
            if ip: pub.append(ip)
        extra = dict(
            vcpus=details['cpu'],
            memory=(details['memoryMB'] / 1024),
            disk=details['storageGB'],
            region=data['locationId'],
            created_at=data['changeInfo']['createdDate'],
            snapshot_ids=details['snapshots'],
            # vendor-specific
            description=data['description'],
            type=data['type'],
            group=data['groupId'],
            #raw=data,
        )
        return Node(
            id=id,
            name=data["name"],
            image=data['os'],
            public_ips=pub,
            private_ips=priv,
            state=self.POWER_STATES[details['powerState']],
            extra=extra,
            driver=self.connection.driver,
            )

    def _to_location(self, data, **kw):
        dc = data['id'].upper()
        co = self.COUNTRY_MAP[dc]
        return NodeLocation(id=dc, name=dc, country=co, driver=self)

    def _to_image(self, data):
        extra = dict(
            storage=data['storageSizeGB'],
            capabilities=data['capabilities'],
        )
        return NodeImage(id=data['name'], name=data['description'], driver=self,
                         extra=extra)
