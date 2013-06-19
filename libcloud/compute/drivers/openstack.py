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
OpenStack driver
"""

try:
    import simplejson as json
except ImportError:
    import json

import warnings

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b
from libcloud.utils.py3 import next
from libcloud.utils.py3 import urlparse

import base64

from xml.etree import ElementTree as ET

from libcloud.common.openstack import OpenStackBaseConnection
from libcloud.common.openstack import OpenStackDriverMixin
from libcloud.common.types import MalformedResponseError
from libcloud.compute.types import NodeState, Provider
from libcloud.compute.base import NodeSize, NodeImage
from libcloud.compute.base import NodeDriver, Node, NodeLocation
from libcloud.pricing import get_size_price
from libcloud.common.base import Response
from libcloud.utils.xml import findall

__all__ = [
    'OpenStack_1_0_Response',
    'OpenStack_1_0_Connection',
    'OpenStack_1_0_NodeDriver',
    'OpenStack_1_0_SharedIpGroup',
    'OpenStack_1_0_NodeIpAddresses',
    'OpenStack_1_1_Response',
    'OpenStack_1_1_Connection',
    'OpenStack_1_1_NodeDriver',
    'OpenStackNodeDriver'
]

ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"

DEFAULT_API_VERSION = '1.1'


class OpenStackResponse(Response):
    node_driver = None

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299

    def has_content_type(self, content_type):
        content_type_value = self.headers.get('content-type') or ''
        content_type_value = content_type_value.lower()
        return content_type_value.find(content_type.lower()) > -1

    def parse_body(self):
        if self.status == httplib.NO_CONTENT or not self.body:
            return None

        if self.has_content_type('application/xml'):
            try:
                return ET.XML(self.body)
            except:
                raise MalformedResponseError(
                    'Failed to parse XML',
                    body=self.body,
                    driver=self.node_driver)

        elif self.has_content_type('application/json'):
            try:
                return json.loads(self.body)
            except:
                raise MalformedResponseError(
                    'Failed to parse JSON',
                    body=self.body,
                    driver=self.node_driver)
        else:
            return self.body

    def parse_error(self):
        text = None
        body = self.parse_body()

        if self.has_content_type('application/xml'):
            text = "; ".join([err.text or '' for err in body.getiterator()
                              if err.text])
        elif self.has_content_type('application/json'):
            values = body.values()

            if len(values) > 0 and 'message' in values[0]:
                text = ';'.join([fault_data['message'] for fault_data
                                 in values])
            else:
                text = body
        else:
            # while we hope a response is always one of xml or json, we have
            # seen html or text in the past, its not clear we can really do
            # something to make it more readable here, so we will just pass
            # it along as the whole response body in the text variable.
            text = body

        return '%s %s %s' % (self.status, self.error, text)


class OpenStackComputeConnection(OpenStackBaseConnection):
    # default config for http://devstack.org/
    service_type = 'compute'
    service_name = 'nova'
    service_region = 'RegionOne'

    def request(self, action, params=None, data='', headers=None,
                method='GET'):
        if not headers:
            headers = {}
        if not params:
            params = {}

        if method in ("POST", "PUT"):
            headers = {'Content-Type': self.default_content_type}

        if method == "GET":
            self._add_cache_busting_to_params(params)

        return super(OpenStackComputeConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers)


class OpenStackNodeDriver(NodeDriver, OpenStackDriverMixin):
    """
    Base OpenStack node driver. Should not be used directly.
    """
    api_name = 'openstack'
    name = 'OpenStack'
    website = 'http://openstack.org/'

    NODE_STATE_MAP = {
        'BUILD': NodeState.PENDING,
        'REBUILD': NodeState.PENDING,
        'ACTIVE': NodeState.RUNNING,
        'SUSPENDED': NodeState.TERMINATED,
        'DELETED': NodeState.TERMINATED,
        'QUEUE_RESIZE': NodeState.PENDING,
        'PREP_RESIZE': NodeState.PENDING,
        'VERIFY_RESIZE': NodeState.RUNNING,
        'PASSWORD': NodeState.PENDING,
        'RESCUE': NodeState.PENDING,
        'REBOOT': NodeState.REBOOTING,
        'HARD_REBOOT': NodeState.REBOOTING,
        'SHARE_IP': NodeState.PENDING,
        'SHARE_IP_NO_CONFIG': NodeState.PENDING,
        'DELETE_IP': NodeState.PENDING,
        'UNKNOWN': NodeState.UNKNOWN
    }

    def __new__(cls, key, secret=None, secure=True, host=None, port=None,
                api_version=DEFAULT_API_VERSION, **kwargs):
        if cls is OpenStackNodeDriver:
            if api_version == '1.0':
                cls = OpenStack_1_0_NodeDriver
            elif api_version == '1.1':
                cls = OpenStack_1_1_NodeDriver
            else:
                raise NotImplementedError(
                    "No OpenStackNodeDriver found for API version %s" %
                    (api_version))
        return super(OpenStackNodeDriver, cls).__new__(cls)

    def __init__(self, *args, **kwargs):
        OpenStackDriverMixin.__init__(self, **kwargs)
        super(OpenStackNodeDriver, self).__init__(*args, **kwargs)

    def destroy_node(self, node):
        uri = '/servers/%s' % (node.id)
        resp = self.connection.request(uri, method='DELETE')
        # The OpenStack and Rackspace documentation both say this API will
        # return a 204, but in-fact, everyone everywhere agrees it actually
        # returns a 202, so we are going to accept either, and someday,
        # someone will fix either the implementation or the documentation to
        # agree.
        return resp.status in (httplib.NO_CONTENT, httplib.ACCEPTED)

    def reboot_node(self, node):
        return self._reboot_node(node, reboot_type='HARD')

    def list_nodes(self):
        return self._to_nodes(
            self.connection.request('/servers/detail').object)

    def list_images(self, location=None, ex_only_active=True):
        """
        @inherits: L{NodeDriver.list_images}

        @param ex_only_active: True if list only active
        @type ex_only_active: C{bool}

        """
        return self._to_images(
            self.connection.request('/images/detail').object, ex_only_active)

    def list_sizes(self, location=None):
        return self._to_sizes(
            self.connection.request('/flavors/detail').object)

    def list_locations(self):
        return [NodeLocation(0, '', '', self)]

    def _ex_connection_class_kwargs(self):
        return self.openstack_connection_kwargs()

    def ex_get_node_details(self, node_id):
        """
        Lists details of the specified server.

        @param       node_id: ID of the node which should be used
        @type        node_id: C{str}

        @rtype: L{Node}
        """
        # @TODO: Remove this if in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        uri = '/servers/%s' % (node_id)
        resp = self.connection.request(uri, method='GET')
        if resp.status == httplib.NOT_FOUND:
            return None

        return self._to_node_from_obj(resp.object)

    def ex_soft_reboot_node(self, node):
        """
        Soft reboots the specified server

        @param      node:  node
        @type       node: L{Node}

        @rtype: C{bool}
        """
        return self._reboot_node(node, reboot_type='SOFT')

    def ex_hard_reboot_node(self, node):
        """
        Hard reboots the specified server

        @param      node:  node
        @type       node: L{Node}

        @rtype: C{bool}
        """
        return self._reboot_node(node, reboot_type='HARD')


class OpenStackNodeSize(NodeSize):
    """
    NodeSize class for the OpenStack.org driver.

    Following the example of OpenNebula.org driver
    and following guidelines:
    https://issues.apache.org/jira/browse/LIBCLOUD-119
    """

    def __init__(self, id, name, ram, disk, bandwidth, price, driver,
                 vcpus=None):
        super(OpenStackNodeSize, self).__init__(id=id, name=name, ram=ram,
                                                disk=disk,
                                                bandwidth=bandwidth,
                                                price=price, driver=driver)
        self.vcpus = vcpus

    def __repr__(self):
        return (('<OpenStackNodeSize: id=%s, name=%s, ram=%s, disk=%s, '
                 'bandwidth=%s, price=%s, driver=%s, vcpus=%s,  ...>')
                % (self.id, self.name, self.ram, self.disk, self.bandwidth,
                   self.price, self.driver.name, self.vcpus))


class OpenStack_1_0_Response(OpenStackResponse):
    def __init__(self, *args, **kwargs):
        # done because of a circular reference from
        # NodeDriver -> Connection -> Response
        self.node_driver = OpenStack_1_0_NodeDriver
        super(OpenStack_1_0_Response, self).__init__(*args, **kwargs)


class OpenStack_1_0_Connection(OpenStackComputeConnection):
    responseCls = OpenStack_1_0_Response
    default_content_type = 'application/xml; charset=UTF-8'
    accept_format = 'application/xml'
    XML_NAMESPACE = 'http://docs.rackspacecloud.com/servers/api/v1.0'


class OpenStack_1_0_NodeDriver(OpenStackNodeDriver):
    """
    OpenStack node driver.

    Extra node attributes:
        - password: root password, available after create.
        - hostId: represents the host your cloud server runs on
        - imageId: id of image
        - flavorId: id of flavor
    """
    connectionCls = OpenStack_1_0_Connection
    type = Provider.OPENSTACK

    features = {"create_node": ["generates_password"]}

    def __init__(self, *args, **kwargs):
        self._ex_force_api_version = str(kwargs.pop('ex_force_api_version',
                                                    None))
        self.XML_NAMESPACE = self.connectionCls.XML_NAMESPACE
        super(OpenStack_1_0_NodeDriver, self).__init__(*args, **kwargs)

    def _to_images(self, object, ex_only_active):
        images = []
        for image in findall(object, 'image', self.XML_NAMESPACE):
            if ex_only_active and image.get('status') != 'ACTIVE':
                continue
            images.append(self._to_image(image))

        return images

    def _to_image(self, element):
        return NodeImage(id=element.get('id'),
                         name=element.get('name'),
                         driver=self.connection.driver,
                         extra={'updated': element.get('updated'),
                                'created': element.get('created'),
                                'status': element.get('status'),
                                'serverId': element.get('serverId'),
                                'progress': element.get('progress'),
                                'minDisk': element.get('minDisk'),
                                'minRam': element.get('minRam')
                                }
                         )

    def _change_password_or_name(self, node, name=None, password=None):
        uri = '/servers/%s' % (node.id)

        if not name:
            name = node.name

        body = {'xmlns': self.XML_NAMESPACE,
                'name': name}

        if password is not None:
            body['adminPass'] = password

        server_elm = ET.Element('server', body)

        resp = self.connection.request(
            uri, method='PUT', data=ET.tostring(server_elm))

        if resp.status == httplib.NO_CONTENT and password is not None:
            node.extra['password'] = password

        return resp.status == httplib.NO_CONTENT

    def create_node(self, **kwargs):
        """
        Create a new node

        @inherits: L{NodeDriver.create_node}

        @keyword    ex_metadata: Key/Value metadata to associate with a node
        @type       ex_metadata: C{dict}

        @keyword    ex_files:   File Path => File contents to create on
                                the node
        @type       ex_files:   C{dict}

        @keyword    ex_shared_ip_group_id: The server is launched into
            that shared IP group
        @type       ex_shared_ip_group_id: C{str}
        """
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']

        attributes = {'xmlns': self.XML_NAMESPACE,
                      'name': name,
                      'imageId': str(image.id),
                      'flavorId': str(size.id)}

        if 'ex_shared_ip_group' in kwargs:
            # Deprecate this. Be explicit and call the variable
            # ex_shared_ip_group_id since user needs to pass in the id, not the
            # name.
            warnings.warn('ex_shared_ip_group argument is deprecated.'
                          ' Please use ex_shared_ip_group_id')

        if 'ex_shared_ip_group_id' in kwargs:
            shared_ip_group_id = kwargs['ex_shared_ip_group_id']
            attributes['sharedIpGroupId'] = shared_ip_group_id

        server_elm = ET.Element('server', attributes)

        metadata_elm = self._metadata_to_xml(kwargs.get("ex_metadata", {}))
        if metadata_elm:
            server_elm.append(metadata_elm)

        files_elm = self._files_to_xml(kwargs.get("ex_files", {}))
        if files_elm:
            server_elm.append(files_elm)

        resp = self.connection.request("/servers",
                                       method='POST',
                                       data=ET.tostring(server_elm))
        return self._to_node(resp.object)

    def ex_set_password(self, node, password):
        """
        Sets the Node's root password.

        This will reboot the instance to complete the operation.

        L{Node.extra['password']} will be set to the new value if the
        operation was successful.

        @param      node: node to set password
        @type       node: L{Node}

        @param      password: new password.
        @type       password: C{str}

        @rtype: C{bool}
        """
        return self._change_password_or_name(node, password=password)

    def ex_set_server_name(self, node, name):
        """
        Sets the Node's name.

        This will reboot the instance to complete the operation.

        @param      node: node to set name
        @type       node: L{Node}

        @param      name: new name
        @type       name: C{str}

        @rtype: C{bool}
        """
        return self._change_password_or_name(node, name=name)

    def ex_resize(self, node, size):
        """
        Change an existing server flavor / scale the server up or down.

        @param      node: node to resize.
        @type       node: L{Node}

        @param      size: new size.
        @type       size: L{NodeSize}

        @rtype: C{bool}
        """
        elm = ET.Element(
            'resize',
            {'xmlns': self.XML_NAMESPACE,
             'flavorId': str(size.id)}
        )

        resp = self.connection.request("/servers/%s/action" % (node.id),
                                       method='POST',
                                       data=ET.tostring(elm))
        return resp.status == httplib.ACCEPTED

    def ex_confirm_resize(self, node):
        """
        Confirm a resize request which is currently in progress. If a resize
        request is not explicitly confirmed or reverted it's automatically
        confirmed after 24 hours.

        For more info refer to the API documentation: http://goo.gl/zjFI1

        @param      node: node for which the resize request will be confirmed.
        @type       node: L{Node}

        @rtype: C{bool}
        """
        elm = ET.Element(
            'confirmResize',
            {'xmlns': self.XML_NAMESPACE},
        )

        resp = self.connection.request("/servers/%s/action" % (node.id),
                                       method='POST',
                                       data=ET.tostring(elm))
        return resp.status == httplib.NO_CONTENT

    def ex_revert_resize(self, node):
        """
        Revert a resize request which is currently in progress.
        All resizes are automatically confirmed after 24 hours if they have
        not already been confirmed explicitly or reverted.

        For more info refer to the API documentation: http://goo.gl/AizBu

        @param      node: node for which the resize request will be reverted.
        @type       node: L{Node}

        @rtype: C{bool}
        """
        elm = ET.Element(
            'revertResize',
            {'xmlns': self.XML_NAMESPACE}
        )

        resp = self.connection.request("/servers/%s/action" % (node.id),
                                       method='POST',
                                       data=ET.tostring(elm))
        return resp.status == httplib.NO_CONTENT

    def ex_rebuild(self, node_id, image_id):
        """
        Rebuilds the specified server.

        @param       node_id: ID of the node which should be used
        @type        node_id: C{str}

        @param       image_id: ID of the image which should be used
        @type        image_id: C{str}

        @rtype: C{bool}
        """
        # @TODO: Remove those ifs in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        if isinstance(image_id, NodeImage):
            image_id = image_id.id

        elm = ET.Element(
            'rebuild',
            {'xmlns': self.XML_NAMESPACE,
             'imageId': image_id}
        )

        resp = self.connection.request("/servers/%s/action" % node_id,
                                       method='POST',
                                       data=ET.tostring(elm))
        return resp.status == httplib.ACCEPTED

    def ex_create_ip_group(self, group_name, node_id=None):
        """
        Creates a shared IP group.

        @param       group_name:  group name which should be used
        @type        group_name: C{str}

        @param       node_id: ID of the node which should be used
        @type        node_id: C{str}

        @rtype: C{bool}
        """
        # @TODO: Remove this if in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        group_elm = ET.Element(
            'sharedIpGroup',
            {'xmlns': self.XML_NAMESPACE,
             'name': group_name}
        )

        if node_id:
            ET.SubElement(
                group_elm,
                'server',
                {'id': node_id}
            )

        resp = self.connection.request('/shared_ip_groups',
                                       method='POST',
                                       data=ET.tostring(group_elm))
        return self._to_shared_ip_group(resp.object)

    def ex_list_ip_groups(self, details=False):
        """
        Lists IDs and names for shared IP groups.
        If details lists all details for shared IP groups.

        @param       details: True if details is required
        @type        details: C{bool}

        @rtype: C{list} of L{OpenStack_1_0_SharedIpGroup}
        """
        uri = '/shared_ip_groups/detail' if details else '/shared_ip_groups'
        resp = self.connection.request(uri,
                                       method='GET')
        groups = findall(resp.object, 'sharedIpGroup',
                         self.XML_NAMESPACE)
        return [self._to_shared_ip_group(el) for el in groups]

    def ex_delete_ip_group(self, group_id):
        """
        Deletes the specified shared IP group.

        @param       group_id:  group id which should be used
        @type        group_id: C{str}

        @rtype: C{bool}
        """
        uri = '/shared_ip_groups/%s' % group_id
        resp = self.connection.request(uri, method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def ex_share_ip(self, group_id, node_id, ip, configure_node=True):
        """
        Shares an IP address to the specified server.

        @param       group_id:  group id which should be used
        @type        group_id: C{str}

        @param       node_id: ID of the node which should be used
        @type        node_id: C{str}

        @param       ip: ip which should be used
        @type        ip: C{str}

        @param       configure_node: configure node
        @type        configure_node: C{bool}

        @rtype: C{bool}
        """
        # @TODO: Remove this if in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        if configure_node:
            str_configure = 'true'
        else:
            str_configure = 'false'

        elm = ET.Element(
            'shareIp',
            {'xmlns': self.XML_NAMESPACE,
             'sharedIpGroupId': group_id,
             'configureServer': str_configure},
        )

        uri = '/servers/%s/ips/public/%s' % (node_id, ip)

        resp = self.connection.request(uri,
                                       method='PUT',
                                       data=ET.tostring(elm))
        return resp.status == httplib.ACCEPTED

    def ex_unshare_ip(self, node_id, ip):
        """
        Removes a shared IP address from the specified server.

        @param       node_id: ID of the node which should be used
        @type        node_id: C{str}

        @param       ip: ip which should be used
        @type        ip: C{str}

        @rtype: C{bool}
        """
        # @TODO: Remove this if in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        uri = '/servers/%s/ips/public/%s' % (node_id, ip)

        resp = self.connection.request(uri,
                                       method='DELETE')
        return resp.status == httplib.ACCEPTED

    def ex_list_ip_addresses(self, node_id):
        """
        List all server addresses.

        @param       node_id: ID of the node which should be used
        @type        node_id: C{str}

        @rtype: C{bool}
        """
        # @TODO: Remove this if in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        uri = '/servers/%s/ips' % node_id
        resp = self.connection.request(uri,
                                       method='GET')
        return self._to_ip_addresses(resp.object)

    def _metadata_to_xml(self, metadata):
        if len(metadata) == 0:
            return None

        metadata_elm = ET.Element('metadata')
        for k, v in list(metadata.items()):
            meta_elm = ET.SubElement(metadata_elm, 'meta', {'key': str(k)})
            meta_elm.text = str(v)

        return metadata_elm

    def _files_to_xml(self, files):
        if len(files) == 0:
            return None

        personality_elm = ET.Element('personality')
        for k, v in list(files.items()):
            file_elm = ET.SubElement(personality_elm,
                                     'file',
                                     {'path': str(k)})
            file_elm.text = base64.b64encode(b(v))

        return personality_elm

    def _reboot_node(self, node, reboot_type='SOFT'):
        resp = self._node_action(node, ['reboot', ('type', reboot_type)])
        return resp.status == httplib.ACCEPTED

    def _node_action(self, node, body):
        if isinstance(body, list):
            attr = ' '.join(['%s="%s"' % (item[0], item[1])
                             for item in body[1:]])
            body = '<%s xmlns="%s" %s/>' % (body[0], self.XML_NAMESPACE, attr)
        uri = '/servers/%s/action' % (node.id)
        resp = self.connection.request(uri, method='POST', data=body)
        return resp

    def _to_nodes(self, object):
        node_elements = findall(object, 'server', self.XML_NAMESPACE)
        return [self._to_node(el) for el in node_elements]

    def _to_node_from_obj(self, obj):
        return self._to_node(findall(obj, 'server', self.XML_NAMESPACE)[0])

    def _to_node(self, el):
        def get_ips(el):
            return [ip.get('addr') for ip in el]

        def get_meta_dict(el):
            d = {}
            for meta in el:
                d[meta.get('key')] = meta.text
            return d

        public_ip = get_ips(findall(el, 'addresses/public/ip',
                                    self.XML_NAMESPACE))
        private_ip = get_ips(findall(el, 'addresses/private/ip',
                                     self.XML_NAMESPACE))
        metadata = get_meta_dict(findall(el, 'metadata/meta',
                                         self.XML_NAMESPACE))

        n = Node(id=el.get('id'),
                 name=el.get('name'),
                 state=self.NODE_STATE_MAP.get(
                     el.get('status'), NodeState.UNKNOWN),
                 public_ips=public_ip,
                 private_ips=private_ip,
                 driver=self.connection.driver,
                 extra={
                     'password': el.get('adminPass'),
                     'hostId': el.get('hostId'),
                     'imageId': el.get('imageId'),
                     'flavorId': el.get('flavorId'),
                     'uri': "https://%s%s/servers/%s" % (
                         self.connection.host,
                         self.connection.request_path, el.get('id')),
                     'metadata': metadata,
                 })
        return n

    def _to_sizes(self, object):
        elements = findall(object, 'flavor', self.XML_NAMESPACE)
        return [self._to_size(el) for el in elements]

    def _to_size(self, el):
        vcpus = int(el.get('vcpus')) if el.get('vcpus', None) else None
        return OpenStackNodeSize(id=el.get('id'),
                                 name=el.get('name'),
                                 ram=int(el.get('ram')),
                                 disk=int(el.get('disk')),
                                 # XXX: needs hardcode
                                 vcpus=vcpus,
                                 bandwidth=None,
                                 # Hardcoded
                                 price=self._get_size_price(el.get('id')),
                                 driver=self.connection.driver)

    def ex_limits(self):
        """
        Extra call to get account's limits, such as
        rates (for example amount of POST requests per day)
        and absolute limits like total amount of available
        RAM to be used by servers.

        @return: dict with keys 'rate' and 'absolute'
        @rtype: C{dict}
        """

        def _to_rate(el):
            rate = {}
            for item in list(el.items()):
                rate[item[0]] = item[1]

            return rate

        def _to_absolute(el):
            return {el.get('name'): el.get('value')}

        limits = self.connection.request("/limits").object
        rate = [_to_rate(el) for el in findall(limits, 'rate/limit',
                                               self.XML_NAMESPACE)]
        absolute = {}
        for item in findall(limits, 'absolute/limit',
                            self.XML_NAMESPACE):
            absolute.update(_to_absolute(item))

        return {"rate": rate, "absolute": absolute}

    def ex_save_image(self, node, name):
        """Create an image for node.

        @param      node: node to use as a base for image
        @type       node: L{Node}

        @param      name: name for new image
        @type       name: C{str}

        @rtype: L{NodeImage}
        """

        image_elm = ET.Element(
            'image',
            {'xmlns': self.XML_NAMESPACE,
             'name': name,
             'serverId': node.id}
        )

        return self._to_image(
            self.connection.request("/images", method="POST",
                                    data=ET.tostring(image_elm)).object)

    def ex_delete_image(self, image):
        """Delete an image for node.

        @param      image: the image to be deleted
        @type       image: L{NodeImage}

        @rtype: C{bool}
        """
        uri = '/images/%s' % image.id
        resp = self.connection.request(uri, method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def _to_shared_ip_group(self, el):
        servers_el = findall(el, 'servers', self.XML_NAMESPACE)
        if servers_el:
            servers = [s.get('id')
                       for s in findall(servers_el[0], 'server',
                                        self.XML_NAMESPACE)]
        else:
            servers = None
        return OpenStack_1_0_SharedIpGroup(id=el.get('id'),
                                           name=el.get('name'),
                                           servers=servers)

    def _to_ip_addresses(self, el):
        public_ips = [ip.get('addr') for ip in findall(
            findall(el, 'public', self.XML_NAMESPACE)[0],
            'ip', self.XML_NAMESPACE)]
        private_ips = [ip.get('addr') for ip in findall(
            findall(el, 'private', self.XML_NAMESPACE)[0],
            'ip', self.XML_NAMESPACE)]

        return OpenStack_1_0_NodeIpAddresses(public_ips, private_ips)

    def _get_size_price(self, size_id):
        try:
            return get_size_price(driver_type='compute',
                                  driver_name=self.api_name,
                                  size_id=size_id)
        except KeyError:
            return 0.0


class OpenStack_1_0_SharedIpGroup(object):
    """
    Shared IP group info.
    """

    def __init__(self, id, name, servers=None):
        self.id = str(id)
        self.name = name
        self.servers = servers


class OpenStack_1_0_NodeIpAddresses(object):
    """
    List of public and private IP addresses of a Node.
    """

    def __init__(self, public_addresses, private_addresses):
        self.public_addresses = public_addresses
        self.private_addresses = private_addresses


class OpenStack_1_1_Response(OpenStackResponse):
    def __init__(self, *args, **kwargs):
        # done because of a circular reference from
        # NodeDriver -> Connection -> Response
        self.node_driver = OpenStack_1_1_NodeDriver
        super(OpenStack_1_1_Response, self).__init__(*args, **kwargs)


class OpenStackNetwork(object):
    """
    A Virtual Network.
    """

    def __init__(self, id, name, cidr, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.cidr = cidr
        self.driver = driver
        self.extra = extra or {}

    def __repr__(self):
        return '<OpenStackNetwork id="%s" name="%s" cidr="%s">' % (self.id,
               self.name, self.cidr,)


class OpenStackSecurityGroup(object):
    """
    A Security Group.
    """

    def __init__(self, id, tenant_id, name, description, driver, rules=None,
                 extra=None):
        """
        Constructor.

        @keyword    id: Group id.
        @type       id: C{str}

        @keyword    tenant_id: Owner of the security group.
        @type       tenant_id: C{str}

        @keyword    name: Human-readable name for the security group. Might
                          not be unique.
        @type       name: C{str}

        @keyword    description: Human-readable description of a security
                                 group.
        @type       description: C{str}

        @keyword    rules: Rules associated with this group.
        @type       description: C{list} of L{OpenStackSecurityGroupRule}

        @keyword    extra: Extra attributes associated with this group.
        @type       extra: C{dict}
        """
        self.id = id
        self.tenant_id = tenant_id
        self.name = name
        self.description = description
        self.driver = driver
        self.rules = rules or []
        self.extra = extra or {}

    def __repr__(self):
        return ('<OpenStackSecurityGroup id=%s tenant_id=%s name=%s \
        description=%s>' % (self.id, self.tenant_id, self.name,
                            self.description))


class OpenStackSecurityGroupRule(object):
    """
    A Rule of a Security Group.
    """

    def __init__(self, id, parent_group_id, ip_protocol, from_port, to_port,
                 driver, ip_range=None, group=None, tenant_id=None,
                 extra=None):
        """
        Constructor.

        @keyword    id: Rule id.
        @type       id: C{str}

        @keyword    parent_group_id: ID of the parent security group.
        @type       parent_group_id: C{str}

        @keyword    ip_protocol: IP Protocol (icmp, tcp, udp, etc).
        @type       ip_protocol: C{str}

        @keyword    from_port: Port at start of range.
        @type       from_port: C{int}

        @keyword    to_port: Port at end of range.
        @type       to_port: C{int}

        @keyword    ip_range: CIDR for address range.
        @type       ip_range: C{str}

        @keyword    group: Name of a source security group to apply to rule.
        @type       group: C{str}

        @keyword    tenant_id: Owner of the security group.
        @type       tenant_id: C{str}

        @keyword    extra: Extra attributes associated with this rule.
        @type       extra: C{dict}
        """
        self.id = id
        self.parent_group_id = parent_group_id
        self.ip_protocol = ip_protocol
        self.from_port = from_port
        self.to_port = to_port
        self.driver = driver
        self.ip_range = ''
        self.group = {}

        if group is None:
            self.ip_range = ip_range
        else:
            self.group = {'name': group, 'tenant_id': tenant_id}

        self.tenant_id = tenant_id
        self.extra = extra or {}

    def __repr__(self):
        return ('<OpenStackSecurityGroupRule id=%s parent_group_id=%s \
                ip_protocol=%s from_port=%s to_port=%s>' % (self.id,
                self.parent_group_id, self.ip_protocol, self.from_port,
                self.to_port))


class OpenStack_1_1_Connection(OpenStackComputeConnection):
    responseCls = OpenStack_1_1_Response
    accept_format = 'application/json'
    default_content_type = 'application/json; charset=UTF-8'

    def encode_data(self, data):
        return json.dumps(data)


class OpenStack_1_1_NodeDriver(OpenStackNodeDriver):
    """
    OpenStack node driver.
    """
    connectionCls = OpenStack_1_1_Connection
    type = Provider.OPENSTACK

    features = {"create_node": ["generates_password"]}

    def __init__(self, *args, **kwargs):
        self._ex_force_api_version = str(kwargs.pop('ex_force_api_version',
                                                    None))
        super(OpenStack_1_1_NodeDriver, self).__init__(*args, **kwargs)

    def create_node(self, **kwargs):
        """Create a new node

        @inherits:  L{NodeDriver.create_node}

        @keyword    ex_metadata: Key/Value metadata to associate with a node
        @type       ex_metadata: C{dict}

        @keyword    ex_files:   File Path => File contents to create on
                                the no  de
        @type       ex_files:   C{dict}

        @keyword    ex_keyname:  Name of existing public key to inject into
                                 instance
        @type       ex_keyname:  C{str}

        @keyword    ex_userdata: String containing user data
                                 see
                                 https://help.ubuntu.com/community/CloudInit
        @type       ex_userdata: C{str}

        @keyword    networks: The server is launched into a set of Networks.
        @type       networks: L{OpenStackNetwork}

        @keyword    ex_security_groups: List of security groups to assign to
                                        the node
        @type       ex_security_groups: C{list} of L{OpenStackSecurityGroup}
        """

        server_params = self._create_args_to_params(None, **kwargs)

        resp = self.connection.request("/servers",
                                       method='POST',
                                       data={'server': server_params})

        create_response = resp.object['server']
        server_resp = self.connection.request(
            '/servers/%s' % create_response['id'])
        server_object = server_resp.object['server']

        # adminPass is not always present
        # http://docs.openstack.org/essex/openstack-compute/admin/
        # content/configuring-compute-API.html#d6e1833
        server_object['adminPass'] = create_response.get('adminPass', None)

        return self._to_node(server_object)

    def _to_images(self, obj, ex_only_active):
        images = []
        for image in obj['images']:
            if ex_only_active and image.get('status') != 'ACTIVE':
                continue
            images.append(self._to_image(image))

        return images

    def _to_image(self, api_image):
        server = api_image.get('server', {})
        return NodeImage(
            id=api_image['id'],
            name=api_image['name'],
            driver=self,
            extra=dict(
                updated=api_image['updated'],
                created=api_image['created'],
                status=api_image['status'],
                progress=api_image.get('progress'),
                metadata=api_image.get('metadata'),
                serverId=server.get('id'),
                minDisk=api_image.get('minDisk'),
                minRam=api_image.get('minRam'),
            )
        )

    def _to_nodes(self, obj):
        servers = obj['servers']
        return [self._to_node(server) for server in servers]

    def _to_sizes(self, obj):
        flavors = obj['flavors']
        return [self._to_size(flavor) for flavor in flavors]

    def _create_args_to_params(self, node, **kwargs):
        server_params = {
            'name': kwargs.get('name'),
            'metadata': kwargs.get('ex_metadata', {}),
            'personality': self._files_to_personality(kwargs.get("ex_files",
                                                                 {}))
        }

        if 'ex_keyname' in kwargs:
            server_params['key_name'] = kwargs['ex_keyname']

        if 'ex_userdata' in kwargs:
            server_params['user_data'] = base64.b64encode(
                b(kwargs['ex_userdata'])).decode('ascii')

        if 'networks' in kwargs:
            networks = kwargs['networks']
            networks = [{'uuid': network.id} for network in networks]
            server_params['networks'] = networks

        if 'ex_security_groups' in kwargs:
            server_params['security_groups'] = []
            for security_group in kwargs['ex_security_groups']:
                name = security_group.name
                server_params['security_groups'].append({'name': name})

        if 'name' in kwargs:
            server_params['name'] = kwargs.get('name')
        else:
            server_params['name'] = node.name

        if 'image' in kwargs:
            server_params['imageRef'] = kwargs.get('image').id
        else:
            server_params['imageRef'] = node.extra.get('imageId')

        if 'size' in kwargs:
            server_params['flavorRef'] = kwargs.get('size').id
        else:
            server_params['flavorRef'] = node.extra.get('flavorId')

        return server_params

    def _files_to_personality(self, files):
        rv = []

        for k, v in list(files.items()):
            rv.append({'path': k, 'contents': base64.b64encode(b(v))})

        return rv

    def _reboot_node(self, node, reboot_type='SOFT'):
        resp = self._node_action(node, 'reboot', type=reboot_type)
        return resp.status == httplib.ACCEPTED

    def ex_set_password(self, node, password):
        """
        Changes the administrator password for a specified server.

        @param      node: Node to rebuild.
        @type       node: L{Node}

        @param      password: The administrator password.
        @type       password: C{str}

        @rtype: C{bool}
        """
        resp = self._node_action(node, 'changePassword', adminPass=password)
        node.extra['password'] = password
        return resp.status == httplib.ACCEPTED

    def ex_rebuild(self, node, image):
        """
        Rebuild a Node.

        @param      node: Node to rebuild.
        @type       node: L{Node}

        @param      image: New image to use.
        @type       image: L{NodeImage}

        @rtype: C{bool}
        """
        server_params = self._create_args_to_params(node, image=image)
        resp = self._node_action(node, 'rebuild', **server_params)
        return resp.status == httplib.ACCEPTED

    def ex_resize(self, node, size):
        """
        Change a node size.

        @param      node: Node to resize.
        @type       node: L{Node}

        @type       size: L{NodeSize}
        @param      size: New size to use.

        @rtype: C{bool}
        """
        server_params = self._create_args_to_params(node, size=size)
        resp = self._node_action(node, 'resize', **server_params)
        return resp.status == httplib.ACCEPTED

    def ex_confirm_resize(self, node):
        """
        Confirms a pending resize action.

        @param      node: Node to resize.
        @type       node: L{Node}

        @rtype: C{bool}
        """
        resp = self._node_action(node, 'confirmResize')
        return resp.status == httplib.NO_CONTENT

    def ex_revert_resize(self, node):
        """
        Cancels and reverts a pending resize action.

        @param      node: Node to resize.
        @type       node: L{Node}

        @rtype: C{bool}
        """
        resp = self._node_action(node, 'revertResize')
        return resp.status == httplib.ACCEPTED

    def ex_save_image(self, node, name, metadata=None):
        """
        Creates a new image.

        @param      node: Node
        @type       node: L{Node}

        @param      name: The name for the new image.
        @type       name: C{str}

        @param      metadata: Key and value pairs for metadata.
        @type       metadata: C{dict}

        @rtype: L{NodeImage}
        """
        optional_params = {}
        if metadata:
            optional_params['metadata'] = metadata
        resp = self._node_action(node, 'createImage', name=name,
                                 **optional_params)
        image_id = self._extract_image_id_from_url(resp.headers['location'])
        return self.ex_get_image(image_id=image_id)

    def ex_set_server_name(self, node, name):
        """
        Sets the Node's name.

        @param      node: Node
        @type       node: L{Node}

        @param      name: The name of the server.
        @type       name: C{str}

        @rtype: L{Node}
        """
        return self._update_node(node, name=name)

    def ex_get_metadata(self, node):
        """
        Get a Node's metadata.

        @param      node: Node
        @type       node: L{Node}

        @return: Key/Value metadata associated with node.
        @rtype: C{dict}
        """
        return self.connection.request(
            '/servers/%s/metadata' % (node.id,),
            method='GET',).object['metadata']

    def ex_set_metadata(self, node, metadata):
        """
        Sets the Node's metadata.

        @param      node: Node
        @type       node: L{Node}

        @param      metadata: Key/Value metadata to associate with a node
        @type       metadata: C{dict}

        @rtype: C{dict}
        """
        return self.connection.request(
            '/servers/%s/metadata' % (node.id,), method='PUT',
            data={'metadata': metadata}
        ).object['metadata']

    def ex_update_node(self, node, **node_updates):
        """
        Update the Node's editable attributes.  The OpenStack API currently
        supports editing name and IPv4/IPv6 access addresses.

        The driver currently only supports updating the node name.

        @param      node: Node
        @type       node: L{Node}

        @keyword    name:   New name for the server
        @type       name:   C{str}

        @rtype: L{Node}
        """
        potential_data = self._create_args_to_params(node, **node_updates)
        updates = {'name': potential_data['name']}
        return self._update_node(node, **updates)

    def _to_networks(self, obj):
        networks = obj['networks']
        return [self._to_network(network) for network in networks]

    def _to_network(self, obj):
        return OpenStackNetwork(id=obj['id'],
                                name=obj['label'],
                                cidr=obj.get('cidr', None),
                                driver=self)

    def ex_list_networks(self):
        """
        Get a list of Networks that are available.

        @rtype: C{list} of L{OpenStackNetwork}
        """
        return self._to_networks(
            self.connection.request('/os-networksv2').object)

    def ex_create_network(self, name, cidr):
        """
        Create a new Network

        @param name: Name of network which should be used
        @type name: C{str}

        @param cidr: cidr of network which should be used
        @type cidr: C{str}

        @rtype: L{OpenStackNetwork}
        """
        return self._to_network(self.connection.request(
            '/os-networksv2', method='POST',
            data={'network': {'cidr': cidr, 'label': name}}
        ).object['network'])

    def ex_delete_network(self, network):
        """
        Get a list of NodeNetorks that are available.

        @param network: Network which should be used
        @type network: L{OpenStackNetwork}

        @rtype: C{bool}
        """
        resp = self.connection.request('/os-networksv2/%s' % (network.id),
                                       method='DELETE')
        return resp.status == httplib.ACCEPTED

    def _to_security_group_rules(self, obj):
        return [self._to_security_group_rule(security_group_rule) for
                security_group_rule in obj]

    def _to_security_group_rule(self, obj):
        ip_range = group = tenant_id = None
        if obj['group'] == {}:
            ip_range = obj['ip_range'].get('cidr', None)
        else:
            group = obj['group'].get('name', None)
            tenant_id = obj['group'].get('tenant_id', None)

        return OpenStackSecurityGroupRule(id=obj['id'],
                                          parent_group_id=
                                          obj['parent_group_id'],
                                          ip_protocol=obj['ip_protocol'],
                                          from_port=obj['from_port'],
                                          to_port=obj['to_port'],
                                          driver=self,
                                          ip_range=ip_range,
                                          group=group,
                                          tenant_id=tenant_id)

    def _to_security_groups(self, obj):
        security_groups = obj['security_groups']
        return [self._to_security_group(security_group) for security_group in
                security_groups]

    def _to_security_group(self, obj):
        return OpenStackSecurityGroup(id=obj['id'],
                                      tenant_id=obj['tenant_id'],
                                      name=obj['name'],
                                      description=obj.get('description', ''),
                                      rules=self._to_security_group_rules(
                                      obj.get('rules', [])),
                                      driver=self)

    def ex_list_security_groups(self):
        """
        Get a list of Security Groups that are available.

        @rtype: C{list} of L{OpenStackSecurityGroup}
        """
        return self._to_security_groups(
            self.connection.request('/os-security-groups').object)

    def ex_get_node_security_groups(self, node):
        """
        Get Security Groups of the specified server.

        @rtype: C{list} of L{OpenStackSecurityGroup}
        """
        return self._to_security_groups(
            self.connection.request('/servers/%s/os-security-groups' %
                                    (node.id)).object)

    def ex_create_security_group(self, name, description):
        """
        Create a new Security Group

        @param name: Name of the new Security Group
        @type  name: C{str}

        @param description: Description of the new Security Group
        @type  description: C{str}

        @rtype: L{OpenStackSecurityGroup}
        """
        return self._to_security_group(self.connection.request(
            '/os-security-groups', method='POST',
            data={'security_group': {'name': name, 'description': description}}
        ).object['security_group'])

    def ex_delete_security_group(self, security_group):
        """
        Delete a Security Group.

        @param security_group: Security Group should be deleted
        @type  security_group: L{OpenStackSecurityGroup}

        @rtype: C{bool}
        """
        resp = self.connection.request('/os-security-groups/%s' %
                                       (security_group.id),
                                       method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def ex_create_security_group_rule(self, security_group, ip_protocol,
                                      from_port, to_port, cidr=None,
                                      source_security_group=None):
        """
        Create a new Rule in a Security Group

        @param security_group: Security Group in which to add the rule
        @type  security_group: L{OpenStackSecurityGroup}

        @param ip_protocol: Protocol to which this rule applies
                            Examples: tcp, udp, ...
        @type  ip_protocol: C{str}

        @param from_port: First port of the port range
        @type  from_port: C{int}

        @param to_port: Last port of the port range
        @type  to_port: C{int}

        @param cidr: CIDR notation of the source IP range for this rule
        @type  cidr: C{str}

        @param source_security_group: Existing Security Group to use as the
                                      source (instead of CIDR)
        @type  source_security_group: L{OpenStackSecurityGroup

        @rtype: L{OpenStackSecurityGroupRule}
        """
        source_security_group_id = None
        if type(source_security_group) == OpenStackSecurityGroup:
            source_security_group_id = source_security_group.id

        return self._to_security_group_rule(self.connection.request(
            '/os-security-group-rules', method='POST',
            data={'security_group_rule': {
            'ip_protocol': ip_protocol,
            'from_port': from_port,
            'to_port': to_port,
            'cidr': cidr,
            'group_id': source_security_group_id,
            'parent_group_id': security_group.id}}
        ).object['security_group_rule'])

    def ex_delete_security_group_rule(self, rule):
        """
        Delete a Rule from a Security Group.

        @param rule: Rule should be deleted
        @type  rule: L{OpenStackSecurityGroupRule}

        @rtype: C{bool}
        """
        resp = self.connection.request('/os-security-group-rules/%s' %
                                       (rule.id), method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def ex_get_size(self, size_id):
        """
        Get a NodeSize

        @param      size_id: ID of the size which should be used
        @type       size_id: C{str}

        @rtype: L{NodeSize}
        """
        return self._to_size(self.connection.request(
            '/flavors/%s' % (size_id,)) .object['flavor'])

    def ex_get_image(self, image_id):
        """
        Get a NodeImage

        @param      image_id: ID of the image which should be used
        @type       image_id: C{str}

        @rtype: L{NodeImage}
        """
        return self._to_image(self.connection.request(
            '/images/%s' % (image_id,)).object['image'])

    def ex_delete_image(self, image):
        """
        Delete a NodeImage

        @param      image: image witch should be used
        @type       image: L{NodeImage}

        @rtype: C{bool}
        """
        resp = self.connection.request('/images/%s' % (image.id,),
                                       method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def _node_action(self, node, action, **params):
        params = params or None
        return self.connection.request('/servers/%s/action' % (node.id,),
                                       method='POST', data={action: params})

    def _update_node(self, node, **node_updates):
        """
        Updates the editable attributes of a server, which currently include
        its name and IPv4/IPv6 access addresses.
        """
        return self._to_node(
            self.connection.request(
                '/servers/%s' % (node.id,), method='PUT',
                data={'server': node_updates}
            ).object['server']
        )

    def _to_node_from_obj(self, obj):
        return self._to_node(obj['server'])

    def _to_node(self, api_node):
        public_networks_labels = ['public', 'internet']

        public_ips, private_ips = [], []

        for label, values in api_node['addresses'].items():
            ips = [v['addr'] for v in values]

            if label in public_networks_labels:
                public_ips.extend(ips)
            else:
                private_ips.extend(ips)

        return Node(
            id=api_node['id'],
            name=api_node['name'],
            state=self.NODE_STATE_MAP.get(api_node['status'],
                                          NodeState.UNKNOWN),
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self,
            extra=dict(
                hostId=api_node['hostId'],
                # Docs says "tenantId", but actual is "tenant_id". *sigh*
                # Best handle both.
                tenantId=api_node.get('tenant_id') or api_node['tenantId'],
                imageId=api_node['image']['id'],
                flavorId=api_node['flavor']['id'],
                uri=next(link['href'] for link in api_node['links'] if
                         link['rel'] == 'self'),
                metadata=api_node['metadata'],
                password=api_node.get('adminPass', None),
                created=api_node['created'],
                updated=api_node['updated'],
                key_name=api_node.get('key_name', None),
            ),
        )

    def _to_size(self, api_flavor, price=None, bandwidth=None):
        # if provider-specific subclasses can get better values for
        # price/bandwidth, then can pass them in when they super().
        if not price:
            price = self._get_size_price(str(api_flavor['id']))

        return OpenStackNodeSize(
            id=api_flavor['id'],
            name=api_flavor['name'],
            ram=api_flavor['ram'],
            disk=api_flavor['disk'],
            vcpus=api_flavor['vcpus'],
            bandwidth=bandwidth,
            price=price,
            driver=self,
        )

    def _get_size_price(self, size_id):
        try:
            return get_size_price(
                driver_type='compute',
                driver_name=self.api_name,
                size_id=size_id,
            )
        except KeyError:
            return(0.0)

    def _extract_image_id_from_url(self, location_header):
        path = urlparse.urlparse(location_header).path
        image_id = path.split('/')[-1]
        return image_id

    def ex_rescue(self, node, password=None):
        # Requires Rescue Mode extension
        """
        Rescue a node

        @param      node: node
        @type       node: L{Node}

        @param      password: password
        @type       password: C{str}

        @rtype: L{Node}
        """
        if password:
            resp = self._node_action(node, 'rescue', adminPass=password)
        else:
            resp = self._node_action(node, 'rescue')
            password = json.loads(resp.body)['adminPass']
        node.extra['password'] = password
        return node

    def ex_unrescue(self, node):
        """
        Unrescue a node

        @param      node: node
        @type       node: L{Node}

        @rtype: C{bool}
        """
        resp = self._node_action(node, 'unrescue')
        return resp.status == httplib.ACCEPTED
