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

import time
try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    crypto = True
except ImportError:
    crypto = False

from libcloud.common.softlayer import SoftLayerConnection, SoftLayerException
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, Node, NodeLocation, NodeSize, \
    NodeImage, KeyPair
from libcloud.compute.types import KeyPairDoesNotExistError

DEFAULT_DOMAIN = 'mist.io'
DEFAULT_CPU_SIZE = 1
DEFAULT_RAM_SIZE = 2048
DEFAULT_DISK_SIZE = 100

DATACENTERS = {
    'hou02': {'country': 'US', 'name': 'Houston'},
    'sea01': {'country': 'US', 'name': 'Seattle - West Coast U.S.'},
    'wdc01': {'country': 'US', 'name': 'Washington, DC'},
    'wdc04': {'country': 'US', 'name': 'Washington 4, DC'},

    'dal01': {'country': 'US', 'name': 'Dal01 - Dallas'},
    'dal02': {'country': 'US', 'name': 'Dal02 - Dallas'},
    'dal04': {'country': 'US', 'name': 'Dal04 - Dallas'},
    'dal05': {'country': 'US', 'name': 'Dal05 - Dallas'},
    'dal06': {'country': 'US', 'name': 'Dal06 - Dallas'},
    'dal07': {'country': 'US', 'name': 'Dal07 - Dallas'},
    'dal09': {'country': 'US', 'name': 'Dal09 - Dallas'},
    'sjc01': {'country': 'US', 'name': 'San Jose'},
    'sng01': {'country': 'SG', 'name': 'Singapore'},
    'ams01': {'country': 'NL', 'name': 'AMS01 - Amsterdam'},
    'ams03': {'country': 'NL', 'name': 'AMS03 - Amsterdam'},
    'how02': {'country': 'US', 'name': 'Houston'},
}

NODE_STATE_MAP = {
    'RUNNING': NodeState.RUNNING,
    'ACTIVE': NodeState.RUNNING,
    'HALTED': NodeState.STOPPED,
    'PAUSED': NodeState.UNKNOWN,
    'INITIATING': NodeState.PENDING,
    'DEPLOY': NodeState.PENDING,
    'DEPLOY2': NodeState.PENDING,
    'MACWAIT': NodeState.PENDING,
    'RECLAIM': NodeState.PENDING,
    '5': NodeState.RUNNING,
    '3': NodeState.PENDING
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
        'name': '1 CPU, 2GB ram, 100GB',
        'ram': 2 * 1024,
        'disk': 100,
        'cpus': 1,
    }, {
        'name': '1 CPU, 4GB ram, 100GB',
        'ram': 4 * 1024,
        'disk': 100,
        'cpus': 1,
    }, {
        'name': '2 CPU, 2GB ram, 100GB',
        'ram': 2 * 1024,
        'disk': 100,
        'cpus': 2,
    }, {
        'name': '2 CPU, 4GB ram, 100GB',
        'ram': 4 * 1024,
        'disk': 100,
        'cpus': 2,
    }, {
        'name': '2 CPU, 8GB ram, 100GB',
        'ram': 8 * 1024,
        'disk': 100,
        'cpus': 2,
    }, {
        'name': '4 CPU, 4GB ram, 100GB',
        'ram': 4 * 1024,
        'disk': 100,
        'cpus': 4,
    }, {
        'name': '4 CPU, 8GB ram, 100GB',
        'ram': 8 * 1024,
        'disk': 100,
        'cpus': 4,
    }, {
        'name': '6 CPU, 4GB ram, 100GB',
        'ram': 4 * 1024,
        'disk': 100,
        'cpus': 6,
    }, {
        'name': '6 CPU, 8GB ram, 100GB',
        'ram': 8 * 1024,
        'disk': 100,
        'cpus': 6,
    }, {

        'name': '8 CPU, 8GB ram, 100GB',
        'ram': 8 * 1024,
        'disk': 100,
        'cpus': 8,
    }, {
        'name': '8 CPU, 16GB ram, 100GB',
        'ram': 16 * 1024,
        'disk': 100,
        'cpus': 8,
    }, {
        'name': '12 CPU, 12GB ram, 100GB',
        'ram': 12 * 1024,
        'disk': 100,
        'cpus': 12,
    }, {
        'name': '12 CPU, 32GB ram, 100GB',
        'ram': 32 * 1024,
        'disk': 100,
        'cpus': 12,
    }, {
        'name': '16 CPU, 16GB ram, 100GB',
        'ram': 16 * 1024,
        'disk': 100,
        'cpus': 16,
    }, {
        'name': '16 CPU, 32GB ram, 100GB',
        'ram': 32 * 1024,
        'disk': 100,
        'cpus': 16,
    }, {
        'name': '16 CPU, 48GB ram, 100GB',
        'ram': 48 * 1024,
        'disk': 100,
        'cpus': 16,
    }, {
        'name': '16 CPU, 64GB ram, 100GB',
        'ram': 64 * 1024,
        'disk': 100,
        'cpus': 16,
    }]

