from libcloud.types import NodeState, Node, InvalidCredsException
from libcloud.interface import INodeDriver
from zope.interface import implements
import base64
import httplib
import struct
import socket
import hashlib
from xml.etree import ElementTree as ET

API_HOST = 'api.slicehost.com'

class SlicehostConnection(object):
  def __init__(self, key):

    self.key = key

    self.api = httplib.HTTPSConnection("%s:%d" % (API_HOST, 443))

  def _headers(self, datalen=0):
    return {
      'Authorization': ('Basic %s'
                        % (base64.b64encode('%s:' % self.key))),
      'Content-Length': str(datalen)
    }

  def make_request(self, path, data='', method='GET'):
    self.api.request(method, path, headers=self._headers(datalen=len(data)))
    return self.api.getresponse()

  def slices(self):
    return Response(self.make_request('/slices.xml'))

  def reboot(self, slice_id):
    uri = '/slices/%s/reboot.xml' % slice_id
    return Response(self.make_request(uri, method='PUT'))

  def hard_reboot(self, slice_id):
    uri = '/slices/%s/hard_reboot.xml' % slice_id
    return Response(self.make_request(uri, method='PUT'))

  def destroy(self, slice_id):
    uri = '/slices/%s/destroy.xml' % slice_id
    return Response(self.make_request(uri, method='PUT'))

class Response(object):
  def __init__(self, http_response):
    if int(http_response.status) == 401:
      raise InvalidCredsException()

    self.http_response = http_response
    self.http_xml = http_response.read()

  def is_error(self):
    return self.http_response.status != 200

  def get_error(self):
    if not self.is_error():
      return None
    else:
      return "; ".join([err.text
                        for err
                        in ET.XML(self.http_xml).findall('error')])

class SlicehostNodeDriver(object):

  implements(INodeDriver)

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

    n = Node(uuid=self.get_uuid(element.findtext('id')),
             name=element.findtext('name'),
             state=state,
             ipaddress=ipaddress,
             creds=self.creds,
             attrs=node_attrs)
    return n

  def get_uuid(self, field):
    return hashlib.sha1("%s:%d" % (field,self.creds.provider)).hexdigest()

  def list_nodes(self):
    res = self.api.slices()
    return [ self._to_node(el)
             for el in ET.XML(res.http_xml).findall('slice') ]

  def reboot_node(self, node):
    """Reboot the node by passing in the node object"""

    # 'hard' could bubble up as kwarg depending on how reboot_node turns out
    # Defaulting to soft reboot
    hard = False
    reboot = self.api.hard_reboot if hard else self.api.reboot
    expected_status = 'hard_reboot' if hard else 'reboot'

    res = reboot(node.attrs['id'])
    if res.is_error():
      raise Exception(res.get_error())
    return ET.XML(res.http_xml).findtext('status') == expected_status

  def destroy_node(self, node):
    """Destroys the node

    Requires 'Allow Slices to be deleted or rebuilt from the API' to be
    ticked at https://manage.slicehost.com/api, otherwise returns:

      <errors>
        <error>You must enable slice deletes in the SliceManager</error>
        <error>Permission denied</error>
      </errors>

    """

    res = self.api.destroy(node.attrs['id'])
    if res.is_error():
      raise Exception(res.get_error())
    return True
