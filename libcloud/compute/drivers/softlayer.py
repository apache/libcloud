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
    from Crypto.PublicKey import RSA
    crypto = True
except ImportError:
    crypto = False

from libcloud.common.types import LibcloudError
from libcloud.common.softlayer import SoftLayerConnection, SoftLayerException,\
    SoftLayerObjectDoesntExist
from libcloud.compute.types import Provider, NodeState, AutoScaleOperator,\
    AutoScaleAdjustmentType, AutoScaleMetric, AutoScaleTerminationPolicy
from libcloud.compute.base import NodeDriver, Node, NodeLocation, NodeSize, \
    NodeImage, KeyPair, AutoScaleGroup, AutoScalePolicy, AutoScaleAlarm
from libcloud.compute.types import KeyPairDoesNotExistError

from libcloud.utils.misc import find, reverse_dict

DEFAULT_DOMAIN = 'example.com'
DEFAULT_CPU_SIZE = 1
DEFAULT_RAM_SIZE = 2048
DEFAULT_DISK_SIZE = 100

DATACENTERS = {
    'hou02': {'country': 'US'},
    'sea01': {'country': 'US', 'name': 'Seattle - West Coast U.S.'},
    'wdc01': {'country': 'US', 'name': 'Washington, DC - East Coast U.S.'},
    'dal01': {'country': 'US'},
    'dal02': {'country': 'US'},
    'dal04': {'country': 'US'},
    'dal05': {'country': 'US', 'name': 'Dallas - Central U.S.'},
    'dal06': {'country': 'US'},
    'dal07': {'country': 'US'},
    'sjc01': {'country': 'US', 'name': 'San Jose - West Coast U.S.'},
    'sng01': {'country': 'SG', 'name': 'Singapore - Southeast Asia'},
    'ams01': {'country': 'NL', 'name': 'Amsterdam - Western Europe'},
    'tok02': {'country': 'JP', 'name': 'Tokyo - Japan'},
}

