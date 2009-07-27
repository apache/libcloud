from libcloud.types import NodeState, Node, InvalidCredsException
from libcloud.interface import INodeDriver
from zope.interface import implements
import base64
import hmac
import httplib
from hashlib import sha256
import time
import urllib
import hashlib
from xml.etree import ElementTree as ET

EC2_US_HOST = 'ec2.amazonaws.com'
EC2_EU_HOST = 'eu-west-1.ec2.amazonaws.com'
API_VERSION = '2009-04-04'
NAMESPACE = "http://ec2.amazonaws.com/doc/%s/" % (API_VERSION)

class AWSAuthConnection(object):
  def __init__(self, aws_access_key_id, aws_secret_access_key, 
                server=EC2_US_HOST):

    self.verbose = False
    self.aws_access_key_id = aws_access_key_id
    self.aws_secret_access_key = aws_secret_access_key
    self.server = server
    self.connection = httplib.HTTPSConnection("%s:%d" % (server, 443))

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

    params['SignatureVersion'] = '2'
    params['SignatureMethod'] = 'HmacSHA256'
    params['AWSAccessKeyId'] = self.aws_access_key_id
    params['Version'] = API_VERSION
    params['Timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    sig = self.get_aws_auth_param(params, self.aws_secret_access_key)

    path = '?%s&Signature=%s' % (
      '&'.join(['='.join([key, urllib.quote_plus(params[key])])
                for key in params]),
      sig)

    self.connection.request('GET', '/%s' % path, data,
                            headers={'Host': self.server})
    return self.connection.getresponse()

  def get_aws_auth_param(self, params, aws_secret_access_key, path='/'):
    """
    creates the signature required for AWS, per:

    http://docs.amazonwebservices.com/AWSEC2/2009-04-04/DeveloperGuide/index.html?using-query-api.html#query-authentication

    StringToSign = HTTPVerb + "\n" +
                   ValueOfHostHeaderInLowercase + "\n" +
                   HTTPRequestURI + "\n" +         
                   CanonicalizedQueryString <from the preceding step>
    """
    keys = params.keys()
    keys.sort()
    pairs = []
    for key in keys:
      pairs.append(urllib.quote(key, safe='') + '=' +
                   urllib.quote(params[key], safe='-_~'))

    qs = '&'.join(pairs)
    string_to_sign = '%s\n' \
                     '%s\n' \
                     '%s\n' \
                     '%s' % ('GET', self.server, path, qs)
                     
    b64_hmac = base64.b64encode(hmac.new(aws_secret_access_key,
                                         string_to_sign,
                                         digestmod=sha256).digest())
    return urllib.quote(b64_hmac)

  def describe_instances(self, instanceIds=[]):
    params = self.pathlist("InstanceId", instanceIds)
    return Response(self.make_request("DescribeInstances", params))

  def reboot_instances(self, instanceIds=[]):
    params = self.pathlist("InstanceId", instanceIds)
    return Response(self.make_request("RebootInstances", params))

class Response(object):
  def __init__(self, http_response):
    if int(http_response.status) == 403:
      raise InvalidCredsException()

    self.http_response = http_response
    self.xml = http_response.read()
    self.http_xml = ET.XML(self.xml)

  def is_error(self):
    return self.http_response.status != 200

  def get_error(self):
    err_list = []
    if self.is_error():
      for err in self.http_xml.findall('Errors/Error'):
        code, message = err.getchildren()
        err_list.append("%s: %s" % (code.text, message.text))
    else:
      return None
    return "\n".join(err_list)

  def get_boolean(self):
    return self.http_xml.getchildren()[0].text == "true"

class EC2NodeDriver(object):

  implements(INodeDriver)

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

    attrs = [ 'dnsName', 'instanceId', 'imageId', 'privateDnsName',
              'instanceState/name', 'amiLaunchIndex',
              'productCodesSet/item/productCode', 'instanceType',
              'launchTime', 'placement/availabilityZone', 'kernelId',
              'ramdiskId' ]

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
    return [ self._to_node(el)
             for el in res.http_xml.findall(
               self._fixxpath('reservationSet/item/instancesSet/item')
             ) ]

  def reboot_node(self, node):
    """
    Reboot the node by passing in the node object
    """
    res = self.api.reboot_instances([node.attrs['instanceId']])
    if res.is_error():
      raise Exception(res.get_error())
    
    return res.get_boolean()

class EC2EUNodeDriver(EC2NodeDriver):

  def __init__(self, creds):
    self.creds = creds
    self.api = AWSAuthConnection(creds.key, creds.secret, server=EC2_EU_HOST)
