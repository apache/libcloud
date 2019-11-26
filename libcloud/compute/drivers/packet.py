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
Packet Driver
"""

try:  # Try to use asyncio to perform requests in parallel across projects
    import asyncio
except ImportError:  # If not available will do things serially
    asyncio = None

import datetime
import json

from libcloud.utils.py3 import httplib

from libcloud.common.base import ConnectionKey, JsonResponse
from libcloud.compute.types import Provider, NodeState, InvalidCredsError
from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation
from libcloud.compute.base import KeyPair
from libcloud.compute.base import StorageVolume, VolumeSnapshot

PACKET_ENDPOINT = "api.packet.net"

# True to use async io if available (aka running under Python 3)
USE_ASYNC_IO_IF_AVAILABLE = True


def use_asyncio():
    return asyncio is not None and USE_ASYNC_IO_IF_AVAILABLE


class PacketResponse(JsonResponse):
    valid_response_codes = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                            httplib.NO_CONTENT]

    def parse_error(self):
        if self.status == httplib.UNAUTHORIZED:
            body = self.parse_body()
            raise InvalidCredsError(body.get('error'))
        else:
            body = self.parse_body()
            if 'message' in body:
                error = '%s (code: %s)' % (body.get('message'), self.status)
            elif 'errors' in body:
                error = body.get('errors')
            else:
                error = body
            raise Exception(error)

    def success(self):
        return self.status in self.valid_response_codes


class PacketConnection(ConnectionKey):
    """
    Connection class for the Packet driver.
    """

    host = PACKET_ENDPOINT
    responseCls = PacketResponse

    def add_default_headers(self, headers):
        """
        Add headers that are necessary for every request
        """
        headers['Content-Type'] = 'application/json'
        headers['X-Auth-Token'] = self.key
        headers['X-Consumer-Token'] = \
            'kcrhMn7hwG8Ceo2hAhGFa2qpxLBvVHxEjS9ue8iqmsNkeeB2iQgMq4dNc1893pYu'
        return headers


class PacketNodeDriver(NodeDriver):
    """
    Packet NodeDriver
    """

    connectionCls = PacketConnection
    type = Provider.PACKET
    name = 'Packet'
    website = 'http://www.packet.com/'

    NODE_STATE_MAP = {'queued': NodeState.PENDING,
                      'provisioning': NodeState.PENDING,
                      'rebuilding': NodeState.PENDING,
                      'powering_on': NodeState.REBOOTING,
                      'powering_off': NodeState.REBOOTING,
                      'rebooting': NodeState.REBOOTING,
                      'inactive': NodeState.STOPPED,
                      'deleted': NodeState.TERMINATED,
                      'deprovisioning': NodeState.TERMINATED,
                      'failed': NodeState.ERROR,
                      'active': NodeState.RUNNING}

    def __init__(self, key, project=None):
        """
        Initialize a NodeDriver for Packet using the API token
        and optionally the project (name or id).

        If project name is specified we validate it lazily and populate
        self.project_id during the first access of self.projects variable
        """
        super(PacketNodeDriver, self).__init__(key=key)

        self.project_name = project
        self.project_id = None

        # Lazily populated on first access to self.project
        self._project = project

        # Variable which indicates if self._projects has been populated yet and
        # has been called self._project validated
        self._projects_populated = False
        self._projects = None

    @property
    def projects(self):
        """
        Lazily retrieve projects and set self.project_id variable on initial
        access to self.projects variable.
        """
        if not self._projects_populated:
            # NOTE: Each Packet account needs at least one project, but to be
            # on the safe side and avoid infinite loop in case there are no
            # projects on the account, we don't use a more robust way to
            # determine if project list has been populated yet
            self._projects = self.ex_list_projects()
            self._projects_populated = True

            # If project name is specified, verify it's valid and populate
            # self.project_id
            if self._project:
                for project_obj in self._projects:
                    if self._project in [project_obj.name, project_obj.id]:
                        self.project_id = project_obj.id
                        break

                if not self.project_id:
                    # Invalid project name
                    self.project_name = None

        return self._projects

    def ex_list_projects(self):
        projects = []
        data = self.connection.request('/projects').object
        projects = data.get('projects')
        if projects:
            projects = [Project(project) for project in projects]
        return projects

    def list_nodes(self, ex_project_id=None):
        if ex_project_id:
            return self.ex_list_nodes_for_project(ex_project_id=ex_project_id)

        # if project has been specified during driver initialization, then
        # return nodes for this project only
        if self.project_id:
            return self.ex_list_nodes_for_project(
                ex_project_id=self.project_id)

        # In case of Python2 perform requests serially
        if not use_asyncio():
            nodes = []
            for project in self.projects:
                nodes.extend(
                    self.ex_list_nodes_for_project(ex_project_id=project.id)
                )
            return nodes
        # In case of Python3 use asyncio to perform requests in parallel
        return self.list_resources_async('nodes')

    def list_resources_async(self, resource_type):
        # The _list_nodes function is defined dynamically using exec in
        # order to prevent a SyntaxError in Python2 due to "yield from".
        # This cruft can be removed once Python2 support is no longer
        # required.
        assert resource_type in ['nodes', 'volumes']
        glob = globals()
        loc = locals()
        exec("""
