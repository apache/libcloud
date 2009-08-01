# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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
from libcloud.types import NodeState, Node, InvalidCredsException
from libcloud.interface import INodeDriver
from zope.interface import implements
import httplib
import urlparse
import hashlib
from xml.etree import ElementTree as ET

AUTH_HOST = 'auth.api.rackspacecloud.com'
API_VERSION = 'v1.0'
NAMESPACE = 'http://docs.rackspacecloud.com/servers/api/v1.0'

class RackspaceConnection(object):
    def __init__(self, user, key):
        self.user = user
        self.key = key
        self.token = None
        self.endpoint = None

    def _authenticate(self):
        self.auth = httplib.HTTPSConnection("%s:%d" % (AUTH_HOST, 443))
        self.auth.request('GET', '/%s' % API_VERSION,
                          headers={ 'X-Auth-User': self.user,
                                    'X-Auth-Key': self.key })
        ret = self.auth.getresponse()
        self.token = ret.getheader('x-auth-token')
        self.endpoint = ret.getheader('x-server-management-url')

        if not self.token or not self.endpoint:
            raise InvalidCredsException()

        scheme, server, self.path, param, query, fragment = (
            urlparse.urlparse(self.endpoint)
        )
        self.api = httplib.HTTPSConnection("%s:%d" % (server, 443))

    def _headers(self):
        if not self.token:
            self._authenticate()

        return { 'X-Auth-Token': self.token,
                 'Accept': 'application/xml' }

    def make_request(self, path, data='', method='GET'):
        if not self.token or not self.endpoint:
            self._authenticate()

        self.api.request(method, '%s/%s' % (self.path, path),
                         headers=self._headers())
        return self.api.getresponse()

    def list_servers(self):
        return Response(self.make_request('servers/detail'))
    
    def action(self, id, verb, params):
        uri = 'servers/%s/action' % id
        data = ('<%s xmlns="%s" %s/>'
                % (verb, NAMESPACE,
                   ' '.join(['%s="%s"' % item for item in params.items()])))
        return Response(self.make_request(uri, data=data, method='POST'))

    def delete(self, id):
        uri = 'servers/%s' % id
        return Response(self.make_request(uri, method='DELETE'))

class Response(object):
    def __init__(self, http_response):
        self.http_response = http_response
        self.http_xml = http_response.read()

    def is_error(self):
        return self.http_response.status != 202

    def get_error(self):
        """Gets error in the following manner:

        - Checks for <{NAMESPACE}message> elem in body
        - Reads against response code
        - Gives up
        """
        tag = "{%s}message" % NAMESPACE;
        info = [ err.text
                 for err in
                 ET.XML(self.http_xml).findall(tag) ]
        if info:
            return "; ".join([ err.text
                               for err in
                               ET.XML(self.http_xml).findall(tag) ])
        else:
            reasons = { 400: "cloudServersFault/badRequest",
                        401: "unauthorized",
                        500: "cloudServersFault",
                        503: "serviceUnavailable",
                        404: "itemNotFound",
                        409: "buildInProgress",
                        413: "overLimit" }
            if self.http_response.status in reasons:
                return reasons[self.http_response.status]
            else:
                return None

class RackspaceNodeDriver(object):

    implements(INodeDriver)

    def __init__(self, creds):
        self.creds = creds
        self.api = RackspaceConnection(creds.key, creds.secret)

    def _fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

    def _findtext(self, element, xpath):
        return element.findtext(self._fixxpath(xpath))

    def _to_node(self, element):
        states = { 'BUILD': NodeState.PENDING,
                   'ACTIVE': NodeState.RUNNING,
                   'SUSPENDED': NodeState.TERMINATED,
                   'QUEUE_RESIZE': NodeState.PENDING,
                   'PREP_RESIZE': NodeState.PENDING,
                   'RESCUE': NodeState.PENDING,
                   'REBUILD': NodeState.PENDING,
                   'REBOOT': NodeState.REBOOTING,
                   'HARD_REBOOT': NodeState.REBOOTING }

        attribs = element.attrib
        node_attrs = attribs

        try:
            state = states[attribs['status']]
        except:
            state = NodeState.UNKNOWN

        n = Node(uuid=self.get_uuid(attribs['id']),
                 name=attribs['name'],
                 state=state,
                 ipaddress=self._findtext(element, 
                                          'metadata/addresses/public'),
                 creds=self.creds,
                 attrs=node_attrs)
        return n

    def get_uuid(self, field):
        hash_str = '%s:%d' % (field, self.creds.provider)
        return hashlib.sha1(hash_str).hexdigest()

    def list_nodes(self):
        res = self.api.list_servers()
        return [ self._to_node(el)
                 for el
                 in ET.XML(res.http_xml).findall(self._fixxpath('server')) ]

    def reboot_node(self, node):
        """Reboot the node by passing in the node object"""

        # 'hard' could bubble up as kwarg depending on how reboot_node 
        # turns out. Defaulting to soft reboot.
        hard = False
        verb = 'reboot'
        id = node.attrs['id']
        params = {'type': 'HARD' if hard else 'SOFT'}

        res = self.api.action(id, verb, params)
        if res.is_error():
            raise Exception(res.get_error())

        return True

    def destroy_node(self, node):
        """Destroy node"""
        res = self.api.delete(node.attrs['id'])
        if res.is_error():
            raise Exception(res.get_error())

        return True
