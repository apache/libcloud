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
import time
import urllib
import hashlib
from xml.etree import ElementTree as ET

HOST = 'api.gogrid.com'
PORTS_BY_SECURITY = { True: 443, False: 80 }
API_VERSION = '1.1'

class GoGridAuthConnection(object):
    def __init__(self, api_key, secret,
                 is_secure=True, server=HOST, port=None):

        if not port:
            port = PORTS_BY_SECURITY[is_secure]

        self.verbose = False
        self.api_key = api_key
        self.secret = secret
        conn_str = "%s:%d" % (server, port)
        if (is_secure):
            self.connection = httplib.HTTPSConnection(conn_str)
        else:
            self.connection = httplib.HTTPConnection(conn_str)


    def make_request(self, action, params={}, data=''):
        if self.verbose:
            print params

        params["api_key"] = self.api_key 
        params["v"] = API_VERSION
        params["format"] = 'xml'
        params["sig"] = self.get_signature(self.api_key, self.secret)

        params = zip(params.keys(), params.values())
        params.sort(key=lambda x: str.lower(x[0]))

        path = "&".join([ "=".join((param[0], urllib.quote_plus(param[1])))
                          for param in params ])
        
        self.connection.request("GET", "/api/%s?%s" % (action, path), data)
        return self.connection.getresponse()

    def get_signature(self, key, secret):
        """ create sig from md5 of key + secret + time """
        return hashlib.md5(key + secret + str(int(time.time()))).hexdigest()

    def server_list(self):
        return Response(self.make_request("/grid/server/list"))

    def server_power(self, id, power):
        # power in ['start', 'stop', 'restart']
        params = {'id': id, 'power': power}
        return Response(self.make_request("/grid/server/power", params))

    def server_delete(self, id):
        params = {'id': id}
        return Response(self.make_request("/grid/server/delete", params))

class Response(object):
    def __init__(self, http_response):
        if int(http_response.status) == 403:
            raise InvalidCredsException()
        self.http_response = http_response
        self.http_xml = http_response.read()

    def is_error(self):
        root = ET.XML(self.http_xml)
        return root.find('response').get('status') != 'success'

    def get_error(self):
        attrs = ET.XML(self.http_xml).findall('.//attribute')
        return ': '.join([attr.text for attr in attrs])

STATE = {
    "Started": NodeState.RUNNING,
}

class GoGridNodeDriver(object):

    implements(INodeDriver)

    def __init__(self, creds):
        self.creds = creds
        self.api = GoGridAuthConnection(creds.key, creds.secret)

    def _findtext(self, element, xpath):
        return element.findtext(xpath)

    def _findattr(self, element, xpath):
        return element.findtext(xpath)

    def get_state(self, element):
        try:
            for stanza in element.findall("object/attribute"):
                if stanza.get('name') == "name":
                    return STATE[stanza.get('name')]
        except:
            pass
        return NodeState.UNKNOWN

    def section(self, element, name):
        return element.get('name') == name

    def section_in(self, element, names):
        return element.get('name') in names

    def get_ip(self, element):
        for stanza in element.getchildren():
            for ips in stanza.getchildren():
                if ips.get('name') == "ip":
                    return ips.text
        raise Exception("No ipaddress found!")

    def get_deepattr(self, element, node_attrs):
        if len(element.getchildren()) > 1:
            i = 0
            for obj in element.getchildren():
                name = "%s_%d" %(element.get('name'), i)
                for attr in obj.getchildren():
                    node_attrs[name+"_"+attr.get("name")] = attr.text
                i += 1
        else:
            for obj in element.getchildren():
                name = element.get('name')
                for attr in obj.getchildren():
                    node_attrs[name+"_"+attr.get("name")] = attr.text
            


    def _to_node(self, element):
        attrs = ['id', 'name', 'description', ]
        deepattrs = ['ram', 'image', 'type', 'os']
        node_attrs = {}
        for shard in element.findall('attribute'):

            if self.section(shard, 'state'):
                state = self.get_state(shard)

            elif self.section(shard, 'ip'):
                node_attrs['ip'] = self.get_ip(shard)

            elif self.section_in(shard, attrs):
                node_attrs[shard.get('name')] = shard.text

            elif self.section_in(shard, deepattrs):
                self.get_deepattr(shard, node_attrs)

        n = Node(uuid=self.get_uuid(node_attrs['id']),
                 name=node_attrs['name'],
                 state=state,
                 ipaddress=node_attrs['ip'],
                 creds=self.creds,
                 attrs=node_attrs)
        return n

    def get_uuid(self, field):
        uuid_str = "%s:%d" % (field,self.creds.provider)
        return hashlib.sha1(uuid_str).hexdigest()
    
    def list_nodes(self):
        res = self.api.server_list()
        return [ self._to_node(el)
                 for el
                 in ET.XML(res.http_xml).findall('response/list/object') ]

    def reboot_node(self, node):
        id = node.attrs['id']
        power = 'restart'

        res = self.api.server_power(id, power)
        if res.is_error():
            raise Exception(res.get_error())

        return True

    def destroy_node(self, node):
        id = node.attrs['id']

        res = self.api.server_delete(id)
        if res.is_error():
            raise Exception(res.get_error())

        return True
