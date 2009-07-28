from libcloud.types import NodeState, Node, InvalidCredsException
from libcloud.interface import INodeDriver
from zope.interface import implements

import base64
import httplib
import hashlib
from xml.etree import ElementTree as ET

API_HOST = 'vps.net'

class VPSNetConnection(object):
    def __init__(self, user, key):

        self.user = user
        self.key = key

        self.api = httplib.HTTPSConnection("%s:%d" % (API_HOST, 443))

    def _headers(self):
        user_b64 = base64.b64encode('%s:%s' % (self.user, self.key))
        return { 'Authorization': 'Basic %s' % (user_b64),
                 'Host': API_HOST }

    def make_request(self, path, data=''):
        self.api.request('GET', '%s' % (path), headers=self._headers())
        return self.api.getresponse()

    def virtual_machines(self):
        return Response(self.make_request('/virtual_machines.xml'))

class Response(object):
    def __init__(self, http_response):
        if int(http_response.status) == 401:
            raise InvalidCredsException()
        self.http_response = http_response
        self.http_xml = http_response.read()

class VPSNetNodeDriver(object):

    implements(INodeDriver)

    def __init__(self, creds):
        self.creds = creds
        self.api = VPSNetConnection(creds.key, creds.secret)

    def _to_node(self, element):
        attrs = [ 'backups_enabled', 'cloud_id', 'consumer_id', 
                  'created_at', 'domain_name', 'hostname', 'id', 'label', 
                  'password', 'system_template_id', 'updated_at', 'running',
                  'power_action_pending', 'slices_count' ]

        node_attrs = {}
        for attr in attrs:
            node_attrs[attr] = element.findtext(attr)

        ipaddress = element.findtext('ip-address')

        state = NodeState.UNKNOWN
        if element.findtext('power_action_pending') == 'true':
            state = NodeState.PENDING
        elif element.findtext('running') == 'true':
            state = NodeState.RUNNING

        n = Node(uuid=self.get_uuid(element.findtext('id')),
                 name=element.findtext('label'),
                 state=state,
                 #XXX:    they do not return this in the vps list!
                 ipaddress=None, 
                 creds=self.creds,
                 attrs=node_attrs)
        return n

    def get_uuid(self, field):
        hash_str = "%s:%d" % (field, self.creds.provider)
        return hashlib.sha1(hash_str).hexdigest()

    def list_nodes(self):
        res = self.api.virtual_machines()
        return [ self._to_node(el)
                 for el in ET.XML(res.http_xml).findall('virtual_machine') ]
