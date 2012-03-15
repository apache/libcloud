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
OpenNebula.org driver.
"""

__docformat__ = 'epytext'

from xml.etree import ElementTree as ET
from base64 import b64encode
import hashlib

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import next
from libcloud.utils.py3 import b

from libcloud.compute.base import NodeState, NodeDriver, Node, NodeLocation
from libcloud.common.base import ConnectionUserAndKey, XmlResponse
from libcloud.compute.base import NodeImage, NodeSize
from libcloud.common.types import InvalidCredsError
from libcloud.compute.providers import Provider

__all__ = [
    'ACTION',
    'OpenNebulaResponse',
    'OpenNebulaConnection',
    'OpenNebulaNodeSize',
    'OpenNebulaNetwork',
    'OpenNebulaNodeDriver',
    'OpenNebula_1_4_NodeDriver',
    'OpenNebula_2_0_NodeDriver',
    'OpenNebula_3_0_NodeDriver',
    'OpenNebula_3_2_NodeDriver']

API_HOST = ''
API_PORT = (4567, 443)
API_SECURE = True
DEFAULT_API_VERSION = '3.2'


class ACTION(object):
    """
    All actions, except RESUME, only apply when the VM is in the "Running"
    state.
    """

    STOP = 'STOPPED'
    """
    The VM is stopped, and its memory state stored to a checkpoint file. VM
    state, and disk image, are transferred back to the front-end. Resuming
    the VM requires the VM instance to be re-scheduled.
    """

    SUSPEND = 'SUSPENDED'
    """
    The VM is stopped, and its memory state stored to a checkpoint file. The VM
    state, and disk image, are left on the host to be resumed later. Resuming
    the VM does not require the VM to be re-scheduled. Rather, after
    suspending, the VM resources are reserved for later resuming.
    """

    RESUME = 'RESUME'
    """
    The VM is resumed using the saved memory state from the checkpoint file,
    and the VM's disk image. The VM is either started immediately, or
    re-scheduled depending on how it was suspended.
    """

    CANCEL = 'CANCEL'
    """
    The VM is forcibly shutdown, its memory state is deleted. If a persistent
    disk image was used, that disk image is transferred back to the front-end.
    Any non-persistent disk images are deleted.
    """

    SHUTDOWN = 'SHUTDOWN'
    """
    The VM is gracefully shutdown by sending the ACPI signal. If the VM does
    not shutdown, then it is considered to still be running. If successfully,
    shutdown, its memory state is deleted. If a persistent disk image was used,
    that disk image is transferred back to the front-end. Any non-persistent
    disk images are deleted.
    """

    REBOOT = 'REBOOT'
    """
    Introduced in OpenNebula v3.2.

    The VM is gracefully restarted by sending the ACPI signal.
    """

    DONE = 'DONE'
    """
    The VM is forcibly shutdown, its memory state is deleted. If a persistent
    disk image was used, that disk image is transferred back to the front-end.
    Any non-persistent disk images are deleted.
    """


class OpenNebulaResponse(XmlResponse):
    """
    XmlResponse class for the OpenNebula.org driver.
    """

    def success(self):
        """
        Check if response has the appropriate HTTP response code to be a
        success.

        @rtype:  C{bool}
        @return: True is success, else False.
        """
        i = int(self.status)
        return i >= 200 and i <= 299

    def parse_error(self):
        """
        Check if response contains any errors.

        @raise: L{InvalidCredsError}

        @rtype:  C{ElementTree}
        @return: Contents of HTTP response body.
        """
        if int(self.status) == httplib.UNAUTHORIZED:
            raise InvalidCredsError(self.body)
        return self.body


class OpenNebulaConnection(ConnectionUserAndKey):
    """
    Connection class for the OpenNebula.org driver.
    """

    host = API_HOST
    port = API_PORT
    secure = API_SECURE
    responseCls = OpenNebulaResponse

    def add_default_headers(self, headers):
        """
        Add headers required by the OpenNebula.org OCCI interface.

        Includes adding Basic HTTP Authorization headers for authenticating
        against the OpenNebula.org OCCI interface.

        @type  headers: C{dict}
        @param headers: Dictionary containing HTTP headers.

        @rtype:  C{dict}
        @return: Dictionary containing updated headers.
        """
        pass_sha1 = hashlib.sha1(b(self.key)).hexdigest()
        headers['Authorization'] = ('Basic %s' % b64encode(b('%s:%s' %
                                                (self.user_id, pass_sha1))))
        return headers


class OpenNebulaNodeSize(NodeSize):
    """
    NodeSize class for the OpenNebula.org driver.
    """

    def __init__(self, id, name, ram, disk, bandwidth, price, driver,
                 cpu=None, vcpu=None):
        super(OpenNebulaNodeSize, self).__init__(id=id, name=name, ram=ram,
                                                 disk=disk,
                                                 bandwidth=bandwidth,
                                                 price=price, driver=driver)
        self.cpu = cpu
        self.vcpu = vcpu

    def __repr__(self):
        return (('<OpenNebulaNodeSize: id=%s, name=%s, ram=%s, disk=%s, '
                 'bandwidth=%s, price=%s, driver=%s, cpu=%s, vcpu=%s ...>')
                % (self.id, self.name, self.ram, self.disk, self.bandwidth,
                   self.price, self.driver.name, self.cpu, self.vcpu))


class OpenNebulaNetwork(object):
    """
    Provide a common interface for handling networks of all types.

    Network objects are analogous to physical switches connecting two or
    more physical nodes together. The Network object provides the interface in
    libcloud through which we can manipulate networks in different cloud
    providers in the same way. Network objects don't actually do much directly
    themselves, instead the network driver handles the connection to the
    network.

    You don't normally create a network object yourself; instead you use
    a driver and then have that create the network for you.

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNetworkDriver()
    >>> network = driver.create_network()
    >>> network = driver.list_networks()[0]
    >>> network.name
    'dummy-1'
    """

    def __init__(self, id, name, address, size, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.address = address
        self.size = size
        self.driver = driver
        self.uuid = self.get_uuid()
        self.extra = extra or {}

    def get_uuid(self):
        """
        Unique hash for this network.

        The hash is a function of an SHA1 hash of the network's ID and
        its driver which means that it should be unique between all
        networks. In some subclasses (e.g. GoGrid) there is no ID
        available so the public IP address is used. This means that,
        unlike a properly done system UUID, the same UUID may mean a
        different system install at a different time

        >>> from libcloud.network.drivers.dummy import DummyNetworkDriver
        >>> driver = DummyNetworkDriver()
        >>> network = driver.create_network()
        >>> network.get_uuid()
        'd3748461511d8b9b0e0bfa0d4d3383a619a2bb9f'

        Note, for example, that this example will always produce the
        same UUID!

        @rtype:  C{string}
        @return: Unique identifier for this instance.
        """
        return hashlib.sha1(b("%s:%d" % (self.id,
                                         self.driver.type))).hexdigest()

    def __repr__(self):
        return (('<OpenNebulaNetwork: uuid=%s, name=%s, address=%s, size=%s, '
                 'provider=%s ...>')
                % (self.uuid, self.name, self.address, self.size,
                   self.driver.name))


class OpenNebulaNodeDriver(NodeDriver):
    """
    OpenNebula.org node driver.
    """

    connectionCls = OpenNebulaConnection
    name = 'OpenNebula'
    type = Provider.OPENNEBULA

    NODE_STATE_MAP = {
        'INIT': NodeState.PENDING,
        'PENDING': NodeState.PENDING,
        'HOLD': NodeState.PENDING,
        'ACTIVE': NodeState.RUNNING,
        'STOPPED': NodeState.TERMINATED,
        'SUSPENDED': NodeState.PENDING,
        'DONE': NodeState.TERMINATED,
        'FAILED': NodeState.TERMINATED}

    def __new__(cls, key, secret=None, api_version=DEFAULT_API_VERSION,
                **kwargs):
        if cls is OpenNebulaNodeDriver:
            if api_version in ['1.4']:
                cls = OpenNebula_1_4_NodeDriver
            elif api_version in ['2.0', '2.2']:
                cls = OpenNebula_2_0_NodeDriver
            elif api_version in ['3.0']:
                cls = OpenNebula_3_0_NodeDriver
            elif api_version in ['3.2']:
                cls = OpenNebula_3_2_NodeDriver
            else:
                raise NotImplementedError(
                    "No OpenNebulaNodeDriver found for API version %s" %
                    (api_version))
            return super(OpenNebulaNodeDriver, cls).__new__(cls)

    def create_node(self, **kwargs):
        """
        Create a new OpenNebula node.

        See L{NodeDriver.create_node} for more keyword args.
        @type    networks: L{OpenNebulaNetwork} or C{list}
                           of L{OpenNebulaNetwork}s
        @keyword networks: List of virtual networks to which this node should
                           connect. (optional)

        @rtype:  L{Node}
        @return: Instance of a newly created node.
        """
        compute = ET.Element('COMPUTE')

        name = ET.SubElement(compute, 'NAME')
        name.text = kwargs['name']

        instance_type = ET.SubElement(compute, 'INSTANCE_TYPE')
        instance_type.text = kwargs['size'].name

        storage = ET.SubElement(compute, 'STORAGE')
        ET.SubElement(storage, 'DISK', {'image': '%s' %
                                                  (str(kwargs['image'].id))})

        if 'networks' in kwargs:
            if not isinstance(kwargs['networks'], list):
                kwargs['networks'] = [kwargs['networks']]

            networkGroup = ET.SubElement(compute, 'NETWORK')
            for network in kwargs['networks']:
                if network.address:
                    ET.SubElement(networkGroup, 'NIC',
                        {'network': '%s' % (str(network.id)),
                        'ip': network.address})
                else:
                    ET.SubElement(networkGroup, 'NIC',
                        {'network': '%s' % (str(network.id))})

        xml = ET.tostring(compute)
        node = self.connection.request('/compute', method='POST',
                                       data=xml).object

        return self._to_node(node)

    def destroy_node(self, node):
        url = '/compute/%s' % (str(node.id))
        resp = self.connection.request(url, method='DELETE')

        return resp.status == httplib.OK

    def list_nodes(self):
        return self._to_nodes(self.connection.request('/compute').object)

    def list_images(self, location=None):
        return self._to_images(self.connection.request('/storage').object)

    def list_sizes(self, location=None):
        """
        Return list of sizes on a provider.

        See L{NodeDriver.list_sizes} for more args.

        @rtype:  C{list} of L{OpenNebulaNodeSize}
        @return: List of compute node sizes supported by the cloud provider.
        """
        return [
            NodeSize(id=1,
                name='small',
                ram=None,
                disk=None,
                bandwidth=None,
                price=None,
                driver=self),
            NodeSize(id=2,
                name='medium',
                ram=None,
                disk=None,
                bandwidth=None,
                price=None,
                driver=self),
            NodeSize(id=3,
                name='large',
                ram=None,
                disk=None,
                bandwidth=None,
                price=None,
                driver=self),
        ]

    def list_locations(self):
        return [NodeLocation(0, '', '', self)]

    def ex_list_networks(self, location=None):
        """
        List virtual networks on a provider.

        @type  location: L{NodeLocation}
        @param location: Location from which to request a list of virtual
                         networks. (optional)

        @rtype:  C{list} of L{OpenNebulaNetwork}
        @return: List of virtual networks available to be connected to a
                 compute node.
        """
        return self._to_networks(self.connection.request('/network').object)

    def ex_node_action(self, node, action):
        """
        Build action representation and instruct node to commit action.

        Build action representation from the compute node ID, and the
        action which should be carried out on that compute node. Then
        instruct the node to carry out that action.

        @type  node: L{Node}
        @param node: Compute node instance.
        @type  action: C{str}
        @param action: Action to be carried out on the compute node.

        @rtype:  C{bool}
        @return: False if an HTTP Bad Request is received, else, True is
                 returned.
        """
        compute_node_id = str(node.id)

        compute = ET.Element('COMPUTE')

        compute_id = ET.SubElement(compute, 'ID')
        compute_id.text = compute_node_id

        state = ET.SubElement(compute, 'STATE')
        state.text = action

        xml = ET.tostring(compute)

        url = '/compute/%s' % compute_node_id
        resp = self.connection.request(url, method='PUT',
                                        data=xml)

        if resp.status == httplib.BAD_REQUEST:
            return False
        else:
            return True

    def _to_images(self, object):
        """
        Request a list of images and convert that list to a list of NodeImage
        objects.

        Request a list of images from the OpenNebula web interface, and
        issue a request to convert each XML object representation of an image
        to a NodeImage object.

        @rtype:  C{list} of L{NodeImage}
        @return: List of images.
        """
        images = []
        for element in object.findall('DISK'):
            image_id = element.attrib['href'].partition('/storage/')[2]
            image = self.connection.request(('/storage/%s' % (
                                             image_id))).object
            images.append(self._to_image(image))

        return images

    def _to_image(self, image):
        """
        Take XML object containing an image description and convert to
        NodeImage object.

        @type  image: L{ElementTree}
        @param image: XML representation of an image.

        @rtype:  L{NodeImage}
        @return: The newly extracted L{NodeImage}.
        """
        return NodeImage(id=image.findtext('ID'),
                         name=image.findtext('NAME'),
                         driver=self.connection.driver,
                         extra={'size': image.findtext('SIZE'),
                                'url': image.findtext('URL')})

    def _to_networks(self, object):
        """
        Request a list of networks and convert that list to a list of
        OpenNebulaNetwork objects.

        Request a list of networks from the OpenNebula web interface, and
        issue a request to convert each XML object representation of a network
        to an OpenNebulaNetwork object.

        @rtype:  C{list} of L{OpenNebulaNetwork}
        @return: List of virtual networks.
        """
        networks = []
        for element in object.findall('NETWORK'):
            network_id = element.attrib['href'].partition('/network/')[2]
            network_element = self.connection.request(('/network/%s' % (
                                             network_id))).object
            networks.append(self._to_network(network_element))

        return networks

    def _to_network(self, element):
        """
        Take XML object containing a network description and convert to
        OpenNebulaNetwork object.

        Take XML representation containing a network description and
        convert to OpenNebulaNetwork object.

        @rtype:  L{OpenNebulaNetwork}
        @return: The newly extracted L{OpenNebulaNetwork}.
        """
        return OpenNebulaNetwork(id=element.findtext('ID'),
                      name=element.findtext('NAME'),
                      address=element.findtext('ADDRESS'),
                      size=element.findtext('SIZE'),
                      driver=self.connection.driver)

    def _to_nodes(self, object):
        """
        Request a list of compute nodes and convert that list to a list of
        Node objects.

        Request a list of compute nodes from the OpenNebula web interface, and
        issue a request to convert each XML object representation of a node
        to a Node object.

        @rtype:  C{list} of L{Node}
        @return: A list of compute nodes.
        """
        computes = []
        for element in object.findall('COMPUTE'):
            compute_id = element.attrib['href'].partition('/compute/')[2]
            compute = self.connection.request(('/compute/%s' % (
                                               compute_id))).object
            computes.append(self._to_node(compute))

        return computes

    def _to_node(self, compute):
        """
        Take XML object containing a compute node description and convert to
        Node object.

        Take XML representation containing a compute node description and
        convert to Node object.

        @type  compute: L{ElementTree}
        @param compute: XML representation of a compute node.

        @rtype:  L{Node}
        @return: The newly extracted L{Node}.
        """
        try:
            state = self.NODE_STATE_MAP[compute.findtext('STATE').upper()]
        except KeyError:
            state = NodeState.UNKNOWN

        return Node(id=compute.findtext('ID'),
                    name=compute.findtext('NAME'),
                    state=state,
                    public_ips=self._extract_networks(compute),
                    private_ips=[],
                    driver=self.connection.driver,
                    image=self._extract_images(compute))

    def _extract_networks(self, compute):
        """
        Extract networks from a compute node XML representation.

        Extract network descriptions from a compute node XML representation,
        converting each network to an OpenNebulaNetwork object.

        @type  compute: L{ElementTree}
        @param compute: XML representation of a compute node.

        @rtype:  C{list} of L{OpenNebulaNetwork}s.
        @return: List of virtual networks attached to the compute node.
        """
        networks = list()

        network_list = compute.find('NETWORK')
        for element in network_list.findall('NIC'):
            networks.append(
                OpenNebulaNetwork(id=element.attrib.get('network', None),
                    name=None,
                    address=element.attrib.get('ip', None),
                    size=1,
                    driver=self.connection.driver))

        return networks

    def _extract_images(self, compute):
        """
        Extract image disks from a compute node XML representation.

        Extract image disk descriptions from a compute node XML representation,
        converting the disks to an NodeImage object.

        @type  compute: L{ElementTree}
        @param compute: XML representation of a compute node.

        @rtype:  L{NodeImage}.
        @return: First disk attached to a compute node.
        """
        disks = list()

        disk_list = compute.find('STORAGE')
        if disk_list is not None:
            for element in disk_list.findall('DISK'):
                disks.append(
                    NodeImage(id=element.attrib.get('image', None),
                        name=None,
                        driver=self.connection.driver,
                        extra={'dev': element.attrib.get('dev', None)}))

        # @TODO: Return all disks when the Node type accepts multiple
        # attached disks per node.
        if len(disks) > 0:
            return disks[0]
        else:
            return None


class OpenNebula_1_4_NodeDriver(OpenNebulaNodeDriver):
    """
    OpenNebula.org node driver for OpenNebula.org v1.4.
    """

    pass


class OpenNebula_2_0_NodeDriver(OpenNebulaNodeDriver):
    """
    OpenNebula.org node driver for OpenNebula.org v2.0 through OpenNebula.org
    v2.2.
    """

    def create_node(self, **kwargs):
        """
        Create a new OpenNebula node.

        See L{NodeDriver.create_node} for more keyword args.
        @type    networks: L{OpenNebulaNetwork} or C{list}
                           of L{OpenNebulaNetwork}s
        @keyword networks: List of virtual networks to which this node should
                           connect. (optional)
        @type    context: C{dict}
        @keyword context: Custom (key, value) pairs to be injected into
                          compute node XML description. (optional)

        @rtype:  L{Node}
        @return: Instance of a newly created node.
        """
        compute = ET.Element('COMPUTE')

        name = ET.SubElement(compute, 'NAME')
        name.text = kwargs['name']

        instance_type = ET.SubElement(compute, 'INSTANCE_TYPE')
        instance_type.text = kwargs['size'].name

        disk = ET.SubElement(compute, 'DISK')
        ET.SubElement(disk, 'STORAGE', {'href': '/storage/%s' %
                                                  (str(kwargs['image'].id))})

        if 'networks' in kwargs:
            if not isinstance(kwargs['networks'], list):
                kwargs['networks'] = [kwargs['networks']]

            for network in kwargs['networks']:
                nic = ET.SubElement(compute, 'NIC')
                ET.SubElement(nic, 'NETWORK',
                            {'href': '/network/%s' % (str(network.id))})
                if network.address:
                    ip_line = ET.SubElement(nic, 'IP')
                    ip_line.text = network.address

        if 'context' in kwargs:
            if isinstance(kwargs['context'], dict):
                contextGroup = ET.SubElement(compute, 'CONTEXT')
                for key, value in list(kwargs['context'].items()):
                    context = ET.SubElement(contextGroup, key.upper())
                    context.text = value

        xml = ET.tostring(compute)
        node = self.connection.request('/compute', method='POST',
                                       data=xml).object

        return self._to_node(node)

    def destroy_node(self, node):
        url = '/compute/%s' % (str(node.id))
        resp = self.connection.request(url, method='DELETE')

        return resp.status == httplib.NO_CONTENT

    def list_sizes(self, location=None):
        """
        Return list of sizes on a provider.

        See L{NodeDriver.list_sizes} for more args.

        @rtype:  C{list} of L{OpenNebulaNodeSize}
        @return: List of compute node sizes supported by the cloud provider.
        """
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
        """
        Request a list of images and convert that list to a list of NodeImage
        objects.

        Request a list of images from the OpenNebula web interface, and
        issue a request to convert each XML object representation of an image
        to a NodeImage object.

        @rtype:  C{list} of L{NodeImage}
        @return: List of images.
        """
        images = []
        for element in object.findall('STORAGE'):
            image_id = element.attrib["href"].partition("/storage/")[2]
            image = self.connection.request(("/storage/%s" %
                                             (image_id))).object
            images.append(self._to_image(image))

        return images

    def _to_image(self, image):
        """
        Take XML object containing an image description and convert to
        NodeImage object.

        @type  image: L{ElementTree}
        @param image: XML representation of an image.

        @rtype:  L{NodeImage}
        @return: The newly extracted L{NodeImage}.
        """
        return NodeImage(id=image.findtext('ID'),
                         name=image.findtext('NAME'),
                         driver=self.connection.driver,
                         extra={'description': image.findtext('DESCRIPTION'),
                                'type': image.findtext('TYPE'),
                                'size': image.findtext('SIZE'),
                                'fstype': image.findtext('FSTYPE', None)})

    def _to_node(self, compute):
        """
        Take XML object containing a compute node description and convert to
        Node object.

        Take XML representation containing a compute node description and
        convert to Node object.

        @type  compute: L{ElementTree}
        @param compute: XML representation of a compute node.

        @rtype:  L{Node}
        @return: The newly extracted L{Node}.
        """
        try:
            state = self.NODE_STATE_MAP[compute.findtext('STATE').upper()]
        except KeyError:
            state = NodeState.UNKNOWN

        return Node(id=compute.findtext('ID'),
                    name=compute.findtext('NAME'),
                    state=state,
                    public_ips=self._extract_networks(compute),
                    private_ips=[],
                    driver=self.connection.driver,
                    image=self._extract_images(compute),
                    size=self._extract_size(compute),
                    extra={'context': self._extract_context(compute)})

    def _extract_networks(self, compute):
        """
        Extract networks from a compute node XML representation.

        Extract network descriptions from a compute node XML representation,
        converting each network to an OpenNebulaNetwork object.

        @type  compute: L{ElementTree}
        @param compute: XML representation of a compute node.

        @rtype:  C{list} of L{OpenNebulaNetwork}
        @return: List of virtual networks attached to the compute node.
        """
        networks = []

        for element in compute.findall('NIC'):
            network = element.find('NETWORK')
            network_id = network.attrib['href'].partition('/network/')[2]

            networks.append(
                OpenNebulaNetwork(id=network_id,
                         name=network.attrib.get('name', None),
                         address=element.findtext('IP'),
                         size=1,
                         driver=self.connection.driver,
                         extra={'mac': element.findtext('MAC')}))

        return networks

    def _extract_images(self, compute):
        """
        Extract image disks from a compute node XML representation.

        Extract image disk descriptions from a compute node XML representation,
        converting the disks to an NodeImage object.

        @type  compute: L{ElementTree}
        @param compute: XML representation of a compute node.

        @rtype:  L{NodeImage}
        @return: First disk attached to a compute node.
        """
        disks = list()

        for element in compute.findall('DISK'):
            disk = element.find('STORAGE')
            disk_id = disk.attrib['href'].partition('/storage/')[2]

            disks.append(
                NodeImage(id=disk_id,
                    name=disk.attrib.get('name', None),
                    driver=self.connection.driver,
                    extra={'type': element.findtext('TYPE'),
                           'target': element.findtext('TARGET')}))

        # @TODO: Return all disks when the Node type accepts multiple
        # attached disks per node.
        if len(disks) > 0:
            return disks[0]
        else:
            return None

    def _extract_size(self, compute):
        """
        Extract size, or node type, from a compute node XML representation.

        Extract node size, or node type, description from a compute node XML
        representation, converting the node size to a NodeSize object.

        @type  compute: L{ElementTree}
        @param compute: XML representation of a compute node.

        @rtype:  L{OpenNebulaNodeSize}
        @return: Node type of compute node.
        """
        instance_type = compute.find('INSTANCE_TYPE')

        try:
            return next((node_size for node_size in self.list_sizes()
                    if node_size.name == instance_type.text))
        except StopIteration:
            return None

    def _extract_context(self, compute):
        """
        Extract size, or node type, from a compute node XML representation.

        Extract node size, or node type, description from a compute node XML
        representation, converting the node size to a NodeSize object.

        @type  compute: L{ElementTree}
        @param compute: XML representation of a compute node.

        @rtype:  C{dict}
        @return: Dictionary containing (key, value) pairs related to
                 compute node context.
        """
        contexts = dict()
        context = compute.find('CONTEXT')

        if context is not None:
            for context_element in list(context):
                contexts[context_element.tag.lower()] = context_element.text

        return contexts


class OpenNebula_3_0_NodeDriver(OpenNebula_2_0_NodeDriver):
    """
    OpenNebula.org node driver for OpenNebula.org v3.0.
    """

    def ex_node_set_save_name(self, node, name):
        """
        Build action representation and instruct node to commit action.

        Build action representation from the compute node ID, the disk image
        which will be saved, and the name under which the image will be saved
        upon shutting down the compute node.

        @type  node: L{Node}
        @param node: Compute node instance.
        @type  name: C{str}
        @param name: Name under which the image should be saved after shutting
                     down the compute node.

        @rtype:  C{bool}
        @return: False if an HTTP Bad Request is received, else, True is
                 returned.
        """
        compute_node_id = str(node.id)

        compute = ET.Element('COMPUTE')

        compute_id = ET.SubElement(compute, 'ID')
        compute_id.text = compute_node_id

        disk = ET.SubElement(compute, 'DISK', {'id': str(node.image.id)})

        ET.SubElement(disk, 'STORAGE', {'href': '/storage/%s' %
                                        (str(node.image.id)),
                                        'name': node.image.name})

        ET.SubElement(disk, 'SAVE_AS', {'name': str(name)})

        xml = ET.tostring(compute)

        url = '/compute/%s' % compute_node_id
        resp = self.connection.request(url, method='PUT',
                                        data=xml)

        if resp.status == httplib.BAD_REQUEST:
            return False
        else:
            return True

    def _to_network(self, element):
        """
        Take XML object containing a network description and convert to
        OpenNebulaNetwork object.

        Take XML representation containing a network description and
        convert to OpenNebulaNetwork object.

        @rtype:  L{OpenNebulaNetwork}
        @return: The newly extracted L{OpenNebulaNetwork}.
        """
        return OpenNebulaNetwork(id=element.findtext('ID'),
                      name=element.findtext('NAME'),
                      address=element.findtext('ADDRESS'),
                      size=element.findtext('SIZE'),
                      driver=self.connection.driver,
                      extra={'public': element.findtext('PUBLIC')})


class OpenNebula_3_2_NodeDriver(OpenNebula_3_0_NodeDriver):
    """
    OpenNebula.org node driver for OpenNebula.org v3.2.
    """

    def reboot_node(self, node):
        return self.ex_node_action(node, ACTION.REBOOT)

    def list_sizes(self, location=None):
        """
        Return list of sizes on a provider.

        See L{NodeDriver.list_sizes} for more args.

        @rtype:  C{list} of L{OpenNebulaNodeSize}
        @return: List of compute node sizes supported by the cloud provider.
        """
        return self._to_sizes(self.connection.request('/instance_type').object)

    def _to_sizes(self, object):
        """
        Request a list of instance types and convert that list to a list of
        OpenNebulaNodeSize objects.

        Request a list of instance types from the OpenNebula web interface,
        and issue a request to convert each XML object representation of an
        instance type to an OpenNebulaNodeSize object.

        @rtype:  C{list} of L{OpenNebulaNodeSize}
        @return: List of instance types.
        """
        sizes = []
        ids = 1
        for element in object.findall('INSTANCE_TYPE'):
            sizes.append(OpenNebulaNodeSize(id=ids,
                         name=element.findtext('NAME'),
                         ram=int(element.findtext('MEMORY'))
                             if element.findtext('MEMORY', None) else None,
                         cpu=float(element.findtext('CPU'))
                             if element.findtext('CPU', None) else None,
                         vcpu=int(element.findtext('VCPU'))
                             if element.findtext('VCPU', None) else None,
                         disk=element.findtext('DISK', None),
                         bandwidth=float(element.findtext('BANDWIDTH'))
                             if element.findtext('BANDWIDTH', None) else None,
                         price=float(element.findtext('PRICE'))
                             if element.findtext('PRICE', None) else None,
                         driver=self))
            ids += 1

        return sizes
