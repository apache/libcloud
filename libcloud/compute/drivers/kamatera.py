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
Kamatera node driver
"""
import base64
import json

from libcloud.utils.py3 import httplib, b, basestring
from libcloud.compute.base import NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage, Node, NodeState, NodeAuthPassword
from libcloud.compute.types import Provider
from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.common.types import InvalidCredsError
# from libcloud.common.upcloud import UpcloudCreateNodeRequestBody
# from libcloud.common.upcloud import UpcloudNodeDestroyer
# from libcloud.common.upcloud import UpcloudNodeOperations
# from libcloud.common.upcloud import PlanPrice


EX_BILLINGCYCLE_HOURLY = 'hourly'
EX_BILLINGCYCLE_MONTHLY = 'monthly'


class KamateraResponse(JsonResponse):
    """
    Response class for KamateraDriver
    """

    # def success(self):
    #     if self.status == httplib.NO_CONTENT:
    #         return True
    #     return super(UpcloudResponse, self).success()

    def parse_error(self):
        data = self.parse_body()
        if 'message' in data:
            return data['message']
        else:
            return json.dumps(data)


class KamateraConnection(ConnectionUserAndKey):
    """
    Connection class for KamateraDriver
    """

    host = 'cloudcli.cloudwm.com'
    responseCls = KamateraResponse

    def add_default_headers(self, headers):
        """Adds headers that are needed for all requests"""
        headers['AuthClientId'] = self.user_id
        headers['AuthSecret'] = self.key
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'
        return headers


class KamateraNodeDriver(NodeDriver):
    """
    Kamatera node driver

    :keyword    key: API Client ID, required for authentication
    :type       key: ``str``

    :keyword    secret: API Secret, required for authentcaiont
    :type       secret: ``str``
    """

    type = Provider.KAMATERA
    name = 'Kamatera'
    website = 'https://www.kamatera.com/'
    connectionCls = KamateraConnection
    features = {'create_node': ['password', 'generates_password']}

    # NODE_STATE_MAP = {
    #     'started': NodeState.RUNNING,
    #     'stopped': NodeState.STOPPED,
    #     'maintenance': NodeState.RECONFIGURING,
    #     'error': NodeState.ERROR
    # }

    def list_locations(self):
        """
        List available locations for deployment

        :rtype: ``list`` of :class:`NodeLocation`
        """
        response = self.connection.request('service/server?datacenter=1')
        return self._to_node_locations(response.object)

    def list_sizes(self, location):
        """
        List predefined sizes for the given location.

        :param location: Location of the deployement.
        :type location: :class:`.NodeLocation`

        @inherits: :class:`NodeDriver.list_sizes`
        """
        response = self.connection.request('service/server?sizes=1&datecenter=%s' % location.id)
        return [NodeSize(id=size['id'],
                         name=size['id'],
                         ram=size['ramMB'],
                         disk=size['diskSizeGB'],
                         bandwidth=0,
                         price=0,
                         driver=self.connection.driver,
                         extra={
                             'cpuType': size['cpuType'],
                             'cpuCores': size['cpuCores'],
                             'monthlyTrafficPackage': size['monthlyTrafficPackage'],
                             'extraDiskSizesGB': []
                         }) for size in response.object]

    def list_images(self, location):
        """
        List available disk images.

        :param location: Location of the deployement. Available disk
        images depend on location.
        :type location: :class:`.NodeLocation`

        :rtype: ``list`` of :class:`NodeImage`
        """
        response = self.connection.request('service/server?images=1&datacenter=%s' % location.id)
        return self._to_node_images(response.object)

    def ex_list_capabilities(self, location):
        """
        List capabilities for given location.

        :param location: Location of the deployment.
        :type location: :class:`.NodeLocation`

        :return: ``dict``
        """
        return self.connection.request('service/server?capabilities=1&datacenter=%s' % location.id).object

    def create_node(self, name, size, image, location, auth=None,
                    ex_dailybackup=False, ex_managed=False, ex_quantity=1,
                    ex_billingcycle=EX_BILLINGCYCLE_HOURLY, ex_poweronaftercreate=True):
        """
        Creates Kamatera instance.

        If auth is not given then password will be generated.

        :param name:   String with a name for this new node (required)
        :type name:   ``str``

        :param size:   The size of resources allocated to this node.
                            (required)
        :type size:   :class:`.NodeSize`

        :param image:  OS Image to boot on node. (required)
        :type image:  :class:`.NodeImage`

        :param location: Which data center to create a node in. If empty,
                              undefined behavior will be selected. (optional)
        :type location: :class:`.NodeLocation`

        :param auth:   Initial authentication information for the node
                            (optional)
        :type auth:   :class:`.NodeAuthSSHKey`

        :param ex_hostname: Hostname. Default is 'localhost'. (optional)
        :type ex_hostname: ``str``

        :param ex_username: User's username, which is created.
                            Default is 'root'. (optional)
        :type ex_username: ``str``

        :return: The newly created node.
        :rtype: :class:`.Node`
        """
        if isinstance(auth, basestring):
            password = auth
            generate_password = False
        else:
            auth_obj = self._get_and_check_auth(auth)
            password = '__generate__' if getattr(auth_obj, "generated", False) else auth_obj.password
            generate_password = True
        response = self.connection.request(
            'service/server',
            method='POST',
            data=json.dumps({
                "name": name,
                "password": password,
                "datacenter": location.id,
                "image": image.id,
                "cpu": '%s%s' % (size.extra['cpuCores'], size.extra['cpuType']),
                "ram": size.ram,
                "disk": ' '.join(['size=%d' % disksize for disksize in [size.disk] + size.extra['extraDiskSizesGB']]),
                "dailybackup": 'yes' if ex_dailybackup else 'no',
                "managed": 'yes' if ex_managed else 'no',
                "network": "name=wan,ip=auto",
                "quantity": ex_quantity,
                "billingcycle": ex_billingcycle,
                "monthlypackage": size.extra['monthlyTrafficPackage'],
                "poweronaftercreate": 'yes' if ex_poweronaftercreate else 'no'
                }))
        if generate_password:
            command_ids = response.object['commandIds']
            generated_password = response.object['password']
        else:
            command_ids = response.object
            generate_password = None

        # server = response.object['server']
        # if getattr(auth_obj, "generated", False):
        #     new_node.extra['password'] = auth_obj.password
        # return new_node

    def list_nodes(self):
        """
        List nodes

        :return: List of node objects
        :rtype: ``list`` of :class:`Node`
        """
        servers = []
        for nid in self._node_ids():
            response = self.connection.request('1.2/server/{0}'.format(nid))
            servers.append(response.object['server'])
        return self._to_nodes(servers)

    def reboot_node(self, node):
        """
        Reboot the given node

        :param      node: the node to reboot
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        body = {
            'restart_server': {
                'stop_type': 'hard'
            }
        }
        self.connection.request('1.2/server/{0}/restart'.format(node.id),
                                method='POST',
                                data=json.dumps(body))
        return True

    def destroy_node(self, node):
        """
        Destroy the given node

        The disk resources, attached to node,  will not be removed.

        :param       node: the node to destroy
        :type        node: :class:`Node`

        :rtype: ``bool``
        """

        operations = UpcloudNodeOperations(self.connection)
        destroyer = UpcloudNodeDestroyer(operations)
        return destroyer.destroy_node(node.id)

    def _node_ids(self):
        """
        Returns list of server uids currently on upcloud
        """
        response = self.connection.request('1.2/server')
        servers = response.object['servers']['server']
        return [server['uuid'] for server in servers]

    def _to_nodes(self, servers):
        return [self._to_node(server) for server in servers]

    def _to_node(self, server, state=None):
        ip_addresses = server['ip_addresses']['ip_address']
        public_ips = [ip['address'] for ip in ip_addresses
                      if ip['access'] == 'public']
        private_ips = [ip['address'] for ip in ip_addresses
                       if ip['access'] == 'private']

        extra = {'vnc_password': server['vnc_password']}
        if 'password' in server:
            extra['password'] = server['password']
        return Node(id=server['uuid'],
                    name=server['title'],
                    state=state or self.NODE_STATE_MAP[server['state']],
                    public_ips=public_ips,
                    private_ips=private_ips,
                    driver=self,
                    extra=extra)

    def _to_node_locations(self, datacenters):
        return [self._construct_node_location(datacenter) for datacenter in datacenters]

    def _construct_node_location(self, datacenter):
        return NodeLocation(id=datacenter['id'],
                            name=datacenter['subCategory'],
                            country=datacenter['name'],
                            driver=self)

    def _to_node_images(self, images):
        return [self._construct_node_image(image) for image in images]

    def _construct_node_image(self, image):
        extra = self._copy_dict(('datacenter', 'os', 'code', 'osDiskSizeGB', 'ramMBMin'), image)
        return NodeImage(id=image['id'],
                         name=image['name'],
                         driver=self,
                         extra=extra)

    def _copy_dict(self, keys, d):
        extra = {}
        for key in keys:
            extra[key] = d[key]
        return extra
