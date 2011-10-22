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

try:
    import simplejson as json
except ImportError:
    import json

from xml.etree import ElementTree as ET
from base64 import b64encode
import hashlib
import sys

from libcloud.compute.base import NodeState, NodeDriver, Node, NodeLocation
from libcloud.common.base import ConnectionUserAndKey, Response
from libcloud.compute.base import NodeImage, NodeSize
from libcloud.common.types import InvalidCredsError
from libcloud.compute.providers import Provider
from libcloud.common.base import Response

API_HOST = ''
API_PORT = (4567, 443)
API_SECURE = True
DEFAULT_API_VERSION = '3.0'


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
            raise InvalidCredsError(self.body)
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
        headers['Authorization'] = ("Basic %s" % b64encode("%s:%s" %
                                                (self.user_id, pass_sha1)))
        return headers


class OpenNebulaNodeSize(NodeSize):

    def __init__(self, id, name, ram, disk, bandwidth, price, driver,
                 cpu=None, vcpu=None):
        self.cpu = cpu
        self.vcpu = vcpu
        super(OpenNebulaNodeSize, self).__init__(id=id, name=name, ram=ram,
                                                 disk=disk,
                                                 bandwidth=bandwidth,
                                                 price=price, driver=driver)

    def __repr__(self):
        return (('<NodeSize: id=%s, name=%s, ram=%s, disk=%s, bandwidth=%s, '
                 'price=%s, driver=%s, cpu=%s ...>')
                % (self.id, self.name, self.ram, self.disk, self.bandwidth,
                   self.price, self.driver.name, self.cpu))


