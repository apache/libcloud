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

""" OpenStack driver """

import httplib
import json
import urlparse
from libcloud.common.base import Response, ConnectionUserAndKey
from libcloud.common.types import MalformedResponseError, InvalidCredsError
from libcloud.compute.types import NodeState, Provider
from libcloud.compute.base import NodeDriver, Node, NodeLocation
from libcloud.compute.base import NodeSize, NodeImage

class OpenStackResponse1_1(Response):

    @staticmethod
    def is_success(status):
        """
         GET /servers /servers/detail code 200 203
         POST /servers code 202
         GET /servers/id code 200 203
         
         GET /servers/id/ips coe 200 203
         GET /servers/id/ips/networkID code 200 203

         GET /flavors /flavors/detail code 200 203
         GET /flavors/id code 200 203

         GET /images /images/detail code 202 203
         POST /images/id code 202
         GET /images/id code 200, 203
         DELETE /images/id code 204
        """
        return int(status) in (200, 202, 203, 204)

    def success(self):
        return OpenStackResponse1_1.is_success(self.status)

    def parse_body(self):
        if not self.body:
            return None
        try:
            body = json.loads(self.body)
        except:
            raise MalformedResponseError("Failed to parse JSON", body=self.body, driver=OpenStackNodeDriver1_1)
        return body

    def parse_error(self):
        """Used in to form message for exception to raise in case self.status is not OK"""
        #TODO get test fixture and implement error message retrieval from json
        return '%s %s' % (self.status, self.error)

class OpenStackConnection1_1(ConnectionUserAndKey):
    """ Connection class for the OpenStack driver """
    
    responseCls = OpenStackResponse1_1

    def __init__(self, user_name, api_key, url, secure):
        self.server_url = url
        r = urlparse.urlparse(url)
        self.api_version = r.path # here we rely on structure http://hostname:port/v1.0 so path=path_version
        self.auth_token = None
        super(OpenStackConnection1_1, self).__init__(user_id=user_name, key=api_key, secure=secure, host=r.hostname, port=r.port)

    def encode_data(self, data): #TODO implement and parametrise body encoding
        return data

    def request(self, action, params=None, data='', headers=None, method='GET', raw=False):

        if not self.auth_token:#TODO deal with token expiration
            self._auth()
        
        if not headers:
            headers = {}
        if not params:
            params = {}
        action = self.server_url + action
        if method in ("POST", "PUT"):
            headers = {'Content-Type': 'application/json'}#TODO parametrise Content-Type
            #TODO check what about token cache-expire in OS
        return super(OpenStackConnection1_1, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers
        )

    def add_default_headers(self, headers):
        headers['X-Auth-Token'] = self.auth_token
        #TODO add parametrised accept
        headers['Accept'] = 'application/json'
        return headers

    def _auth(self):
        """ OpenStack needs first to get an authentication token """
        
        self.connection.request(
            method='GET',
            url=self.api_version,#TODO get version from access point directly?
            headers={'X-Auth-User': self.user_id, 'X-Auth-Key': self.key}
        )

        resp = self.connection.getresponse()

        if resp.status != httplib.NO_CONTENT:
            raise InvalidCredsError()

        headers = dict(resp.getheaders())

        try:
            self.server_url = headers['x-server-management-url']
            self.auth_token = headers['x-auth-token']
        except KeyError:
            raise InvalidCredsError()
        
