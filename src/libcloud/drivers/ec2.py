from libcloud.types import NodeState, Node
import base64
import hmac
import httplib
import sha
import time
import urllib
import hashlib
from xml.etree import ElementTree as ET

EC2_US_HOST = 'ec2.amazonaws.com'
EC2_EU_HOST = 'eu-west.amazonaws.com'
PORTS_BY_SECURITY = { True: 443, False: 80 }
API_VERSION = '2008-02-01'
NAMESPACE = "http://ec2.amazonaws.com/doc/%s/" % (API_VERSION)

class AWSAuthConnection(object):
  def __init__(self, aws_access_key_id, aws_secret_access_key,
         is_secure=True, server=EC2_US_HOST, port=None):

    if not port:
      port = PORTS_BY_SECURITY[is_secure]

    self.verbose = False
    self.aws_access_key_id = aws_access_key_id
    self.aws_secret_access_key = aws_secret_access_key
    if (is_secure):
      self.connection = httplib.HTTPSConnection("%s:%d" % (server, port))
    else:
      self.connection = httplib.HTTPConnection("%s:%d" % (server, port))

  def pathlist(self, key, arr):
    """Converts a key and an array of values into AWS query param format."""
    params = {}
    i = 0
    for value in arr:
      i += 1
      params["%s.%s" % (key, i)] = value
    return params

  def make_request(self, action, params, data=''):
    params["Action"] = action
    if self.verbose:
      print params

    params["SignatureVersion"] = "1"
    params["AWSAccessKeyId"] = self.aws_access_key_id
    params["Version"] = API_VERSION
    params["Timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    params = zip(params.keys(), params.values())
    params.sort(key=lambda x: str.lower(x[0]))
    
    sig = self.get_aws_auth_param(params, self.aws_secret_access_key)

    path = "?%s&Signature=%s" % (
      "&".join(["=".join([param[0], urllib.quote_plus(param[1])]) for param in params]),
      sig)

    self.connection.request("GET", "/%s" % path, data)
    return self.connection.getresponse()

  # computes the base64'ed hmac-sha hash of the canonical string and
  # the secret access key, optionally urlencoding the result
  def encode(self, aws_secret_access_key, str, urlencode=True):
    b64_hmac = base64.encodestring(hmac.new(aws_secret_access_key, str, sha).digest()).strip()
    if urlencode:
      return urllib.quote_plus(b64_hmac)
    else:
      return b64_hmac

  def get_aws_auth_param(self, params, aws_secret_access_key):
    canonical_string = "".join(["".join(param) for param in params])
    return self.encode(aws_secret_access_key, canonical_string)

  def describe_instances(self, instanceIds=[]):
    params = self.pathlist("InstanceId", instanceIds)
    return Response(self.make_request("DescribeInstances", params))

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




class EC2EUProvider(EC2Provider):

  def __init__(self, creds):
    self.creds = creds
    self.api = AWSAuthConnection(creds.key, creds.secret, server=EC2_EU_HOST)