class OpenNebulaNodeDriver(NodeDriver):
    """
    OpenNebula node driver
    """

    connectionCls = OpenNebulaConnection
    type = Provider.OPENNEBULA
    name = 'OpenNebula'

    NODE_STATE_MAP = {
        'pending': NodeState.PENDING,
        'hold': NodeState.PENDING,
        'prolog': NodeState.PENDING,
        'running': NodeState.RUNNING,
        'migrate': NodeState.PENDING,
        'epilog': NodeState.TERMINATED,
        'stopped': NodeState.TERMINATED,
        'suspended': NodeState.PENDING,
        'failed': NodeState.TERMINATED,
        'unknown': NodeState.UNKNOWN,
        'done': NodeState.TERMINATED,
    }

    def __new__(cls, key, secret=None, api_version=DEFAULT_API_VERSION,
                **kwargs):
        if cls is OpenNebulaNodeDriver:
            if api_version == '1.4':
                cls = OpenNebula_1_4_NodeDriver
            elif api_version == '3.0':
                cls = OpenNebula_3_0_NodeDriver
            else:
                raise NotImplementedError(
                    "No OpenNebulaNodeDriver found for API version %s" %
                    (api_version)
                )
            return super(OpenNebulaNodeDriver, cls).__new__(cls)

    def list_sizes(self, location=None):
        return [
            OpenNebulaNodeSize(id=1,
                name='small',
                ram=None,
                disk=None,
                bandwidth=None,
                price=None,
                driver=self),
            OpenNebulaNodeSize(id=2,
                name='medium',
                ram=None,
                disk=None,
                bandwidth=None,
                price=None,
                driver=self),
            OpenNebulaNodeSize(id=3,
                name='large',
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
        resp1 = self.connection.request(url, method='PUT',
                                        data=self._xml_action(compute_id,
                                                              'STOPPED'))

        if resp1.status == 400:
            return False

        resp2 = self.connection.request(url, method='PUT',
                                        data=self._xml_action(compute_id,
                                        'RESUME'))

        if resp2.status == 400:
            return False

        return True

    def destroy_node(self, node):
        url = '/compute/%s' % (str(node.id))
        resp = self.connection.request(url, method='DELETE')

        return resp.status == 204

    def create_node(self, **kwargs):
        """Create a new OpenNebula node

        See L{NodeDriver.create_node} for more keyword args.
        """
        compute = ET.Element('COMPUTE')

        name = ET.SubElement(compute, 'NAME')
        name.text = kwargs['name']

        xml = ET.tostring(compute)
        node = self.connection.request('/compute', method='POST',
                                       data=xml).object

        return self._to_node(node)

    def _to_images(self, object):
        images = []
        for element in object.findall("DISK"):
            image_id = element.attrib["href"].partition("/storage/")[2]
            image = self.connection.request(("/storage/%s" % (
                                             image_id))).object
            images.append(self._to_image(image))

        return images

    def _to_image(self, image):
        return NodeImage(id=image.findtext("ID"),
                         name=image.findtext("NAME"),
                         driver=self.connection.driver,
                         extra={"size": image.findtext("SIZE"),
                                "url": image.findtext("URL")})

    def _to_nodes(self, object):
        computes = []
        for element in object.findall("COMPUTE"):
            compute_id = element.attrib["href"].partition("/compute/")[2]
            compute = self.connection.request(("/compute/%s" % (
                                               compute_id))).object
            computes.append(self._to_node(compute))

        return computes

    def _extract_networks(self, compute):
        networks = []

        for element in compute.findall("NIC"):
            ip = element.element.attrib.get('ip', None)

            if ip is not None:
                networks.append(ip)

        return networks

    def _to_node(self, compute):
        try:
            state = self.NODE_STATE_MAP[compute.findtext("STATE")]
        except KeyError:
            state = NodeState.UNKNOWN

        networks = self._extract_networks(compute)

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


class OpenNebula_1_4_NodeDriver(OpenNebulaNodeDriver):
    pass


class OpenNebula_3_0_NodeDriver(OpenNebulaNodeDriver):
    def create_node(self, **kwargs):
        """Create a new OpenNebula node

        See L{NodeDriver.create_node} for more keyword args.
        """
        compute = ET.Element('COMPUTE')

        name = ET.SubElement(compute, 'NAME')
        name.text = kwargs['name']

        instance_type = ET.SubElement(compute, 'INSTANCE_TYPE')
        instance_type.text = kwargs['size'].name

        disk = ET.SubElement(compute, 'DISK')
        storage = ET.SubElement(disk, 'STORAGE', {'href': '/storage/%s' %
                                                  (str(kwargs['image'].id))})

        xml = ET.tostring(compute)
        node = self.connection.request('/compute', method='POST',
                                       data=xml).object

        return self._to_node(node)

    def list_sizes(self, location=None):
        return [
          OpenNebulaNodeSize(id=1,
                   name='small',
                   ram=1024,
                   cpu=1,
                   disk=None,
                   bandwidth=None,
                   price=None,
                   driver=self),
          OpenNebulaNodeSize(id=2,
                   name='medium',
                   ram=4096,
                   cpu=4,
                   disk=None,
                   bandwidth=None,
                   price=None,
                   driver=self),
          OpenNebulaNodeSize(id=3,
                   name='large',
                   ram=8192,
                   cpu=8,
                   disk=None,
                   bandwidth=None,
                   price=None,
                   driver=self),
          OpenNebulaNodeSize(id=4,
                   name='custom',
                   ram=0,
                   cpu=0,
                   disk=None,
                   bandwidth=None,
                   price=None,
                   driver=self),
        ]

    def _to_images(self, object):
        images = []
        for element in object.findall("STORAGE"):
            image_id = element.attrib["href"].partition("/storage/")[2]
            image = self.connection.request(("/storage/%s" %
                                             (image_id))).object
            images.append(self._to_image(image))

        return images

    def _to_image(self, image):
        return NodeImage(id=image.findtext("ID"),
                         name=image.findtext("NAME"),
                         driver=self.connection.driver,
                         extra={"description": image.findtext("DESCRIPTION"),
                                "TYPE": image.findtext("TYPE"),
                                "size": image.findtext("SIZE"),
                                "fstype": image.findtext("FSTYPE", None)})

    def _extract_networks(self, compute):
        networks = []
        for element in compute.findall("NIC"):
            for ip in element.findall("IP"):
                networks.append(ip)

        return networks
