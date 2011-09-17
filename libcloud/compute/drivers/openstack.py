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
import os

import base64
import warnings

from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

from libcloud.pricing import get_size_price, PRICING_DATA
from libcloud.common.base import Response
from libcloud.common.types import MalformedResponseError
from libcloud.compute.types import NodeState, Provider
from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.base import NodeSize, NodeImage
from libcloud.common.openstack import OpenStackBaseConnection

__all__ = [
    'OpenStackResponse',
    'OpenStackConnection',
    'OpenStackNodeDriver',
    'OpenStackSharedIpGroup',
    'OpenStackNodeIpAddresses',
    ]

NAMESPACE = 'http://docs.rackspacecloud.com/servers/api/v1.0'


class OpenStackResponse(Response):

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299

    def has_content_type(self, content_type):
        content_type_value = self.headers.get('content-type') or ''
        content_type_value = content_type_value.lower()
        return content_type_value.find(content_type.lower()) > -1

    def parse_body(self):
        if self.has_content_type('application/xml'):
            try:
                return ET.XML(self.body)
            except:
                raise MalformedResponseError(
                    'Failed to parse XML',
                    body=self.body,
                    driver=OpenStackNodeDriver)

        else:
            return self.body

    def parse_error(self):
        # TODO: fixup; only uses response codes really!
        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError(
                "Failed to parse XML",
                body=self.body, driver=OpenStackNodeDriver)
        try:
            text = "; ".join([err.text or ''
                              for err in
                              body.getiterator()
                              if err.text])
        except ExpatError:
            text = self.body
        return '%s %s %s' % (self.status, self.error, text)


class OpenStackConnection(OpenStackBaseConnection):

    responseCls = OpenStackResponse
    _url_key = "server_url"

    def __init__(self, user_id, key, secure=True, host=None, port=None, ex_force_base_url=None):
        super(OpenStackConnection, self).__init__(
            user_id, key, host=host, port=port, ex_force_base_url=ex_force_base_url)
        self.api_version = 'v1.0'
        self.accept_format = 'application/xml'

    def request(self, action, params=None, data='', headers=None,
                method='GET'):
        if not headers:
            headers = {}
        if not params:
            params = {}

        if method in ("POST", "PUT"):
            headers = {'Content-Type': 'application/xml; charset=UTF-8'}
        if method == "GET":
            params['cache-busting'] = os.urandom(8).encode('hex')
        return super(OpenStackConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers
        )