SL_TEMPLATES = {}
for i, template in enumerate(SL_BASE_TEMPLATES):
    # Add local disk templates
    local = template.copy()
    local['local_disk'] = True
    SL_TEMPLATES[i] = local


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

    features = {'create_node': ['generates_password', 'ssh_key']}
    api_name = 'softlayer'

    def _to_node(self, host, bare_metal=None):
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

        # When machine is launching it gets state halted
        # we change this to pending
        if bare_metal:
            createDate = host.get('provisionDate', None)
            try:
                state = NODE_STATE_MAP.get(str(host['hardwareStatusId']),
                                           NodeState.UNKNOWN)
            except:
                state = NodeState.UNKNOWN
        else:
            state = NODE_STATE_MAP.get(host['powerState']['keyName'],
                                       NodeState.UNKNOWN)

        if not password and state == NodeState.UNKNOWN:
            state = NODE_STATE_MAP['INITIATING']

        public_ips = []
        private_ips = []
        if 'primaryIpAddress' in host:
            public_ips.append(host['primaryIpAddress'])

        if 'primaryBackendIpAddress' in host:
            private_ips.append(host['primaryBackendIpAddress'])

        image = host.get('operatingSystem', {}).get('softwareLicense', {}) \
                    .get('softwareDescription', {}) \
                    .get('longDescription', None)

        extra = {
            'hostname': host['hostname'],
            'fullyQualifiedDomainName': host['fullyQualifiedDomainName'],
            'password': password,
            'datacenter': host.get('datacenter', {}).get('name', None),
            'image': image,
            'size': host.get('typeId', ''),
            'hourlyRecurringFee': hourlyRecurringFee,
            'recurringFee': recurringFee,
            'recurringMonths': recurringMonths,
            'created': createDate,
            'plan_description': host.get('billingItem',
                {}).get('description', ''),
            'hoursUsed': host.get('billingItem', {}).get('hoursUsed', ''),
        }

        notes = host.get('notes', None)
        if notes:
            extra['notes'] = notes
        billingItem = host.get('billingItem', {}).get('id', None)
        if billingItem:
            extra['billingItem'] = billingItem
        billingItemChildren = host.get('billingItem', {}).get('children', [])
        if billingItemChildren:
            extra['billingItemChildren'] = billingItemChildren

        if bare_metal:
            extra['memory'] = host.get('memoryCapacity')
            extra['cpu'] = host.get('processorPhysicalCoreAmount')
            extra['server_type'] = 'Bare Metal'
        else:
            extra['maxCpu'] = host.get('maxCpu', None)
            extra['maxMemory'] = host.get('maxMemory', None)
            extra['server_type'] = 'Cloud server'

        return Node(
            id=host['id'],
            name=host['fullyQualifiedDomainName'],
            state=state,
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self,
            extra=extra
        )

    def destroy_node(self, node):
        if node.extra.get('server_type', '') == 'Bare Metal':
            try:
                billingItem = node.extra.get('billingItem')
                if billingItem:
                    self.connection.request(
                        'SoftLayer_Billing_Item', 'cancelItem',
                        True, True, id=billingItem)
                else:
                    return False
            except:
                return False
        else:
            self.connection.request(
                'SoftLayer_Virtual_Guest',
                'deleteObject',
                id=node.id
                )
        return True

    def reboot_node(self, node):
        if node.extra.get('server_type', '') == 'Bare Metal':
            self.connection.request(
                'SoftLayer_Hardware', 'rebootSoft', id=node.id
            )
        else:
            self.connection.request(
                'SoftLayer_Virtual_Guest', 'rebootSoft', id=node.id
            )
        return True

    def ex_stop_node(self, node):
        if node.extra.get('server_type', '') == 'Bare Metal':
            self.connection.request(
                'SoftLayer_Hardware', 'powerOff', id=node.id
            )
        else:
            self.connection.request(
                'SoftLayer_Virtual_Guest', 'powerOff', id=node.id
            )
        return True

    def ex_start_node(self, node):
        if node.extra.get('server_type', '') == 'Bare Metal':
            self.connection.request(
                'SoftLayer_Hardware', 'powerOn', id=node.id
            )
        else:
            self.connection.request(
                'SoftLayer_Virtual_Guest', 'powerOn', id=node.id
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

        @inherits: :class:`NodeDriver.create_node`

        :keyword    ex_domain: e.g. libcloud.org
        :type       ex_domain: ``str``
        :keyword    ex_cpus: e.g. 2
        :type       ex_cpus: ``int``
        :keyword    ex_disk: e.g. 100
        :type       ex_disk: ``int``
        :keyword    ex_ram: e.g. 2048
        :type       ex_ram: ``int``
        :keyword    ex_bandwidth: e.g. 100
        :type       ex_bandwidth: ``int``
        :keyword    ex_local_disk: e.g. True
        :type       ex_local_disk: ``bool``
        :keyword    ex_datacenter: e.g. Dal05
        :type       ex_datacenter: ``str``
        :keyword    ex_os: e.g. UBUNTU_LATEST
        :type       ex_os: ``str``
        :keyword    ex_keyname: The name of the key pair
        :type       ex_keyname: ``str``
        :keyword    ex_backend_vlan: Id of the backend (private) network Vlan
        :type       ex_backend_vlan: ``int``
        :keyword    bare_metal: Whether the server will be bare metal
        :type       bare_metal: ``bool``
        :keyword    sshKeys: ssh key id to deploy on create node
        :type       sshKeys: ``str``
        """
        name = kwargs['name']
        os = 'DEBIAN_LATEST'
        if 'ex_os' in kwargs:
            os = kwargs['ex_os']
        elif 'image' in kwargs:
            os = kwargs['image'].id

        size = kwargs.get('size', NodeSize(id=123, name='Custom', ram=None,
                                           disk=None, bandwidth=None,
                                           price=None,
                                           driver=self.connection.driver))
        try:
            ex_size_data = SL_TEMPLATES.get(int(size.id)) or {}
            # plan keys are ints for cloud servers, while str for bare metal
        except:
            ex_size_data = {}
        cpu_count = kwargs.get('ex_cpus') or ex_size_data.get('cpus') or \
            DEFAULT_CPU_SIZE
        ram = kwargs.get('ex_ram') or ex_size_data.get('ram') or \
            DEFAULT_RAM_SIZE
        bandwidth = kwargs.get('ex_bandwidth') or size.bandwidth or 1000
        hourly = 'true' if kwargs.get('ex_hourly', True) else 'false'

        local_disk = 'true'
        if ex_size_data.get('local_disk') is False:
            local_disk = 'false'

        if kwargs.get('ex_local_disk') is False:
            local_disk = 'false'

        disk_size = DEFAULT_DISK_SIZE
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
            domain = DEFAULT_DOMAIN

        postInstallScriptUri = kwargs.get('postInstallScriptUri')

        bare_metal = kwargs.get('bare_metal', False)

        ex_backend_vlan = kwargs.get('ex_backend_vlan', None)

        if bare_metal:
            newCCI = {
                'hostname': name,
                'domain': domain,
                'fixedConfigurationPreset': {'keyName': size.id},
                'networkComponents': [{'maxSpeed': bandwidth}],
                'hourlyBillingFlag': hourly,
                'operatingSystemReferenceCode': os
                }
        else:
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
        # sshKeys is an optional ssh key id to deploy
        sshKeys = kwargs.get('sshKeys')
        if sshKeys:
            newCCI['sshKeys'] = [{'id': sshKeys}]
        if postInstallScriptUri:
            newCCI['postInstallScriptUri'] = postInstallScriptUri

        if ex_backend_vlan:
            backend_network = {
                'networkVlan': {
                    'id': int(ex_backend_vlan)
                }
            }
            newCCI['primaryBackendNetworkComponent'] = backend_network

        if 'ex_keyname' in kwargs:
            newCCI['sshKeys'] = [
                {
                    'id': self._key_name_to_id(kwargs['ex_keyname'])
                }
            ]

        if bare_metal:
            existing_nodes = self.list_nodes()
            res = self.connection.request(
                'SoftLayer_Hardware', 'createObject', newCCI
            ).object
            # softlayer won't return the id after this,
            # it is available only after machine is provisioned
            # so we have to find it ourselves
            new_node = None
            for i in range(0, 10):
                nodes = self.list_nodes()
                for node in nodes:
                    if node.id not in [n.id for n in existing_nodes] and \
                       node.extra['hostname'] == name:
                            new_node = node
                            return new_node
                time.sleep(10)
        else:
            res = self.connection.request(
                'SoftLayer_Virtual_Guest', 'createObject', newCCI
            ).object
            node_id = res['id']
            node = Node(id=node_id, name=name, state=NodeState.PENDING,
                        public_ips=[], private_ips=[], extra=None,
                        driver=self)
            return node

    def list_key_pairs(self):
        result = self.connection.request(
            'SoftLayer_Account', 'getSshKeys'
        ).object
        elems = [x for x in result]
        key_pairs = self._to_key_pairs(elems=elems)
        return key_pairs

    def get_key_pair(self, name):
        key_id = self._key_name_to_id(name=name)
        result = self.connection.request(
            'SoftLayer_Security_Ssh_Key', 'getObject', id=key_id
        ).object
        return self._to_key_pair(result)

    # TODO: Check this with the libcloud guys,
    # can we create new dependencies?
    def create_key_pair(self, name, ex_size=4096):
        if crypto is False:
            raise NotImplementedError('create_key_pair needs'
                                      'the cryptography library')
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        public_key = key.public_key().public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        )
        new_key = {
            'key': public_key,
            'label': name,
            'notes': '',
        }
        result = self.connection.request(
            'SoftLayer_Security_Ssh_Key', 'createObject', new_key
        ).object
        result['private'] = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        return self._to_key_pair(result)

    def import_key_pair_from_string(self, name, key_material):
        new_key = {
            'key': key_material,
            'label': name,
            'notes': '',
        }
        result = self.connection.request(
            'SoftLayer_Security_Ssh_Key', 'createObject', new_key
        ).object

        key_pair = self._to_key_pair(result)
        return key_pair

    def delete_key_pair(self, key_pair):
        key = self._key_name_to_id(key_pair)
        result = self.connection.request(
            'SoftLayer_Security_Ssh_Key', 'deleteObject', id=key
        ).object
        return result

    def _to_image(self, img):
        return NodeImage(
            id=img['template']['operatingSystemReferenceCode'],
            name=img['itemPrice']['item']['description'],
            driver=self.connection.driver
        )

    def _to_bare_metal_image(self, img):
        return NodeImage(
            id=img['template']['operatingSystemReferenceCode'],
            name="Bare Metal: %s" % img['itemPrice']['item']['description'],
            driver=self.connection.driver
        )

    def list_images(self, location=None):
        cloud_images = self.connection.request('SoftLayer_Virtual_Guest',
                                               'getCreateObjectOptions').object
        cloud_images = [self._to_image(i)
                        for i in cloud_images['operatingSystems']]
        bm_images = self.connection.request('SoftLayer_Hardware',
                                            'getCreateObjectOptions').object
        bm_images = [self._to_bare_metal_image(i)
                     for i in bm_images['operatingSystems']]
        return cloud_images + bm_images

    def get_image(self, image_id):
        """
        Gets an image based on an image_id.

        :param image_id: Image identifier
        :type image_id: ``str``

        :return: A NodeImage object
        :rtype: :class:`NodeImage`

        """
        images = self.list_images()
        images = [image for image in images if image.id == image_id]
        if len(images) < 1:
            raise SoftLayerException('could not find the image with id %s'
                                     % image_id)
        image = images[0]
        return image

    def _to_size(self, id, size):
        return NodeSize(
            id=id,
            name=size['name'],
            ram=size['ram'],
            disk=size['disk'],
            extra={'cpus': size['cpus']},
            bandwidth=size.get('bandwidth'),
            price=None,
            driver=self.connection.driver,
        )

    def _to_bare_metal_size(self, size):
        return NodeSize(
            id=size['keyName'],
            name='Bare Metal: %s' % size['description'],
            price=size['totalMinimumHourlyFee'],
            ram=None,
            disk=None,
            bandwidth=None,
            driver=self.connection.driver,
        )

    def list_sizes(self, location=None):
        bm_sizes = self.connection.request('SoftLayer_Hardware',
                                           'getCreateObjectOptions').object
        bm_sizes = [self._to_bare_metal_size(size['preset'])
                    for size in bm_sizes['fixedConfigurationPresets']]
        cloud_sizes = [self._to_size(id, s) for id, s in SL_TEMPLATES.items()]
        return bm_sizes + cloud_sizes

    def _to_loc(self, loc):
        country = 'UNKNOWN'
        loc_id = loc['template']['datacenter']['name']
        name = loc_id

        if loc_id in DATACENTERS:
            country = DATACENTERS[loc_id]['country']
            name = DATACENTERS[loc_id].get('name', loc_id)
        return NodeLocation(id=loc_id, name=name,
                            country=country, driver=self)

    def list_locations(self):
        locations = self.connection.request('SoftLayer_Virtual_Guest',
                                            'getCreateObjectOptions').object
        locations = [self._to_loc(location)
                     for location in locations['datacenters']]

        return locations

    def list_nodes(self):
        # virtual servers
        virtual_mask = {
            'virtualGuests': {
                'powerState': '',
                'hostname': '',
                'maxMemory': '',
                'datacenter': '',
                'operatingSystem': {'passwords': ''},
                'billingItem': {'children': ''},
            },
        }
        res = self.connection.request(
            'SoftLayer_Account',
            'getVirtualGuests',
            object_mask=virtual_mask
        ).object
        virtual = [self._to_node(h) for h in res]
        # bare metal servers
        bare_mask = {
            'hardware': {
                'id': '',
                'hostname': '',
                'domain': '',
                'hardwareStatusId': '',
                'globalIdentifier': '',
                'fullyQualifiedDomainName': '',
                'processorPhysicalCoreAmount': '',
                'memoryCapacity': '',
                'primaryBackendIpAddress': '',
                'primaryIpAddress': '',
                'datacenter': '',
                'billingItem': {'children': ''},
                'operatingSystem': {'passwords': ''}
            },
        }

        res = self.connection.request(
            'SoftLayer_Account',
            'getHardware',
            object_mask=bare_mask
        ).object
        bare_metal = [self._to_node(h, bare_metal=True) for h in res]
        return virtual + bare_metal

    def _to_key_pairs(self, elems):
        key_pairs = [self._to_key_pair(elem=elem) for elem in elems]
        return key_pairs

    def _to_key_pair(self, elem):
        key_pair = KeyPair(name=elem['label'],
                           public_key=elem['key'],
                           fingerprint=elem['fingerprint'],
                           private_key=elem.get('private', None),
                           driver=self,
                           extra={'id': elem['id']})
        return key_pair

    def _key_name_to_id(self, name):
        result = self.connection.request(
            'SoftLayer_Account', 'getSshKeys'
        ).object
        key_id = [x for x in result if x['label'] == name]
        if len(key_id) == 0:
            raise KeyPairDoesNotExistError(name, self)
        else:
            return int(key_id[0]['id'])
