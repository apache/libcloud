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

import os
import binascii

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.misc import reverse_dict
from libcloud.common.base import JsonResponse
from libcloud.loadbalancer.base import LoadBalancer, Member, Driver, Algorithm
from libcloud.loadbalancer.base import DEFAULT_ALGORITHM
from libcloud.loadbalancer.types import State
from libcloud.common.openstack import OpenStackBaseConnection
from libcloud.common.rackspace import (
        AUTH_URL_US, AUTH_URL_UK)


class RackspaceResponse(JsonResponse):

    def parse_body(self):
        if not self.body:
            return None
        return super(RackspaceResponse, self).parse_body()

    def success(self):
        return 200 <= int(self.status) <= 299


class RackspaceHealthMonitor(object):
    """
    @param type: type of load balancer.  currently CONNECT (connection
                 monitoring), HTTP, HTTPS (connection and HTTP
                 monitoring) are supported.
    @type type: C{str}

    @param delay: minimum seconds to wait before executing the health
                  monitor.  (Must be between 1 and 3600)
    @type delay: C{int}

    @param timeout: maximum seconds to wait when establishing a
                    connection before timing out.  (Must be between 1
                    and 3600)
    @type timeout: C{int}

    @param attempts_before_deactivation: Number of monitor failures
                                         before removing a node from
                                         rotation. (Must be between 1
                                         and 10)
    @type attempts_before_deactivation: C{int}
    """

    def __init__(self, type, delay, timeout, attempts_before_deactivation):
        self.type = type
        self.delay = delay
        self.timeout = timeout
        self.attempts_before_deactivation = attempts_before_deactivation


class RackspaceHTTPHealthMonitor(RackspaceHealthMonitor):
    """
    A HTTP health monitor adds extra features to a Rackspace health monitor.

    @param path: the HTTP path to monitor.
    @type path: C{str}

    @param body_regex: Regular expression used to evaluate the body of
                       the HTTP response.
    @type body_regex: C{str}

    @param status_regex: Regular expression used to evaluate the HTTP
                         status code of the response.
    @type status_regex: C{str}
    """

    def __init__(self, type, delay, timeout, attempts_before_deactivation,
                 path, body_regex, status_regex):
        super(RackspaceHTTPHealthMonitor, self).__init__(type, delay, timeout,
            attempts_before_deactivation)
        self.path = path
        self.body_regex = body_regex
        self.status_regex = status_regex


class RackspaceConnectionThrottle(object):
    """
    @param min_connections: Minimum number of connections per IP address
                            before applying throttling.
    @type min_connections: C{int}

    @param max_connections: Maximum number of of connections per IP address.
                            (Must be between 0 and 100000, 0 allows an 
                            unlimited number of connections.)
    @type max_connections: C{int}

    @param max_connection_rate: Maximum number of connections allowed
                                from a single IP address within the
                                given rate_interval_seconds.  (Must be
                                between 0 and 100000, 0 allows an
                                unlimited number of connections.)
    @type max_connection_rate: C{int}

    @param rate_interval_seconds: Interval at which the
                                  max_connection_rate is enforced.
                                  (Must be between 1 and 3600.)
    @type rate_interval_seconds: C{int}
    """

    def __init__(self, min_connections, max_connections,
                 max_connection_rate, rate_interval_seconds):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_connection_rate = max_connection_rate
        self.rate_interval_seconds = rate_interval_seconds


class RackspaceAccessRuleType(object):
    ALLOW = 0
    DENY = 1


class RackspaceAccessRule(object):
    """
    An access rule allows or denies traffic to a Load Balancer based on the
    incoming IPs.

    @param id: Unique identifier to refer to this rule by.
    @type id: C{str}

    @param rule_type: ALLOW or DENY.
    @type id: C{RackspaceAccessRuleType}

    @param address: IP address or cidr (can be IPv4 or IPv6).
    @type address: C{str}
    """

    def __init__(self, id, rule_type, address):
        self.id = id
        self.rule_type = rule_type
        self.address = address


