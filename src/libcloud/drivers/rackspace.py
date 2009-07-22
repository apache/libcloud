from libcloud.types import NodeState, Node
import base64
import hmac
import httplib
import sha
import time
import urllib
import hashlib
from xml.etree import ElementTree as ET

AUTH_HOST = 'auth.api.rackspacecloud.com'
API_VERSION = 'v1.0'

class RackspaceConnection(object):
  def __init__(self, user, key):

    self.user = user
    self.key = key
    self.auth = httplib.HTTPSConnection("%s:%d" % (AUTH_HOST, 443))
    self.api = httplib.HTTPSConnection("%s:%d" % (AUTH_HOST, 443))

    self.auth.request('GET', '/%s' % API_VERSION, headers={'X-Auth-User': user, 'X-Auth-Key': key})
    ret = self.auth.getresponse()
    self.token = ret.getheader('x-auth-token')
    self.endpoint = ret.getheader('x-server-management-url')

  def _headers(self):
    return {'X-Auth-User': self.user, 'X-Auth-Key': self.key}

  def make_request(self, path, data=''):
    self.api.request('GET', '/%s/%s' % (API_VERSION, path), headers=self._auth_headers())
    return self.api.getresponse()

  def list_servers(self):
    return Response(self.make_request('servers'))

class Response(object):
  def __init__(self, http_response):
      self.http_response = http_response
      self.http_xml = http_response.read()

class EC2Provider(object):

  def __init__(self, creds):
    self.creds = creds
    self.api = AWSAuthConnection(creds.key, creds.secret)

  def _findtext(self, element, xpath):
    return element.findtext(self._fixxpath(xpath))

  def _fixxpath(self, xpath):
    # ElementTree wants namespaces in its xpaths, so here we add them.
    return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

  def _findattr(self, element, xpath):
    return element.findtext(self._fixxpath(xpath))

  def _to_node(self, element):
    states = {'pending':NodeState.PENDING,
              'running':NodeState.RUNNING,
              'shutting-down':NodeState.TERMINATED,
              'terminated':NodeState.TERMINATED }

    attrs = [ 'dnsName', 'instanceId', 'imageId', 'privateDnsName', 'instanceState/name', 
              'amiLaunchIndex', 'productCodesSet/item/productCode', 'instanceType', 
              'launchTime', 'placement/availabilityZone', 'kernelId', 'ramdiskId' ]

    node_attrs = {}
    for attr in attrs:
      node_attrs[attr] = self._findattr(element, attr)

    try:
      state = states[self._findattr(element, "instanceState/name")]
    except:
      state = NodeState.UNKNOWN

    n = Node(uuid = self.get_uuid(self._findtext(element, "instanceId")),
             name = self._findtext(element, "instanceId"),
             state = state,
             ipaddress = self._findtext(element, "dnsName"),
             creds = self.creds,
             attrs = node_attrs)
    return n

  def get_uuid(self, field):
    return hashlib.sha1("%s:%d" % (field,self.creds.provider)).hexdigest()
    
  def list_nodes(self):
    res = self.api.describe_instances()
    return [ self._to_node(el) for el in ET.XML(res.http_xml).findall(self._fixxpath('reservationSet/item/instancesSet/item')) ]

