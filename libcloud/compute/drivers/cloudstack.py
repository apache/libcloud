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

from __future__ import with_statement

import os
import base64

from libcloud.utils.py3 import b

from libcloud.compute.providers import Provider
from libcloud.common.cloudstack import CloudStackDriverMixIn
from libcloud.compute.base import Node, NodeDriver, NodeImage, NodeLocation,\
    NodeSize, StorageVolume, is_private_subnet
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

    def ex_start(self):
        "Starts a stopped virtual machine"
        return self.driver.ex_start(self)

    def ex_stop(self):
        "Stops a running virtual machine"
        return self.driver.ex_stop(self)


class CloudStackAddress(object):
    "A public IP address."

    def __init__(self, id, address, driver):
        self.id = id
        self.address = address
        self.driver = driver

    def release(self):
        self.driver.ex_release_public_ip(self)

    def __str__(self):
        return self.address

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.id == other.id


class CloudStackIPForwardingRule(object):
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


class CloudStackPortForwardingRule(object):
    "A Port forwarding rule for Source NAT."

    def __init__(self, node, rule_id, address, protocol, public_port,
                 private_port, public_end_port=None, private_end_port=None):
        """
        A Port forwarding rule for Source NAT.

        @note: This is a non-standard extension API, and only works for EC2.

        :param      node: Node for rule
        :type       node: :class:`Node`

        :param      rule_id: Rule ID
        :type       rule_id: ``int``

        :param      address: External IP address
        :type       address: :class:`CloudStackAddress`

        :param      protocol: TCP/IP Protocol (TCP, UDP)
        :type       protocol: ``str``

        :param      public_port: External port for rule (or start port if
                                 public_end_port is also provided)
        :type       public_port: ``int``

        :param      private_port: Internal node port for rule (or start port if
                                  public_end_port is also provided)
        :type       private_port: ``int``

        :param      public_end_port: End of external port range
        :type       public_end_port: ``int``

        :param      private_end_port: End of internal port range
        :type       private_end_port: ``int``

        :rtype: :class:`CloudStackPortForwardingRule`
        """
        self.node = node
        self.id = rule_id
        self.address = address
        self.protocol = protocol
        self.public_port = public_port
        self.public_end_port = public_end_port
        self.private_port = private_port
        self.private_end_port = private_end_port

    def delete(self):
        self.node.ex_delete_port_forwarding_rule(self)

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


class CloudStackNetwork(object):
    """Class representing a CloudStack Network"""

    def __init__(self, displaytext, name, networkofferingid, id, zoneid,
                 driver):
        self.displaytext = displaytext
        self.name = name
        self.networkofferingid = networkofferingid
        self.id = id
        self.zoneid = zoneid
        self.driver = driver

    def __repr__(self):
        return (('<CloudStackNetwork: id=%s, displaytext=%s, name=%s, '
                 'networkofferingid=%s, zoneid=%s, driver%s>')
                % (self.id, self.displaytext, self.name,
                   self.networkofferingid, self.zoneid, self.driver.name))


