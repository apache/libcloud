# Copyright 2002-2009, Distributed Systems Architecture Group, Universidad
# Complutense de Madrid (dsa-research.org)
#
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
OpenNebula driver
"""

from base64 import b64encode
import hashlib
from xml.etree import ElementTree as ET

from libcloud.providers import Provider
from libcloud.types import NodeState, InvalidCredsException
from libcloud.base import Response, ConnectionUserAndKey
from libcloud.base import NodeDriver, Node, NodeLocation
from libcloud.base import NodeImage, NodeSize


API_HOST = ''
API_PORT = (4567, 443)
API_SECURE = True


class OpenNebulaResponse(Response):

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299

    def parse_body(self):
        if not self.body:
            return None
        return ET.XML(self.body)

    def parse_error(self):
        if int(self.status) == 401:
            raise InvalidCredsException(self.body)
        return self.body


class OpenNebulaConnection(ConnectionUserAndKey):
    """
    Connection class for the OpenNebula driver
    """

    host = API_HOST
    port = API_PORT
    secure = API_SECURE
    responseCls = OpenNebulaResponse

    def add_default_headers(self, headers):
        pass_sha1 = hashlib.sha1(self.key).hexdigest()
        headers['Authorization'] = ("Basic %s" % b64encode("%s:%s" % (self.user_id, pass_sha1)))
        return headers


class OpenNebulaNodeDriver(NodeDriver):
    """
    OpenNebula node driver
    """

    connectionCls = OpenNebulaConnection
    type = Provider.OPENNEBULA
    name = 'OpenNebula'

    NODE_STATE_MAP = {
        'PENDING': NodeState.PENDING,
        'ACTIVE': NodeState.RUNNING,
        'DONE': NodeState.TERMINATED,
        'STOPPED': NodeState.TERMINATED
    }

    def list_sizes(self, location=None):
        return [
          NodeSize(id=1,
                   name="small",
                   ram=None,
                   disk=None,
                   bandwidth=None,
                   price=None,
                   driver=self),
          NodeSize(id=2,
                   name="medium",
                   ram=None,
                   disk=None,
                   bandwidth=None,
                   price=None,
                   driver=self),
          NodeSize(id=3,
                   name="large",
                   ram=None,
                   disk=None,
                   bandwidth=None,
                   price=None,
                   driver=self),
        ]

    def list_nodes(self):
        return self._to_nodes(self.connection.request('/compute').object)

    def list_images(self, location=None):
        return self._to_images(self.connection.request('/storage').object)

    def list_locations(self):
        return [NodeLocation(0,  'OpenNebula', 'ONE', self)]

    def reboot_node(self, node):
        compute_id = str(node.id)

        url = '/compute/%s' % compute_id
        resp1 = self.connection.request(url,method='PUT',data=self._xml_action(compute_id,'STOPPED'))

        if resp1.status == 400:
            return False

        resp2 = self.connection.request(url,method='PUT',data=self._xml_action(compute_id,'RESUME'))

        if resp2.status == 400:
            return False

        return True

    def destroy_node(self, node):
        url = '/compute/%s' % (str(node.id))
        resp = self.connection.request(url,method='DELETE')

        return resp.status == 204

    def create_node(self, **kwargs):
        """Create a new OpenNebula node

        See L{NodeDriver.create_node} for more keyword args.
        """
        compute = ET.Element('COMPUTE')

        name = ET.SubElement(compute, 'NAME')
        name.text = kwargs['name']

        # """
        # Other extractable (but unused) information
        # """
        # instance_type = ET.SubElement(compute, 'INSTANCE_TYPE')
        # instance_type.text = kwargs['size'].name
        #
        # storage = ET.SubElement(compute, 'STORAGE')
        # disk = ET.SubElement(storage, 'DISK', {'image': str(kwargs['image'].id),
        #                                        'dev': 'sda1'})

        xml = ET.tostring(compute)

        node = self.connection.request('/compute',method='POST',data=xml).object

        return self._to_node(node)

    def _to_images(self, object):
        images = []
        for element in object.findall("DISK"):
            image_id = element.attrib["href"].partition("/storage/")[2]
            image = self.connection.request(("/storage/%s" % (image_id))).object
            images.append(self._to_image(image))

        return images

    def _to_image(self, image):
        return NodeImage(id=image.findtext("ID"),
                         name=image.findtext("NAME"),
                         driver=self.connection.driver)

    def _to_nodes(self, object):
        computes = []
        for element in object.findall("COMPUTE"):
            compute_id = element.attrib["href"].partition("/compute/")[2]
            compute = self.connection.request(("/compute/%s" % (compute_id))).object
            computes.append(self._to_node(compute))

        return computes

    def _to_node(self, compute):
        try:
            state = self.NODE_STATE_MAP[compute.findtext("STATE")]
        except KeyError:
            state = NodeState.UNKNOWN

        networks = []
        for element in compute.findall("NIC"):
            networks.append(element.attrib["ip"])

        return Node(id=compute.findtext("ID"),
                    name=compute.findtext("NAME"),
                    state=state,
                    public_ip=networks,
                    private_ip=[],
                    driver=self.connection.driver)

    def _xml_action(self, compute_id, action):
        compute = ET.Element('COMPUTE')

        compute_id = ET.SubElement(compute, 'ID')
        compute_id.text = str(compute_id)

        state = ET.SubElement(compute, 'STATE')
        state.text = action

        xml = ET.tostring(compute)
        return xml
