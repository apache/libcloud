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
from datetime import datetime

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.misc import reverse_dict
from libcloud.loadbalancer.base import LoadBalancer, Member, Driver, Algorithm
from libcloud.loadbalancer.base import DEFAULT_ALGORITHM
from libcloud.common.types import LibcloudError
from libcloud.common.base import JsonResponse, PollingConnection
from libcloud.loadbalancer.types import State, MemberCondition
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

    def __repr__(self):
        return ('<RackspaceHealthMonitor: type=%s, delay=%d, timeout=%d, '
                'attempts_before_deactivation=%d>' %
                (self.type, self.delay, self.timeout,
                 self.attempts_before_deactivation))

    def _to_dict(self):
        return {
            'type': self.type,
            'delay': self.delay,
            'timeout': self.timeout,
            'attemptsBeforeDeactivation': self.attempts_before_deactivation
        }


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

    def __repr__(self):
        return ('<RackspaceHTTPHealthMonitor: type=%s, delay=%d, timeout=%d, '
                'attempts_before_deactivation=%d, path=%s, body_regex=%s, '
                'status_regex=%s>' %
                (self.type, self.delay, self.timeout,
                 self.attempts_before_deactivation, self.path, self.body_regex,
                 self.status_regex))

    def _to_dict(self):
        super_dict = super(RackspaceHTTPHealthMonitor, self)._to_dict()
        super_dict['path'] = self.path
        super_dict['statusRegex'] = self.status_regex
        super_dict['bodyRegex'] = self.body_regex

        return super_dict


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

    def __repr__(self):
        return ('<RackspaceConnectionThrottle: min_connections=%d, '
                'max_connections=%d, max_connection_rate=%d, '
                'rate_interval_seconds=%d>' %
                (self.min_connections, self.max_connections,
                 self.max_connection_rate, self.rate_interval_seconds))

    def _to_dict(self):
        return {
            'maxConnections': self.max_connections,
            'minConnections': self.min_connections,
            'maxConnectionRate': self.max_connection_rate,
            'rateInterval': self.rate_interval_seconds
        }


class RackspaceAccessRuleType(object):
    ALLOW = 0
    DENY = 1

    _RULE_TYPE_STRING_MAP = {
        ALLOW: 'ALLOW',
        DENY: 'DENY'
    }


class RackspaceAccessRule(object):
    """
    An access rule allows or denies traffic to a Load Balancer based on the
    incoming IPs.

    @param id: Unique identifier to refer to this rule by.
    @type id: C{str}

    @param rule_type: RackspaceAccessRuleType.ALLOW or
                      RackspaceAccessRuleType.DENY.
    @type id: C{int}

    @param address: IP address or cidr (can be IPv4 or IPv6).
    @type address: C{str}
    """

    def __init__(self, id=None, rule_type=None, address=None):
        self.id = id
        self.rule_type = rule_type
        self.address = address

    def _to_dict(self):
        type_string = \
            RackspaceAccessRuleType._RULE_TYPE_STRING_MAP[self.rule_type]

        as_dict = {
            'type': type_string,
            'address': self.address
        }

        if self.id is not None:
            as_dict['id'] = self.id

        return as_dict


