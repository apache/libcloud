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

import binascii

try:
    import simplejson as json
except ImportError:
    import json

import os

import warnings

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b
from libcloud.utils.py3 import next
from libcloud.utils.py3 import urlparse

import base64

from xml.etree import ElementTree as ET

from libcloud.common.openstack import OpenStackBaseConnection
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
            text = ';'.join([fault_data['message'] for fault_data
                             in body.values()])
        else:
            # while we hope a response is always one of xml or json, we have
            # seen html or text in the past, its not clear we can really do
            # something to make it more readable here, so we will just pass
            # it along as the whole response body in the text variable.
            text = body

        return '%s %s %s' % (self.status, self.error, text)


class OpenStackComputeConnection(OpenStackBaseConnection):

    def request(self, action, params=None, data='', headers=None,
                method='GET'):
        if not headers:
            headers = {}
        if not params:
            params = {}

        if method in ("POST", "PUT"):
            headers = {'Content-Type': self.default_content_type}

        if method == "GET":
            params['cache-busting'] = binascii.hexlify(os.urandom(8))

        return super(OpenStackComputeConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers)


class OpenStackNodeDriver(NodeDriver):
    """
    Base OpenStack node driver. Should not be used directly.
    """

    NODE_STATE_MAP = {
        'BUILD': NodeState.PENDING,
        'REBUILD': NodeState.PENDING,
        'ACTIVE': NodeState.RUNNING,
        'SUSPENDED': NodeState.TERMINATED,
        'QUEUE_RESIZE': NodeState.PENDING,
        'PREP_RESIZE': NodeState.PENDING,
        'VERIFY_RESIZE': NodeState.RUNNING,
        'PASSWORD': NodeState.PENDING,
        'RESCUE': NodeState.PENDING,
        'REBUILD': NodeState.PENDING,
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
        return self._to_nodes(self.connection.request('/servers/detail')
                                             .object)

    def list_images(self, location=None, ex_only_active=True):
        return self._to_images(self.connection.request('/images/detail')
                                              .object, ex_only_active)

    def list_sizes(self, location=None):
        return self._to_sizes(self.connection.request('/flavors/detail')
                                             .object)

    def list_locations(self):
        return [NodeLocation(0, '', '', self)]

    def _ex_connection_class_kwargs(self):
        rv = {}
        if self._ex_force_base_url:
            rv['ex_force_base_url'] = self._ex_force_base_url
        if self._ex_force_auth_url:
            rv['ex_force_auth_url'] = self._ex_force_auth_url
        if self._ex_force_auth_version:
            rv['ex_force_auth_version'] = self._ex_force_auth_version
        return rv

    def ex_get_node_details(self, node_id):
        # @TODO: Remove this if in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        uri = '/servers/%s' % (node_id)
        resp = self.connection.request(uri, method='GET')
        if resp.status == httplib.NOT_FOUND:
            return None

        return self._to_node_from_obj(resp.object)

    def ex_soft_reboot_node(self, node):
        return self._reboot_node(node, reboot_type='SOFT')

    def ex_hard_reboot_node(self, node):
        return self._reboot_node(node, reboot_type='HARD')


class OpenStack_1_0_Response(OpenStackResponse):

    def __init__(self, *args, **kwargs):
        # done because of a circular reference from
        # NodeDriver -> Connection -> Response
        self.node_driver = OpenStack_1_0_NodeDriver
        super(OpenStack_1_0_Response, self).__init__(*args, **kwargs)


class OpenStack_1_0_Connection(OpenStackComputeConnection):
    responseCls = OpenStack_1_0_Response
    _url_key = "server_url"
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
    api_name = 'openstack'
    name = 'OpenStack'

    features = {"create_node": ["generates_password"]}

    def __init__(self, *args, **kwargs):
        self._ex_force_base_url = kwargs.pop('ex_force_base_url', None)
        self._ex_force_auth_url = kwargs.pop('ex_force_auth_url', None)
        self._ex_force_auth_version = kwargs.pop('ex_force_auth_version', None)
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
                             'progress': element.get('progress')})

    def _change_password_or_name(self, node, name=None, password=None):
        uri = '/servers/%s' % (node.id)

        if not name:
            name = node.name

        body = {'xmlns': self.XML_NAMESPACE,
                 'name': name}

        if password != None:
            body['adminPass'] = password

        server_elm = ET.Element('server', body)

        resp = self.connection.request(
            uri, method='PUT', data=ET.tostring(server_elm))

        if resp.status == httplib.NO_CONTENT and password != None:
            node.extra['password'] = password

        return resp.status == httplib.NO_CONTENT

    def create_node(self, **kwargs):
        """
        Create a new node

        See L{NodeDriver.create_node} for more keyword args.
        @keyword    ex_metadata: Key/Value metadata to associate with a node
        @type       ex_metadata: C{dict}

        @keyword    ex_files:   File Path => File contents to create on
                                the node
        @type       ex_files:   C{dict}
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
            warnings.warn('ex_shared_ip_group argument is deprecated. Please'
                          + ' use ex_shared_ip_group_id')

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

        L{node.extra['password']} will be set to the new value if the
        operation was successful.
        """
        return self._change_password_or_name(node, password=password)

    def ex_set_server_name(self, node, name):
        """
        Sets the Node's name.

        This will reboot the instance to complete the operation.
        """
        return self._change_password_or_name(node, name=name)

    def ex_resize(self, node, size):
        """
        Change an existing server flavor / scale the server up or down.

        @keyword    node: node to resize.
        @param      node: C{Node}

        @keyword    size: new size.
        @param      size: C{NodeSize}
        """
        elm = ET.Element(
            'resize',
            {'xmlns': self.XML_NAMESPACE,
             'flavorId': str(size.id),
            }
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

        @keyword    node: node for which the resize request will be confirmed.
        @param      node: C{Node}
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

        @keyword    node: node for which the resize request will be reverted.
        @param      node: C{Node}
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
        # @TODO: Remove those ifs in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        if isinstance(image_id, NodeImage):
            image_id = image_id.id

        elm = ET.Element(
            'rebuild',
            {'xmlns': self.XML_NAMESPACE,
             'imageId': image_id,
            }
        )

        resp = self.connection.request("/servers/%s/action" % node_id,
                                       method='POST',
                                       data=ET.tostring(elm))
        return resp.status == httplib.ACCEPTED

    def ex_create_ip_group(self, group_name, node_id=None):
        # @TODO: Remove this if in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        group_elm = ET.Element(
            'sharedIpGroup',
            {'xmlns': self.XML_NAMESPACE,
             'name': group_name,
            }
        )

        if node_id:
            ET.SubElement(group_elm,
                'server',
                {'id': node_id}
            )

        resp = self.connection.request('/shared_ip_groups',
                                       method='POST',
                                       data=ET.tostring(group_elm))
        return self._to_shared_ip_group(resp.object)

    def ex_list_ip_groups(self, details=False):
        uri = '/shared_ip_groups/detail' if details else '/shared_ip_groups'
        resp = self.connection.request(uri,
                                       method='GET')
        groups = findall(resp.object, 'sharedIpGroup',
                               self.XML_NAMESPACE)
        return [self._to_shared_ip_group(el) for el in groups]

    def ex_delete_ip_group(self, group_id):
        uri = '/shared_ip_groups/%s' % group_id
        resp = self.connection.request(uri, method='DELETE')
        return resp.status == httplib.NO_CONTENT

    def ex_share_ip(self, group_id, node_id, ip, configure_node=True):
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
        # @TODO: Remove this if in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        uri = '/servers/%s/ips/public/%s' % (node_id, ip)

        resp = self.connection.request(uri,
                                       method='DELETE')
        return resp.status == httplib.ACCEPTED

    def ex_list_ip_addresses(self, node_id):
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
        return self._to_node(findall(obj, 'server',
                                           self.XML_NAMESPACE)[0])

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
        return NodeSize(id=el.get('id'),
                     name=el.get('name'),
                     ram=int(el.get('ram')),
                     disk=int(el.get('disk')),
                     # XXX: needs hardcode
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

        @return: C{dict} with keys 'rate' and 'absolute'
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

        @keyword    node: node to use as a base for image
        @param      node: L{Node}
        @keyword    name: name for new image
        @param      name: C{string}
        """

        image_elm = ET.Element(
                'image',
                {'xmlns': self.XML_NAMESPACE,
                    'name': name,
                    'serverId': node.id})

        return self._to_image(self.connection.request("/images",
                    method="POST",
                    data=ET.tostring(image_elm)).object)

    def ex_delete_image(self, image):
        """Delete an image for node.

        @keyword    image: the image to be deleted
        @param      image: L{NodeImage}
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
        return OpenStack_1_0_NodeIpAddresses(
            [ip.get('addr') for ip in
             findall(findall(el, 'public', self.XML_NAMESPACE)[0],
             'ip', self.XML_NAMESPACE)],
            [ip.get('addr') for ip in
             findall(findall(el, 'private', self.XML_NAMESPACE)[0],
             'ip', self.XML_NAMESPACE)])

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


class OpenStack_1_1_Connection(OpenStackComputeConnection):
    responseCls = OpenStack_1_1_Response
    _url_key = "server_url"
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
    api_name = 'openstack'
    name = 'OpenStack'

    features = {"create_node": ["generates_password"]}

    def __init__(self, *args, **kwargs):
        self._ex_force_base_url = kwargs.pop('ex_force_base_url', None)
        self._ex_force_auth_url = kwargs.pop('ex_force_auth_url', None)
        self._ex_force_auth_version = kwargs.pop('ex_force_auth_version',
                                                 None)
        self._ex_force_api_version = str(kwargs.pop('ex_force_api_version',
                                                    None))
        super(OpenStack_1_1_NodeDriver, self).__init__(*args, **kwargs)

    def create_node(self, **kwargs):
        """Create a new node

        See L{NodeDriver.create_node} for more keyword args.
        @keyword    ex_metadata: Key/Value metadata to associate with a node
        @type       ex_metadata: C{dict}

        @keyword    ex_files:   File Path => File contents to create on
                                the node
        @type       ex_files:   C{dict}
        """

        server_params = self._create_args_to_params(None, **kwargs)

        resp = self.connection.request("/servers",
                                       method='POST',
                                       data={'server': server_params})

        create_response = resp.object['server']
        server_resp = self.connection.request('/servers/%s' % create_response['id'])
        server_object = server_resp.object['server']
        server_object['adminPass'] = create_response['adminPass']

        return self._to_node(server_object)

    def _to_images(self, obj, ex_only_active):
        images = []
        for image in obj['images']:
            if ex_only_active and image.get('status') != 'ACTIVE':
                continue
            images.append(self._to_image(image))

        return images

    def _to_image(self, api_image):
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
        resp = self._node_action(node, 'changePassword', adminPass=password)
        node.extra['password'] = password
        return resp.status == httplib.ACCEPTED

    def ex_rebuild(self, node, image):
        """
        Rebuild a Node.

        @type node: C{Node}
        @param node: Node to rebuild.

        @type image: C{NodeImage}
        @param image: New image to use.
        """
        server_params = self._create_args_to_params(node, image=image)
        resp = self._node_action(node, 'rebuild', **server_params)
        return resp.status == httplib.ACCEPTED

    def ex_resize(self, node, size):
        """
        Change a node size.

        @type node: C{Node}
        @param node: Node to resize.

        @type image: C{NodeSize}
        @param image: New size to use.
        """

        server_params = self._create_args_to_params(node, size=size)
        resp = self._node_action(node, 'resize', **server_params)
        return resp.status == httplib.ACCEPTED

    def ex_confirm_resize(self, node):
        resp = self._node_action(node, 'confirmResize')
        return resp.status == httplib.NO_CONTENT

    def ex_revert_resize(self, node):
        resp = self._node_action(node, 'revertResize')
        return resp.status == httplib.ACCEPTED

    def ex_save_image(self, node, name, metadata=None):
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
        """
        return self._update_node(node, name=name)

    def ex_get_metadata(self, node):
        """
        Get a Node's metadata.

        @return     Key/Value metadata associated with node.
        @type       C{dict}
        """
        return self.connection.request(
                '/servers/%s/metadata' % (node.id,), method='GET',
            ).object['metadata']

    def ex_set_metadata(self, node, metadata):
        """
        Sets the Node's metadata.

        @keyword    metadata: Key/Value metadata to associate with a node
        @type       metadata: C{dict}
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

        @keyword    name:   New name for the server
        @type       name:   C{str}
        """
        potential_data = self._create_args_to_params(node, **node_updates)
        updates = {'name': potential_data['name']}
        return self._update_node(node, **updates)

    def ex_get_size(self, size_id):
        return self._to_size(self.connection.request('/flavors/%s' %
                                                     (size_id,))
                   .object['flavor'])

    def ex_get_image(self, image_id):
        return self._to_image(self.connection.request('/images/%s' %
                                                      (image_id,))
                   .object['image'])

    def ex_delete_image(self, image):
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
        return Node(
            id=api_node['id'],
            name=api_node['name'],
            state=self.NODE_STATE_MAP.get(api_node['status'],
                                          NodeState.UNKNOWN),
            public_ips=[addr_desc['addr'] for addr_desc in
                       api_node['addresses'].get('public', [])],
            private_ips=[addr_desc['addr'] for addr_desc in
                        api_node['addresses'].get('private', [])],
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
                password=api_node.get('adminPass'),
            ),
        )

    def _to_size(self, api_flavor, price=None, bandwidth=None):
        # if provider-specific subclasses can get better values for
        # price/bandwidth, then can pass them in when they super().
        if not price:
            price = self._get_size_price(str(api_flavor['id']))

        return NodeSize(
            id=api_flavor['id'],
            name=api_flavor['name'],
            ram=api_flavor['ram'],
            disk=api_flavor['disk'],
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