class OpenStackNodeDriver1_1(NodeDriver):
    """ OpenStack node driver. """
    connectionCls = OpenStackConnection1_1
    name = 'OpenStack1.1'
    type = Provider.OPENSTACK1_1

    features = {"create_node": ["generates_password"]}

    NODE_STATE_MAP = { 'BUILD': NodeState.PENDING,
                       'REBUILD': NodeState.PENDING,
                       'ACTIVE': NodeState.RUNNING,
                       'SUSPENDED': NodeState.TERMINATED,
                       'QUEUE_RESIZE': NodeState.PENDING,
                       'PREP_RESIZE': NodeState.PENDING,
                       'VERIFY_RESIZE': NodeState.RUNNING,
                       'RESIZE': NodeState.PENDING,
                       'PASSWORD': NodeState.PENDING,
                       'RESCUE': NodeState.PENDING,
                       'REBOOT': NodeState.REBOOTING,
                       'HARD_REBOOT': NodeState.REBOOTING,
                       'DELETE_IP': NodeState.PENDING,
                       'UNKNOWN': NodeState.UNKNOWN}

    def __init__(self, user_name, api_key, url, secure=False):
        """
        @keyword    user_name:    NOVA_USERNAME as reported by OpenStack
        @type       user_name:    str

        @keyword    api_key: NOVA_API_KEY as reported by OpenStack
        @type       api_key: str

        @keyword    url: NOVA_URL as reported by OpenStack.
        @type       url: str

        @keyword    secure: use HTTPS or HTTP. Note: currently only HTTP
        @type       secure: bool
        """
        self.connection = OpenStackConnection1_1(user_name=user_name, api_key=api_key, url=url, secure= secure)
        self.connection.driver = self
        self.connection.connect()

    def list_locations(self):
        """Lists available locations. So far there is no public locations so we return fake location """
        return [NodeLocation(id=0, name='OpenStack is private cloud', country='NoCountry', driver=self)]

    def list_sizes(self, location=None):
        flavors_dict = self.connection.request('/flavors/detail').object
        try:
            flavors = flavors_dict['flavors']
            values = flavors
        except KeyError:
            raise MalformedResponseError(value='no flavors-values clause', body=flavors_dict, driver=self)
        return [ self._to_size(value) for value in values ]

    def ex_list_flavors(self):
        self.list_sizes()

    def _to_size(self, el):
        s = OpenstackNodeSize1_1(id=el.get('id'),
                     ram=int(el.get('ram')),
                     disk=int(el.get('disk')),
                     name=el.get('name'),
                     price=None,
                     bandwidth=None,
                     driver=self.connection.driver,
                     links=el.get('links'))
        return s
    
    def list_images(self, location=None):
        images_dict = self.connection.request('/images/detail').object
        try:
            images = images_dict['images']
        except KeyError:
            raise MalformedResponseError(value='no images clause', body=images_dict, driver=self)
        return [ self._to_image(image) for image in images if image.get('status') == 'ACTIVE' ]

    def _to_image(self, el):
        i = NodeImage(id=el.get('id'),
                     name=el.get('name'),
                     driver=self.connection.driver,
                     extra={'updated': el.get('updated'), 'links': el.get('links')})
        return i

    def list_nodes(self):
        servers_dict = self.connection.request('/servers/detail').object
        try:
            servers = servers_dict['servers']
            values = servers
        except KeyError:
            raise MalformedResponseError(value='in list_nodes: no servers-values clause', body=servers_dict, driver=self)
        return [ self._to_node(value) for value in values ]

    def ex_list_servers(self):
        self.list_nodes()

    def create_node(self, **kwargs):
        """Create a new node

        See L{NodeDriver.create_node} for more keyword args.
        @keyword    ex_metadata: Key/Value metadata to associate with a node
        @type       ex_metadata: C{dict}

        @keyword    ex_files:   List of personalities => File contents to create on the node
        @type       ex_files:   C{dict}
        """
        name = kwargs['name']
        node_image = kwargs['image']
        node_size = kwargs['size']
        ex_metadata = kwargs.get('ex_metadata')
        ex_personality = kwargs.get('ex_personality')

        flavorRef = node_size.links[0]['href']
        imageRef = node_image.extra['links'][0]['href']
        request = {'server': {'name': name, 'flavorRef': flavorRef, 'imageRef': imageRef}}
        if ex_metadata:
            request['server']['metadata']=ex_metadata
        if ex_personality:
            request['server']['personality']=ex_personality

        data=json.dumps(request)
        resp = self.connection.request("/servers", method='POST', data=data)
        try:
            server_dict = resp.object['server']
        except KeyError:
            raise MalformedResponseError(value='no server clause', body=resp.object, driver=self)
        return self._to_node(server_dict=server_dict)

    def _to_node(self, server_dict):
        """ Here we expect a dictionary which is under the clause server or servers in /servers or /servers/detail """
        ips = OpenStackIps1_1(server_dict['addresses'])

        n = Node(id=server_dict.get('id'),
                 name=server_dict.get('name'),
                 state=self.NODE_STATE_MAP.get(server_dict.get('status'), NodeState.UNKNOWN),
                 public_ip=ips.public_ipv4, #list of addresses
                 private_ip=ips.private_ipv4, #list of addresses
                 driver=self.connection.driver,
                 extra={
                    'adminPass': server_dict.get('adminPass'),
                    'affinityId': server_dict.get('affinityId'),
                    'created': server_dict.get('created'),
                    'flavorRef': server_dict.get('flavorRef'),
                    'hostId': server_dict.get('hostId'),
                    'id': server_dict.get('id'),
                    'imageRef': server_dict.get('imageRef'),
                    'links':  server_dict.get('links'),
                    'metadata': server_dict.get('metadata'),
                    'progress': server_dict.get('progress')
                 })
        return n

    def destroy_node(self, node):
        uri = '/servers/%s' % node.id
        resp = self.connection.request(uri, method='DELETE')
        return OpenStackResponse1_1.is_success(resp.status)

    def reboot_node(self, node):
        return self._reboot_node(node, reboot_type='HARD')

    def ex_soft_reboot_node(self, node):
        return self._reboot_node(node, reboot_type='SOFT')

    def ex_hard_reboot_node(self, node):
        return self._reboot_node(node, reboot_type='HARD')
        
    def _reboot_node(self, node, reboot_type):
        resp = self._node_action(node, json.dumps({'reboot': {'type': reboot_type}}))
        return resp.status == 202

    def _node_action(self, node, body):
        uri = '/servers/%s/action' % node.id
        resp = self.connection.request(uri, method='POST', data=body)
        return resp

    def ex_rebuild(self, node_id, image_id): #TODO support real data
        resp = self.connection.request("/servers/%s/action" % node_id,
                                       method='POST',
                                       data='')
        return resp.status == 202

    def ex_get_node_details(self, node_id):
        uri = '/servers/%s' % node_id
        resp = self.connection.request(uri, method='GET')
        if resp.status == 404:
            return None
        return self._to_node(resp.object)

    def ex_limits(self):
        resp = self.connection.request('/limits', method='GET')
        return resp.object['limits']

class OpenStackIps1_1(object):
    """
        Contains the list of public and private IPs
        @keyword    ip_list: IPs with the structure C{dict} {'values'}: [{'version':4, 'addr':''}, ], 'id' : 'public'}
        @type       ip_list: C{list}
    """
    public_ipv4 = []
    private_ipv4 = []
    public_ipv6 = []
    private_ipv6 = []
    def __init__(self, ip_list):
        self._separate_by_protocol(ip_list['public'], self.public_ipv4, self.public_ipv6)
        self._separate_by_protocol(ip_list['private'], self.private_ipv4, self.private_ipv6)

    def _separate_by_protocol(self, input_list, out_list_v4, out_list_v6):
        """ convert IP dictionary to tuple of the structure """
        for ip in input_list:
            if ip['version'] == 4:
                out_list_v4.append(ip['addr'])
            if ip['version'] == 6:
                out_list_v6.append(ip['addr'])

class OpenstackNodeSize1_1(NodeSize):
    """ extends base NodeSize with links section """
    links = []
    def __init__(self, id, name, ram, disk, bandwidth, price, driver, links):
        super(OpenstackNodeSize1_1, self).__init__(id, name, ram, disk, bandwidth, price, driver)
        self.links = links