class RackspaceConnection(OpenStackBaseConnection, PollingConnection):
    responseCls = RackspaceResponse
    auth_url = AUTH_URL_US
    _url_key = "lb_url"
    poll_interval = 2
    timeout = 80

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

    def get_poll_request_kwargs(self, response, context, request_kwargs):
        return {'action': request_kwargs['action'],
                'method': 'GET'}

    def has_completed(self, response):
        state = response.object['loadBalancer']['status']
        if state == 'ERROR':
            raise LibcloudError("Load balancer entered an ERROR state.",
                                driver=self.driver)

        return state == 'ACTIVE'


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

    LB_MEMBER_CONDITION_MAP = {
        'ENABLED': MemberCondition.ENABLED,
        'DISABLED': MemberCondition.DISABLED,
        'DRAINING': MemberCondition.DRAINING
    }

    CONDITION_LB_MEMBER_MAP = reverse_dict(LB_MEMBER_CONDITION_MAP)

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

    def ex_list_protocols_with_default_ports(self):
        """
        @rtype: C{list} of tuples of protocols (C{str}) with default ports
        (C{int}).
        @return: A list of protocols with default ports included.
        """
        return self._to_protocols_with_default_ports(
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

    def ex_destroy_balancers(self, balancers):
        """
        Destroys a list of Balancers (the API supports up to 10).

        @param balancers: A list of Balancers to destroy.
        @type balancers: C{list}

        @rtype: C{bool}
        @return: Returns whether the destroy request was accepted.
        """
        ids = [('id', balancer.id) for balancer in balancers]
        resp = self.connection.request('/loadbalancers',
            method='DELETE',
            params=ids)

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

    def ex_balancer_detach_members(self, balancer, members):
        """
        Detaches a list of members from a balancer (the API supports up to 10).
        This method blocks until the detach request has been processed and the
        balancer is in a RUNNING state again.

        @param balancer: The Balancer to detach members from.
        @type balancer: C{Balancer}

        @param members: A list of Members to detach.
        @type members: C{list}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        accepted = self.ex_balancer_detach_members_no_poll(balancer, members)

        if not accepted:
            msg = 'Detach members request was not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_balancer_detach_members_no_poll(self, balancer, members):
        """
        Detaches a list of members from a balancer (the API supports up to 10).
        This method returns immediately.

        @param balancer: The Balancer to detach members from.
        @type balancer: C{Balancer}

        @param members: A list of Members to detach.
        @type members: C{list}

        @rtype: C{bool}
        @return: Returns whether the detach request was accepted.
        """
        uri = '/loadbalancers/%s/nodes' % (balancer.id)
        ids = [('id', member.id) for member in members]
        resp = self.connection.request(uri, method='DELETE', params=ids)

        return resp.status == httplib.ACCEPTED

    def balancer_list_members(self, balancer):
        uri = '/loadbalancers/%s/nodes' % (balancer.id)
        return self._to_members(
                self.connection.request(uri).object)

    def update_balancer(self, balancer, **kwargs):
        attrs = self._kwargs_to_mutable_attrs(**kwargs)
        resp = self.connection.async_request(
                    action='/loadbalancers/%s' % balancer.id,
                    method='PUT',
                    data=json.dumps(attrs))
        return self._to_balancer(resp.object["loadBalancer"])

    def ex_update_balancer_no_poll(self, balancer, **kwargs):
        attrs = self._kwargs_to_mutable_attrs(**kwargs)
        resp = self.connection.request(
                    action='/loadbalancers/%s' % balancer.id,
                    method='PUT',
                    data=json.dumps(attrs))
        return resp.status == httplib.ACCEPTED

    def ex_balancer_update_member(self, balancer, member, **kwargs):
        """
        Updates a Member's extra attributes for a Balancer.  The attributes can
        include 'weight' or 'condition'.  This method blocks until the update
        request has been processed and the balancer is in a RUNNING state
        again.

        @param balancer: Balancer to update the member on.
        @type balancer: C{Balancer}

        @param **kwargs: New attributes.  Should contain either 'weight'
        or 'condition'.  'condition' can be set to 'ENABLED', 'DISABLED'.
        or 'DRAINING'.  'weight' can be set to a positive integer between
        1 and 100, with a higher weight indicating that the node will receive
        more traffic (assuming the Balancer is using a weighted algorithm).
        @type **kwargs: C{dict}

        @rtype: C{Member}
        @return: Updated Member.
        """
        accepted = self.ex_balancer_update_member_no_poll(
            balancer, member, **kwargs)

        if not accepted:
            msg = 'Update member attributes was not accepted'
            raise LibcloudError(msg, driver=self)

        balancer = self._get_updated_balancer(balancer)
        members = balancer.extra['members']

        updated_members = [m for m in members if m.id == member.id]

        if not updated_members:
            raise LibcloudError('Could not find updated member')

        return updated_members[0]

    def ex_balancer_update_member_no_poll(self, balancer, member, **kwargs):
        """
        Updates a Member's extra attributes for a Balancer.  The attribute can
        include 'weight' or 'condition'.  This method returns immediately.

        @param balancer: Balancer to update the member on.
        @type balancer: C{Balancer}

        @param **kwargs: New attributes.  Should contain either 'weight'
        or 'condition'.  'condition' can be set to 'ENABLED', 'DISABLED'.
        or 'DRAINING'.  'weight' can be set to a positive integer between
        1 and 100, with a higher weight indicating that the node will receive
        more traffic (assuming the Balancer is using a weighted algorithm).
        @type **kwargs: C{dict}

        @rtype: C{bool}
        @return: Returns whether the update request was accepted.
        """
        resp = self.connection.request(
            action='/loadbalancers/%s/nodes/%s' % (balancer.id, member.id),
            method='PUT',
            data=json.dumps(self._kwargs_to_mutable_member_attrs(**kwargs))
        )

        return resp.status == httplib.ACCEPTED

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

    def _get_updated_balancer(self, balancer):
        """
        Updating a balancer's attributes puts a balancer into
        'PENDING_UPDATE' status.  Wait until the balancer is
        back in 'ACTIVE' status and then return the individual
        balancer details call.
        """
        resp = self.connection.async_request(
            action='/loadbalancers/%s' % balancer.id,
            method='GET')

        return self._to_balancer(resp.object['loadBalancer'])

    def ex_update_balancer_health_monitor(self, balancer, health_monitor):
        """
        Sets a Balancer's health monitor.  This method blocks until the update
        request has been processed and the balancer is in a RUNNING state
        again.

        @param balancer: Balancer to update.
        @type balancer: C{Balancer}

        @param health_monitor: Health Monitor for the balancer.
        @type health_monitor: C{RackspaceHealthMonitor}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        accepted = self.ex_update_balancer_health_monitor_no_poll(balancer,
                    health_monitor)
        if not accepted:
            msg = 'Update health monitor request not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_update_balancer_health_monitor_no_poll(self, balancer,
                                                  health_monitor):
        """
        Sets a Balancer's health monitor.  This method returns immediately.

        @param balancer: Balancer to update health monitor on.
        @type balancer: C{Balancer}

        @param health_monitor: Health Monitor for the balancer.
        @type health_monitor: C{RackspaceHealthMonitor}

        @rtype: C{bool}
        @return: Returns whether the update request was accepted.
        """
        uri = '/loadbalancers/%s/healthmonitor' % (balancer.id)

        resp = self.connection.request(uri,
            method='PUT',
            data=json.dumps(health_monitor._to_dict()))

        return resp.status == httplib.ACCEPTED

    def ex_disable_balancer_health_monitor(self, balancer):
        """
        Disables a Balancer's health monitor.  This method blocks until the
        disable request has been processed and the balancer is in a RUNNING
        state again.

        @param balancer: Balancer to disable health monitor on.
        @type balancer: C{Balancer}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        if not self.ex_disable_balancer_health_monitor_no_poll(balancer):
            msg = 'Disable health monitor request not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_disable_balancer_health_monitor_no_poll(self, balancer):
        """
        Disables a Balancer's health monitor.  This method returns
        immediately.

        @param balancer: Balancer to disable health monitor on.
        @type balancer: C{Balancer}

        @rtype: C{bool}
        @return: Returns whether the disable request was accepted.
        """
        uri = '/loadbalancers/%s/healthmonitor' % (balancer.id)

        resp = self.connection.request(uri,
            method='DELETE')

        return resp.status == httplib.ACCEPTED

    def ex_update_balancer_connection_throttle(self, balancer,
                                               connection_throttle):
        """
        Updates a Balancer's connection throttle.  This method blocks until
        the update request has been processed and the balancer is in a
        RUNNING state again.

        @param balancer: Balancer to update connection throttle on.
        @type balancer: C{Balancer}

        @param connection_throttle: Connection Throttle for the balancer.
        @type connection_throttle: C{RackspaceConnectionThrottle}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        accepted = self.ex_update_balancer_connection_throttle_no_poll(
            balancer, connection_throttle)

        if not accepted:
            msg = 'Update connection throttle request not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_update_balancer_connection_throttle_no_poll(self, balancer,
                                                       connection_throttle):
        """
        Sets a Balancer's connection throttle.  This method returns
        immediately.

        @param balancer: Balancer to update connection throttle on.
        @type balancer: C{Balancer}

        @param connection_throttle: Connection Throttle for the balancer.
        @type connection_throttle: C{RackspaceConnectionThrottle}

        @rtype: C{bool}
        @return: Returns whether the update request was accepted.
        """
        uri = '/loadbalancers/%s/connectionthrottle' % (balancer.id)
        resp = self.connection.request(uri, method='PUT',
            data=json.dumps(connection_throttle._to_dict()))

        return resp.status == httplib.ACCEPTED

    def ex_disable_balancer_connection_throttle(self, balancer):
        """
        Disables a Balancer's connection throttle.  This method blocks until
        the disable request has been processed and the balancer is in a RUNNING
        state again.

        @param balancer: Balancer to disable connection throttle on.
        @type balancer: C{Balancer}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        if not self.ex_disable_balancer_connection_throttle_no_poll(balancer):
            msg = 'Disable connection throttle request not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_disable_balancer_connection_throttle_no_poll(self, balancer):
        """
        Disables a Balancer's connection throttle.  This method returns
        immediately.

        @param balancer: Balancer to disable connection throttle on.
        @type balancer: C{Balancer}

        @rtype: C{bool}
        @return: Returns whether the disable request was accepted.
        """
        uri = '/loadbalancers/%s/connectionthrottle' % (balancer.id)
        resp = self.connection.request(uri, method='DELETE')

        return resp.status == httplib.ACCEPTED

    def ex_enable_balancer_connection_logging(self, balancer):
        """
        Enables connection logging for a Balancer.  This method blocks until
        the enable request has been processed and the balancer is in a RUNNING
        state again.

        @param balancer: Balancer to enable connection logging on.
        @type balancer: C{Balancer}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        if not self.ex_enable_balancer_connection_logging_no_poll(balancer):
            msg = 'Enable connection logging request not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_enable_balancer_connection_logging_no_poll(self, balancer):
        """
        Enables connection logging for a Balancer.  This method returns
        immediately.

        @param balancer: Balancer to enable connection logging on.
        @type balancer: C{Balancer}

        @rtype: C{bool}
        @return: Returns whether the enable request was accepted.
        """
        uri = '/loadbalancers/%s/connectionlogging' % (balancer.id)

        resp = self.connection.request(uri, method='PUT',
            data=json.dumps({
            'connectionLogging': {
                'enabled': True
            }
        }))

        return resp.status == httplib.ACCEPTED

    def ex_disable_balancer_connection_logging(self, balancer):
        """
        Disables connection logging for a Balancer.  This method blocks until
        the enable request has been processed and the balancer is in a RUNNING
        state again.

        @param balancer: Balancer to disable connection logging on.
        @type balancer: C{Balancer}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        if not self.ex_disable_balancer_connection_logging_no_poll(balancer):
            msg = 'Disable connection logging request not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_disable_balancer_connection_logging_no_poll(self, balancer):
        """
        Disables connection logging for a Balancer.  This method returns
        immediately.

        @param balancer: Balancer to disable connection logging on.
        @type balancer: C{Balancer}

        @rtype: C{bool}
        @return: Returns whether the disable request was accepted.
        """
        uri = '/loadbalancers/%s/connectionlogging' % (balancer.id)
        resp = self.connection.request(uri, method='PUT',
            data=json.dumps({
            'connectionLogging': {
                'enabled': False
            }
        }))

        return resp.status == httplib.ACCEPTED

    def ex_enable_balancer_session_persistence(self, balancer):
        """
        Enables session persistence for a Balancer by setting the persistence
        type to 'HTTP_COOKIE'.  This method blocks until the enable request
        has been processed and the balancer is in a RUNNING state again.

        @param balancer: Balancer to enable session persistence on.
        @type balancer: C{Balancer}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        if not self.ex_enable_balancer_session_persistence_no_poll(balancer):
            msg = 'Enable session persistence request not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_enable_balancer_session_persistence_no_poll(self, balancer):
        """
        Enables session persistence for a Balancer by setting the persistence
        type to 'HTTP_COOKIE'.  This method returns immediately.

        @param balancer: Balancer to enable session persistence on.
        @type balancer: C{Balancer}

        @rtype: C{bool}
        @return: Returns whether the enable request was accepted.
        """
        uri = '/loadbalancers/%s/sessionpersistence' % (balancer.id)
        resp = self.connection.request(uri, method='PUT',
            data=json.dumps({
                'sessionPersistence': {
                    'persistenceType': 'HTTP_COOKIE'
                }
            }))

        return resp.status == httplib.ACCEPTED

    def ex_disable_balancer_session_persistence(self, balancer):
        """
        Disables session persistence for a Balancer.  This method blocks until
        the disable request has been processed and the balancer is in a RUNNING
        state again.

        @param balancer: Balancer to disable session persistence on.
        @type balancer: C{Balancer}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        if not self.ex_disable_balancer_session_persistence_no_poll(balancer):
            msg = 'Disable session persistence request not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_disable_balancer_session_persistence_no_poll(self, balancer):
        """
        Disables session persistence for a Balancer.  This method returns
        immediately.

        @param balancer: Balancer to disable session persistence for.
        @type balancer: C{Balancer}

        @rtype: C{bool}
        @return: Returns whether the disable request was accepted.
        """
        uri = '/loadbalancers/%s/sessionpersistence' % (balancer.id)
        resp = self.connection.request(uri, method='DELETE')

        return resp.status == httplib.ACCEPTED

    def ex_update_balancer_error_page(self, balancer, page_content):
        """
        Updates a Balancer's custom error page.  This method blocks until
        the update request has been processed and the balancer is in a
        RUNNING state again.

        @param balancer: Balancer to update the custom error page for.
        @type balancer: C{Balancer}

        @param page_content: HTML content for the custom error page.
        @type page_content: C{string}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        accepted = self.ex_update_balancer_error_page_no_poll(balancer,
                                                              page_content)
        if not accepted:
            msg = 'Update error page request not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_update_balancer_error_page_no_poll(self, balancer, page_content):
        """
        Updates a Balancer's custom error page.  This method returns
        immediately.

        @param balancer: Balancer to update the custom error page for.
        @type balancer: C{Balancer}

        @param page_content: HTML content for the custom error page.
        @type page_content: C{string}

        @rtype: C{bool}
        @return: Returns whether the update request was accepted.
        """
        uri = '/loadbalancers/%s/errorpage' % (balancer.id)
        resp = self.connection.request(uri, method='PUT',
            data=json.dumps({
                'errorpage': {
                    'content': page_content
                }
            }))

        return resp.status == httplib.ACCEPTED

    def ex_disable_balancer_custom_error_page(self, balancer):
        """
        Disables a Balancer's custom error page, returning its error page to
        the Rackspace-provided default.  This method blocks until the disable
        request has been processed and the balancer is in a RUNNING state
        again.

        @param balancer: Balancer to disable the custom error page for.
        @type balancer: C{Balancer}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        if not self.ex_disable_balancer_custom_error_page_no_poll(balancer):
            msg = 'Disable custom error page request not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_disable_balancer_custom_error_page_no_poll(self, balancer):
        """
        Disables a Balancer's custom error page, returning its error page to
        the Rackspace-provided default.  This method returns immediately.

        @param balancer: Balancer to disable the custom error page for.
        @type balancer: C{Balancer}

        @rtype: C{bool}
        @return: Returns whether the disable request was accepted.
        """
        uri = '/loadbalancers/%s/errorpage' % (balancer.id)
        resp = self.connection.request(uri, method='DELETE')

        # Load Balancer API currently returns 200 OK on custom error page
        # delete.
        return resp.status == httplib.OK or resp.status == httplib.ACCEPTED

    def ex_create_balancer_access_rule(self, balancer, rule):
        """
        Adds an access rule to a Balancer's access list.  This method blocks
        until the update request has been processed and the balancer is in a
        RUNNING state again.

        @param balancer: Balancer to create the access rule for.
        @type balancer: C{Balancer}

        @param rule: Access Rule to add to the balancer.
        @type rule: C{RackspaceAccessRule}

        @rtype: C{RackspaceAccessRule}
        @return: The created access rule.
        """
        accepted = self.ex_create_balancer_access_rule_no_poll(balancer, rule)
        if not accepted:
            msg = 'Create access rule not accepted'
            raise LibcloudError(msg, driver=self)

        balancer = self._get_updated_balancer(balancer)
        access_list = balancer.extra['accessList']

        # LB API does not return the ID for the newly created item, so we have
        # to fudge it. Rule types and addresses are unique, so this is a safe
        # way to uniquely identify the new access rule.
        created_rule = [r for r in access_list \
                        if rule.rule_type == r.rule_type and \
                           rule.address == r.address]

        if not created_rule:
            raise LibcloudError('Could not find created rule')

        return created_rule[0]

    def ex_create_balancer_access_rule_no_poll(self, balancer, rule):
        """
        Adds an access rule to a Balancer's access list.  This method returns
        immediately.

        @param balancer: Balancer to create the access rule for.
        @type balancer: C{Balancer}

        @param rule: Access Rule to add to the balancer.
        @type rule: C{RackspaceAccessRule}

        @rtype: C{bool}
        @return: Returns whether the create request was accepted.
        """
        uri = '/loadbalancers/%s/accesslist' % (balancer.id)
        resp = self.connection.request(uri, method='POST',
            data=json.dumps({
                'networkItem': rule._to_dict()
            }))

        return resp.status == httplib.ACCEPTED

    def ex_destroy_balancer_access_rule(self, balancer, rule):
        """
        Removes an access rule from a Balancer's access list.  This method
        blocks until the update request has been processed and the balancer
        is in a RUNNING state again.

        @param balancer: Balancer to remove the access rule from.
        @type balancer: C{Balancer}

        @param rule: Access Rule to remove from the balancer.
        @type rule: C{RackspaceAccessRule}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        accepted = self.ex_destroy_balancer_access_rule_no_poll(balancer, rule)
        if not accepted:
            msg = 'Delete access rule not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_destroy_balancer_access_rule_no_poll(self, balancer, rule):
        """
        Removes an access rule from a Balancer's access list.  This method
        returns immediately.

        @param balancer: Balancer to remove the access rule from.
        @type balancer: C{Balancer}

        @param rule: Access Rule to remove from the balancer.
        @type rule: C{RackspaceAccessRule}

        @rtype: C{bool}
        @return: Returns whether the destroy request was accepted.
        """
        uri = '/loadbalancers/%s/accesslist/%s' % (balancer.id, rule.id)
        resp = self.connection.request(uri, method='DELETE')

        return resp.status == httplib.ACCEPTED

    def ex_destroy_balancer_access_rules(self, balancer, rules):
        """
        Removes a list of access rules from a Balancer's access list.  This
        method blocks until the update request has been processed and the
        balancer is in a RUNNING state again.

        @param balancer: Balancer to remove the access rules from.
        @type balancer: C{Balancer}

        @param rules: List of C{RackspaceAccessRule} objects to remove from the
        balancer.
        @type rules: C{list}

        @rtype: C{Balancer}
        @return: Updated Balancer.
        """
        accepted = self.ex_destroy_balancer_access_rules_no_poll(
            balancer, rules)

        if not accepted:
            msg = 'Destroy access rules request not accepted'
            raise LibcloudError(msg, driver=self)

        return self._get_updated_balancer(balancer)

    def ex_destroy_balancer_access_rules_no_poll(self, balancer, rules):
        """
        Removes a list of access rules from a Balancer's access list.  This
        method returns immediately.

        @param balancer: Balancer to remove the access rules from.
        @type balancer: C{Balancer}

        @param rules: List of C{RackspaceAccessRule} objects to remove from the
        balancer.
        @type rules: C{list}

        @rtype: C{bool}
        @return: Returns whether the destroy request was accepted.
        """
        ids = [('id', rule.id) for rule in rules]
        uri = '/loadbalancers/%s/accesslist' % balancer.id

        resp = self.connection.request(uri,
            method='DELETE',
            params=ids)

        return resp.status == httplib.ACCEPTED

    def _to_protocols(self, object):
        protocols = []
        for item in object["protocols"]:
            protocols.append(item['name'].lower())
        return protocols

    def _to_protocols_with_default_ports(self, object):
        protocols = []
        for item in object["protocols"]:
            name = item['name'].lower()
            port = int(item['port'])
            protocols.append((name, port))

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

        if 'algorithm' in el and el["algorithm"] in \
            self._VALUE_TO_ALGORITHM_MAP:
            extra["algorithm"] = self._value_to_algorithm(el["algorithm"])

        if 'healthMonitor' in el:
            health_monitor = self._to_health_monitor(el)
            if health_monitor:
                extra["healthMonitor"] = health_monitor

        if 'connectionThrottle' in el:
            extra["connectionThrottle"] = self._to_connection_throttle(el)

        if 'sessionPersistence' in el:
            persistence = el["sessionPersistence"]
            extra["sessionPersistenceType"] = \
                    persistence.get("persistenceType")

        if 'connectionLogging' in el:
            logging = el["connectionLogging"]
            extra["connectionLoggingEnabled"] = logging.get("enabled")

        if 'nodes' in el:
            extra['members'] = self._to_members(el)

        if 'created' in el:
            extra['created'] = self._iso_to_datetime(el['created']['time'])

        if 'updated' in el:
            extra['updated'] = self._iso_to_datetime(el['updated']['time'])

        if 'accessList' in el:
            extra['accessList'] = [self._to_access_rule(rule) \
                                   for rule in el['accessList']]

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

        if 'condition' in el and el['condition'] in \
           self.LB_MEMBER_CONDITION_MAP:
            extra['condition'] = \
                    self.LB_MEMBER_CONDITION_MAP.get(el["condition"])

        if 'status' in el:
            extra['status'] = el["status"]

        lbmember = Member(id=el["id"],
                ip=el["address"],
                port=el["port"],
                extra=extra)
        return lbmember

    def _protocol_to_value(self, protocol):
        non_standard_protocols = {'imapv2': 'IMAPv2', 'imapv3': 'IMAPv3',
                                  'imapv4': 'IMAPv4'}
        protocol_name = protocol.lower()

        if protocol_name in non_standard_protocols:
            protocol_value = non_standard_protocols[protocol_name]
        else:
            protocol_value = protocol.upper()

        return protocol_value

    def _kwargs_to_mutable_attrs(self, **attrs):
        update_attrs = {}
        if "name" in attrs:
            update_attrs['name'] = attrs['name']

        if "algorithm" in attrs:
            algorithm_value = self._algorithm_to_value(attrs['algorithm'])
            update_attrs['algorithm'] = algorithm_value

        if "protocol" in attrs:
            update_attrs['protocol'] = \
                self._protocol_to_value(attrs['protocol'])

        if "port" in attrs:
            update_attrs['port'] = int(attrs['port'])

        return update_attrs

    def _kwargs_to_mutable_member_attrs(self, **attrs):
        update_attrs = {}
        if 'condition' in attrs:
            update_attrs['condition'] = \
                self.CONDITION_LB_MEMBER_MAP.get(attrs['condition'])

        if 'weight' in attrs:
            update_attrs['weight'] = attrs['weight']

        return update_attrs

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
        attempts_before_deactivation = \
                health_monitor_data.get("attemptsBeforeDeactivation")

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

    def _iso_to_datetime(self, isodate):
        date_formats = ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S%z')
        date = None

        for date_format in date_formats:
            try:
                date = datetime.strptime(isodate, date_format)
            except ValueError:
                pass

            if date:
                break

        return date


class RackspaceUKLBDriver(RackspaceLBDriver):
    connectionCls = RackspaceUKConnection
