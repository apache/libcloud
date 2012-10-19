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
from libcloud.common.cloudstack import CloudStackDriverMixIn
from libcloud.compute.base import Node, NodeDriver, NodeImage, NodeLocation,\
    NodeSize, StorageVolume
from libcloud.compute.types import NodeState, LibcloudError


class CloudStackNode(Node):
    "Subclass of Node so we can expose our extension methods."

    def ex_allocate_public_ip(self):
        "Allocate a public IP and bind it to this node."
        return self.driver.ex_allocate_public_ip(self)

    def ex_release_public_ip(self, address):
        "Release a public IP that this node holds."
        return self.driver.ex_release_public_ip(self, address)

    def ex_add_ip_forwarding_rule(self, address, protocol, start_port,
                                  end_port=None):
        "Add a NAT/firewall forwarding rule for a port or ports."
        return self.driver.ex_add_ip_forwarding_rule(self, address, protocol,
                                                     start_port, end_port)

    def ex_delete_ip_forwarding_rule(self, rule):
        "Delete a NAT/firewall rule."
        return self.driver.ex_delete_ip_forwarding_rule(self, rule)


class CloudStackAddress(object):
    "A public IP address."

    def __init__(self, node, id, address):
        self.node = node
        self.id = id
        self.address = address

    def release(self):
        self.node.ex_release_public_ip(self)

    def __str__(self):
        return self.address

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.id == other.id


class CloudStackForwardingRule(object):
    "A NAT/firewall forwarding rule."

    def __init__(self, node, id, address, protocol, start_port, end_port=None):
        self.node = node
        self.id = id
        self.address = address
        self.protocol = protocol
        self.start_port = start_port
        self.end_port = end_port

    def delete(self):
        self.node.ex_delete_ip_forwarding_rule(self)

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.id == other.id


class CloudStackDiskOffering(object):
    """A disk offering within CloudStack."""

    def __init__(self, id, name, size, customizable):
        self.id = id
        self.name = name
        self.size = size
        self.customizable = customizable

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.id == other.id


