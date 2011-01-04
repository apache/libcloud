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
Driver for the IBM Developer Cloud.
"""
from libcloud.types import NodeState, InvalidCredsError, Provider
from libcloud.base import Response, ConnectionUserAndKey, NodeDriver, Node, NodeImage, NodeSize, NodeLocation, NodeAuthSSHKey
import base64, urllib

from xml.etree import ElementTree as ET

HOST = 'www-147.ibm.com'
REST_BASE = '/computecloud/enterprise/api/rest/20100331'

class IBMResponse(Response):
    def success(self):
        return int(self.status) == 200

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        if int(self.status) == 401:
            if not self.body:
                raise InvalidCredsError(str(self.status) + ': ' + self.error)
            else:
                raise InvalidCredsError(self.body)
        return self.body

class IBMConnection(ConnectionUserAndKey):
    """
    Connection class for the IBM Developer Cloud driver
    """

    host = HOST
    responseCls = IBMResponse

    def add_default_headers(self, headers):
        headers['Accept'] = 'text/xml'
        headers['Authorization'] = ('Basic %s' % (base64.b64encode('%s:%s' % (self.user_id, self.key))))
        if not 'Content-Type' in headers:
            headers['Content-Type'] = 'text/xml'
        return headers

    def encode_data(self, data):
        return urllib.urlencode(data)

class IBMNodeDriver(NodeDriver):
    """
    IBM Developer Cloud node driver.
    """
    connectionCls = IBMConnection
    type = Provider.IBM
    name = "IBM Developer Cloud"

    NODE_STATE_MAP = { 0: NodeState.PENDING,
                       1: NodeState.PENDING,
                       2: NodeState.TERMINATED,
                       3: NodeState.TERMINATED,
                       4: NodeState.TERMINATED,
                       5: NodeState.RUNNING,
                       6: NodeState.UNKNOWN,
                       7: NodeState.PENDING,
                       8: NodeState.REBOOTING,
                       9: NodeState.PENDING,
                       10: NodeState.PENDING,
                       11: NodeState.TERMINATED,
                       12: NodeState.PENDING,   # Deprovision pending
                       13: NodeState.PENDING }  # Restart pending

    def create_node(self, **kwargs):
        """
        Creates a node in the IBM Developer Cloud.

        See L{NodeDriver.create_node} for more keyword args.

        @keyword    ex_configurationData: Image-specific configuration parameters.
                                       Configuration parameters are defined in
                                       the parameters.xml file.  The URL to
                                       this file is defined in the NodeImage
                                       at extra[parametersURL].
        @type       ex_configurationData: C{dict}
        """

        # Compose headers for message body
        data = {}
        data.update({'name': kwargs['name']})
        data.update({'imageID': kwargs['image'].id})
        data.update({'instanceType': kwargs['size'].id})
        if 'location' in kwargs:
            data.update({'location': kwargs['location'].id})
        else:
            data.update({'location': '1'})
        if 'auth' in kwargs and isinstance(kwargs['auth'], NodeAuthSSHKey):
            data.update({'publicKey': kwargs['auth'].pubkey})
        if 'ex_configurationData' in kwargs:
            configurationData = kwargs['ex_configurationData']
            for key in configurationData.keys():
                data.update({key: configurationData.get(key)})

        # Send request!
        resp = self.connection.request(action = REST_BASE + '/instances',
                                       headers = {'Content-Type': 'application/x-www-form-urlencoded'},
                                       method = 'POST',
                                       data = data).object
        return self._to_nodes(resp)[0]

    def destroy_node(self, node):
        url = REST_BASE + '/instances/%s' % (node.id)
        status = int(self.connection.request(action = url, method='DELETE').status)
        return status == 200

    def reboot_node(self, node):
        url = REST_BASE + '/instances/%s' % (node.id)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'state': 'restart'}

        resp = self.connection.request(action = url,
                                       method = 'PUT',
                                       headers = headers,
                                       data = data)
        return int(resp.status) == 200

    def list_nodes(self):
        return self._to_nodes(self.connection.request(REST_BASE + '/instances').object)

    def list_images(self, location = None):
        return self._to_images(self.connection.request(REST_BASE + '/offerings/image').object)

    def list_sizes(self, location = None):        
        return [ NodeSize('BRZ32.1/2048/60*175', 'Bronze 32 bit', None, None, None, None, self.connection.driver),
                 NodeSize('BRZ64.2/4096/60*500*350', 'Bronze 64 bit', None, None, None, None, self.connection.driver),
                 NodeSize('COP32.1/2048/60', 'Copper 32 bit', None, None, None, None, self.connection.driver),
                 NodeSize('COP64.2/4096/60', 'Copper 64 bit', None, None, None, None, self.connection.driver),
                 NodeSize('SLV32.2/4096/60*350', 'Silver 32 bit', None, None, None, None, self.connection.driver),
                 NodeSize('SLV64.4/8192/60*500*500', 'Silver 64 bit', None, None, None, None, self.connection.driver),
                 NodeSize('GLD32.4/4096/60*350', 'Gold 32 bit', None, None, None, None, self.connection.driver),
                 NodeSize('GLD64.8/16384/60*500*500', 'Gold 64 bit', None, None, None, None, self.connection.driver),
                 NodeSize('PLT64.16/16384/60*500*500*500*500', 'Platinum 64 bit', None, None, None, None, self.connection.driver) ]

    def list_locations(self):
        return self._to_locations(self.connection.request(REST_BASE + '/locations').object)

    def _to_nodes(self, object):
        return [ self._to_node(instance) for instance in object.findall('Instance') ]

    def _to_node(self, instance):
        return Node(id = instance.findtext('ID'),
                    name = instance.findtext('Name'),
                    state = self.NODE_STATE_MAP[int(instance.findtext('Status'))],
                    public_ip = instance.findtext('IP'),
                    private_ip = None,
                    driver = self.connection.driver)

    def _to_images(self, object):
        return [ self._to_image(image) for image in object.findall('Image') ]

    def _to_image(self, image):
        return NodeImage(id = image.findtext('ID'),
                         name = image.findtext('Name'),
                         driver = self.connection.driver,
                         extra = {'parametersURL': image.findtext('Manifest')})

    def _to_locations(self, object):
        return [ self._to_location(location) for location in object.findall('Location') ]

    def _to_location(self, location):
        # NOTE: country currently hardcoded
        return NodeLocation(id = location.findtext('ID'),
                            name = location.findtext('Name'),
                            country = 'US',
                            driver = self.connection.driver)
