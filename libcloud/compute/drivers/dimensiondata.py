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
Dimension Data Driver
"""

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from base64 import b64encode

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b

from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.base import NodeSize, NodeImage, NodeLocation
from libcloud.common.types import LibcloudError, InvalidCredsError
from libcloud.common.base import ConnectionUserAndKey, XmlResponse
from libcloud.utils.xml import fixxpath, findtext, findall
from libcloud.compute.types import NodeState, Provider

# Roadmap / TODO:
#
# 1.0 - Copied from OpSource API, named provider details.

# setup a few variables to represent all of the DimensionData cloud namespaces
NAMESPACE_BASE = "http://oec.api.opsource.net/schemas"
ORGANIZATION_NS = NAMESPACE_BASE + "/organization"
SERVER_NS = NAMESPACE_BASE + "/server"
NETWORK_NS = NAMESPACE_BASE + "/network"
DIRECTORY_NS = NAMESPACE_BASE + "/directory"
RESET_NS = NAMESPACE_BASE + "/reset"
VIP_NS = NAMESPACE_BASE + "/vip"
IMAGEIMPORTEXPORT_NS = NAMESPACE_BASE + "/imageimportexport"
DATACENTER_NS = NAMESPACE_BASE + "/datacenter"
SUPPORT_NS = NAMESPACE_BASE + "/support"
GENERAL_NS = NAMESPACE_BASE + "/general"
IPPLAN_NS = NAMESPACE_BASE + "/ipplan"
WHITELABEL_NS = NAMESPACE_BASE + "/whitelabel"

# API end-points
API_ENDPOINTS = {
    'dd-na': {
        'name': 'North America (NA)',
        'host': 'api-na.dimensiondata.com',
        'vendor': 'DimensionData'
    },
    'dd-eu': {
        'name': 'Europe (EU)',
        'host': 'api-eu.dimensiondata.com',
        'vendor': 'DimensionData'
    },
    'dd-au': {
        'name': 'Australia (AU)',
        'host': 'api-au.dimensiondata.com',
        'vendor': 'DimensionData'
    },
    'dd-af': {
        'name': 'Africa (AF)',
        'host': 'api-af.dimensiondata.com',
        'vendor': 'DimensionData'
    },
    'dd-ap': {
        'name': 'Asia Pacific (AP)',
        'host': 'api-na.dimensiondata.com',
        'vendor': 'DimensionData'
    },
    'dd-latam': {
        'name': 'South America (LATAM)',
        'host': 'api-latam.dimensiondata.com',
        'vendor': 'DimensionData'
    },
    'dd-canada': {
        'name': 'Canada (CA)',
        'host': 'api-canada.dimensiondata.com',
        'vendor': 'DimensionData'
    }
}

# Default API end-point for the base connection class.
DEFAULT_REGION = 'dd-na'


class DimensionDataResponse(XmlResponse):
    def parse_error(self):
        if self.status == httplib.UNAUTHORIZED:
            raise InvalidCredsError(self.body)
        elif self.status == httplib.FORBIDDEN:
            raise InvalidCredsError(self.body)

        body = self.parse_body()

        if self.status == httplib.BAD_REQUEST:
            code = findtext(body, 'resultCode', SERVER_NS)
            message = findtext(body, 'resultDetail', SERVER_NS)
            raise DimensionDataAPIException(code,
                                            message,
                                            driver=DimensionDataNodeDriver)

        return self.body


class DimensionDataAPIException(LibcloudError):
    def __init__(self, code, msg, driver):
        self.code = code
        self.msg = msg
        self.driver = driver

    def __str__(self):
        return "%s: %s" % (self.code, self.msg)

    def __repr__(self):
        return ("<DimensionDataAPIException: code='%s', msg='%s'>" %
                (self.code, self.msg))


class DimensionDataConnection(ConnectionUserAndKey):
    """
    Connection class for the DimensionData driver
    """

    api_path = '/oec'
    api_version = '0.9'
    _orgId = None
    responseCls = DimensionDataResponse

    allow_insecure = False

    def __init__(self, user_id, key, secure=True, host=None, port=None,
                 url=None, timeout=None, proxy_url=None, **conn_kwargs):
        super(DimensionDataConnection, self).__init__(
            user_id=user_id,
            key=key,
            secure=secure,
            host=host, port=port,
            url=url, timeout=timeout,
            proxy_url=proxy_url)

        if conn_kwargs['region']:
            self.host = conn_kwargs['region']['host']

    def add_default_headers(self, headers):
        headers['Authorization'] = \
            ('Basic %s' % b64encode(b('%s:%s' % (self.user_id,
                                                 self.key))).decode('utf-8'))
        return headers

    def request(self, action, params=None, data='',
                headers=None, method='GET'):
        action = "%s/%s/%s" % (self.api_path, self.api_version, action)

        return super(DimensionDataConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers)

    def request_with_orgId(self, action, params=None, data='',
                           headers=None, method='GET'):
        action = "%s/%s" % (self.get_resource_path(), action)

        return super(DimensionDataConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers)

    def get_resource_path(self):
        """
        This method returns a resource path which is necessary for referencing
        resources that require a full path instead of just an ID, such as
        networks, and customer snapshots.
        """
        return ("%s/%s/%s" % (self.api_path, self.api_version,
                              self._get_orgId()))

    def _get_orgId(self):
        """
        Send the /myaccount API request to DimensionData cloud and parse the
        'orgId' from the XML response object. We need the orgId to use most
        of the other API functions
        """
        if self._orgId is None:
            body = self.request('myaccount').object
            self._orgId = findtext(body, 'orgId', DIRECTORY_NS)
        return self._orgId


class DimensionDataStatus(object):
    """
    DimensionData API pending operation status class
        action, request_time, user_name, number_of_steps, update_time,
        step.name, step.number, step.percent_complete, failure_reason,
    """
    def __init__(self, action=None, request_time=None, user_name=None,
                 number_of_steps=None, update_time=None, step_name=None,
                 step_number=None, step_percent_complete=None,
                 failure_reason=None):
        self.action = action
        self.request_time = request_time
        self.user_name = user_name
        self.number_of_steps = number_of_steps
        self.update_time = update_time
        self.step_name = step_name
        self.step_number = step_number
        self.step_percent_complete = step_percent_complete
        self.failure_reason = failure_reason

    def __repr__(self):
        return (('<DimensionDataStatus: action=%s, request_time=%s, '
                 'user_name=%s, number_of_steps=%s, update_time=%s, '
                 'step_name=%s, step_number=%s, '
                 'step_percent_complete=%s, failure_reason=%s')
                % (self.action, self.request_time, self.user_name,
                   self.number_of_steps, self.update_time, self.step_name,
                   self.step_number, self.step_percent_complete,
                   self.failure_reason))


class DimensionDataNetwork(object):
    """
    DimensionData network with location.
    """

    def __init__(self, id, name, description, location, private_net,
                 multicast, status):
        self.id = str(id)
        self.name = name
        self.description = description
        self.location = location
        self.private_net = private_net
        self.multicast = multicast
        self.status = status

    def __repr__(self):
        return (('<DimensionDataNetwork: id=%s, name=%s, description=%s, '
                 'location=%s, private_net=%s, multicast=%s>')
                % (self.id, self.name, self.description, self.location,
                   self.private_net, self.multicast))


class DimensionDataNodeDriver(NodeDriver):
    """
    DimensionData node driver.
    """

    selected_region = None
    connectionCls = DimensionDataConnection
    name = 'DimensionData'
    website = 'http://www.dimensiondata.com/'
    type = Provider.DIMENSIONDATA
    features = {'create_node': ['password']}
    api_version = 1.0

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=None, region=DEFAULT_REGION, **kwargs):

        if region not in API_ENDPOINTS:
            raise ValueError('Invalid region: %s' % (region))

        self.selected_region = API_ENDPOINTS[region]

        super(DimensionDataNodeDriver, self).__init__(key=key, secret=secret,
                                                      secure=secure, host=host,
                                                      port=port,
                                                      api_version=api_version,
                                                      region=region,
                                                      **kwargs)

    def _ex_connection_class_kwargs(self):
        """
            Add the region to the kwargs before the connection is instantiated
        """

        kwargs = super(DimensionDataNodeDriver,
                       self)._ex_connection_class_kwargs()
        kwargs['region'] = self.selected_region
        return kwargs

    def create_node(self, name, image, auth, ex_description,
                    ex_network, ex_is_started=True, **kwargs):
        """
        Create a new DimensionData node

        :keyword    name:   String with a name for this new node (required)
        :type       name:   ``str``

        :keyword    image:  OS Image to boot on node. (required)
        :type       image:  :class:`NodeImage`

        :keyword    auth:   Initial authentication information for the
                            node (required)
        :type       auth:   :class:`NodeAuthPassword`

        :keyword    ex_description:  description for this node (required)
        :type       ex_description:  ``str``

        :keyword    ex_network:  Network to create the node within (required)
        :type       ex_network: :class:`DimensionDataNetwork`

        :keyword    ex_is_started:  Start server after creation? default
                                   true (required)
        :type       ex_is_started:  ``bool``

        :return: The newly created :class:`Node`. NOTE: DimensionData does not
                 provide a
                 way to determine the ID of the server that was just created,
                 so the returned :class:`Node` is not guaranteed to be the same
                 one that was created.  This is only the case when multiple
                 nodes with the same name exist.
        :rtype: :class:`Node`
        """

        # XXX:  Node sizes can be adjusted after a node is created, but
        #       cannot be set at create time because size is part of the
        #       image definition.
        password = None
        auth_obj = self._get_and_check_auth(auth)
        password = auth_obj.password

        if not isinstance(ex_network, DimensionDataNetwork):
            raise ValueError('ex_network must be of DimensionDataNetwork type')
        vlanResourcePath = "%s/%s" % (self.connection.get_resource_path(),
                                      ex_network.id)

        imageResourcePath = None
        if 'resourcePath' in image.extra:
            imageResourcePath = image.extra['resourcePath']
        else:
            imageResourcePath = "%s/%s" % (self.connection.get_resource_path(),
                                           image.id)

        server_elm = ET.Element('Server', {'xmlns': SERVER_NS})
        ET.SubElement(server_elm, "name").text = name
        ET.SubElement(server_elm, "description").text = ex_description
        ET.SubElement(server_elm, "vlanResourcePath").text = vlanResourcePath
        ET.SubElement(server_elm, "imageResourcePath").text = imageResourcePath
        ET.SubElement(server_elm, "administratorPassword").text = password
        ET.SubElement(server_elm, "isStarted").text = str(ex_is_started)

        self.connection.request_with_orgId('server',
                                           method='POST',
                                           data=ET.tostring(server_elm)).object

        # XXX: return the last node in the list that has a matching name.  this
        #      is likely but not guaranteed to be the node we just created
        #      because DimensionData allows multiple
        #      nodes to have the same name
        node = list(filter(lambda x: x.name == name, self.list_nodes()))[-1]

        if getattr(auth_obj, "generated", False):
            node.extra['password'] = auth_obj.password

        return node

    def destroy_node(self, node):
        body = self.connection.request_with_orgId(
            'server/%s?delete' % (node.id)).object

        result = findtext(body, 'result', GENERAL_NS)
        return result == 'SUCCESS'

    def reboot_node(self, node):
        body = self.connection.request_with_orgId(
            'server/%s?restart' % (node.id)).object
        result = findtext(body, 'result', GENERAL_NS)
        return result == 'SUCCESS'

    def list_nodes(self):
        nodes = self._to_nodes(
            self.connection.request_with_orgId('server/deployed').object)
        nodes.extend(self._to_nodes(
            self.connection.request_with_orgId('server/pendingDeploy').object))
        return nodes

    def list_images(self, location=None):
        """
        return a list of available images
            Currently only returns the default 'base OS images' provided by
            DimensionData. Customer images (snapshots) are not yet supported.

        @inherits: :class:`NodeDriver.list_images`
        """
        return self._to_base_images(
            self.connection.request('base/image').object)

    def list_sizes(self, location=None):
        return [
            NodeSize(id=1,
                     name="default",
                     ram=0,
                     disk=0,
                     bandwidth=0,
                     price=0,
                     driver=self.connection.driver),
        ]

    def list_locations(self):
        """
        list locations (datacenters) available for instantiating servers and
        networks.

        @inherits: :class:`NodeDriver.list_locations`
        """
        return self._to_locations(
            self.connection.request_with_orgId('datacenter').object)

    def list_networks(self, location=None):
        """
        List networks deployed across all data center locations for your
        organization.  The response includes the location of each network.


        :keyword location: The location
        :type    location: :class:`NodeLocation`

        :return: a list of DimensionDataNetwork objects
        :rtype: ``list`` of :class:`DimensionDataNetwork`
        """
        return self._to_networks(
            self.connection.request_with_orgId('networkWithLocation').object)

    def _to_base_images(self, object):
        images = []
        for element in object.findall(fixxpath("ServerImage", SERVER_NS)):
            images.append(self._to_base_image(element))

        return images

    def _to_base_image(self, element):
        # Eventually we will probably need multiple _to_image() functions
        # that parse <ServerImage> differently than <DeployedImage>.
        # DeployedImages are customer snapshot images, and ServerImages are
        # 'base' images provided by DimensionData
        location_id = findtext(element, 'location', SERVER_NS)
        location = self.ex_get_location_by_id(location_id)

        extra = {
            'description': findtext(element, 'description', SERVER_NS),
            'OS_type': findtext(element, 'operatingSystem/type', SERVER_NS),
            'OS_displayName': findtext(element, 'operatingSystem/displayName',
                                       SERVER_NS),
            'cpuCount': findtext(element, 'cpuCount', SERVER_NS),
            'resourcePath': findtext(element, 'resourcePath', SERVER_NS),
            'memory': findtext(element, 'memory', SERVER_NS),
            'osStorage': findtext(element, 'osStorage', SERVER_NS),
            'additionalStorage': findtext(element, 'additionalStorage',
                                          SERVER_NS),
            'created': findtext(element, 'created', SERVER_NS),
            'location': location,
        }

        return NodeImage(id=str(findtext(element, 'id', SERVER_NS)),
                         name=str(findtext(element, 'name', SERVER_NS)),
                         extra=extra,
                         driver=self.connection.driver)

    def ex_start_node(self, node):
        """
        Powers on an existing deployed server

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        body = self.connection.request_with_orgId(
            'server/%s?start' % node.id).object
        result = findtext(body, 'result', GENERAL_NS)
        return result == 'SUCCESS'

    def ex_shutdown_graceful(self, node):
        """
        This function will attempt to "gracefully" stop a server by
        initiating a shutdown sequence within the guest operating system.
        A successful response on this function means the system has
        successfully passed the request into the operating system.

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        body = self.connection.request_with_orgId(
            'server/%s?shutdown' % (node.id)).object
        result = findtext(body, 'result', GENERAL_NS)
        return result == 'SUCCESS'

    def ex_power_off(self, node):
        """
        This function will abruptly power-off a server.  Unlike
        ex_shutdown_graceful, success ensures the node will stop but some OS
        and application configurations may be adversely affected by the
        equivalent of pulling the power plug out of the machine.

        :param      node: Node which should be used
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        body = self.connection.request_with_orgId(
            'server/%s?poweroff' % node.id).object
        result = findtext(body, 'result', GENERAL_NS)
        return result == 'SUCCESS'

    def ex_list_networks(self):
        """
        List networks deployed across all data center locations for your
        organization.  The response includes the location of each network.

        :return: a list of DimensionDataNetwork objects
        :rtype: ``list`` of :class:`DimensionDataNetwork`
        """
        response = self.connection.request_with_orgId('networkWithLocation') \
                                  .object
        return self._to_networks(response)

    def ex_get_location_by_id(self, id):
        """
        Get location by ID.

        :param  id: ID of the node location which should be used
        :type   id: ``str``

        :rtype: :class:`NodeLocation`
        """
        if not hasattr(self, '_cached_locations_'):
            self._cached_locations_ = self.list_locations()

        location = None
        if id is not None:
            location = list(
                filter(lambda x: x.id == id, self._cached_locations_))[0]
        return location

    def _to_networks(self, object):
        networks = []
        for element in findall(object, 'network', NETWORK_NS):
            networks.append(self._to_network(element))

        return networks

    def _to_network(self, element):
        multicast = False
        if findtext(element, 'multicast', NETWORK_NS) == 'true':
            multicast = True

        status = self._to_status(element.find(fixxpath('status', NETWORK_NS)))

        location_id = findtext(element, 'location', NETWORK_NS)
        location = self.ex_get_location_by_id(location_id)

        return DimensionDataNetwork(
            id=findtext(element, 'id', NETWORK_NS),
            name=findtext(element, 'name', NETWORK_NS),
            description=findtext(element, 'description',
                                 NETWORK_NS),
            location=location,
            private_net=findtext(element, 'privateNet',
                                 NETWORK_NS),
            multicast=multicast,
            status=status)

    def _to_locations(self, object):
        locations = []
        for element in object.findall(fixxpath('datacenter', DATACENTER_NS)):
            locations.append(self._to_location(element))

        return locations

    def _to_location(self, element):
        l = NodeLocation(id=findtext(element, 'location', DATACENTER_NS),
                         name=findtext(element, 'displayName', DATACENTER_NS),
                         country=findtext(element, 'country', DATACENTER_NS),
                         driver=self)
        return l

    def _to_nodes(self, object):
        node_elements = object.findall(fixxpath('DeployedServer', SERVER_NS))
        node_elements.extend(object.findall(
            fixxpath('PendingDeployServer', SERVER_NS)))
        return [self._to_node(el) for el in node_elements]

    def _to_node(self, element):
        if findtext(element, 'isStarted', SERVER_NS) == 'true':
            state = NodeState.RUNNING
        else:
            state = NodeState.TERMINATED

        status = self._to_status(element.find(fixxpath('status', SERVER_NS)))

        extra = {
            'description': findtext(element, 'description', SERVER_NS),
            'sourceImageId': findtext(element, 'sourceImageId', SERVER_NS),
            'networkId': findtext(element, 'networkId', SERVER_NS),
            'machineName': findtext(element, 'machineName', SERVER_NS),
            'deployedTime': findtext(element, 'deployedTime', SERVER_NS),
            'cpuCount': findtext(element, 'machineSpecification/cpuCount',
                                 SERVER_NS),
            'memoryMb': findtext(element, 'machineSpecification/memoryMb',
                                 SERVER_NS),
            'osStorageGb': findtext(element,
                                    'machineSpecification/osStorageGb',
                                    SERVER_NS),
            'additionalLocalStorageGb': findtext(
                element, 'machineSpecification/additionalLocalStorageGb',
                SERVER_NS),
            'OS_type': findtext(element,
                                'machineSpecification/operatingSystem/type',
                                SERVER_NS),
            'OS_displayName': findtext(
                element, 'machineSpecification/operatingSystem/displayName',
                SERVER_NS),
            'status': status,
        }

        public_ip = findtext(element, 'publicIpAddress', SERVER_NS)

        n = Node(id=findtext(element, 'id', SERVER_NS),
                 name=findtext(element, 'name', SERVER_NS),
                 state=state,
                 public_ips=[public_ip] if public_ip is not None else [],
                 private_ips=findtext(element, 'privateIpAddress', SERVER_NS),
                 driver=self.connection.driver,
                 extra=extra)
        return n

    def _to_status(self, element):
        if element is None:
            return DimensionDataStatus()
        s = DimensionDataStatus(action=findtext(element, 'action', SERVER_NS),
                                request_time=findtext(
                                    element,
                                    'requestTime',
                                    SERVER_NS),
                                user_name=findtext(
                                    element,
                                    'userName',
                                    SERVER_NS),
                                number_of_steps=findtext(
                                    element,
                                    'numberOfSteps',
                                    SERVER_NS),
                                step_name=findtext(
                                    element,
                                    'step/name',
                                    SERVER_NS),
                                step_number=findtext(
                                    element,
                                    'step_number',
                                    SERVER_NS),
                                step_percent_complete=findtext(
                                    element,
                                    'step/percentComplete',
                                    SERVER_NS),
                                failure_reason=findtext(
                                    element,
                                    'failureReason',
                                    SERVER_NS))
        return s