NODE_STATE_MAP = {
    'RUNNING': NodeState.RUNNING,
    'HALTED': NodeState.UNKNOWN,
    'PAUSED': NodeState.UNKNOWN,
    'INITIATING': NodeState.PENDING
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

    _VALUE_TO_SCALE_OPERATOR_TYPE_MAP = {
        '>': AutoScaleOperator.GT,
        '<': AutoScaleOperator.LT
    }

    _SCALE_OPERATOR_TYPE_TO_VALUE_MAP = reverse_dict(
        _VALUE_TO_SCALE_OPERATOR_TYPE_MAP)

    _VALUE_TO_SCALE_ADJUSTMENT_TYPE_MAP = {
        'RELATIVE': AutoScaleAdjustmentType.CHANGE_IN_CAPACITY,
        'ABSOLUTE': AutoScaleAdjustmentType.EXACT_CAPACITY,
        'PERCENT': AutoScaleAdjustmentType.PERCENT_CHANGE_IN_CAPACITY
    }

    _SCALE_ADJUSTMENT_TYPE_TO_VALUE_MAP = reverse_dict(
        _VALUE_TO_SCALE_ADJUSTMENT_TYPE_MAP)

    _VALUE_TO_TERMINATION_POLICY_MAP = {
        'OLDEST': AutoScaleTerminationPolicy.OLDEST_INSTANCE,
        'NEWEST': AutoScaleTerminationPolicy.NEWEST_INSTANCE,
        'CLOSEST_TO_NEXT_CHARGE': AutoScaleTerminationPolicy.
        CLOSEST_TO_NEXT_CHARGE
    }

    _TERMINATION_POLICY_TO_VALUE_MAP = reverse_dict(
        _VALUE_TO_TERMINATION_POLICY_MAP)

    _VALUE_TO_METRIC_MAP = {
        'host.cpu.percent': AutoScaleMetric.CPU_UTIL
    }

    _METRIC_TO_VALUE_MAP = reverse_dict(
        _VALUE_TO_METRIC_MAP)

    connectionCls = SoftLayerConnection
    name = 'SoftLayer'
    website = 'http://www.softlayer.com/'
    type = Provider.SOFTLAYER

    features = {'create_node': ['generates_password', 'ssh_key']}

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

        # When machine is launching it gets state halted
        # we change this to pending
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

        return Node(
            id=host['id'],
            name=host['fullyQualifiedDomainName'],
            state=state,
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self,
            extra={
                'hostname': host['hostname'],
                'fullyQualifiedDomainName': host['fullyQualifiedDomainName'],
                'password': password,
                'maxCpu': host.get('maxCpu', None),
                'datacenter': host.get('datacenter', {}).get('longName', None),
                'maxMemory': host.get('maxMemory', None),
                'image': image,
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

    def ex_stop_node(self, node):
        self.connection.request(
            'SoftLayer_Virtual_Guest', 'powerOff', id=node.id
        )
        return True

    def ex_start_node(self, node):
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
        ex_size_data = SL_TEMPLATES.get(int(size.id)) or {}
        # plan keys are ints
        cpu_count = kwargs.get('ex_cpus') or ex_size_data.get('cpus') or \
            DEFAULT_CPU_SIZE
        ram = kwargs.get('ex_ram') or ex_size_data.get('ram') or \
            DEFAULT_RAM_SIZE
        bandwidth = kwargs.get('ex_bandwidth') or size.bandwidth or 10
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

        newCCI = {
            'hostname': name,
            'domain': domain,
            'startCpus': cpu_count,
            'maxMemory': ram,
            'networkComponents': [{'maxSpeed': bandwidth}],
            'hourlyBillingFlag': hourly,
            'operatingSystemReferenceCode': os,
            'localDiskFlag': local_disk,
            'blockDevices': [{
                'device': '0',
                'diskImage': {
                    'capacity': disk_size,
                }
            }]
        }

        if datacenter:
            newCCI['datacenter'] = {'name': datacenter}

        if 'ex_keyname' in kwargs:
            newCCI['sshKeys'] = [
                {
                    'id': self._key_name_to_id(kwargs['ex_keyname'])
                }
            ]

        res = self.connection.request(
            'SoftLayer_Virtual_Guest', 'createObject', newCCI
        ).object

        node_id = res['id']
        raw_node = self._get_order_information(node_id)

        return self._to_node(raw_node)

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
                                      'the pycrypto library')
        key = RSA.generate(ex_size)
        new_key = {
            'key': key.publickey().exportKey('OpenSSH'),
            'label': name,
            'notes': '',
        }
        result = self.connection.request(
            'SoftLayer_Security_Ssh_Key', 'createObject', new_key
        ).object
        result['private'] = key.exportKey('PEM')
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
        loc_id = loc['template']['datacenter']['name']
        name = loc_id

        if loc_id in DATACENTERS:
            country = DATACENTERS[loc_id]['country']
            name = DATACENTERS[loc_id].get('name', loc_id)
        return NodeLocation(id=loc_id, name=name,
                            country=country, driver=self)

    def list_locations(self):
        res = self.connection.request(
            'SoftLayer_Virtual_Guest', 'getCreateObjectOptions'
        ).object
        return [self._to_loc(l) for l in res['datacenters']]

    def list_nodes(self):
        mask = {
            'virtualGuests': {
                'powerState': '',
                'hostname': '',
                'maxMemory': '',
                'datacenter': '',
                'operatingSystem': {'passwords': ''},
                'billingItem': '',
            },
        }
        res = self.connection.request(
            'SoftLayer_Account',
            'getVirtualGuests',
            object_mask=mask
        ).object
        return [self._to_node(h) for h in res]

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

    def list_auto_scale_groups(self):

        mask = {
            'scaleGroups': {
                'terminationPolicy': ''
            }
        }

        res = self.connection.request('SoftLayer_Account',
                                      'getScaleGroups', object_mask=mask).\
            object
        return self._to_autoscale_groups(res)

    def create_auto_scale_group(
            self, name, min_size, max_size, cooldown, image=None,
            termination_policies=AutoScaleTerminationPolicy.OLDEST_INSTANCE,
            balancer=None, **kwargs):
        """
        Create a new auto scale group.

        @inherits: :class:`NodeDriver.create_auto_scale_group`

        :param name: Group name.
        :type name: ``str``

        :param min_size: Minimum membership size of group.
        :type min_size: ``int``

        :param max_size: Maximum membership size of group.
        :type max_size: ``int``

        :param cooldown: Group cooldown (in seconds).
        :type cooldown: ``int``

        :param termination_policies: Termination policy for this group.
        Note: Softlayer support single policy so type is a single value
        :type termination_policies: value within
                                  :class:`AutoScaleTerminationPolicy`

        :param image: The image to create the member with.
        :type image: :class:`.NodeImage`

        :param balancer: The load balancer to attach this group.
        :type balancer: :class:`.LoadBalancer`

        :keyword    size: Size definition for group members instances.
        :type       size: :class:`.NodeSize`

        :keyword location: Which data center to create the members in.
        Datacenter must be within the given region.
        :type location: :class:`.NodeLocation`

        :keyword    ex_region: The region the group will be created in.
        :type       ex_region: ``str``

        :keyword    ex_datacenter: The datacenter that the group members will
                                   be created in.
        :type       ex_datacenter:   ``str``

        :keyword    ex_region: The region the group will be created in.
        :type       ex_region: ``str``

        :keyword    ex_service_port: Service port to be used by the group
                                     members.
        :type       ex_service_port: ``int``

        :keyword    ex_instance_name: The name of the group members instances.
        :type       ex_instance_name: ``str``

        :keyword    ex_domain: Group members domain name e.g. libcloud.org
        :type       ex_domain: ``str``

        :keyword    ex_os: Operating system the group members will be created
                           with e.g. UBUNTU_LATEST.
        :type       ex_os:   ``str``

        :keyword    ex_cpus: CPU count for the group members.
                           e.g. 1.
        :type       ex_cpus:   ``int``

        :keyword    ex_ram: RAM for the group members.
                           e.g. 2048.
        :type       ex_ram:   ``int``

        :keyword    ex_disk: Disk size for the group members.
                           e.g. 100.
        :type       ex_disk:   ``int``

        :keyword    ex_userdata: User data to be injected to group members.
        :type       ex_userdata: ``str``

        :return: The newly created scale group.
        :rtype: :class:`.AutoScaleGroup`
        """
        DEFAULT_REGION = 'eu-deu-west-1'
        DEFAULT_TIMEOUT = 12000
        os = 'DEBIAN_LATEST'
        if 'ex_os' in kwargs:
            os = kwargs['ex_os']
        elif image:
            os = image.id

        size = kwargs.get('size', NodeSize(id=123, name='Custom', ram=None,
                                           disk=None, bandwidth=None,
                                           price=None,
                                           driver=self.connection.driver))
        ex_size_data = SL_TEMPLATES.get(int(size.id)) or {}

        cpu_count = kwargs.get('ex_cpus') or ex_size_data.get('cpus') or \
            DEFAULT_CPU_SIZE
        ram = kwargs.get('ex_ram') or ex_size_data.get('ram') or \
            DEFAULT_RAM_SIZE
        bandwidth = kwargs.get('ex_bandwidth') or size.bandwidth or 10
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

        # handle region and datacenter within it
        if 'ex_region' not in kwargs:
            kwargs['ex_region'] = DEFAULT_REGION
        datacenter = ''
        if 'ex_datacenter' in kwargs:
            datacenter = kwargs['ex_datacenter']
        elif 'location' in kwargs:
            datacenter = kwargs['location'].id

        # retrieve all available regions to extract the
        # matched id
        res = self.connection.request(
            'SoftLayer_Location_Group_Regional',
            'getAllObjects').object

        r = find(res, lambda r: r['name'] == kwargs['ex_region'])
        if not r:
            raise SoftLayerException('Unable to find region id for region: %s'
                                     % kwargs['ex_region'])
        ex_region_id = r['id']

        import base64
        template = {
            'startCpus': cpu_count,
            'maxMemory': ram,
            'networkComponents': [{'maxSpeed': bandwidth}],
            'hourlyBillingFlag': 'true',
            'operatingSystemReferenceCode': os,
            'localDiskFlag': local_disk,
            'blockDevices': [{
                'device': '0',
                'diskImage': {
                    'capacity': disk_size
                }
            }]
        }

        if 'ex_userdata' in kwargs:
            template['UserData'] = \
                [{'value': base64.b64encode(kwargs['ex_userdata'])}]

        if 'ex_instance_name' not in kwargs:
            kwargs['ex_instance_name'] = name

        ex_instance_name = kwargs['ex_instance_name']
        template['hostname'] = ex_instance_name

        domain = kwargs.get('ex_domain')
        if domain is None:
            if ex_instance_name.find('.') != -1:
                domain = ex_instance_name[ex_instance_name.find('.') + 1:]
        if domain is None:
            domain = DEFAULT_DOMAIN

        template['domain'] = domain
        if datacenter:
            template['datacenter'] = {'name': datacenter}

        def _wait_for_creation(group_id):
            # 5 seconds
            POLL_INTERVAL = 5

            end = time.time() + DEFAULT_TIMEOUT
            completed = False
            while time.time() < end and not completed:
                status_name = self._get_group_status(group_id)
                if status_name != 'ACTIVE':
                    time.sleep(POLL_INTERVAL)
                else:
                    completed = True

            if not completed:
                raise LibcloudError('Group creation did not complete in %s'
                                    ' seconds' % (DEFAULT_TIMEOUT))

        data = {}
        data['name'] = name
        data['minimumMemberCount'] = min_size
        data['maximumMemberCount'] = max_size
        data['cooldown'] = cooldown

        data['regionalGroupId'] = ex_region_id
        data['suspendedFlag'] = False

        if termination_policies:
            termination_policy = termination_policies[0] if \
                isinstance(termination_policies, list) else \
                termination_policies
            data['terminationPolicy'] = {
                'keyName':
                    self._termination_policy_to_value(termination_policy)
            }

        data['virtualGuestMemberTemplate'] = template

        if balancer:
            if not datacenter:
                raise ValueError('location or ex_datacenter must be supplied'
                                 ' when supplying loadbalancer')

            ex_service_port = kwargs.get('ex_service_port', 80)
            data['loadBalancers'] = [
                self._generate_balancer_template(balancer, ex_service_port)]

        res = self.connection.request('SoftLayer_Scale_Group',
                                      'createObject', data).object

        _wait_for_creation(res['id'])
        mask = {
            'terminationPolicy': ''
        }

        res = self.connection.request('SoftLayer_Scale_Group', 'getObject',
                                      object_mask=mask, id=res['id']).object
        group = self._to_autoscale_group(res)

        return group

    def list_auto_scale_group_members(self, group):
        mask = {
            'virtualGuest': {
                'billingItem': '',
                'powerState': '',
                'operatingSystem': {'passwords': ''},
                'provisionDate': ''
            }
        }

        res = self.connection.request('SoftLayer_Scale_Group',
                                      'getVirtualGuestMembers',
                                      id=group.id).object

        nodes = []
        for r in res:
            # NOTE: r[id]  is ID of virtual guest member
            # (not instance itself)
            res_node = self.connection.request('SoftLayer_Scale_Member_'
                                               'Virtual_Guest',
                                               'getVirtualGuest', id=r['id'],
                                               object_mask=mask).object

            nodes.append(self._to_node(res_node))

        return nodes

    def create_auto_scale_policy(self, group, name, adjustment_type,
                                 scaling_adjustment):
        """
        Create an auto scale policy for the given group.

        @inherits: :class:`NodeDriver.create_auto_scale_policy`

        :param group: Group object.
        :type group: :class:`.AutoScaleGroup`

        :param name: Policy name.
        :type name: ``str``

        :param adjustment_type: The adjustment type.
        :type adjustment_type: value within :class:`AutoScaleAdjustmentType`

        :param scaling_adjustment: The number of instances by which to scale.
        :type scaling_adjustment: ``int``

        :return: The newly created policy.
        :rtype: :class:`.AutoScalePolicy`
        """
        data = {}
        data['name'] = name
        data['scaleGroupId'] = int(group.id)

        policy_action = {}
        # 'SCALE'
        policy_action['typeId'] = 1
        policy_action['scaleType'] = \
            self._scale_adjustment_to_value(adjustment_type)
        policy_action['amount'] = scaling_adjustment

        data['scaleActions'] = [policy_action]

        res = self.connection.request('SoftLayer_Scale_Policy',
                                      'createObject', data).object
        mask = {
            'scaleActions': ''
        }

        res = self.connection.request('SoftLayer_Scale_Policy',
                                      'getObject', id=res['id'],
                                      object_mask=mask).object
        policy = self._to_autoscale_policy(res)

        return policy

    def list_auto_scale_policies(self, group):
        mask = {
            'policies': {
                'scaleActions': ''
            }
        }

        res = self.connection.request('SoftLayer_Scale_Group', 'getPolicies',
                                      id=group.id, object_mask=mask).object
        return [self._to_autoscale_policy(r) for r in res]

    def delete_auto_scale_policy(self, policy):
        self.connection.request('SoftLayer_Scale_Policy',
                                'deleteObject', id=policy.id).object
        return True

    def create_auto_scale_alarm(self, name, policy, metric_name, operator,
                                threshold, period, **kwargs):
        """
        Create an auto scale alarm for the given policy.

        @inherits: :class:`NodeDriver.create_auto_scale_alarm`

        :param name: Descriptive name of the alarm.
        :type name: ``str``

        :param policy: Policy object.
        :type policy: :class:`.AutoScalePolicy`

        :param metric_name: The metric to watch.
        :type metric_name: value within :class:`AutoScaleMetric`

        :param operator: The operator to use for comparison.
        :type operator: value within :class:`AutoScaleOperator`

        :param threshold: The value against which the specified statistic is
                          compared.
        :type threshold: ``int``

        :param name: The descriptive name for the alarm.
        :type name: ``str``

        :param period: The number of seconds the values are aggregated for when
                       compared to threshold.
        :type period: ``int``

        :return: The newly created alarm.
        :rtype: :class:`.AutoScaleAlarm`
        """

        data = {}
        # 'RESOURCE_USE'
        data['typeId'] = 3
        data['scalePolicyId'] = policy.id

        trigger_watch = {}
        trigger_watch['algorithm'] = 'EWMA'
        trigger_watch['metric'] = self._metric_to_value(metric_name)

        trigger_watch['operator'] = \
            self._operator_type_to_value(operator)

        trigger_watch['value'] = threshold
        trigger_watch['period'] = period

        data['watches'] = [trigger_watch]

        res = self.connection.\
            request('SoftLayer_Scale_Policy_Trigger_ResourceUse',
                    'createObject', data).object

        mask = {
            'watches': ''
        }

        res = self.connection.\
            request('SoftLayer_Scale_Policy_Trigger_ResourceUse',
                    'getObject', id=res['id'], object_mask=mask).object
        alarm = self._to_autoscale_alarm(res)

        return alarm

    def list_auto_scale_alarms(self, policy):
        mask = {
            'resourceUseTriggers': {
                'watches': ''
            }
        }

        res = self.connection.request('SoftLayer_Scale_Policy',
                                      'getResourceUseTriggers',
                                      object_mask=mask, id=policy.id).object
        return [self._to_autoscale_alarm(r) for r in res]

    def delete_auto_scale_alarm(self, alarm):
        self.connection.request('SoftLayer_Scale_Policy_Trigger_ResourceUse',
                                'deleteObject', id=alarm.id).object
        return True

    def delete_auto_scale_group(self, group):
        DEFAULT_TIMEOUT = 12000

        def _wait_for_deletion(group_name):
            # 5 seconds
            POLL_INTERVAL = 5

            end = time.time() + DEFAULT_TIMEOUT
            completed = False
            while time.time() < end and not completed:
                try:
                    self._get_auto_scale_group(group_name)
                    time.sleep(POLL_INTERVAL)
                except SoftLayerObjectDoesntExist:
                    # for now treat this as not found
                    completed = True
            if not completed:
                raise LibcloudError('Operation did not complete in %s seconds'
                                    % (DEFAULT_TIMEOUT))

        self.connection.request(
            'SoftLayer_Scale_Group', 'forceDeleteObject', id=group.id).object

        _wait_for_deletion(group.name)

        return True

    def ex_attach_balancer_to_auto_scale_group(self, group, balancer,
                                               ex_service_port=80):
        """
        Attach loadbalancer to auto scale group.

        :param group: Group object.
        :type group: :class:`.AutoScaleGroup`

        :param balancer: The loadbalancer object.
        :type balancer: :class:`.LoadBalancer`

        :param ex_service_port: Service port to be used by the group members.
        :type  ex_service_port: ``int``

        :return: ``True`` if attach_balancer_to_auto_scale_group was
        successful.
        :rtype: ``bool``
        """
        def _get_group_model(group_id):

            mask = {
                'loadBalancers': ''
            }

            return self.connection.request('SoftLayer_Scale_Group',
                                           'getObject', object_mask=mask,
                                           id=group_id).object

        res = _get_group_model(group.id)
        res['loadBalancers'].append(
            self._generate_balancer_template(balancer, ex_service_port))

        self.connection.request('SoftLayer_Scale_Group', 'editObject', res,
                                id=group.id)
        return True

    def ex_detach_balancer_from_auto_scale_group(self, group, balancer):
        """
        Detach loadbalancer from auto scale group.

        :param group: Group object.
        :type group: :class:`.AutoScaleGroup`

        :param balancer: The loadbalancer object.
        :type balancer: :class:`.LoadBalancer`

        :return: ``True`` if detach_balancer_from_auto_scale_group was
        successful.
        :rtype: ``bool``
        """

        def _get_group_model(group_id):

            mask = {
                'loadBalancers': ''
            }

            return self.connection.request('SoftLayer_Scale_Group',
                                           'getObject', object_mask=mask,
                                           id=group_id).object

        def _get_balancer_model(balancer_id):

            lb_service = 'SoftLayer_Network_Application_Delivery_Controller_'\
                'LoadBalancer_VirtualIpAddress'

            lb_mask = {
                'virtualServers': {
                    'serviceGroups': {
                        'services': ''
                    },
                    'scaleLoadBalancers': {
                    }
                }
            }

            lb_res = self.connection.request(lb_service, 'getObject',
                                             object_mask=lb_mask,
                                             id=balancer_id).object
            return lb_res

        def _locate_vs(lb, port):

            vs = None
            if port < 0:
                vs = lb['virtualServers'][0] if lb['virtualServers']\
                    else None
            else:
                for v in lb['virtualServers']:
                    if v['port'] == port:
                        vs = v

            return vs

        res = _get_group_model(group.id)
        lb_res = _get_balancer_model(balancer.id)
        vs = _locate_vs(lb_res, balancer.port)
        if not vs:
            raise LibcloudError(value='No service_group found for port: %s' %
                                balancer.port, driver=self)
        lbs_to_remove = [lb['id'] for lb in res['loadBalancers'] if
                         lb['virtualServerId'] == vs['id']]
        for lb in lbs_to_remove:
            self.connection.request('SoftLayer_Scale_LoadBalancer',
                                    'deleteObject', id=lb)
        return True

    def _generate_balancer_template(self, balancer, ex_service_port):

        lb_service = 'SoftLayer_Network_Application_Delivery_Controller_'\
            'LoadBalancer_VirtualIpAddress'

        lb_mask = {
            'virtualServers': {
                'serviceGroups': {
                },
                'scaleLoadBalancers': {
                }
            }
        }

        # get the loadbalancer
        lb_res = self.connection.request(
            lb_service, 'getObject', object_mask=lb_mask,
            id=balancer.id).object

        # find the vs with matching balancer port
        # we need vs id for the scale template to 'connect' it
        vss = lb_res.get('virtualServers', [])
        vs = find(vss, lambda vs: vs['port'] == balancer.port)
        if not vs:
            raise LibcloudError(value='No virtualServers found for'
                                ' Softlayer loadbalancer with port: %s' %
                                balancer.port, driver=self)

        scale_lb_template = {
            # connect it to the matched vs
            'virtualServerId': vs['id'],
            'port': ex_service_port,
            # DEFAULT health check
            'healthCheck': {
                'healthCheckTypeId': 21
            }
        }
        return scale_lb_template

    def _get_auto_scale_group(self, group_name):

        groups = self.list_auto_scale_groups()
        group = find(groups, lambda g: g.name == group_name)
        if not group:
            raise SoftLayerObjectDoesntExist('Group name: %s does not exist'
                                             % group_name)
        return group

    def _get_group_status(self, group_id):
        res = self.connection.request('SoftLayer_Scale_Group',
                                      'getStatus', id=group_id).object
        return res['keyName']

    def _to_autoscale_policy(self, plc):

        plc_id = plc['id']
        name = plc['name']

        adj_type = None
        adjustment_type = None
        scaling_adjustment = None

        if plc.get('scaleActions', []):

            adj_type = plc['scaleActions'][0]['scaleType']
            adjustment_type = self._value_to_scale_adjustment(adj_type)
            scaling_adjustment = plc['scaleActions'][0]['amount']

        return AutoScalePolicy(id=plc_id, name=name,
                               adjustment_type=adjustment_type,
                               scaling_adjustment=scaling_adjustment,
                               driver=self.connection.driver)

    def _to_autoscale_groups(self, res):
        groups = [self._to_autoscale_group(grp) for grp in res]
        return groups

    def _to_autoscale_group(self, grp):

        grp_id = grp['id']
        name = grp['name']
        cooldown = grp['cooldown']
        min_size = grp['minimumMemberCount']
        max_size = grp['maximumMemberCount']

        sl_tp = self._value_to_termination_policy(
            grp['terminationPolicy']['keyName'])
        termination_policies = [sl_tp]

        extra = {}
        extra['id'] = grp_id
        extra['state'] = grp['status']['keyName']
        # TODO: set with region name
        extra['region'] = 'softlayer'
        extra['regionalGroupId'] = grp['regionalGroupId']
        extra['suspendedFlag'] = grp['suspendedFlag']
        extra['terminationPolicyId'] = grp['terminationPolicyId']

        return AutoScaleGroup(id=grp_id, name=name, cooldown=cooldown,
                              min_size=min_size, max_size=max_size,
                              termination_policies=termination_policies,
                              driver=self.connection.driver,
                              extra=extra)

    def _to_autoscale_alarm(self, alrm):

        alrm_id = alrm['id']

        metric = None
        operator = None
        period = None
        threshold = None

        if alrm.get('watches', []):

            metric = self._value_to_metric(alrm['watches'][0]['metric'])
            op = alrm['watches'][0]['operator']
            operator = self._value_to_operator_type(op)
            period = alrm['watches'][0]['period']
            threshold = alrm['watches'][0]['value']

        return AutoScaleAlarm(id=alrm_id, name='N/A', metric_name=metric,
                              operator=operator, period=period,
                              threshold=int(threshold),
                              driver=self.connection.driver)

    def _value_to_operator_type(self, value):

        try:
            return self._VALUE_TO_SCALE_OPERATOR_TYPE_MAP[value]
        except KeyError:
            raise LibcloudError(value='Invalid value: %s' % (value),
                                driver=self)

    def _operator_type_to_value(self, operator_type):
        try:
            return self._SCALE_OPERATOR_TYPE_TO_VALUE_MAP[operator_type]
        except KeyError:
            raise LibcloudError(value='Invalid operator type: %s'
                                % (operator_type), driver=self)

    def _value_to_scale_adjustment(self, value):
        try:
            return self._VALUE_TO_SCALE_ADJUSTMENT_TYPE_MAP[value]
        except KeyError:
            raise LibcloudError(value='Invalid value: %s' % (value),
                                driver=self)

    def _scale_adjustment_to_value(self, scale_adjustment):
        try:
            return self._SCALE_ADJUSTMENT_TYPE_TO_VALUE_MAP[scale_adjustment]
        except KeyError:
            raise LibcloudError(value='Invalid scale adjustment: %s'
                                % (scale_adjustment), driver=self)

    def _value_to_termination_policy(self, value):
        try:
            return self._VALUE_TO_TERMINATION_POLICY_MAP[value]
        except KeyError:
            raise LibcloudError(value='Invalid value: %s' % (value),
                                driver=self)

    def _termination_policy_to_value(self, termination_policy):
        try:
            return self._TERMINATION_POLICY_TO_VALUE_MAP[termination_policy]
        except KeyError:
            raise LibcloudError(value='Invalid termination policy: %s'
                                % (termination_policy), driver=self)

    def _value_to_metric(self, value):

        try:
            return self._VALUE_TO_METRIC_MAP[value]
        except KeyError:
            raise LibcloudError(value='Invalid value: %s' % (value),
                                driver=self)

    def _metric_to_value(self, metric):
        try:
            return self._METRIC_TO_VALUE_MAP[metric]
        except KeyError:
            raise LibcloudError(value='Invalid metric: %s' % (metric),
                                driver=self)