class CloudStackNodeDriver(CloudStackDriverMixIn, NodeDriver):
    """Driver for the CloudStack API.

    @cvar host: The host where the API can be reached.
    @cvar path: The path where the API can be reached.
    @cvar async_poll_frequency: How often (in seconds) to poll for async
                                job completion.
    @type async_poll_frequency: C{int}"""

    name = 'CloudStack'
    api_name = 'cloudstack'
    website = 'http://cloudstack.org/'
    type = Provider.CLOUDSTACK

    NODE_STATE_MAP = {
        'Running': NodeState.RUNNING,
        'Starting': NodeState.REBOOTING,
        'Stopped': NodeState.TERMINATED,
        'Stopping': NodeState.TERMINATED,
        'Destroyed': NodeState.TERMINATED
    }

    def __init__(self, key, secret=None, secure=True, host=None,
                 path=None, port=None, *args, **kwargs):
        """
        @inherits: L{NodeDriver.__init__}

        @param    host: The host where the API can be reached. (required)
        @type     host: C{str}

        @param    path: The host where the API can be reached. (required)
        @type     path: C{str}
        """
        host = host if host else self.host

        if path is not None:
            self.path = path

        if host is not None:
            self.host = host

        if (self.type == Provider.CLOUDSTACK) and (not host or not path):
            raise Exception('When instantiating CloudStack driver directly ' +
                            'you also need to provide host and path argument')

        NodeDriver.__init__(self, key=key, secret=secret, secure=secure,
                            host=host, port=port)

    def list_images(self, location=None):
        args = {
            'templatefilter': 'executable'
        }
        if location is not None:
            args['zoneid'] = location.id
        imgs = self._sync_request('listTemplates', **args)
        images = []
        for img in imgs.get('template', []):
            images.append(NodeImage(img['id'], img['name'], self, {
                'hypervisor': img['hypervisor'],
                'format': img['format'],
                'os': img['ostypename'],
                }))
        return images

    def list_locations(self):
        locs = self._sync_request('listZones')
        locations = []
        for loc in locs['zone']:
            locations.append(NodeLocation(loc['id'], loc['name'], 'AU', self))
        return locations

    def list_nodes(self):
        """
        @inherits: L{NodeDriver.list_nodes}
        @rtype: C{list} of L{CloudStackNode}
        """
        vms = self._sync_request('listVirtualMachines')
        addrs = self._sync_request('listPublicIpAddresses')

        public_ips = {}
        for addr in addrs.get('publicipaddress', []):
            if 'virtualmachineid' not in addr:
                continue
            vm_id = addr['virtualmachineid']
            if vm_id not in public_ips:
                public_ips[vm_id] = {}
            public_ips[vm_id][addr['ipaddress']] = addr['id']

        nodes = []

        for vm in vms.get('virtualmachine', []):
            private_ips = []

            for nic in vm['nic']:
                if 'ipaddress' in nic:
                    private_ips.append(nic['ipaddress'])

            node = CloudStackNode(
                id=vm['id'],
                name=vm.get('displayname', None),
                state=self.NODE_STATE_MAP[vm['state']],
                public_ips=public_ips.get(vm['id'], {}).keys(),
                private_ips=private_ips,
                driver=self,
                extra={'zoneid': vm['zoneid'], }
            )

            addrs = public_ips.get(vm['id'], {}).items()
            addrs = [CloudStackAddress(node, v, k) for k, v in addrs]
            node.extra['ip_addresses'] = addrs

            rules = []
            for addr in addrs:
                result = self._sync_request('listIpForwardingRules')
                for r in result.get('ipforwardingrule', []):
                    rule = CloudStackForwardingRule(node, r['id'], addr,
                                                    r['protocol'].upper(),
                                                    r['startport'],
                                                    r['endport'])
                    rules.append(rule)
            node.extra['ip_forwarding_rules'] = rules

            nodes.append(node)

        return nodes

    def list_sizes(self, location=None):
        szs = self._sync_request('listServiceOfferings')
        sizes = []
        for sz in szs['serviceoffering']:
            sizes.append(NodeSize(sz['id'], sz['name'], sz['memory'], 0, 0,
                                  0, self))
        return sizes

    def create_node(self, name, size, image, location=None, **kwargs):
        """
        @inherits: L{NodeDriver.create_node}
        @rtype: L{CloudStackNode}
        """
        extra_args = {}
        if location is None:
            location = self.list_locations()[0]

        if 'network_id' in kwargs:
            extra_args['networkids'] = network_id

        result = self._async_request(
            'deployVirtualMachine', name=name, displayname=name,
            serviceofferingid=size.id, templateid=image.id,
            zoneid=location.id, **extra_args
        )

        node = result['virtualmachine']

        return Node(
            id=node['id'],
            name=node['displayname'],
            state=self.NODE_STATE_MAP[node['state']],
            public_ips=[],
            private_ips=[],
            driver=self,
            extra={
                'zoneid': location.id,
                'ip_addresses': [],
                'forwarding_rules': [],
                }
        )

    def destroy_node(self, node):
        """
        @inherits: L{NodeDriver.reboot_node}
        @type node: L{CloudStackNode}
        """
        self._async_request('destroyVirtualMachine', id=node.id)
        return True

    def reboot_node(self, node):
        """
        @inherits: L{NodeDriver.reboot_node}
        @type node: L{CloudStackNode}
        """
        self._async_request('rebootVirtualMachine', id=node.id)
        return True

    def ex_list_disk_offerings(self):
        """Fetch a list of all available disk offerings.

        @rtype: C{list} of L{CloudStackDiskOffering}
        """

        diskOfferings = []

        diskOfferResponse = self._sync_request('listDiskOfferings')
        for diskOfferDict in diskOfferResponse.get('diskoffering', ()):
            diskOfferings.append(
                CloudStackDiskOffering(
                    id=diskOfferDict['id'],
                    name=diskOfferDict['name'],
                    size=diskOfferDict['disksize'],
                    customizable=diskOfferDict['iscustomized']))

        return diskOfferings

    def create_volume(self, size, name, location, snapshot=None):
        # TODO Add snapshot handling
        for diskOffering in self.ex_list_disk_offerings():
            if diskOffering.size == size or diskOffering.customizable:
                break
        else:
            raise LibcloudError(
                'Disk offering with size=%s not found' % size)

        extraParams = dict()
        if diskOffering.customizable:
            extraParams['size'] = size

        requestResult = self._async_request('createVolume',
                                            name=name,
                                            diskOfferingId=diskOffering.id,
                                            zoneId=location.id,
                                            **extraParams)

        volumeResponse = requestResult['volume']

        return StorageVolume(id=volumeResponse['id'],
                             name=name,
                             size=size,
                             driver=self,
                             extra=dict(name=volumeResponse['name']))

    def attach_volume(self, node, volume, device=None):
        """
        @inherits: L{NodeDriver.attach_volume}
        @type node: L{CloudStackNode}
        """
        # TODO Add handling for device name
        self._async_request('attachVolume', id=volume.id,
                            virtualMachineId=node.id)
        return True

    def detach_volume(self, volume):
        self._async_request('detachVolume', id=volume.id)
        return True

    def destroy_volume(self, volume):
        self._sync_request('deleteVolume', id=volume.id)
        return True

    def ex_allocate_public_ip(self, node):
        """
        "Allocate a public IP and bind it to a node.

        @param node: Node which should be used
        @type  node: L{CloudStackNode}

        @rtype: L{CloudStackAddress}
        """

        zoneid = node.extra['zoneid']
        addr = self._async_request('associateIpAddress', zoneid=zoneid)
        addr = addr['ipaddress']
        result = self._sync_request('enableStaticNat',
                                    virtualmachineid=node.id,
                                    ipaddressid=addr['id'])
        if result.get('success', '').lower() != 'true':
            return None

        node.public_ips.append(addr['ipaddress'])
        addr = CloudStackAddress(node, addr['id'], addr['ipaddress'])
        node.extra['ip_addresses'].append(addr)
        return addr

    def ex_release_public_ip(self, node, address):
        """
        Release a public IP.

        @param node: Node which should be used
        @type  node: L{CloudStackNode}

        @param address: CloudStackAddress which should be used
        @type  address: L{CloudStackAddress}

        @rtype: C{bool}
        """

        node.extra['ip_addresses'].remove(address)
        node.public_ips.remove(address.address)

        self._async_request('disableStaticNat', ipaddressid=address.id)
        self._async_request('disassociateIpAddress', id=address.id)
        return True

    def ex_add_ip_forwarding_rule(self, node, address, protocol,
                                  start_port, end_port=None):
        """
        "Add a NAT/firewall forwarding rule.

        @param node: Node which should be used
        @type  node: L{CloudStackNode}

        @param      address: CloudStackAddress which should be used
        @type       address: L{CloudStackAddress}

        @param      protocol: Protocol which should be used (TCP or UDP)
        @type       protocol: C{str}

        @param      start_port: Start port which should be used
        @type       start_port: C{int}

        @param end_port: End port which should be used
        @type end_port: C{int}

        @rtype: L{CloudStackForwardingRule}
        """

        protocol = protocol.upper()
        if protocol not in ('TCP', 'UDP'):
            return None

        args = {
            'ipaddressid': address.id,
            'protocol': protocol,
            'startport': int(start_port)
        }
        if end_port is not None:
            args['endport'] = int(end_port)

        result = self._async_request('createIpForwardingRule', **args)
        result = result['ipforwardingrule']
        rule = CloudStackForwardingRule(node, result['id'], address,
                                        protocol, start_port, end_port)
        node.extra['ip_forwarding_rules'].append(rule)
        return rule

    def ex_delete_ip_forwarding_rule(self, node, rule):
        """
        Remove a NAT/firewall forwarding rule.

        @param node: Node which should be used
        @type  node: L{CloudStackNode}

        @param rule: Forwarding rule which should be used
        @type rule: L{CloudStackForwardingRule}

        @rtype: C{bool}
        """

        node.extra['ip_forwarding_rules'].remove(rule)
        self._async_request('deleteIpForwardingRule', id=rule.id)
        return True

    def ex_register_iso(self, name, url, location=None, **kwargs):
        """
        Registers an existing ISO by URL.

        @param      name: Name which should be used
        @type       name: C{str}

        @param      url: Url should be used
        @type       url: C{str}

        @param      location: Location which should be used
        @type       location: L{NodeLocation}

        @rtype: C{str}
        """
        if location is None:
            location = self.list_locations()[0]

        extra_args = {}
        extra_args['bootable'] = kwargs.pop('bootable', False)
        if extra_args['bootable']:
            os_type_id = kwargs.pop('ostypeid', None)

            if not os_type_id:
                raise LibcloudError('If bootable=True, ostypeid is required!')

            extra_args['ostypeid'] = os_type_id

        return self._sync_request('registerIso',
                                  name=name,
                                  displaytext=name,
                                  url=url,
                                  zoneid=location.id,
                                  **extra_args)
