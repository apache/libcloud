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
Softlayer driver
"""

import sys
import time

import libcloud

from libcloud.utils.py3 import xmlrpclib

from libcloud.common.base import ConnectionUserAndKey
from libcloud.common.xmlrpc import XMLRPCResponse, XMLRPCConnection
from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, Node, NodeLocation, NodeSize, \
    NodeImage

DATACENTERS = {
    'hou02': {'country': 'US'},
    'sea01': {'country': 'US'},
    'wdc01': {'country': 'US'},
    'dal01': {'country': 'US'},
    'dal02': {'country': 'US'},
    'dal04': {'country': 'US'},
    'dal05': {'country': 'US'},
    'dal06': {'country': 'US'},
    'dal07': {'country': 'US'},
    'sjc01': {'country': 'US'},
    'sng01': {'country': 'SG'},
    'ams01': {'country': 'NL'},
}

NODE_STATE_MAP = {
    'RUNNING': NodeState.RUNNING,
    'HALTED': NodeState.TERMINATED,
    'PAUSED': NodeState.TERMINATED,
}

SL_BASE_TEMPLATES = [
    {
        'name': '1 CPU, 1GB ram, 25GB',
        'ram': 1024,
        'disk': 25,
        'cpus': 1,
    }, {
        'name': '1 CPU, 1GB ram, 100GB',
        'ram': 1024,
        'disk': 100,
        'cpus': 1,
    }, {
        'name': '2 CPU, 2GB ram, 100GB',
        'ram': 4 * 1024,
        'disk': 100,
        'cpus': 2,
    }, {
        'name': '4 CPU, 4GB ram, 100GB',
        'ram': 4 * 1024,
        'disk': 100,
        'cpus': 4,
    }, {
        'name': '8 CPU, 8GB ram, 100GB',
        'ram': 8 * 1024,
        'disk': 100,
        'cpus': 8,
    }]

SL_TEMPLATES = {}
for i, template in enumerate(SL_BASE_TEMPLATES):
    # Add local disk templates
    local = template.copy()
    local['local_disk'] = True
    SL_TEMPLATES['sl%s_local_disk' % (i + 1,)] = local

    # Add san disk templates
    san = template.copy()
    san['local_disk'] = False
    SL_TEMPLATES['sl%s_san_disk' % (i + 1,)] = san


class SoftLayerException(LibcloudError):
    """
    Exception class for SoftLayer driver
    """
    pass


class SoftLayerResponse(XMLRPCResponse):
    defaultExceptionCls = SoftLayerException
    exceptions = {
        'SoftLayer_Account': InvalidCredsError,
    }


class SoftLayerConnection(XMLRPCConnection, ConnectionUserAndKey):
    responseCls = SoftLayerResponse
    host = 'api.softlayer.com'
    endpoint = '/xmlrpc/v3'

    def request(self, service, method, *args, **kwargs):
        headers = {}
        headers.update(self._get_auth_headers())
        headers.update(self._get_init_params(service, kwargs.get('id')))
        headers.update(
            self._get_object_mask(service, kwargs.get('object_mask')))
        headers.update(
            self._get_object_mask(service, kwargs.get('object_mask')))

        args = ({'headers': headers}, ) + args
        endpoint = '%s/%s' % (self.endpoint, service)

        return super(SoftLayerConnection, self).request(method, *args,
                                                        **{'endpoint':
                                                            endpoint})

    def _get_auth_headers(self):
        return {
            'authenticate': {
                'username': self.user_id,
                'apiKey': self.key
            }
        }

    def _get_init_params(self, service, id):
        if id is not None:
            return {
                '%sInitParameters' % service: {'id': id}
            }
        else:
            return {}

    def _get_object_mask(self, service, mask):
        if mask is not None:
            return {
                '%sObjectMask' % service: {'mask': mask}
            }
        else:
            return {}


class SoftLayerNodeDriver(NodeDriver):
    """
    SoftLayer node driver

    Extra node attributes:
        - password: root password
        - hourlyRecurringFee: hourly price (if applicable)
        - recurringFee      : flat rate    (if applicable)
        - recurringMonths   : The number of months in which the recurringFee
         will be incurred.
    """
    connectionCls = SoftLayerConnection
    name = 'SoftLayer'
    website = 'http://www.softlayer.com/'
    type = Provider.SOFTLAYER

    features = {'create_node': ['generates_password']}

    def _to_node(self, host):
        try:
            password = \
                host['operatingSystem']['passwords'][0]['password']
        except (IndexError, KeyError):
            password = None

        hourlyRecurringFee = host.get('billingItem', {}).get(
            'hourlyRecurringFee', 0)
        recurringFee = host.get('billingItem', {}).get('recurringFee', 0)
        recurringMonths = host.get('billingItem', {}).get('recurringMonths', 0)
        createDate = host.get('createDate', None)

        return Node(
            id=host['id'],
            name=host['hostname'],
            state=NODE_STATE_MAP.get(
                host['powerState']['keyName'], NodeState.UNKNOWN
            ),
            public_ips=[host['primaryIpAddress']],
            private_ips=[host['primaryBackendIpAddress']],
            driver=self,
            extra={
                'password': password,
                'hourlyRecurringFee': hourlyRecurringFee,
                'recurringFee': recurringFee,
                'recurringMonths': recurringMonths,
                'created': createDate,
            }
        )

    def destroy_node(self, node):
        self.connection.request(
            'SoftLayer_Virtual_Guest', 'deleteObject', id=node.id
        )
        return True

    def reboot_node(self, node):
        self.connection.request(
            'SoftLayer_Virtual_Guest', 'rebootSoft', id=node.id
        )
        return True

    def _get_order_information(self, node_id, timeout=1200, check_interval=5):
        mask = {
            'billingItem': '',
            'powerState': '',
            'operatingSystem': {'passwords': ''},
            'provisionDate': '',
        }

        for i in range(0, timeout, check_interval):
            res = self.connection.request(
                'SoftLayer_Virtual_Guest',
                'getObject',
                id=node_id,
                object_mask=mask
            ).object

            if res.get('provisionDate', None):
                return res

            time.sleep(check_interval)

        raise SoftLayerException('Timeout on getting node details')

    def create_node(self, **kwargs):
        """Create a new SoftLayer node

        @inherits: L{NodeDriver.create_node}

        @keyword    ex_domain: e.g. libcloud.org
        @type       ex_domain: C{str}
        @keyword    ex_cpus: e.g. 2
        @type       ex_cpus: C{int}
        @keyword    ex_disk: e.g. 100
        @type       ex_disk: C{int}
        @keyword    ex_ram: e.g. 2048
        @type       ex_ram: C{int}
        @keyword    ex_bandwidth: e.g. 100
        @type       ex_bandwidth: C{int}
        @keyword    ex_local_disk: e.g. True
        @type       ex_local_disk: C{bool}
        @keyword    ex_datacenter: e.g. Dal05
        @type       ex_datacenter: C{str}
        @keyword    ex_os: e.g. UBUNTU_LATEST
        @type       ex_os: C{str}
        """
        name = kwargs['name']
        os = 'DEBIAN_LATEST'
        if 'ex_os' in kwargs:
            os = kwargs['ex_os']
        elif 'image' in kwargs:
            os = kwargs['image'].id

        size = kwargs.get('size', NodeSize(id=None, name='Custom', ram=None,
                                           disk=None, bandwidth=None,
                                           price=None,
                                           driver=self.connection.driver))

        ex_size_data = SL_TEMPLATES.get(size.id) or {}
        cpu_count = kwargs.get('ex_cpus') or ex_size_data.get('cpus') or 1
        ram = kwargs.get('ex_ram') or size.ram or 2048
        bandwidth = kwargs.get('ex_bandwidth') or size.bandwidth or 10
        hourly = 'true' if kwargs.get('ex_hourly', True) else 'false'

        local_disk = 'true'
        if ex_size_data.get('local_disk') is False:
            local_disk = 'false'

        if kwargs.get('ex_local_disk') is False:
            local_disk = 'false'

        disk_size = 100
        if size.disk:
            disk_size = size.disk
        if kwargs.get('ex_disk'):
            disk_size = kwargs.get('ex_disk')

        datacenter = ''
        if 'ex_datacenter' in kwargs:
            datacenter = kwargs['ex_datacenter']
        elif 'location' in kwargs:
            datacenter = kwargs['location'].id

        domain = kwargs.get('ex_domain')
        if domain is None:
            if name.find('.') != -1:
                domain = name[name.find('.') + 1:]
        if domain is None:
            # TODO: domain is a required argument for the Sofylayer API, but it
            # it shouldn't be.
            domain = 'example.com'

        newCCI = {
            'hostname': name,
            'domain': domain,
            'startCpus': cpu_count,
            'maxMemory': ram,
            'networkComponents': [{'maxSpeed': bandwidth}],
            'hourlyBillingFlag': hourly,
            'operatingSystemReferenceCode': os,
            'localDiskFlag': local_disk,
            'blockDevices': [
                {
                    'device': '0',
                    'diskImage': {
                        'capacity': disk_size,
                    }
                }
            ]

        }

        if datacenter:
            newCCI['datacenter'] = {'name': datacenter}

        res = self.connection.request(
            'SoftLayer_Virtual_Guest', 'createObject', newCCI
        ).object

        node_id = res['id']
        raw_node = self._get_order_information(node_id)

        return self._to_node(raw_node)

    def _to_image(self, img):
        return NodeImage(
            id=img['template']['operatingSystemReferenceCode'],
            name=img['itemPrice']['item']['description'],
            driver=self.connection.driver
        )

    def list_images(self, location=None):
        result = self.connection.request(
            'SoftLayer_Virtual_Guest', 'getCreateObjectOptions'
        ).object
        return [self._to_image(i) for i in result['operatingSystems']]

    def _to_size(self, id, size):
        return NodeSize(
            id=id,
            name=size['name'],
            ram=size['ram'],
            disk=size['disk'],
            bandwidth=size.get('bandwidth'),
            price=None,
            driver=self.connection.driver,
        )

    def list_sizes(self, location=None):
        return [self._to_size(id, s) for id, s in SL_TEMPLATES.items()]

    def _to_loc(self, loc):
        country = 'UNKNOWN'
        if loc['name'] in DATACENTERS:
            country = DATACENTERS[loc['name']]['country']
        return NodeLocation(id=loc['name'], name=loc['longName'],
                            country=country, driver=self)

    def list_locations(self):
        res = self.connection.request(
            'SoftLayer_Location_Datacenter', 'getDatacenters'
        ).object
        return [self._to_loc(l) for l in res]

    def list_nodes(self):
        mask = {
            'virtualGuests': {
                'powerState': '',
                'operatingSystem': {'passwords': ''},
                'billingItem': '',
            },
        }
        res = self.connection.request(
            "SoftLayer_Account",
            "getVirtualGuests",
            object_mask=mask
        ).object
        return [self._to_node(h) for h in res]
