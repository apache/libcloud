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
Dimension Data Common Components
"""
from base64 import b64encode
from time import sleep
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b

from libcloud.common.base import ConnectionUserAndKey, XmlResponse
from libcloud.common.types import LibcloudError, InvalidCredsError
from libcloud.utils.xml import findtext

# Roadmap / TODO:
#
# 1.0 - Copied from OpSource API, named provider details.

# setup a few variables to represent all of the DimensionData cloud namespaces
NAMESPACE_BASE = "http://oec.api.opsource.net/schemas"
ORGANIZATION_NS = NAMESPACE_BASE + "/organization"
SERVER_NS = NAMESPACE_BASE + "/server"
NETWORK_NS = NAMESPACE_BASE + "/network"
DIRECTORY_NS = NAMESPACE_BASE + "/directory"

# API 2.0 Namespaces and URNs
TYPES_URN = "urn:didata.com:api:cloud:types"

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
        'host': 'api-ap.dimensiondata.com',
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


class NetworkDomainServicePlan(object):
    ESSENTIALS = "ESSENTIALS"
    ADVANCED = "ADVANCED"


class DimensionDataResponse(XmlResponse):
    def parse_error(self):
        if self.status == httplib.UNAUTHORIZED:
            raise InvalidCredsError(self.body)
        elif self.status == httplib.FORBIDDEN:
            raise InvalidCredsError(self.body)

        body = self.parse_body()

        if self.status == httplib.BAD_REQUEST:
            code = findtext(body, 'responseCode', SERVER_NS)
            if code is None:
                code = findtext(body, 'responseCode', TYPES_URN)
            message = findtext(body, 'message', SERVER_NS)
            if message is None:
                message = findtext(body, 'message', TYPES_URN)
            raise DimensionDataAPIException(code=code,
                                            msg=message,
                                            driver=self.connection.driver)
        if self.status is not httplib.OK:
            raise DimensionDataAPIException(code=self.status,
                                            msg=body,
                                            driver=self.connection.driver)

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

    api_path_version_1 = '/oec'
    api_path_version_2 = '/caas'
    api_version_1 = '0.9'
    api_version_2 = '2.0'

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
        headers['Content-Type'] = 'application/xml'
        return headers

    def request_api_1(self, action, params=None, data='',
                      headers=None, method='GET'):
        action = "%s/%s/%s" % (self.api_path_version_1,
                               self.api_version_1, action)

        return super(DimensionDataConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers)

    def request_api_2(self, path, action, params=None, data='',
                      headers=None, method='GET'):
        action = "%s/%s/%s/%s" % (self.api_path_version_2,
                                  self.api_version_2, path, action)

        return super(DimensionDataConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers)

    def request_with_orgId_api_1(self, action, params=None, data='',
                                 headers=None, method='GET'):
        action = "%s/%s" % (self.get_resource_path_api_1(), action)

        return super(DimensionDataConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers)

    def request_with_orgId_api_2(self, action, params=None, data='',
                                 headers=None, method='GET'):
        action = "%s/%s" % (self.get_resource_path_api_2(), action)

        return super(DimensionDataConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers)

    def get_resource_path_api_1(self):
        """
        This method returns a resource path which is necessary for referencing
        resources that require a full path instead of just an ID, such as
        networks, and customer snapshots.
        """
        return ("%s/%s/%s" % (self.api_path_version_1, self.api_version_1,
                              self._get_orgId()))

    def get_resource_path_api_2(self):
        """
        This method returns a resource path which is necessary for referencing
        resources that require a full path instead of just an ID, such as
        networks, and customer snapshots.
        """
        return ("%s/%s/%s" % (self.api_path_version_2, self.api_version_2,
                              self._get_orgId()))

    def wait_for_state(self, state, func, poll_interval, timeout, *args, **kwargs):
        """
        Wait for the function which returns a instance
        with field status to match

        Keep polling func until one of the desired states is matched

        :param state: Either the desired state (`str`) or a `list` of states
        :type  state: ``str`` or ``list``

        :param  func: The function to call, e.g. ex_get_vlan
        :type   func: ``function``

        :param  poll_interval: The number of seconds to wait between checks
        :type   poll_interval: `int`

        :param  timeout: The total number of seconds to wait to reach a state
        :type   timeout: `int`

        :param  args: The arguments for func
        :type   args: Positional arguments

        :param  kwargs: The arguments for func
        :type   kwargs: Keyword arguments
        """
        cnt = 0
        while cnt < timeout/poll_interval:
            response = func(*args, **kwargs)
            if response.status is state or response.status in state:
                return response
            sleep(poll_interval)
            cnt+=1
        raise Error("Request timed out")

    def _get_orgId(self):
        """
        Send the /myaccount API request to DimensionData cloud and parse the
        'orgId' from the XML response object. We need the orgId to use most
        of the other API functions
        """
        if self._orgId is None:
            body = self.request_api_1('myaccount').object
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


class DimensionDataNetworkDomain(object):
    """
    DimensionData network domain with location.
    """

    def __init__(self, id, name, description, location, status, plan):
        self.id = str(id)
        self.name = name
        self.description = description
        self.location = location
        self.status = status
        self.plan = plan

    def __repr__(self):
        return (('<DimensionDataNetworkDomain: id=%s, name=%s,'
                 'description=%s, location=%s, status=%s>')
                % (self.id, self.name, self.description, self.location,
                   self.status))


class DimensionDataPublicIpBlock(object):
    """
    DimensionData Public IP Block with location.
    """

    def __init__(self, id, base_ip, size, location, network_domain,
                 status):
        self.id = str(id)
        self.base_ip = base_ip
        self.size = size
        self.location = location
        self.network_domain = network_domain
        self.status = status

    def __repr__(self):
        return (('<DimensionDataNetworkDomain: id=%s, base_ip=%s,'
                 'size=%s, location=%s, status=%s>')
                % (self.id, self.base_ip, self.size, self.location,
                   self.status))


class DimensionDataFirewallRule(object):
    """
    DimensionData Firewall Rule for a network domain
    """

    def __init__(self, id, name, action, location, network_domain,
                 status, ip_version, protocol, source, destination,
                 enabled):
        self.id = str(id)
        self.name = name
        self.action = action
        self.location = location
        self.network_domain = network_domain
        self.status = status
        self.ip_version = ip_version
        self.protocol = protocol
        self.source = source
        self.destination = destination
        self.enabled = enabled

    def __repr__(self):
        return (('<DimensionDataNetworkDomain: id=%s, name=%s,'
                 'action=%s, location=%s, status=%s>')
                % (self.id, self.name, self.action, self.location,
                   self.status))


class DimensionDataFirewallAddress(object):
    """
    The source or destination model in a firewall rule
    """
    def __init__(self, any_ip, ip_address, ip_prefix_size,
                 port_begin, port_end):
        self.any_ip = any_ip
        self.ip_address = ip_address
        self.ip_prefix_size = ip_prefix_size
        self.port_begin = port_begin
        self.port_end = port_end


class DimensionDataNatRule(object):
    """
    An IP NAT rule in a network domain
    """
    def __init__(self, id, network_domain, internal_ip, external_ip, status):
        self.id = id
        self.network_domain = network_domain
        self.internal_ip = internal_ip
        self.external_ip = external_ip
        self.status = status

    def __repr__(self):
        return (('<DimensionDataNatRule: id=%s, status=%s>')
                % (self.id, self.status))


class DimensionDataVlan(object):
    """
    DimensionData VLAN.
    """

    def __init__(self, id, name, description, location, network_domain,
                 status, private_ipv4_range_address, private_ipv4_range_size):
        """
        Initialize an instance of ``DimensionDataVlan``

        :param id: The ID of the VLAN
        :type  id: ``string``

        :param name: The name of the VLAN
        :type  name: ``string``

        :param description: Plan text description of the VLAN
        :type  description: ``string``

        :param location: The location (data center) of the VLAN
        :type  location: ``NodeLocation``

        :param network_domain: The Network Domain that owns this VLAN
        :type  network_domain: :class:`DimensionDataNetworkDomain`

        :param status: The status of the VLAN
        :type  status: :class:`DimensionDataStatus`

        :param private_ipv4_range_address: The host address of the VLAN
                                            IP space
        :type  private_ipv4_range_address: ``string``

        :param private_ipv4_range_address: The size (e.g. '24') of the VLAN
                                            as a CIDR range size
        :type  private_ipv4_range_address: ``string``
        """
        self.id = str(id)
        self.name = name
        self.location = location
        self.description = description
        self.network_domain = network_domain
        self.status = status
        self.private_ipv4_range_address = private_ipv4_range_address
        self.private_ipv4_range_size = private_ipv4_range_size

    def __repr__(self):
        return (('<DimensionDataVlan: id=%s, name=%s, '
                 'description=%s, location=%s, status=%s>')
                % (self.id, self.name, self.description,
                   self.location, self.status))


class DimensionDataPool(object):
    """
    DimensionData VIP Pool.
    """

    def __init__(self, id, name, description, status, load_balance_method,
                 health_monitor_id, service_down_action, slow_ramp_time):
        self.id = str(id)
        self.name = name
        self.description = description
        self.status = status
        self.load_balance_method = load_balance_method
        self.health_monitor_id = health_monitor_id
        self.service_down_action = service_down_action
        self.slow_ramp_time = slow_ramp_time

    def __repr__(self):
        return (('<DimensionDataPool: id=%s, name=%s, '
                 'description=%s, status=%s>')
                % (self.id, self.name, self.description,
                   self.status))


class DimensionDataPoolMember(object):
    """
    DimensionData VIP Pool Member.
    """

    def __init__(self, id, name, status, ip, port, node_id):
        self.id = str(id)
        self.name = name
        self.status = status
        self.ip = ip
        self.port = port
        self.node_id = node_id

    def __repr__(self):
        return (('<DimensionDataPool: id=%s, name=%s, '
                 'ip=%s, status=%s, port=%s, node_id=%s')
                % (self.id, self.name,
                   self.ip, self.status, self.port,
                   self.node_id))


class DimensionDataVIPNode(object):
    def __init__(self, id, name, status, ip, connection_limit='10000',
                 connection_rate_limit='10000'):
        self.id = str(id)
        self.name = name
        self.status = status
        self.ip = ip
        self.connection_limit = connection_limit
        self.connection_rate_limit = connection_rate_limit

    def __repr__(self):
        return (('<DimensionDataVIPNode: id=%s, name=%s, '
                 'status=%s, ip=%s>')
                % (self.id, self.name,
                   self.status, self.ip))


class DimensionDataVirtualListener(object):
    """
    DimensionData Virtual Listener.
    """

    def __init__(self, id, name, status, ip):
        self.id = str(id)
        self.name = name
        self.status = status
        self.ip = ip

    def __repr__(self):
        return (('<DimensionDataPool: id=%s, name=%s, '
                 'status=%s, ip=%s>')
                % (self.id, self.name,
                   self.status, self.ip))
