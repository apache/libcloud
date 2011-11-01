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
from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver, CloudStackAddress, CloudStackForwardingRule
from libcloud.common.types import MalformedResponseError


class CloudComForwardingRule(CloudStackForwardingRule):

    def __init__(self, node, id, address, protocol, public_port, private_port, public_end_port=None, private_end_port=None, state=None):
        self.node = node
        self.id = id
        self.address = address
        self.protocol = protocol
        self.public_port = public_port
        self.public_end_port = public_end_port
        self.private_port = private_port
        self.private_end_port = private_end_port
        self.state = state


class CloudComNodeDriver(CloudStackNodeDriver):
    "Driver for Ninefold's Compute platform."

    path = '/client/api'

    type = Provider.CLOUDCOM
    name = 'CloudCom'
    
    api_name = 'cloudcom'
    
    def __init__(self, key, secret=None, secure=False, host=None, port=None):
        host = host or self.host
        super(CloudComNodeDriver, self).__init__(key, secret, secure, host, port)

    def create_node(self, size, image, location=None, **kwargs):
        if location is None:
            location = self.list_locations()[0]
        network_id = kwargs.pop('network_id', None)
        if network_id is None:
            networks = self._sync_request('listNetworks')
            network_id = networks['network'][0]['id']
        result = self._async_request('deployVirtualMachine',
                                     serviceOfferingId=size.id,
                                     templateId=image.id,
                                     zoneId=location.id,
                                     networkIds=network_id,
                                     **kwargs
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
                   'ip_forwarding_rules': [],
                   'password': node.get('password', ''),
                   }
                )
    
    
    def ex_add_ip_forwarding_rule(self, node, address, protocol,
                                  public_port, private_port,
                                  public_end_port=None, private_end_port=None, openfirewall=True):
        "Add a NAT/firewall forwarding rule."

        protocol = protocol.upper()
        if protocol not in ('TCP', 'UDP'):
            return None

        args = {
            'ipaddressid': address.id,
            'protocol': protocol,
            'publicport': int(public_port),
            'privateport': int(private_port),
            'virtualmachineid': node.id,
            'openfirewall': openfirewall,
        }

        if public_end_port is not None:
            args['publicendport'] = int(public_end_port)
        if private_end_port is not None:
            args['privateendport'] = int(private_end_port)

        result = self._async_request('createPortForwardingRule', **args)
        result = result['portforwardingrule']
        adresses = self.ex_list_public_ip()
        rule = CloudComForwardingRule(node=node,
                                      id=result['id'],
                                      address=filter(lambda addr: addr.address == result['ipaddress'], adresses)[0],
                                      protocol=result['protocol'],
                                      public_port=result['publicport'],
                                      private_port=result['privateport'],
                                      public_end_port=result.get('publicendport', None),
                                      private_end_port=result.get('privateendport', None),
                                      state=result['state']
                                    )
        node.extra['ip_forwarding_rules'].append(rule)
        node.public_ip.append(result['ipaddress'])
        return rule
    
    
    def ex_list_public_ip(self):
        addresses = self._sync_request('listPublicIpAddresses')
        return [CloudStackAddress(None, addr['id'], addr['ipaddress']) for addr in addresses['publicipaddress']]


    def ex_list_ip_forwarding_rule(self):
        rules = self._sync_request('listPortForwardingRules')['portforwardingrule']
        adresses = self.ex_list_public_ip()
        nodes = self.list_nodes()
        return [CloudComForwardingRule(node=filter(lambda node: int(node.id) == rule['virtualmachineid'], nodes)[0],
                                      id=rule['id'],
                                      address=filter(lambda addr: addr.address == rule['ipaddress'], adresses)[0],
                                      protocol=rule['protocol'],
                                      public_port=rule['publicport'],
                                      private_port=rule['privateport'],
                                      public_end_port=rule.get('publicendport', None),
                                      private_end_port=rule.get('privateendport', None),
                                      state=rule['state']
                                        ) for rule in rules]
    
    def ex_create_keypair(self, name):
        keypair = self._sync_request('createSSHKeyPair', name=name)
        return keypair['keypair']
    
    def ex_list_keypair(self, name=None):
        if name is None:
            keypair_list = self._sync_request('listSSHKeyPairs')
        else:
            keypair_list = self._sync_request('listSSHKeyPairs', name=name)
        return keypair_list['keypair']
    
    def ex_import_keypair(self, name, publickey):
        keypair = self._sync_request('registerSSHKeyPair', name=name, publickey=publickey)
        return keypair['keypair']
    
    def ex_delete_keypair(self, name):
        keypair = self._sync_request('deleteSSHKeyPair', name=name)
        return keypair['success']
