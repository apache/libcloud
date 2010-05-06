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
Rackspace driver
"""
from libcloud.types import NodeState, InvalidCredsException, Provider
from libcloud.base import ConnectionUserAndKey, Response, NodeDriver, Node
from libcloud.base import NodeSize, NodeImage, NodeLocation
import os

import base64
import urlparse

from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

NAMESPACE = 'http://docs.rackspacecloud.com/servers/api/v1.0'

class RackspaceResponse(Response):

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        # TODO: fixup, Rackspace only uses response codes really!
        try:
            object = ET.XML(self.body)
            text = "; ".join([ err.text or ''
                               for err in
                               object.getiterator()
                               if err.text])
        except ExpatError:
            text = self.body
        return '%s %s %s' % (self.status, self.error, text)


class RackspaceConnection(ConnectionUserAndKey):
    """
    Connection class for the Rackspace driver
    """

    api_version = 'v1.0'
    auth_host = 'auth.api.rackspacecloud.com'
    responseCls = RackspaceResponse

    def __init__(self, user_id, key, secure=True):
        self.__host = None
        self.path = None
        self.token = None
        super(RackspaceConnection, self).__init__(user_id, key, secure)

    def add_default_headers(self, headers):
        headers['X-Auth-Token'] = self.token;
        headers['Accept'] = 'application/xml'
        return headers

    @property
    def host(self):
        """
        Rackspace uses a separate host for API calls which is only provided
        after an initial authentication request. If we haven't made that
        request yet, do it here. Otherwise, just return the management host.

        TODO: Fixup for when our token expires (!!!)
        """
        if not self.__host:
            # Initial connection used for authentication
            conn = self.conn_classes[self.secure](self.auth_host, self.port[self.secure])
            conn.request(
                method='GET',
                url='/%s' % self.api_version,
                headers={
                    'X-Auth-User': self.user_id,
                    'X-Auth-Key': self.key
                }
            )
            resp = conn.getresponse()
            headers = dict(resp.getheaders())
            try:
                self.token = headers['x-auth-token']
                endpoint = headers['x-server-management-url']
            except KeyError:
                raise InvalidCredsException()

            scheme, server, self.path, param, query, fragment = (
                urlparse.urlparse(endpoint)
            )
            if scheme is "https" and self.secure is not 1:
                # TODO: Custom exception (?)
                raise InvalidCredsException()

            # Set host to where we want to make further requests to;
            # close auth conn
            self.__host = server
            conn.close()

        return self.__host

    def request(self, action, params=None, data='', headers=None, method='GET'):
        if not headers:
            headers = {}
        if not params:
            params = {}
        # Due to first-run authentication request, we may not have a path
        if self.path:
            action = self.path + action
        if method == "POST":
            headers = {'Content-Type': 'application/xml; charset=UTF-8'}
        if method == "GET":
            params['cache-busting'] = os.urandom(8).encode('hex')
        return super(RackspaceConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers
        )


class RackspaceNodeDriver(NodeDriver):
    """
    Rackspace node driver.

    Extra node attributes:
        - password: root password, available after create.
        - hostId: represents the host your cloud server runs on
        - imageId: id of image
        - flavorId: id of flavor
    """
    connectionCls = RackspaceConnection
    type = Provider.RACKSPACE
    name = 'Rackspace'

    features = {"create_node": ["generates_password"]}

    NODE_STATE_MAP = { 'BUILD': NodeState.PENDING,
                       'REBUILD': NodeState.PENDING,
                       'ACTIVE': NodeState.RUNNING,
                       'SUSPENDED': NodeState.TERMINATED,
                       'QUEUE_RESIZE': NodeState.PENDING,
                       'PREP_RESIZE': NodeState.PENDING,
                       'VERIFY_RESIZE': NodeState.RUNNING,
                       'PASSWORD': NodeState.PENDING,
                       'RESCUE': NodeState.PENDING,
                       'REBUILD': NodeState.PENDING,
                       'REBOOT': NodeState.REBOOTING,
                       'HARD_REBOOT': NodeState.REBOOTING,
                       'SHARE_IP': NodeState.PENDING,
                       'SHARE_IP_NO_CONFIG': NodeState.PENDING,
                       'DELETE_IP': NodeState.PENDING,
                       'UNKNOWN': NodeState.UNKNOWN}

    def list_nodes(self):
        return self._to_nodes(self.connection.request('/servers/detail').object)

    def list_sizes(self, location=None):
        return self._to_sizes(self.connection.request('/flavors/detail').object)

    def list_images(self, location=None):
        return self._to_images(self.connection.request('/images/detail').object)

    def list_locations(self):
        return [NodeLocation(0, "Rackspace DFW1", 'US', self)]

    def create_node(self, **kwargs):
        """Create a new rackspace node

        See L{NodeDriver.create_node} for more keyword args.
        @keyword    ex_metadata: Key/Value metadata to associate with a node
        @type       ex_metadata: C{dict}

        @keyword    ex_files:   File Path => File contents to create on the node
        @type       ex_files:   C{dict}
        """
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']
        server_elm = ET.Element(
            'server',
            {'xmlns': NAMESPACE,
             'name': name,
             'imageId': str(image.id),
             'flavorId': str(size.id)}
        )

        metadata_elm = self._metadata_to_xml(kwargs.get("ex_metadata", {}))
        if metadata_elm:
            server_elm.append(metadata_elm)

        files_elm = self._files_to_xml(kwargs.get("ex_files", {}))
        if files_elm:
            server_elm.append(files_elm)

        resp = self.connection.request("/servers",
                                       method='POST',
                                       data=ET.tostring(server_elm))
        return self._to_node(resp.object)

    def _metadata_to_xml(self, metadata):
        if len(metadata) == 0:
            return None

        metadata_elm = ET.Element('metadata')
        for k, v in metadata.items():
            meta_elm = ET.SubElement(metadata_elm, 'meta', {'key': str(k) })
            meta_elm.text = str(v)

        return metadata_elm

    def _files_to_xml(self, files):
        if len(files) == 0:
            return None

        personality_elm = ET.Element('personality')
        for k, v in files.items():
            file_elm = ET.SubElement(personality_elm,
                                     'file',
                                     {'path': str(k)})
            file_elm.text = base64.b64encode(v)

        return personality_elm

    def reboot_node(self, node):
        # TODO: Hard Reboots should be supported too!
        resp = self._node_action(node, ['reboot', ('type', 'SOFT')])
        return resp.status == 202

    def destroy_node(self, node):
        uri = '/servers/%s' % (node.id)
        resp = self.connection.request(uri, method='DELETE')
        return resp.status == 202

    def _node_action(self, node, body):
        if isinstance(body, list):
            attr = ' '.join(['%s="%s"' % (item[0], item[1])
                             for item in body[1:]])
            body = '<%s xmlns="%s" %s/>' % (body[0], NAMESPACE, attr)
        uri = '/servers/%s/action' % (node.id)
        resp = self.connection.request(uri, method='POST', data=body)
        return resp

    def _to_nodes(self, object):
        node_elements = self._findall(object, 'server')
        return [ self._to_node(el) for el in node_elements ]

    def _fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

    def _findall(self, element, xpath):
        return element.findall(self._fixxpath(xpath))

    def _to_node(self, el):
        def get_ips(el):
            return [ip.get('addr') for ip in el]

        def get_meta_dict(el):
            d = {}
            for meta in el:
                d[meta.get('key')] =  meta.text
            return d

        public_ip = get_ips(self._findall(el,
                                          'addresses/public/ip'))
        private_ip = get_ips(self._findall(el,
                                          'addresses/private/ip'))
        metadata = get_meta_dict(self._findall(el, 'metadata/meta'))

        n = Node(id=el.get('id'),
                 name=el.get('name'),
                 state=self.NODE_STATE_MAP.get(el.get('status'), NodeState.UNKNOWN),
                 public_ip=public_ip,
                 private_ip=private_ip,
                 driver=self.connection.driver,
                 extra={
                    'password': el.get('adminPass'),
                    'hostId': el.get('hostId'),
                    'imageId': el.get('imageId'),
                    'flavorId': el.get('flavorId'),
                    'metadata': metadata,
                 })
        return n

    def _to_sizes(self, object):
        elements = self._findall(object, 'flavor')
        return [ self._to_size(el) for el in elements ]

    def _to_size(self, el):
        s = NodeSize(id=el.get('id'),
                     name=el.get('name'),
                     ram=int(el.get('ram')),
                     disk=int(el.get('disk')),
                     bandwidth=None, # XXX: needs hardcode
                     price=None, # XXX: needs hardcode,
                     driver=self.connection.driver)
        return s

    def _to_images(self, object):
        elements = self._findall(object, "image")
        return [ self._to_image(el)
                 for el in elements
                 if el.get('status') == 'ACTIVE' ]

    def _to_image(self, el):
        i = NodeImage(id=el.get('id'),
                     name=el.get('name'),
                     driver=self.connection.driver,
                     extra={'serverId': el.get('serverId')})
        return i