class OpenStackNodeDriver(NodeDriver):
    """
    OpenStack node driver.

    Extra node attributes:
        - password: root password, available after create.
        - hostId: represents the host your cloud server runs on
        - imageId: id of image
        - flavorId: id of flavor
    """
    connectionCls = OpenStackConnection
    type = Provider.OPENSTACK
    api_name = 'openstack'
    name = 'OpenStack'

    features = {"create_node": ["generates_password"]}

    NODE_STATE_MAP = {'BUILD': NodeState.PENDING,
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
                      'UNKNOWN': NodeState.UNKNOWN}

    def __init__(self, *args, **kwargs):
        self._ex_force_base_url = kwargs.pop('ex_force_base_url', None)
        super(OpenStackNodeDriver, self).__init__(*args, **kwargs)

    def _ex_connection_class_kwargs(self):
        if self._ex_force_base_url:
            return {'ex_force_base_url': self._ex_force_base_url}
        return {}


    def list_nodes(self):
        return self._to_nodes(self.connection.request('/servers/detail')
                                             .object)

    def list_sizes(self, location=None):
        return self._to_sizes(self.connection.request('/flavors/detail')
                                             .object)

    def list_images(self, location=None):
        return self._to_images(self.connection.request('/images/detail')
                                              .object)
    # TODO: def list_locations: Is there an OpenStack way to do this? Rackspace-specific docstring says no.

    def _change_password_or_name(self, node, name=None, password=None):
        uri = '/servers/%s' % (node.id)

        if not name:
            name = node.name

        body = {'xmlns': NAMESPACE,
                 'name': name}

        if password != None:
            body['adminPass'] = password

        server_elm = ET.Element('server', body)

        resp = self.connection.request(
            uri, method='PUT', data=ET.tostring(server_elm))

        if resp.status == 204 and password != None:
            node.extra['password'] = password

        return resp.status == 204

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

    def create_node(self, **kwargs):
        """Create a new node

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

        attributes = {'xmlns': NAMESPACE,
             'name': name,
             'imageId': str(image.id),
             'flavorId': str(size.id)
        }

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
            {'xmlns': NAMESPACE,
             'flavorId': str(size.id),
            }
        )

        resp = self.connection.request("/servers/%s/action" % (node.id),
                                       method='POST',
                                       data=ET.tostring(elm))
        return resp.status == 202

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
            {'xmlns': NAMESPACE}
        )

        resp = self.connection.request("/servers/%s/action" % (node.id),
                                       method='POST',
                                       data=ET.tostring(elm))
        return resp.status == 204

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
            {'xmlns': NAMESPACE}
        )

        resp = self.connection.request("/servers/%s/action" % (node.id),
                                       method='POST',
                                       data=ET.tostring(elm))
        return resp.status == 204

    def ex_rebuild(self, node_id, image_id):
        # @TODO: Remove those ifs in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        if isinstance(image_id, NodeImage):
            image_id = image_id.id

        elm = ET.Element(
            'rebuild',
            {'xmlns': NAMESPACE,
             'imageId': image_id,
            }
        )
        resp = self.connection.request("/servers/%s/action" % node_id,
                                       method='POST',
                                       data=ET.tostring(elm))
        return resp.status == 202

    def ex_create_ip_group(self, group_name, node_id=None):
        # @TODO: Remove this if in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        group_elm = ET.Element(
            'sharedIpGroup',
            {'xmlns': NAMESPACE,
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
        groups = self._findall(resp.object, 'sharedIpGroup')
        return [self._to_shared_ip_group(el) for el in groups]

    def ex_delete_ip_group(self, group_id):
        uri = '/shared_ip_groups/%s' % group_id
        resp = self.connection.request(uri, method='DELETE')
        return resp.status == 204

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
            {'xmlns': NAMESPACE,
             'sharedIpGroupId': group_id,
             'configureServer': str_configure}
        )

        uri = '/servers/%s/ips/public/%s' % (node_id, ip)

        resp = self.connection.request(uri,
                                       method='PUT',
                                       data=ET.tostring(elm))
        return resp.status == 202

    def ex_unshare_ip(self, node_id, ip):
        # @TODO: Remove this if in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        uri = '/servers/%s/ips/public/%s' % (node_id, ip)

        resp = self.connection.request(uri,
                                       method='DELETE')
        return resp.status == 202

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
        for k, v in metadata.items():
            meta_elm = ET.SubElement(metadata_elm, 'meta', {'key': str(k)})
            meta_elm.text = str(v)

        return metadata_elm

    def _files_to_xml(self, files):
        if len(files) == 0:
            return None

        personality_elm = ET.Element('personality')
        for k, v in files.items():
            file_elm = ET.SubElement(personality_elm,
                                     'file',
                                     {'path': str(k)})
            file_elm.text = base64.b64encode(v)

        return personality_elm

    def _reboot_node(self, node, reboot_type='SOFT'):
        resp = self._node_action(node, ['reboot', ('type', reboot_type)])
        return resp.status == 202

    def ex_soft_reboot_node(self, node):
        return self._reboot_node(node, reboot_type='SOFT')

    def ex_hard_reboot_node(self, node):
        return self._reboot_node(node, reboot_type='HARD')

    def reboot_node(self, node):
        return self._reboot_node(node, reboot_type='HARD')

    def destroy_node(self, node):
        uri = '/servers/%s' % (node.id)
        resp = self.connection.request(uri, method='DELETE')
        return resp.status == 202

    def ex_get_node_details(self, node_id):
        # @TODO: Remove this if in 0.6
        if isinstance(node_id, Node):
            node_id = node_id.id

        uri = '/servers/%s' % (node_id)
        resp = self.connection.request(uri, method='GET')
        if resp.status == 404:
            return None
        return self._to_node(resp.object)

    def _node_action(self, node, body):
        if isinstance(body, list):
            attr = ' '.join(['%s="%s"' % (item[0], item[1])
                             for item in body[1:]])
            body = '<%s xmlns="%s" %s/>' % (body[0], NAMESPACE, attr)
        uri = '/servers/%s/action' % (node.id)
        resp = self.connection.request(uri, method='POST', data=body)
        return resp

    def _to_nodes(self, object):
        node_elements = self._findall(object, 'server')
        return [self._to_node(el) for el in node_elements]

    def _fixxpath(self, xpath):
        # ElementTree wants namespaces in its xpaths, so here we add them.
        return "/".join(["{%s}%s" % (NAMESPACE, e) for e in xpath.split("/")])

    def _findall(self, element, xpath):
        return element.findall(self._fixxpath(xpath))

    def _to_node(self, el):
        def get_ips(el):
            return [ip.get('addr') for ip in el]

        def get_meta_dict(el):
            d = {}
            for meta in el:
                d[meta.get('key')] = meta.text
            return d

        public_ip = get_ips(self._findall(el,
                                          'addresses/public/ip'))
        private_ip = get_ips(self._findall(el,
                                          'addresses/private/ip'))
        metadata = get_meta_dict(self._findall(el, 'metadata/meta'))

        n = Node(id=el.get('id'),
                 name=el.get('name'),
                 state=self.NODE_STATE_MAP.get(
                     el.get('status'), NodeState.UNKNOWN),
                 public_ip=public_ip,
                 private_ip=private_ip,
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
        elements = self._findall(object, 'flavor')
        return [self._to_size(el) for el in elements]

    def _to_size(self, el):
        s = NodeSize(id=el.get('id'),
                     name=el.get('name'),
                     ram=int(el.get('ram')),
                     disk=int(el.get('disk')),
                     bandwidth=None, # XXX: needs hardcode
                     price=self._get_size_price(el.get('id')), # Hardcoded,
                     driver=self.connection.driver)
        return s

    def _to_images(self, object):
        elements = self._findall(object, "image")
        return [self._to_image(el)
                for el in elements
                if el.get('status') == 'ACTIVE']

    def _to_image(self, el):
        i = NodeImage(id=el.get('id'),
                      name=el.get('name'),
                      driver=self.connection.driver,
                      extra={'updated': el.get('updated'),
                             'created': el.get('created'),
                             'status': el.get('status'),
                             'serverId': el.get('serverId'),
                             'progress': el.get('progress')})
        return i

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
            for item in el.items():
                rate[item[0]] = item[1]

            return rate

        def _to_absolute(el):
            return {el.get('name'): el.get('value')}

        limits = self.connection.request("/limits").object
        rate = [_to_rate(el) for el in self._findall(limits, 'rate/limit')]
        absolute = {}
        for item in self._findall(limits, 'absolute/limit'):
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
                {'xmlns': NAMESPACE,
                    'name': name,
                    'serverId': node.id}
        )

        return self._to_image(self.connection.request("/images",
                    method="POST",
                    data=ET.tostring(image_elm)).object)

    def _to_shared_ip_group(self, el):
        servers_el = self._findall(el, 'servers')
        if servers_el:
            servers = [s.get('id')
                       for s in self._findall(servers_el[0], 'server')]
        else:
            servers = None
        return OpenStackSharedIpGroup(id=el.get('id'),
                                      name=el.get('name'),
                                      servers=servers)

    def _to_ip_addresses(self, el):
        return OpenStackNodeIpAddresses(
            [ip.get('addr') for ip in
             self._findall(self._findall(el, 'public')[0], 'ip')],
            [ip.get('addr') for ip in
             self._findall(self._findall(el, 'private')[0], 'ip')]
        )

    def _get_size_price(self, size_id):
        if 'openstack' not in PRICING_DATA['compute']:
            return 0.0

        return get_size_price(driver_type='compute',
                              driver_name='openstack',
                              size_id=size_id)


class OpenStackSharedIpGroup(object):
    """
    Shared IP group info.
    """

    def __init__(self, id, name, servers=None):
        self.id = str(id)
        self.name = name
        self.servers = servers


class OpenStackNodeIpAddresses(object):
    """
    List of public and private IP addresses of a Node.
    """

    def __init__(self, public_addresses, private_addresses):
        self.public_addresses = public_addresses
        self.private_addresses = private_addresses