class CloudStackNodeDriver(CloudStackDriverMixIn, NodeDriver):
    """Driver for the CloudStack API.

    :cvar host: The host where the API can be reached.
    :cvar path: The path where the API can be reached.
    :cvar async_poll_frequency: How often (in seconds) to poll for async
                                job completion.
    :type async_poll_frequency: ``int``"""

    name = 'CloudStack'
    api_name = 'cloudstack'
    website = 'http://cloudstack.org/'
    type = Provider.CLOUDSTACK

    features = {"create_node": ["generates_password", ]}

    NODE_STATE_MAP = {
        'Running': NodeState.RUNNING,
        'Starting': NodeState.REBOOTING,
        'Stopped': NodeState.TERMINATED,
        'Stopping': NodeState.TERMINATED,
        'Destroyed': NodeState.TERMINATED,
        'Expunging': NodeState.TERMINATED,
        'Error': NodeState.TERMINATED
    }

    def __init__(self, key, secret=None, secure=True, host=None,
                 path=None, port=None, *args, **kwargs):
        """
        @inherits: :class:`NodeDriver.__init__`

        :param    host: The host where the API can be reached. (required)
        :type     host: ``str``

        :param    path: The host where the API can be reached. (required)
        :type     path: ``str``
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
            images.append(NodeImage(
                id=img['id'],
                name=img['name'],
                driver=self.connection.driver,
                extra={
                    'hypervisor': img['hypervisor'],
                    'format': img['format'],
                    'os': img['ostypename'],
                    'displaytext': img['displaytext']}))
        return images

    def list_locations(self):
        """
        :rtype ``list`` of :class:`NodeLocation`
        """
        locs = self._sync_request('listZones')
        locations = []
        for loc in locs['zone']:
            locations.append(NodeLocation(loc['id'], loc['name'], 'AU', self))
        return locations

    def list_nodes(self):
        """
        @inherits: :class:`NodeDriver.list_nodes`
        :rtype: ``list`` of :class:`CloudStackNode`
        """
        vms = self._sync_request('listVirtualMachines')
        addrs = self._sync_request('listPublicIpAddresses')

        public_ips_map = {}
        for addr in addrs.get('publicipaddress', []):
            if 'virtualmachineid' not in addr:
                continue
            vm_id = str(addr['virtualmachineid'])
            if vm_id not in public_ips_map:
                public_ips_map[vm_id] = {}
            public_ips_map[vm_id][addr['ipaddress']] = addr['id']

        nodes = []

        for vm in vms.get('virtualmachine', []):
            state = self.NODE_STATE_MAP[vm['state']]

            public_ips = []
            private_ips = []

            for nic in vm['nic']:
                if 'ipaddress' in nic:
                    private_ips.append(nic['ipaddress'])

            public_ips = public_ips_map.get(vm['id'], {}).keys()
            public_ips = list(public_ips)
            public_ips.extend([ip for ip in private_ips
                              if not is_private_subnet(ip)])

            keypair, password, securitygroup = None, None, None
            if 'keypair' in vm.keys():
                keypair = vm['keypair']
            if 'password' in vm.keys():
                password = vm['password']
            if 'securitygroup' in vm.keys():
                securitygroup = [sg['name'] for sg in vm['securitygroup']]

            node = CloudStackNode(
                id=vm['id'],
                name=vm.get('displayname', None),
                state=state,
                public_ips=public_ips,
                private_ips=private_ips,
                driver=self,
                extra={'zoneid': vm['zoneid'],
                       'password': password,
                       'keyname': keypair,
                       'securitygroup': securitygroup,
                       'created': vm['created']
                       }
            )

            addresses = public_ips_map.get(vm['id'], {}).items()
            addresses = [CloudStackAddress(node, v, k) for k, v in addresses]
            node.extra['ip_addresses'] = addresses

            rules = []
            for addr in addresses:
                result = self._sync_request('listIpForwardingRules')
                for r in result.get('ipforwardingrule', []):
                    if str(r['virtualmachineid']) == node.id:
                        rule = CloudStackIPForwardingRule(node, r['id'],
                                                          addr,
                                                          r['protocol']
                                                          .upper(),
                                                          r['startport'],
                                                          r['endport'])
                        rules.append(rule)
            node.extra['ip_forwarding_rules'] = rules

            rules = []
            public_ips = self.ex_list_public_ips()
            result = self._sync_request('listPortForwardingRules')
            for r in result.get('portforwardingrule', []):
                if str(r['virtualmachineid']) == node.id:
                    addr = [a for a in public_ips if
                            a.address == r['ipaddress']]
                    rule = CloudStackPortForwardingRule(node, r['id'],
                                                        addr[0],
                                                        r['protocol'].upper(),
                                                        r['publicport'],
                                                        r['privateport'],
                                                        r['publicendport'],
                                                        r['privateendport'])
                    if not addr[0].address in node.public_ips:
                        node.public_ips.append(addr[0].address)
                    rules.append(rule)
            node.extra['port_forwarding_rules'] = rules

            nodes.append(node)

        return nodes

    def list_sizes(self, location=None):
        """
        :rtype ``list`` of :class:`NodeSize`
        """
        szs = self._sync_request('listServiceOfferings')
        sizes = []
        for sz in szs['serviceoffering']:
            sizes.append(NodeSize(sz['id'], sz['name'], sz['memory'], 0, 0,
                                  0, self))
        return sizes

    def create_node(self, **kwargs):
        """
        Create a new node

        @inherits: :class:`NodeDriver.create_node`

        :keyword    ex_keyname:  Name of existing keypair
        :type       ex_keyname:  ``str``

        :keyword    ex_userdata: String containing user data
        :type       ex_userdata: ``str``

        :keyword    networks: The server is launched into a set of Networks.
        :type       networks: :class:`CloudStackNetwork`

        :keyword    ex_security_groups: List of security groups to assign to
                                        the node
        :type       ex_security_groups: ``list`` of ``str``

        :rtype:     :class:`CloudStackNode`
        """

        server_params = self._create_args_to_params(None, **kwargs)

        node = self._async_request('deployVirtualMachine',
                                   **server_params)['virtualmachine']
        public_ips = []
        private_ips = []
        for nic in node['nic']:
            if is_private_subnet(nic['ipaddress']):
                private_ips.append(nic['ipaddress'])
            else:
                public_ips.append(nic['ipaddress'])

        keypair, password, securitygroup = None, None, None
        if 'keypair' in node.keys():
            keypair = node['keypair']
        if 'password' in node.keys():
            password = node['password']
        if 'securitygroup' in node.keys():
            securitygroup = [sg['name'] for sg in node['securitygroup']]

        return CloudStackNode(
            id=node['id'],
            name=node['displayname'],
            state=self.NODE_STATE_MAP[node['state']],
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self,
            extra={'zoneid': server_params['zoneid'],
                   'ip_addresses': [],
                   'ip_forwarding_rules': [],
                   'port_forwarding_rules': [],
                   'password': password,
                   'keyname': keypair,
                   'securitygroup': securitygroup,
                   'created': node['created']
                   }

        )

    def _create_args_to_params(self, node, **kwargs):
        server_params = {
            'name': kwargs.get('name'),
        }

        if 'name' in kwargs:
            server_params['displayname'] = kwargs.get('name')

        if 'size' in kwargs:
            server_params['serviceofferingid'] = kwargs.get('size').id

        if 'image' in kwargs:
            server_params['templateid'] = kwargs.get('image').id

        if 'location' in kwargs:
            server_params['zoneid'] = kwargs.get('location').id
        else:
            server_params['zoneid'] = self.list_locations()[0].id

        if 'ex_keyname' in kwargs:
            server_params['keypair'] = kwargs['ex_keyname']

        if 'ex_userdata' in kwargs:
            server_params['userdata'] = base64.b64encode(
                b(kwargs['ex_userdata'])).decode('ascii')

        if 'networks' in kwargs:
            networks = kwargs['networks']
            networks = ','.join([network.id for network in networks])
            server_params['networkids'] = networks

        if 'ex_security_groups' in kwargs:
            security_groups = kwargs['ex_security_groups']
            security_groups = ','.join(security_groups)
            server_params['securitygroupnames'] = security_groups

        return server_params

    def destroy_node(self, node):
        """
        @inherits: :class:`NodeDriver.reboot_node`
        :type node: :class:`CloudStackNode`

        :rtype: ``bool``
        """
        self._async_request('destroyVirtualMachine', id=node.id)
        return True

    def reboot_node(self, node):
        """
        @inherits: :class:`NodeDriver.reboot_node`
        :type node: :class:`CloudStackNode`

        :rtype: ``bool``
        """
        self._async_request('rebootVirtualMachine', id=node.id)
        return True

    def ex_start(self, node):
        """
        Starts/Resumes a stopped virtual machine

        :type node: :class:`CloudStackNode`

        :param id: The ID of the virtual machine (required)
        :type  id: ``str``

        :param hostid: destination Host ID to deploy the VM to
                       parameter available for root admin only
        :type  hostid: ``str``

        :rtype ``str``
        """
        res = self._async_request('startVirtualMachine', id=node.id)
        return res['virtualmachine']['state']

    def ex_stop(self, node):
        """
        Stops/Suspends a running virtual machine

        :type node: :class:`CloudStackNode`

        :param id: The ID of the virtual machine
        :type  id: ``str``

        :param forced: Force stop the VM
                       (vm is marked as Stopped even when command
                        fails to be send to the backend).
                       The caller knows the VM is stopped.
        :type  forced: ``bool``

        :rtype ``str``
        """
        res = self._async_request('stopVirtualMachine', id=node.id)
        return res['virtualmachine']['state']

    def ex_list_disk_offerings(self):
        """
        Fetch a list of all available disk offerings.

        :rtype: ``list`` of :class:`CloudStackDiskOffering`
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

    def ex_list_networks(self):
        """
        List the available networks

        :rtype ``list`` of :class:`CloudStackNetwork`
        """

        nets = self._sync_request('listNetworks')['network']

        networks = []
        for net in nets:
            networks.append(CloudStackNetwork(
                net['displaytext'],
                net['name'],
                net['networkofferingid'],
                net['id'],
                net['zoneid'],
                self))

        return networks

    def create_volume(self, size, name, location=None, snapshot=None):
        """
        Creates a data volume
        Defaults to the first location
        """
        for diskOffering in self.ex_list_disk_offerings():
            if diskOffering.size == size or diskOffering.customizable:
                break
        else:
            raise LibcloudError(
                'Disk offering with size=%s not found' % size)

        extraParams = dict()
        if diskOffering.customizable:
            extraParams['size'] = size

        if location is None:
            location = self.list_locations()[0]

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

    def destroy_volume(self, volume):
        """
        :rtype: ``bool``
        """
        self._sync_request('deleteVolume', id=volume.id)
        return True

    def attach_volume(self, node, volume, device=None):
        """
        @inherits: :class:`NodeDriver.attach_volume`
        :type node: :class:`CloudStackNode`

        :rtype: ``bool``
        """
        # TODO Add handling for device name
        self._async_request('attachVolume', id=volume.id,
                            virtualMachineId=node.id)
        return True

    def detach_volume(self, volume):
        """
        :rtype: ``bool``
        """
        self._async_request('detachVolume', id=volume.id)
        return True

    def list_volumes(self, node=None):
        """
        List all volumes

        :param node: Only return volumes for the provided node.
        :type node: :class:`CloudStackNode`

        :rtype: ``list`` of :class:`StorageVolume`
        """
        if node:
            volumes = self._sync_request('listVolumes',
                                         virtualmachineid=node.id)
        else:
            volumes = self._sync_request('listVolumes')

        list_volumes = []
        for vol in volumes['volume']:
            list_volumes.append(StorageVolume(id=vol['id'],
                                name=vol['name'],
                                size=vol['size'],
                                driver=self))
        return list_volumes

    def ex_list_public_ips(self):
        """
        Lists all Public IP Addresses.

        :rtype: ``list`` of :class:`CloudStackAddress`
        """
        ips = []

        res = self._sync_request('listPublicIpAddresses')

        # Workaround for basic zones
        if not res:
            return ips

        for ip in res['publicipaddress']:
            ips.append(CloudStackAddress(ip['id'], ip['ipaddress'], self))
        return ips

    def ex_allocate_public_ip(self, location=None):
        """
        Allocate a public IP.

        :param location: Zone
        :type  location: :class:`NodeLocation`

        :rtype: :class:`CloudStackAddress`
        """
        if location is None:
            location = self.list_locations()[0]

        addr = self._async_request('associateIpAddress', zoneid=location.id)
        addr = addr['ipaddress']
        addr = CloudStackAddress(addr['id'], addr['ipaddress'], self)
        return addr

    def ex_release_public_ip(self, address):
        """
        Release a public IP.

        :param address: CloudStackAddress which should be used
        :type  address: :class:`CloudStackAddress`

        :rtype: ``bool``
        """
        res = self._async_request('disassociateIpAddress', id=address.id)
        return res['success']

    def ex_list_port_forwarding_rules(self):
        """
        Lists all Port Forwarding Rules

        :rtype: ``list`` of :class:`CloudStackPortForwardingRule`
        """
        rules = []
        result = self._sync_request('listPortForwardingRules')
        if result != {}:
            public_ips = self.ex_list_public_ips()
            nodes = self.list_nodes()
            for rule in result['portforwardingrule']:
                node = [n for n in nodes
                        if n.id == str(rule['virtualmachineid'])]
                addr = [a for a in public_ips if
                        a.address == rule['ipaddress']]
                rules.append(CloudStackPortForwardingRule
                             (node[0],
                              rule['id'],
                              addr[0],
                              rule['protocol'],
                              rule['publicport'],
                              rule['privateport'],
                              rule['publicendport'],
                              rule['privateendport']))

        return rules

    def ex_create_port_forwarding_rule(self, address, private_port,
                                       public_port, protocol, node,
                                       public_end_port=None,
                                       private_end_port=None,
                                       openfirewall=True):
        """
        Creates a Port Forwarding Rule, used for Source NAT

        :param  address: IP address of the Source NAT
        :type   address: :class:`CloudStackAddress`

        :param  private_port: Port of the virtual machine
        :type   private_port: ``int``

        :param  protocol: Protocol of the rule
        :type   protocol: ``str``

        :param  public_port: Public port on the Source NAT address
        :type   public_port: ``int``

        :param  node: The virtual machine
        :type   node: :class:`CloudStackNode`

        :rtype: :class:`CloudStackPortForwardingRule`
        """
        args = {
            'ipaddressid': address.id,
            'protocol': protocol,
            'privateport': int(private_port),
            'publicport': int(public_port),
            'virtualmachineid': node.id,
            'openfirewall': openfirewall
        }
        if public_end_port:
            args['publicendport'] = int(public_end_port)
        if private_end_port:
            args['privateendport'] = int(private_end_port)

        result = self._async_request('createPortForwardingRule', **args)
        rule = CloudStackPortForwardingRule(node,
                                            result['portforwardingrule']
                                            ['id'],
                                            address,
                                            protocol,
                                            public_port,
                                            private_port,
                                            public_end_port,
                                            private_end_port)
        node.extra['port_forwarding_rules'].append(rule)
        node.public_ips.append(address.address)
        return rule

    def ex_delete_port_forwarding_rule(self, node, rule):
        """
        Remove a Port forwarding rule.

        :param node: Node used in the rule
        :type  node: :class:`CloudStackNode`

        :param rule: Forwarding rule which should be used
        :type  rule: :class:`CloudStackPortForwardingRule`

        :rtype: ``bool``
        """

        node.extra['port_forwarding_rules'].remove(rule)
        node.public_ips.remove(rule.address.address)
        res = self._async_request('deletePortForwardingRule', id=rule.id)
        return res['success']

    def ex_add_ip_forwarding_rule(self, node, address, protocol,
                                  start_port, end_port=None):
        """
        "Add a NAT/firewall forwarding rule.

        :param      node: Node which should be used
        :type       node: :class:`CloudStackNode`

        :param      address: CloudStackAddress which should be used
        :type       address: :class:`CloudStackAddress`

        :param      protocol: Protocol which should be used (TCP or UDP)
        :type       protocol: ``str``

        :param      start_port: Start port which should be used
        :type       start_port: ``int``

        :param      end_port: End port which should be used
        :type       end_port: ``int``

        :rtype:     :class:`CloudStackForwardingRule`
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
        rule = CloudStackIPForwardingRule(node, result['id'], address,
                                          protocol, start_port, end_port)
        node.extra['ip_forwarding_rules'].append(rule)
        return rule

    def ex_delete_ip_forwarding_rule(self, node, rule):
        """
        Remove a NAT/firewall forwarding rule.

        :param node: Node which should be used
        :type  node: :class:`CloudStackNode`

        :param rule: Forwarding rule which should be used
        :type  rule: :class:`CloudStackForwardingRule`

        :rtype: ``bool``
        """

        node.extra['ip_forwarding_rules'].remove(rule)
        self._async_request('deleteIpForwardingRule', id=rule.id)
        return True

    def ex_list_keypairs(self, **kwargs):
        """
        List Registered SSH Key Pairs

        :param     projectid: list objects by project
        :type      projectid: ``str``

        :param     page: The page to list the keypairs from
        :type      page: ``int``

        :param     keyword: List by keyword
        :type      keyword: ``str``

        :param     listall: If set to false, list only resources
                            belonging to the command's caller;
                            if set to true - list resources that
                            the caller is authorized to see.
                            Default value is false

        :type      listall: ``bool``

        :param     pagesize: The number of results per page
        :type      pagesize: ``int``

        :param     account: List resources by account.
                            Must be used with the domainId parameter
        :type      account: ``str``

        :param     isrecursive: Defaults to false, but if true,
                                lists all resources from
                                the parent specified by the
                                domainId till leaves.
        :type      isrecursive: ``bool``

        :param     fingerprint: A public key fingerprint to look for
        :type      fingerprint: ``str``

        :param     name: A key pair name to look for
        :type      name: ``str``

        :param     domainid: List only resources belonging to
                                     the domain specified
        :type      domainid: ``str``

        :return:   A list of keypair dictionaries
        :rtype:   ``list`` of ``dict``
        """

        extra_args = kwargs.copy()
        res = self._sync_request('listSSHKeyPairs', **extra_args)
        keypairs = res.get('sshkeypair', [])
        return keypairs

    def ex_create_keypair(self, name, **kwargs):
        """
        Creates a SSH KeyPair, returns fingerprint and private key

        :param     name: Name of the keypair (required)
        :type      name: ``str``

        :param     projectid: An optional project for the ssh key
        :type      projectid: ``str``

        :param     domainid: An optional domainId for the ssh key.
                             If the account parameter is used,
                             domainId must also be used.
        :type      domainid: ``str``

        :param     account: An optional account for the ssh key.
                            Must be used with domainId.
        :type      account: ``str``

        :return:   A keypair dictionary
        :rtype:    ``dict``
        """
        extra_args = kwargs.copy()

        for keypair in self.ex_list_keypairs():
            if keypair['name'] == name:
                raise LibcloudError('SSH KeyPair with name=%s already exists'
                                    % (name))

        res = self._sync_request('createSSHKeyPair', name=name, **extra_args)
        return res['keypair']

    def ex_delete_keypair(self, keypair, **kwargs):
        """
        Deletes an existing SSH KeyPair

        :param     keypair: Name of the keypair (required)
        :type      keypair: ``str``

        :param     projectid: The project associated with keypair
        :type      projectid: ``str``

        :param     domainid : The domain ID associated with the keypair
        :type      domainid: ``str``

        :param     account : The account associated with the keypair.
                             Must be used with the domainId parameter.
        :type      account: ``str``

        :return:   True of False based on success of Keypair deletion
        :rtype:    ``bool``
        """

        extra_args = kwargs.copy()

        res = self._sync_request('deleteSSHKeyPair', name=keypair,
                                 **extra_args)
        return res['success']

    def ex_import_keypair_from_string(self, name, key_material):
        """
        Imports a new public key where the public key is passed in as a string

        :param     name: The name of the public key to import.
        :type      name: ``str``

        :param     key_material: The contents of a public key file.
        :type      key_material: ``str``

        :rtype: ``dict``
        """
        res = self._sync_request('registerSSHKeyPair', name=name,
                                 publickey=key_material)
        return {
            'keyName': res['keypair']['name'],
            'keyFingerprint': res['keypair']['fingerprint']
        }

    def ex_import_keypair(self, name, keyfile):
        """
        Imports a new public key where the public key is passed via a filename

        :param     name: The name of the public key to import.
        :type      name: ``str``

        :param     keyfile: The filename with path of the public key to import.
        :type      keyfile: ``str``

        :rtype: ``dict``
        """
        with open(os.path.expanduser(keyfile)) as fh:
            content = fh.read()
        return self.ex_import_keypair_from_string(name, content)

    def ex_list_security_groups(self, **kwargs):
        """
        Lists Security Groups

        :param domainid: List only resources belonging to the domain specified
        :type  domainid: ``str``

        :param account: List resources by account. Must be used with
                                                   the domainId parameter.
        :type  account: ``str``

        :param listall: If set to false, list only resources belonging to
                                         the command's caller; if set to true
                                         list resources that the caller is
                                         authorized to see.
                                         Default value is false
        :type  listall: ``bool``

        :param pagesize: Number of entries per page
        :type  pagesize: ``int``

        :param keyword: List by keyword
        :type  keyword: ``str``

        :param tags: List resources by tags (key/value pairs)
        :type  tags: ``dict``

        :param id: list the security group by the id provided
        :type  id: ``str``

        :param securitygroupname: lists security groups by name
        :type  securitygroupname: ``str``

        :param virtualmachineid: lists security groups by virtual machine id
        :type  virtualmachineid: ``str``

        :param projectid: list objects by project
        :type  projectid: ``str``

        :param isrecursive: (boolean) defaults to false, but if true,
                                      lists all resources from the parent
                                      specified by the domainId till leaves.
        :type  isrecursive: ``bool``

        :param page: (integer)
        :type  page: ``int``

        :rtype ``list``
        """
        extra_args = kwargs
        res = self._sync_request('listSecurityGroups', **extra_args)

        security_groups = res.get('securitygroup', [])
        return security_groups

    def ex_create_security_group(self, name, **kwargs):
        """
        Creates a new Security Group

        :param name: name of the security group (required)
        :type  name: ``str``

        :param account: An optional account for the security group.
                        Must be used with domainId.
        :type  account: ``str``

        :param domainid: An optional domainId for the security group.
                         If the account parameter is used,
                         domainId must also be used.
        :type  domainid: ``str``

        :param description: The description of the security group
        :type  description: ``str``

        :param projectid: Deploy vm for the project
        :type  projectid: ``str``

        :rtype: ``dict``
        """

        extra_args = kwargs.copy()

        for sg in self.ex_list_security_groups():
            if name in sg['name']:
                raise LibcloudError('This Security Group name already exists')

        return self._sync_request('createSecurityGroup',
                                  name=name, **extra_args)['securitygroup']

    def ex_delete_security_group(self, name):
        """
        Deletes a given Security Group

        :param domainid: The domain ID of account owning
                         the security group
        :type  domainid: ``str``

        :param id: The ID of the security group.
                   Mutually exclusive with name parameter
        :type  id: ``str``

        :param name: The ID of the security group.
                     Mutually exclusive with id parameter
        :type name: ``str``

        :param account: The account of the security group.
                        Must be specified with domain ID
        :type  account: ``str``

        :param projectid:  The project of the security group
        :type  projectid:  ``str``

        :rtype: ``bool``
        """

        return self._sync_request('deleteSecurityGroup', name=name)['success']

    def ex_authorize_security_group_ingress(self, securitygroupname,
                                            protocol, cidrlist, startport,
                                            endport=None):
        """
        Creates a new Security Group Ingress rule

        :param domainid: An optional domainId for the security group.
                         If the account parameter is used,
                         domainId must also be used.
        :type domainid: ``str``

        :param startport: Start port for this ingress rule
        :type  startport: ``int``

        :param securitygroupid: The ID of the security group.
                                Mutually exclusive with securityGroupName
                                parameter
        :type  securitygroupid: ``str``

        :param cidrlist: The cidr list associated
        :type  cidrlist: ``list``

        :param usersecuritygrouplist: user to security group mapping
        :type  usersecuritygrouplist: ``dict``

        :param securitygroupname: The name of the security group.
                                  Mutually exclusive with
                                  securityGroupName parameter
        :type  securitygroupname: ``str``

        :param account: An optional account for the security group.
                        Must be used with domainId.
        :type  account: ``str``

        :param icmpcode: Error code for this icmp message
        :type  icmpcode: ``int``

        :param protocol: TCP is default. UDP is the other supported protocol
        :type  protocol: ``str``

        :param icmptype: type of the icmp message being sent
        :type  icmptype: ``int``

        :param projectid: An optional project of the security group
        :type  projectid: ``str``

        :param endport: end port for this ingress rule
        :type  endport: ``int``

        :rtype: ``list``
        """

        protocol = protocol.upper()
        if protocol not in ('TCP', 'ICMP'):
            raise LibcloudError('Only TCP and ICMP are allowed')

        args = {
            'securitygroupname': securitygroupname,
            'protocol': protocol,
            'startport': int(startport),
            'cidrlist': cidrlist
        }
        if endport is None:
            args['endport'] = int(startport)

        return self._async_request('authorizeSecurityGroupIngress',
                                   **args)['securitygroup']

    def ex_register_iso(self, name, url, location=None, **kwargs):
        """
        Registers an existing ISO by URL.

        :param      name: Name which should be used
        :type       name: ``str``

        :param      url: Url should be used
        :type       url: ``str``

        :param      location: Location which should be used
        :type       location: :class:`NodeLocation`

        :rtype: ``str``
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
