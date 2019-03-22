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
import multiprocessing.pool

from libcloud.utils.py3 import httplib

from libcloud.common.base import ConnectionKey, JsonResponse
from libcloud.compute.types import Provider, NodeState, InvalidCredsError
from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.providers import get_driver
from libcloud.compute.base import NodeImage, NodeSize, NodeLocation
from libcloud.compute.base import KeyPair

PACKET_ENDPOINT = "api.packet.net"


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
    website = 'http://www.packet.net/'

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
        # initialize a NodeDriver for packet.net using the API token
        # and optionally the project (name or id)
        # If project specified we need to be sure this is a valid project
        # so we create the variable self.project_id
        super(PacketNodeDriver, self).__init__(key=key, project=None)
        self.project_name = project
        self.project_id = None
        self.projects = self.ex_list_projects()
        if project:
            for project_obj in self.projects:
                if project in [project_obj.name, project_obj.id]:
                    self.project_id = project_obj.id
                    break
            if not self.project_id:
                self.project_name = None

    def ex_list_projects(self):
        projects = []
        data = self.connection.request('/projects').object
        projects = data.get('projects')
        if projects:
            projects = [Project(project) for project in projects]
        return projects

    def list_nodes(self, ex_project_id=None):
        if ex_project_id:
            return self.list_nodes_for_project(ex_project_id=ex_project_id)
        else:
            # if project has been specified on initialization of driver, then
            # return nodes for this project only
            if self.project_id:
                return self.list_nodes_for_project(
                    ex_project_id=self.project_id)
            else:
                projects = [project.id for project in self.projects]

                def _list_one(project):
                    driver = get_driver(self.type)(self.key)
                    try:
                        return driver.list_nodes_for_project(project)
                    except Exception:
                        return []
                pool = multiprocessing.pool.ThreadPool(8)
                results = pool.map(_list_one, projects)
                pool.terminate()
                nodes = []
                for result in results:
                    nodes.extend(result)
                return nodes

    def list_nodes_for_project(self, ex_project_id, include='plan', page=1,
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

    def list_sizes(self):
        data = self.connection.request('/plans').object['plans']
        return [self._to_size(size) for size in data if
                size.get('line') == 'baremetal']

    def create_node(self, name, size, image, location,
                    ex_project_id=None, cloud_init=None, **kwargs):
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

        params = {'hostname': name, 'plan': size.id,
                  'operating_system': image.id, 'facility': location.id,
                  'include': 'plan', 'billing_cycle': 'hourly'}
        params.update(kwargs)
        if cloud_init:
            params["userdata"] = cloud_init
        data = self.connection.request('/projects/%s/devices' %
                                       (ex_project_id),
                                       params=params, method='POST')

        status = data.object.get('status', 'OK')
        if status == 'ERROR':
            message = data.object.get('message', None)
            error_message = data.object.get('error_message', message)
            raise ValueError('Failed to create node: %s' % (error_message))
        return self._to_node(data=data.object)

    def reboot_node(self, node):
        params = {'type': 'reboot'}
        res = self.connection.request('/devices/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.OK

    def ex_start_node(self, node):
        params = {'type': 'power_on'}
        res = self.connection.request('/devices/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.OK

    def ex_stop_node(self, node):
        params = {'type': 'power_off'}
        res = self.connection.request('/devices/%s/actions' % (node.id),
                                      params=params, method='POST')
        return res.status == httplib.OK

    def destroy_node(self, node):
        res = self.connection.request('/devices/%s' % (node.id),
                                      method='DELETE')
        return res.status == httplib.OK

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
            extra['facility'] = data['facility'].get('code')

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
        return NodeLocation(id=data['code'], name=data['name'], country=None,
                            driver=self)

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
                        ram=int(ram.replace('GB', ''))*1024, disk=disk,
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

    def ex_list_events_for_node(self, node, include=None, page=1, per_page=10):
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
