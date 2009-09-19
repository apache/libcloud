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
from libcloud.providers import Provider
from libcloud.types import NodeState, InvalidCredsException
from libcloud.base import Node, Response, ConnectionUserAndKey, NodeDriver, NodeSize
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

# Sizes must be hardcoded, because amazon doesn't provide an API to fetch them.
# From http://aws.amazon.com/ec2/instance-types/
EC2_INSTANCE_TYPES = [{'id': 'm1.small',
                       'name': 'Small Instance',
                       'ram': '1740MB',
                       'disk': '160GB',
                       'bandwidth': None,
                       'price': '.1'},
                      {'id': 'm1.large',
                       'name': 'Large Instance',
                       'ram': '7680MB',
                       'disk': '850GB',
                       'bandwidth': None,
                       'price': '.4'},
                      {'id': 'm1.xlarge',
                       'name': 'Extra Large Instance',
                       'ram': '15360MB',
                       'disk': '1690GB',
                       'bandwidth': None,
                       'price': '.8'},
                      {'id': 'c1.medium',
                       'name': 'High-CPU Medium Instance',
                       'ram': '1740MB',
                       'disk': '350GB',
                       'bandwidth': None,
                       'price': '.2'},
                      {'id': 'c1.xlarge',
                       'name': 'High-CPU Extra Large Instance',
                       'ram': '7680MB',
                       'disk': '1690GB',
                       'bandwidth': None,
                       'price': '.8'}]

class EC2Response(Response):

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        try:
            err_list = []
            for err in ET.XML(self.body).findall('Errors/Error'):
                code, message = err.getchildren()
                err_list.append("%s: %s" % (code.text, message.text))
            return "\n".join(err_list)
        except ExpatError:
            return self.body

class EC2Connection(ConnectionUserAndKey):

    host = EC2_US_HOST
    responseCls = EC2Response

    def add_default_params(self, params):
        params['SignatureVersion'] = '2'
        params['SignatureMethod'] = 'HmacSHA256'
        params['AWSAccessKeyId'] = self.user_id
        params['Version'] = API_VERSION
        params['Timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', 
                                            time.gmtime())
        params['Signature'] = self._get_aws_auth_param(params, self.key)
        return params
        
    def _get_aws_auth_param(self, params, secret_key, path='/'):
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
        string_to_sign = '\n'.join(('GET', self.host, path, qs))
                                         
        b64_hmac = base64.b64encode(
                        hmac.new(secret_key, string_to_sign, 
                            digestmod=sha256).digest())
        return b64_hmac

class EC2NodeDriver(NodeDriver):

    connectionCls = EC2Connection
    type = Provider.EC2
    name = 'Amazon EC2 (us-east-1)'

    NODE_STATE_MAP = { 'pending': NodeState.PENDING,
                       'running': NodeState.RUNNING,
                       'shutting-down': NodeState.TERMINATED,
                       'terminated': NodeState.TERMINATED }

    def _findtext(self, element, xpath):
        return element.findtext(self._fixxpath(xpath))

    def _fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

    def _findattr(self, element, xpath):
        return element.findtext(self._fixxpath(xpath))

    def _pathlist(self, key, arr):
        """Converts a key and an array of values into AWS query param 
           format."""
        params = {}
        i = 0
        for value in arr:
            i += 1
            params["%s.%s" % (key, i)] = value
        return params

    def _get_boolean(self, element):
        tag = "{%s}%s" % (NAMESPACE, 'return')
        return element.findtext(tag) == 'true'

    def _get_terminate_boolean(self, element):
        status = element.findtext(".//{%s}%s" % (NAMESPACE, 'name'))
        return any([ term_status == status for term_status
                     in ('shutting-down', 'terminated') ])

    def _to_nodes(self, object):
        return [ self._to_node(el) 
                 for el in object.findall(
                    self._fixxpath('reservationSet/item/instancesSet/item')) ]
        
    def _to_node(self, element):
        try:
            state = self.NODE_STATE_MAP[self._findattr(element, 
                                        "instanceState/name")]
        except KeyError:
            state = NodeState.UNKNOWN

        n = Node(id=self._findtext(element, 'instanceId'),
                 name=self._findtext(element, 'instanceId'),
                 state=state,
                 public_ip=self._findtext(element, 'dnsName'),
                 private_ip=self._findtext(element, 'privateDnsName'),
                 driver=self.connection.driver)
        return n

    def list_nodes(self):
        params = {'Action': 'DescribeInstances' }
        nodes = self._to_nodes(
                    self.connection.request('/', params=params).object)
        return nodes

    def list_sizes(self):
        return [ NodeSize(driver=self.connection.driver, **i) 
                    for i in EC2_INSTANCE_TYPES ]

    def reboot_node(self, node):
        """
        Reboot the node by passing in the node object
        """
        params = {'Action': 'RebootInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request('/', params=params).object
        return self._get_boolean(res)

    def destroy_node(self, node):
        """
        Destroy node by passing in the node object
        """
        params = {'Action': 'TerminateInstances'}
        params.update(self._pathlist('InstanceId', [node.id]))
        res = self.connection.request('/', params=params).object
        return self._get_terminate_boolean(res)

class EC2EUConnection(EC2Connection):

    host = EC2_EU_HOST

class EC2EUNodeDriver(EC2NodeDriver):

    connectionCls = EC2EUConnection
