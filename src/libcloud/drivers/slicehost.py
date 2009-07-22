from libcloud.types import NodeState, Node
import base64
import httplib
import struct
import socket
from xml.etree import ElementTree as ET

AUTH_HOST = 'api.slicehost.com'

class SlicehostConnection(object):
  def __init__(self, key):

    self.key = key

    self.api = httplib.HTTPSConnection("%s:%d" % (AUTH_HOST, 443))

  def _headers(self):
    return {'Authorization': 'Basic %s' % (base64.b64encode('%s:' % self.key)) }

  def make_request(self, path, data=''):
    self.api.request('GET', '%s' % (path), headers=self._headers())
    return self.api.getresponse()

  def list_servers(self):
    return Response(self.make_request('/slices.xml'))

class Response(object):
  def __init__(self, http_response):
    self.http_response = http_response
    self.http_xml = http_response.read()

class SlicehostProvider(object):

  def __init__(self, creds):
    self.creds = creds
    self.api = SlicehostConnection(creds.key)

  def _is_private_subnet(self, ip):
    private_subnets = [ {'subnet': '10.0.0.0', 'mask': '255.0.0.0'},
                        {'subnet': '172.16.0.0', 'mask': '172.16.0.0'},
                        {'subnet': '192.168.0.0', 'mask': '192.168.0.0'} ]

    ip = struct.unpack('I',socket.inet_aton(ip))[0]

    for network in private_subnets:
      subnet = struct.unpack('I',socket.inet_aton(network['subnet']))[0]
      mask = struct.unpack('I',socket.inet_aton(network['mask']))[0]

      if (ip&mask) == (subnet&mask):
        return True
      
    return False

  def _to_node(self, element):
    states = { 'active': NodeState.RUNNING,
               'build': NodeState.PENDING,
               'terminated': NodeState.TERMINATED }

    attrs = [ 'name', 'image-id', 'progress', 'id', 'bw-out', 'bw-in', 
              'flavor-id', 'status', 'ip-address' ]

    node_attrs = {}
    for attr in attrs:
      node_attrs[attr] = element.findtext(attr)

    ipaddress = element.findtext('ip-address')
    if self._is_private_subnet(ipaddress):
      # sometimes slicehost gives us a private address in ip-address
      for addr in element.findall('addresses/address'):
        ip = addr.text
        try:
          socket.inet_aton(ip)
        except socket.error:
          # not a valid ip
          continue
        if not self._is_private_subnet(ip):
          ipaddress = ip
          break
    try:
      state = states[element.findtext('status')]
    except:
      state = NodeState.UNKNOWN

    n = Node(uuid = element.findtext('id'),
             name = element.findtext('name'),
             state = state,
             ipaddress = ipaddress,
             creds = self.creds,
             attrs = node_attrs)
    return n

  def list_nodes(self):
    res = self.api.list_servers()
    return [ self._to_node(el) for el in ET.XML(res.http_xml).findall('slice') ]