class RackspaceConnection(OpenStackBaseConnection):
    responseCls = RackspaceResponse
    auth_url = AUTH_URL_US
    _url_key = "lb_url"

    def __init__(self, user_id, key, secure=True, **kwargs):
        super(RackspaceConnection, self).__init__(user_id, key, secure, 
                                                  **kwargs)
        self.api_version = 'v1.0'
        self.accept_format = 'application/json'

    def request(self, action, params=None, data='', headers=None,
                method='GET'):
        if not headers:
            headers = {}
        if not params:
            params = {}

        if method in ('POST', 'PUT'):
            headers['Content-Type'] = 'application/json'
        if method == 'GET':
            params['cache-busing'] = binascii.hexlify(os.urandom(8))

        return super(RackspaceConnection, self).request(action=action,
                params=params, data=data, method=method, headers=headers)


class RackspaceUKConnection(RackspaceConnection):
    auth_url = AUTH_URL_UK


class RackspaceLBDriver(Driver):
    connectionCls = RackspaceConnection
    api_name = 'rackspace_lb'
    name = 'Rackspace LB'

    LB_STATE_MAP = {
        'ACTIVE': State.RUNNING,
        'BUILD': State.PENDING,
        'ERROR': State.ERROR,
        'DELETED': State.DELETED,
        'PENDING_UPDATE': State.PENDING,
        'PENDING_DELETE': State.PENDING
    }

    _VALUE_TO_ALGORITHM_MAP = {
        'RANDOM': Algorithm.RANDOM,
        'ROUND_ROBIN': Algorithm.ROUND_ROBIN,
        'LEAST_CONNECTIONS': Algorithm.LEAST_CONNECTIONS,
        'WEIGHTED_ROUND_ROBIN': Algorithm.WEIGHTED_ROUND_ROBIN,
        'WEIGHTED_LEAST_CONNECTIONS': Algorithm.WEIGHTED_LEAST_CONNECTIONS
    }

    _ALGORITHM_TO_VALUE_MAP = reverse_dict(_VALUE_TO_ALGORITHM_MAP)

    def list_protocols(self):
        return self._to_protocols(
                   self.connection.request('/loadbalancers/protocols').object)

    def list_balancers(self, ex_member_address=None):
        """
        @param ex_member_address: Optional IP address of the attachment member.
                                  If provided, only the load balancers which
                                  have this member attached will be returned.
        @type ex_member_address: C{str}
        """
        params = {}

        if ex_member_address:
            params['nodeaddress'] = ex_member_address

        return self._to_balancers(
                self.connection.request('/loadbalancers', params=params)
                    .object)

    def create_balancer(self, name, members, protocol='http',
                        port=80, algorithm=DEFAULT_ALGORITHM):
        balancer_attrs = self._kwargs_to_mutable_attrs(
                                name=name,
                                protocol=protocol,
                                port=port,
                                algorithm=algorithm)

        balancer_attrs.update({
            "virtualIps": [{"type": "PUBLIC"}],
            "nodes": [{"address": member.ip,
                "port": member.port,
                "condition": "ENABLED"} for member in members],
            })
        balancer_object = {"loadBalancer": balancer_attrs}

        resp = self.connection.request('/loadbalancers',
                method='POST',
                data=json.dumps(balancer_object))
        return self._to_balancer(resp.object["loadBalancer"])

    def destroy_balancer(self, balancer):
        uri = '/loadbalancers/%s' % (balancer.id)
        resp = self.connection.request(uri, method='DELETE')

        return resp.status == httplib.ACCEPTED

    def get_balancer(self, balancer_id):
        uri = '/loadbalancers/%s' % (balancer_id)
        resp = self.connection.request(uri)

        return self._to_balancer(resp.object["loadBalancer"])

    def balancer_attach_member(self, balancer, member):
        ip = member.ip
        port = member.port

        member_object = {"nodes":
                [{"port": port,
                    "address": ip,
                    "condition": "ENABLED"}]
                }

        uri = '/loadbalancers/%s/nodes' % (balancer.id)
        resp = self.connection.request(uri, method='POST',
                data=json.dumps(member_object))
        return self._to_members(resp.object)[0]

    def balancer_detach_member(self, balancer, member):
        # Loadbalancer always needs to have at least 1 member.
        # Last member cannot be detached. You can only disable it or destroy
        # the balancer.
        uri = '/loadbalancers/%s/nodes/%s' % (balancer.id, member.id)
        resp = self.connection.request(uri, method='DELETE')

        return resp.status == httplib.ACCEPTED

    def balancer_list_members(self, balancer):
        uri = '/loadbalancers/%s/nodes' % (balancer.id)
        return self._to_members(
                self.connection.request(uri).object)

    def update_balancer(self, balancer, **kwargs):
        """
        Sets the name, algorithm, protocol, or port on a Rackspace load balancer.

        @keyword    name: New load balancer name
        @type       metadata: C{str}

        @keyword    algorithm: New load balancer algorithm
        @type       metadata: C{libcloud.loadbalancer.base.Algorithm}

        @keyword    protocol: New load balancer protocol
        @type       metadata: C{str}

        @keyword    port: New load balancer port
        @type       metadata: C{int}
        """
        attrs = self._kwargs_to_mutable_attrs(**kwargs)
        resp = self.connection.request('/loadbalancers/%s' % balancer.id,
                method='PUT',
                data=json.dumps(attrs))
        return resp.status == httplib.ACCEPTED

    def _kwargs_to_mutable_attrs(self, **attrs):
        update_attrs = {}
        if "name" in attrs:
            update_attrs['name'] = attrs['name']

        if "algorithm" in attrs:
            algorithm_value = self._algorithm_to_value(attrs['algorithm'])
            update_attrs['algorithm'] = algorithm_value

        if "protocol" in attrs:
            update_attrs['protocol'] = attrs['protocol'].upper()

        if "port" in attrs:
            update_attrs['port'] = int(attrs['port'])

        return update_attrs

    def ex_list_algorithm_names(self):
        """
        Lists algorithms supported by the API.  Returned as strings because
        this list may change in the future.
        """
        response = self.connection.request('/loadbalancers/algorithms')
        return [a["name"].upper() for a in response.object["algorithms"]]

    def ex_get_balancer_error_page(self, balancer):
        uri = '/loadbalancers/%s/errorpage' % (balancer.id)
        resp = self.connection.request(uri)

        return resp.object["errorpage"]["content"]

    def ex_balancer_access_list(self, balancer):
        uri = '/loadbalancers/%s/accesslist' % (balancer.id)
        resp = self.connection.request(uri)

        return [self._to_access_rule(el) for el in resp.object["accessList"]]

    def _to_protocols(self, object):
        protocols = []
        for item in object["protocols"]:
            protocols.append(item['name'].lower())
        return protocols

    def _to_balancers(self, object):
        return [self._to_balancer(el) for el in object["loadBalancers"]]

    def _to_balancer(self, el):
        ip = None
        port = None
        sourceAddresses = {}

        if 'virtualIps' in el:
            ip = el["virtualIps"][0]["address"]

        if 'port' in el:
            port = el["port"]

        if 'sourceAddresses' in el:
            sourceAddresses = el['sourceAddresses']

        extra = {
            "publicVips": self._ex_public_virtual_ips(el),
            "privateVips": self._ex_private_virtual_ips(el),
            "ipv6PublicSource": sourceAddresses.get("ipv6Public"),
            "ipv4PublicSource": sourceAddresses.get("ipv4Public"),
            "ipv4PrivateSource": sourceAddresses.get("ipv4Servicenet"),
        }

        if 'protocol' in el:
            extra['protocol'] = el['protocol']

        if 'algorithm' in el and el["algorithm"] in self._VALUE_TO_ALGORITHM_MAP:
            extra["algorithm"] = self._value_to_algorithm(el["algorithm"])

        if 'healthMonitor' in el:
            health_monitor = self._to_health_monitor(el)
            if health_monitor:
                extra["healthMonitor"] = health_monitor

        if 'connectionThrottle' in el:
            extra["connectionThrottle"] = self._to_connection_throttle(el)

        if 'sessionPersistence' in el:
            persistence = el["sessionPersistence"]
            extra["sessionPersistenceType"] = persistence.get("persistenceType")

        if 'connectionLogging' in el:
            logging = el["connectionLogging"]
            extra["connectionLoggingEnabled"] = logging.get("enabled")

        if 'nodes' in el:
            extra['members'] = self._to_members(el)

        return LoadBalancer(id=el["id"],
                name=el["name"],
                state=self.LB_STATE_MAP.get(
                    el["status"], State.UNKNOWN),
                ip=ip,
                port=port,
                driver=self.connection.driver,
                extra=extra)

    def _to_members(self, object):
        return [self._to_member(el) for el in object["nodes"]]

    def _to_member(self, el):
        extra = {}
        if 'weight' in el:
            extra['weight'] = el["weight"]

        if 'condition' in el:
            extra['condition'] = el["condition"]

        lbmember = Member(id=el["id"],
                ip=el["address"],
                port=el["port"],
                extra=extra)
        return lbmember

    def _ex_private_virtual_ips(self, el):
        if not 'virtualIps' in el:
            return None

        servicenet_vips = [ip for ip in el['virtualIps']
                           if ip['type'] == 'SERVICENET']
        return [vip["address"] for vip in servicenet_vips]

    def _ex_public_virtual_ips(self, el):
        if not 'virtualIps' in el:
            return None

        public_vips = [ip for ip in el['virtualIps'] if ip['type'] == 'PUBLIC']
        return [vip["address"] for vip in public_vips]

    def _to_health_monitor(self, el):
        health_monitor_data = el["healthMonitor"]

        type = health_monitor_data.get("type")
        delay = health_monitor_data.get("delay")
        timeout = health_monitor_data.get("timeout")
        attempts_before_deactivation = health_monitor_data.get("attemptsBeforeDeactivation")

        if type == "CONNECT":
            return RackspaceHealthMonitor(type=type, delay=delay,
                timeout=timeout,
                attempts_before_deactivation=attempts_before_deactivation)

        if type == "HTTP" or type == "HTTPS":
            return RackspaceHTTPHealthMonitor(type=type, delay=delay,
                timeout=timeout,
                attempts_before_deactivation=attempts_before_deactivation,
                path=health_monitor_data.get("path"),
                status_regex=health_monitor_data.get("statusRegex"),
                body_regex=health_monitor_data.get("bodyRegex"))

        return None

    def _to_connection_throttle(self, el):
        connection_throttle_data = el["connectionThrottle"]

        min_connections = connection_throttle_data.get("minConnections")
        max_connections = connection_throttle_data.get("maxConnections")
        max_connection_rate = connection_throttle_data.get("maxConnectionRate")
        rate_interval = connection_throttle_data.get("rateInterval")

        return RackspaceConnectionThrottle(min_connections=min_connections,
            max_connections=max_connections,
            max_connection_rate=max_connection_rate,
            rate_interval_seconds=rate_interval)

    def _to_access_rule(self, el):
        return RackspaceAccessRule(id=el.get("id"),
            rule_type=self._to_access_rule_type(el.get("type")),
            address=el.get("address"))

    def _to_access_rule_type(self, type):
        if type == "ALLOW":
            return RackspaceAccessRuleType.ALLOW
        elif type == "DENY":
            return RackspaceAccessRuleType.DENY


class RackspaceUKLBDriver(RackspaceLBDriver):
    connectionCls = RackspaceUKConnection