import asyncio
@asyncio.coroutine
def _list_async(driver):
    projects = [project.id for project in driver.projects]
    loop = asyncio.get_event_loop()
    futures = [
        loop.run_in_executor(None, driver.ex_list_%s_for_project, p)
        for p in projects
    ]
    retval = []
    for future in futures:
        result = yield from future
        retval.extend(result)
    return retval""" % resource_type, glob, loc)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(loc['_list_async'](loc['self']))

    def ex_list_nodes_for_project(self, ex_project_id, include='plan', page=1,
                                  per_page=1000):
        params = {
            'include': include,
            'page': page,
            'per_page': per_page
        }
        data = self.connection.request(
            '/projects/%s/devices' % (ex_project_id),
            params=params).object['devices']
        return list(map(self._to_node, data))

    def list_locations(self):
        data = self.connection.request('/facilities')\
            .object['facilities']
        return list(map(self._to_location, data))

    def list_images(self):
        data = self.connection.request('/operating-systems')\
            .object['operating_systems']
        return list(map(self._to_image, data))

    def list_sizes(self, ex_project_id=None):
        project_id = ex_project_id or self.project_id or (
            len(self.projects) and self.projects[0].id)
        if project_id:
            data = self.connection.request('/projects/%s/plans' %
                                           project_id).object['plans']
        else:  # This only works with personal tokens
            data = self.connection.request('/plans').object['plans']
        return [self._to_size(size) for size in data if
                size.get('line') == 'baremetal']

    def create_node(self, name, size, image, location,
                    ex_project_id=None, ip_addresses=[], cloud_init=None,
                    **kwargs):
        """
        Create a node.

        :return: The newly created node.
        :rtype: :class:`Node`
        """
        # if project has been specified on initialization of driver, then
        # create on this project

        if self.project_id:
            ex_project_id = self.project_id
        else:
            if not ex_project_id:
                raise Exception('ex_project_id needs to be specified')

        facility = location.extra['code']
        params = {'hostname': name, 'plan': size.id,
                  'operating_system': image.id, 'facility': facility,
                  'include': 'plan', 'billing_cycle': 'hourly',
                  'ip_addresses': ip_addresses}
        params.update(kwargs)
        if cloud_init:
            params["userdata"] = cloud_init
        data = self.connection.request('/projects/%s/devices' %
                                       (ex_project_id),
                                       data=json.dumps(params), method='POST')

        status = data.object.get('status', 'OK')
        if status == 'ERROR':
            message = data.object.get('message', None)
            error_message = data.object.get('error_message', message)
            raise ValueError('Failed to create node: %s' % (error_message))
        node = self._to_node(data=data.object)
        if kwargs.get('disk'):
            self.attach_volume(node, kwargs.get('disk'))
        if kwargs.get('disk_size'):
            volume = self.create_volume(size=kwargs.get('disk_size'),
                                        location=location)
            self.attach_volume(node, volume)
        return node

    def reboot_node(self, node):
        params = {'type': 'reboot'}
        res = self.connection.request('/devices/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.OK

    def start_node(self, node):
        params = {'type': 'power_on'}
        res = self.connection.request('/devices/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.OK

    def stop_node(self, node):
        params = {'type': 'power_off'}
        res = self.connection.request('/devices/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.OK

    def destroy_node(self, node):
        res = self.connection.request('/devices/%s' % (node.id),
                                      method='DELETE')
        return res.status == httplib.OK

    def ex_start_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        return self.start_node(node=node)

    def ex_stop_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        return self.stop_node(node=node)

    def ex_reinstall_node(self, node):
        params = {'type': 'reinstall'}
        res = self.connection.request('/devices/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.OK

    def ex_rescue_node(self, node):
        params = {'type': 'rescue'}
        res = self.connection.request('/devices/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.OK

    def ex_update_node(self, node, **kwargs):
        path = '/devices/%s' % node.id
        res = self.connection.request(path, params=kwargs, method='PUT')
        return res.status == httplib.OK

    def ex_get_node_bandwidth(self, node, from_time, until_time):
        path = '/devices/%s/bandwidth' % node.id
        params = {'from': from_time, 'until': until_time}
        return self.connection.request(path, params=params).object

    def ex_list_ip_assignments_for_node(self, node, include=''):
        path = '/devices/%s/ips' % node.id
        params = {'include': include}
        return self.connection.request(path, params=params).object

    def list_key_pairs(self):
        """
        List all the available SSH keys.

        :return: Available SSH keys.
        :rtype: ``list`` of :class:`.KeyPair` objects
        """
        data = self.connection.request('/ssh-keys').object['ssh_keys']
        return list(map(self._to_key_pairs, data))

    def create_key_pair(self, name, public_key):
        """
        Create a new SSH key.

        :param      name: Key name (required)
        :type       name: ``str``

        :param      public_key: Valid public key string (required)
        :type       public_key: ``str``
        """
        params = {'label': name, 'key': public_key}
        data = self.connection.request('/ssh-keys', method='POST',
                                       params=params).object
        return self._to_key_pairs(data)

    def delete_key_pair(self, key):
        """
        Delete an existing SSH key.

        :param      key: SSH key (required)
        :type       key: :class:`KeyPair`
        """
        key_id = key.name
        res = self.connection.request('/ssh-keys/%s' % (key_id),
                                      method='DELETE')
        return res.status == httplib.NO_CONTENT

    def _to_node(self, data):
        extra = {}
        extra_keys = ['created_at', 'updated_at',
                      'userdata', 'billing_cycle', 'locked',
                      'iqn', 'locked', 'project', 'description']
        if 'state' in data:
            state = self.NODE_STATE_MAP.get(data['state'], NodeState.UNKNOWN)
        else:
            state = NodeState.UNKNOWN

        if 'ip_addresses' in data and data['ip_addresses'] is not None:
            ips = self._parse_ips(data['ip_addresses'])

        if 'operating_system' in data and data['operating_system'] is not None:
            image = self._to_image(data['operating_system'])
            extra['operating_system'] = data['operating_system'].get('name')
        else:
            image = None

        if 'plan' in data and data['plan'] is not None:
            size = self._to_size(data['plan'])
            extra['plan'] = data['plan'].get('slug')
        else:
            size = None
        if 'facility' in data:
            extra['facility'] = data['facility']

        for key in extra_keys:
            if key in data:
                extra[key] = data[key]

        node = Node(id=data['id'], name=data['hostname'], state=state,
                    public_ips=ips['public'], private_ips=ips['private'],
                    size=size, image=image, extra=extra, driver=self)
        return node

    def _to_image(self, data):
        extra = {'distro': data['distro'], 'version': data['version']}
        return NodeImage(id=data['slug'], name=data['name'], extra=extra,
                         driver=self)

    def _to_location(self, data):
        extra = data
        return NodeLocation(id=data['id'], name=data['name'], country=None,
                            driver=self, extra=extra)

    def _to_size(self, data):
        cpus = data['specs']['cpus'][0].get('count')
        extra = {'description': data['description'], 'line': data['line'],
                 'cpus': cpus}

        ram = data['specs']['memory']['total']
        disk = 0
        for disks in data['specs']['drives']:
            disk_size = disks['size'].replace('GB', '')
            if 'TB' in disk_size:
                disk_size = float(disks['size'].replace('TB', '')) * 1000
            disk += disks['count'] * int(disk_size)
        name = "%s - %s RAM" % (data.get('name'), ram)
        price = data['pricing'].get('hour')
        return NodeSize(id=data['slug'], name=name,
                        ram=int(ram.replace('GB', '')) * 1024, disk=disk,
                        bandwidth=0, price=price, extra=extra, driver=self)

    def _to_key_pairs(self, data):
        extra = {'label': data['label'],
                 'created_at': data['created_at'],
                 'updated_at': data['updated_at']}
        return KeyPair(name=data['id'],
                       fingerprint=data['fingerprint'],
                       public_key=data['key'],
                       private_key=None,
                       driver=self,
                       extra=extra)

    def _parse_ips(self, data):
        public_ips = []
        private_ips = []
        for address in data:
            if 'address' in address and address['address'] is not None:
                if 'public' in address and address['public'] is True:
                    public_ips.append(address['address'])
                else:
                    private_ips.append(address['address'])
        return {'public': public_ips, 'private': private_ips}

    def ex_get_bgp_config_for_project(self, ex_project_id):
        path = '/projects/%s/bgp-config' % ex_project_id
        return self.connection.request(path).object

    def ex_get_bgp_config(self, ex_project_id=None):
        if ex_project_id:
            projects = [ex_project_id]
        elif self.project_id:
            projects = [self.project_id]
        else:
            projects = [p.id for p in self.projects]
        retval = []
        for p in projects:
            config = self.ex_get_bgp_config_for_project(p)
            if config:
                retval.append(config)
        return retval

    def ex_get_bgp_session(self, session_uuid):
        path = '/bgp/sessions/%s' % session_uuid
        return self.connection.request(path).object

    def ex_list_bgp_sessions_for_node(self, node):
        path = '/devices/%s/bgp/sessions' % node.id
        return self.connection.request(path).object

    def ex_list_bgp_sessions_for_project(self, ex_project_id):
        path = '/projects/%s/bgp/sessions' % ex_project_id
        return self.connection.request(path).object

    def ex_list_bgp_sessions(self, ex_project_id=None):
        if ex_project_id:
            projects = [ex_project_id]
        elif self.project_id:
            projects = [self.project_id]
        else:
            projects = [p.id for p in self.projects]
        retval = []
        for p in projects:
            retval.extend(self.ex_list_bgp_sessions_for_project(
                p)['bgp_sessions'])
        return retval

    def ex_create_bgp_session(self, node, address_family='ipv4'):
        path = '/devices/%s/bgp/sessions' % node.id
        params = {'address_family': address_family}
        res = self.connection.request(path, params=params, method='POST')
        return res.object

    def ex_delete_bgp_session(self, session_uuid):
        path = '/bgp/sessions/%s' % session_uuid
        res = self.connection.request(path, method='DELETE')
        return res.status == httplib.OK  # or res.status == httplib.NO_CONTENT

    def ex_list_events_for_node(self, node, include=None,
                                page=1, per_page=10):
        path = '/devices/%s/events' % node.id
        params = {
            'include': include,
            'page': page,
            'per_page': per_page
        }
        return self.connection.request(path, params=params).object

    def ex_list_events_for_project(self, project, include=None, page=1,
                                   per_page=10):
        path = '/projects/%s/events' % project.id
        params = {
            'include': include,
            'page': page,
            'per_page': per_page
        }
        return self.connection.request(path, params=params).object

    def ex_describe_all_addresses(self, ex_project_id=None,
                                  only_associated=False):
        if ex_project_id:
            projects = [ex_project_id]
        elif self.project_id:
            projects = [self.project_id]
        else:
            projects = [p.id for p in self.projects]
        retval = []
        for project in projects:
            retval.extend(self.ex_describe_all_addresses_for_project(
                project, only_associated))
        return retval

    def ex_describe_all_addresses_for_project(self, ex_project_id,
                                              include=None,
                                              only_associated=False):
        """
        Returns all the reserved IP addresses for this project
        optionally, returns only addresses associated with nodes.

        :param    only_associated: If true, return only the addresses
                                   that are associated with an instance.
        :type     only_associated: ``bool``

        :return:  List of IP addresses.
        :rtype:   ``list`` of :class:`dict`
        """
        path = '/projects/%s/ips' % ex_project_id
        params = {
            'include': include,
        }
        ip_addresses = self.connection.request(path, params=params).object
        result = [a for a in ip_addresses.get('ip_addresses', [])
                  if not only_associated or len(a.get('assignments', [])) > 0]
        return result

    def ex_describe_address(self, ex_address_id, include=None):
        path = '/ips/%s' % ex_address_id
        params = {
            'include': include,
        }
        result = self.connection.request(path, params=params).object
        return result

    def ex_request_address_reservation(self, ex_project_id, location_id=None,
                                       address_family='global_ipv4',
                                       quantity=1, comments='',
                                       customdata=''):
        path = '/projects/%s/ips' % ex_project_id
        params = {
            'type': address_family,
            'quantity': quantity,
        }
        if location_id:
            params['facility'] = location_id
        if comments:
            params['comments'] = comments
        if customdata:
            params['customdata'] = customdata
        result = self.connection.request(
            path, params=params, method='POST').object
        return result

    def ex_associate_address_with_node(self, node, address, manageable=False,
                                       customdata=''):
        path = '/devices/%s/ips' % node.id
        params = {
            'address': address,
            'manageable': manageable,
            'customdata': customdata
        }
        result = self.connection.request(
            path, params=params, method='POST').object
        return result

    def ex_disassociate_address(self, address_uuid, include=None):
        path = '/ips/%s' % address_uuid
        params = {}
        if include:
            params['include'] = include
        result = self.connection.request(
            path, params=params, method='DELETE').object
        return result

    def list_volumes(self, ex_project_id=None):
        if ex_project_id:
            return self.ex_list_volumes_for_project(
                ex_project_id=ex_project_id)

        # if project has been specified during driver initialization, then
        # return nodes for this project only
        if self.project_id:
            return self.ex_list_volumes_for_project(
                ex_project_id=self.project_id)

        # In case of Python2 perform requests serially
        if not use_asyncio():
            nodes = []
            for project in self.projects:
                nodes.extend(
                    self.ex_list_volumes_for_project(ex_project_id=project.id)
                )
            return nodes
        # In case of Python3 use asyncio to perform requests in parallel
        return self.list_resources_async('volumes')

    def ex_list_volumes_for_project(self, ex_project_id, include='plan',
                                    page=1, per_page=1000):
        params = {
            'include': include,
            'page': page,
            'per_page': per_page
        }
        data = self.connection.request(
            '/projects/%s/storage' % (ex_project_id),
            params=params).object['volumes']
        return list(map(self._to_volume, data))

    def _to_volume(self, data):
        return StorageVolume(id=data['id'], name=data['name'],
                             size=data['size'], driver=self,
                             extra=data)

    def create_volume(self, size, location, plan='storage_1', description='',
                      ex_project_id=None, locked=False, billing_cycle=None,
                      customdata='', snapshot_policies=None, **kwargs):
        """
        Create a new volume.

        :param size: Size of volume in gigabytes (required)
        :type size: ``int``

        :param location: Which data center to create a volume in. If
                               empty, undefined behavior will be selected.
                               (optional)
        :type location: :class:`.NodeLocation`
        :return: The newly created volume.
        :rtype: :class:`StorageVolume`
        """
        path = '/projects/%s/storage' % (ex_project_id or self.projects[0].id)
        try:
            facility = location.extra['code']
        except AttributeError:
            facility = location
        params = {
            'facility': facility,
            'plan': plan,
            'size': size,
            'locked': locked
        }
        params.update(kwargs)
        if description:
            params['description'] = description
        if customdata:
            params['customdata'] = customdata
        if billing_cycle:
            params['billing_cycle'] = billing_cycle
        if snapshot_policies:
            params['snapshot_policies'] = snapshot_policies
        data = self.connection.request(
            path, params=params, method='POST').object
        return self._to_volume(data)

    def destroy_volume(self, volume):
        """
        Destroys a storage volume.

        :param volume: Volume to be destroyed
        :type volume: :class:`StorageVolume`

        :rtype: ``bool``
        """
        path = '/storage/%s' % volume.id
        res = self.connection.request(path, method='DELETE')
        return res.status == httplib.NO_CONTENT

    def attach_volume(self, node, volume):
        """
        Attaches volume to node.

        :param node: Node to attach volume to.
        :type node: :class:`.Node`

        :param volume: Volume to attach.
        :type volume: :class:`.StorageVolume`

        :rytpe: ``bool``
        """
        path = '/storage/%s/attachments' % volume.id
        params = {
            'device_id': node.id
        }
        res = self.connection.request(path, params=params, method='POST')
        return res.status == httplib.OK

    def detach_volume(self, volume, ex_node=None, ex_attachment_id=''):
        """
        Detaches a volume from a node.

        :param volume: Volume to be detached
        :type volume: :class:`.StorageVolume`

        :param ex_attachment_id: Attachment id to be detached, if empty detach
                                        all attachments
        :type name: ``str``

        :rtype: ``bool``
        """
        path = '/storage/%s/attachments' % volume.id
        attachments = volume.extra['attachments']
        assert len(attachments) > 0, "Volume is not attached to any node"
        success = True
        result = None
        for attachment in attachments:
            if not ex_attachment_id or ex_attachment_id in attachment['href']:
                attachment_id = attachment['href'].split('/')[-1]
                if ex_node:
                    node_id = self.ex_describe_attachment(
                        attachment_id)['device']['href'].split('/')[-1]
                    if node_id != ex_node.id:
                        continue
                path = '/storage/attachments/%s' % (
                    ex_attachment_id or attachment_id)
                result = self.connection.request(path, method='DELETE')
                success = success and result.status == httplib.NO_CONTENT

        return result and success

    def create_volume_snapshot(self, volume, name=''):
        """
        Create a new volume snapshot.

        :param volume: Volume to create a snapshot for
        :type volume: class:`StorageVolume`

        :return: The newly created volume snapshot.
        :rtype: :class:`VolumeSnapshot`
        """
        path = '/storage/%s/snapshots' % volume.id
        res = self.connection.request(path, method='POST')
        assert res.status == httplib.ACCEPTED
        return volume.list_snapshots()[-1]

    def destroy_volume_snapshot(self, snapshot):
        """
        Delete a volume snapshot

        :param snapshot: volume snapshot to delete
        :type snapshot: class:`VolumeSnapshot`

        :rtype: ``bool``
        """
        volume_id = snapshot.extra['volume']['href'].split('/')[-1]
        path = '/storage/%s/snapshots/%s' % (volume_id, snapshot.id)
        res = self.connection.request(path, method='DELETE')
        return res.status == httplib.NO_CONTENT

    def list_volume_snapshots(self, volume, include=''):
        """
        List snapshots for a volume.

        :param volume: Volume to list snapshots for
        :type volume: class:`StorageVolume`

        :return: List of volume snapshots.
        :rtype: ``list`` of :class: `VolumeSnapshot`
        """
        path = '/storage/%s/snapshots' % volume.id
        params = {}
        if include:
            params['include'] = include
        data = self.connection.request(path, params=params).object['snapshots']
        return list(map(self._to_volume_snapshot, data))

    def _to_volume_snapshot(self, data):
        created = datetime.datetime.strptime(
            data['created_at'], "%Y-%m-%dT%H:%M:%S")
        return VolumeSnapshot(id=data['id'],
                              name=data['id'],
                              created=created,
                              state=data['status'],
                              driver=self, extra=data)

    def ex_modify_volume(self, volume, description=None, size=None,
                         locked=None, billing_cycle=None,
                         customdata=None):
        path = '/storage/%s' % volume.id
        params = {}
        if description:
            params['description'] = description
        if size:
            params['size'] = size
        if locked is not None:
            params['locked'] = locked
        if billing_cycle:
            params['billing_cycle'] = billing_cycle
        res = self.connection.request(path, params=params, method='PUT')
        return self._to_volume(res.object)

    def ex_restore_volume(self, snapshot):
        volume_id = snapshot.extra['volume']['href'].split('/')[-1]
        ts = snapshot.extra['timestamp']
        path = '/storage/%s/restore?restore_point=%s' % (volume_id, ts)
        res = self.connection.request(path, method='POST')
        return res.status == httplib.NO_CONTENT

    def ex_clone_volume(self, volume, snapshot=None):
        path = '/storage/%s/clone' % volume.id
        if snapshot:
            path += '?snapshot_timestamp=%s' % snapshot.extra['timestamp']
        res = self.connection.request(path, method='POST')
        return res.status == httplib.NO_CONTENT

    def ex_describe_volume(self, volume_id):
        path = '/storage/%s' % volume_id
        data = self.connection.request(path).object
        return self._to_volume(data)

    def ex_describe_attachment(self, attachment_id):
        path = '/storage/attachments/%s' % attachment_id
        data = self.connection.request(path).object
        return data


class Project(object):
    def __init__(self, project):
        self.id = project.get('id')
        self.name = project.get('name')
        self.extra = {}
        self.extra['max_devices'] = project.get('max_devices')
        self.extra['payment_method'] = project.get('payment_method')
        self.extra['created_at'] = project.get('created_at')
        self.extra['credit_amount'] = project.get('credit_amount')
        self.extra['devices'] = project.get('devices')
        self.extra['invitations'] = project.get('invitations')
        self.extra['memberships'] = project.get('memberships')
        self.extra['href'] = project.get('href')
        self.extra['members'] = project.get('members')
        self.extra['ssh_keys'] = project.get('ssh_keys')

    def __repr__(self):
        return (('<Project: id=%s, name=%s>') %
                (self.id, self.name))
