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

from libcloud.common.base import ConnectionKey, BaseDriver
from libcloud.common.types import LibcloudError

__all__ = [
    "Member",
    "LoadBalancer",
    "Driver",
    "Algorithm"
]


class Member(object):

    def __init__(self, id, ip, port, balancer=None, extra=None):
        self.id = str(id) if id else None
        self.ip = ip
        self.port = port
        self.balancer = balancer
        self.extra = extra or {}

    def __repr__(self):
        return ('<Member: id=%s, address=%s:%s>' % (self.id,
                                                    self.ip, self.port))


class Algorithm(object):
    RANDOM = 0
    ROUND_ROBIN = 1
    LEAST_CONNECTIONS = 2
    WEIGHTED_ROUND_ROBIN = 3
    WEIGHTED_LEAST_CONNECTIONS = 4

DEFAULT_ALGORITHM = Algorithm.ROUND_ROBIN


class LoadBalancer(object):
    """
    Provide a common interface for handling Load Balancers.
    """

    name = None
    website = None

    def __init__(self, id, name, state, ip, port, driver, extra=None):
        self.id = str(id) if id else None
        self.name = name
        self.state = state
        self.ip = ip
        self.port = port
        self.driver = driver
        self.extra = extra or {}

    def attach_compute_node(self, node):
        return self.driver.balancer_attach_compute_node(balancer=self,
                                                        node=node)

    def attach_member(self, member):
        return self.driver.balancer_attach_member(balancer=self,
                                                  member=member)

    def detach_member(self, member):
        return self.driver.balancer_detach_member(balancer=self,
                                                  member=member)

    def list_members(self):
        return self.driver.balancer_list_members(balancer=self)

    def destroy(self):
        return self.driver.destroy_balancer(balancer=self)

    def __repr__(self):
        return ('<LoadBalancer: id=%s, name=%s, state=%s>' % (self.id,
                self.name, self.state))


class Driver(BaseDriver):
    """
    A base LBDriver class to derive from

    This class is always subclassed by a specific driver.

    """

    connectionCls = ConnectionKey
    _ALGORITHM_TO_VALUE_MAP = {}
    _VALUE_TO_ALGORITHM_MAP = {}

    def __init__(self, key, secret=None, secure=True, host=None,
                 port=None, **kwargs):
        super(Driver, self).__init__(key=key, secret=secret, secure=secure,
                                     host=host, port=port, **kwargs)

    def list_protocols(self):
        """
        Return a list of supported protocols.

        @rtype: C{list} of C{str}
        """
        raise NotImplementedError(
            'list_protocols not implemented for this driver')

    def list_balancers(self):
        """
        List all loadbalancers

        @rtype: C{list} of L{LoadBalancer}
        """
        raise NotImplementedError(
            'list_balancers not implemented for this driver')

    def create_balancer(self, name, port, protocol, algorithm, members):
        """
        Create a new load balancer instance

        @param name: Name of the new load balancer (required)
        @type  name: C{str}

        @param port: Port the load balancer should listen on, defaults to 80
        @type  port: C{str}

        @param protocol: Loadbalancer protocol, defaults to http.
        @type  protocol: C{str}

        @param members: list of Members to attach to balancer
        @type  members: C{list} of L{Member}

        @param algorithm: Load balancing algorithm, defaults to ROUND_ROBIN
        @type algorithm: L{Algorithm}

        @rtype: L{LoadBalancer}
        """
        raise NotImplementedError(
            'create_balancer not implemented for this driver')

    def destroy_balancer(self, balancer):
        """Destroy a load balancer

        @param balancer: LoadBalancer which should be used
        @type  balancer: L{LoadBalancer}

        @return: True if the destroy was successful, otherwise False
        @rtype: C{bool}
        """

        raise NotImplementedError(
            'destroy_balancer not implemented for this driver')

    def get_balancer(self, balancer_id):
        """
        Return a L{LoadBalancer} object.

        @param balancer_id: id of a load balancer you want to fetch
        @type  balancer_id: C{str}

        @rtype: L{LoadBalancer}
        """

        raise NotImplementedError(
            'get_balancer not implemented for this driver')

    def update_balancer(self, balancer, **kwargs):
        """
        Sets the name, algorithm, protocol, or port on a load balancer.

        @param   balancer: LoadBalancer which should be used
        @type    balancer: L{LoadBalancer}

        @keyword name: New load balancer name
        @type    name: C{str}

        @keyword algorithm: New load balancer algorithm
        @type    algorithm: L{Algorithm}

        @keyword protocol: New load balancer protocol
        @type    protocol: C{str}

        @keyword port: New load balancer port
        @type    port: C{int}

        @rtype: L{LoadBalancer}
        """
        raise NotImplementedError(
            'update_balancer not implemented for this driver')

    def balancer_attach_compute_node(self, balancer, node):
        """
        Attach a compute node as a member to the load balancer.

        @param balancer: LoadBalancer which should be used
        @type  balancer: L{LoadBalancer}

        @param node: Node to join to the balancer
        @type  node: L{Node}

        @return: Member after joining the balancer.
        @rtype: L{Member}
        """

        return self.balancer_attach_member(balancer, Member(id=None,
                                                            ip=node.public_ips[0],
                                                            port=balancer.port))

    def balancer_attach_member(self, balancer, member):
        """
        Attach a member to balancer

        @param balancer: LoadBalancer which should be used
        @type  balancer: L{LoadBalancer}

        @param member: Member to join to the balancer
        @type member: L{Member}

        @return: Member after joining the balancer.
        @rtype: L{Member}
        """

        raise NotImplementedError(
            'balancer_attach_member not implemented for this driver')

    def balancer_detach_member(self, balancer, member):
        """
        Detach member from balancer

        @param balancer: LoadBalancer which should be used
        @type  balancer: L{LoadBalancer}

        @param member: Member which should be used
        @type member: L{Member}

        @return: True if member detach was successful, otherwise False
        @rtype: C{bool}
        """

        raise NotImplementedError(
            'balancer_detach_member not implemented for this driver')

    def balancer_list_members(self, balancer):
        """
        Return list of members attached to balancer

        @param balancer: LoadBalancer which should be used
        @type  balancer: L{LoadBalancer}

        @rtype: C{list} of L{Member}
        """

        raise NotImplementedError(
            'balancer_list_members not implemented for this driver')

    def _value_to_algorithm(self, value):
        """
        Return C{LBAlgorithm} based on the value.
        """
        try:
            return self._VALUE_TO_ALGORITHM_MAP[value]
        except KeyError:
            raise LibcloudError(value='Invalid value: %s' % (value),
                                driver=self)

    def _algorithm_to_value(self, algorithm):
        """
        Return value based in the algorithm (C{LBAlgorithm}).
        """
        try:
            return self._ALGORITHM_TO_VALUE_MAP[algorithm]
        except KeyError:
            raise LibcloudError(value='Invalid algorithm: %s' % (algorithm),
                                driver=self)

    def list_supported_algorithms(self):
        """
        Return algorithms supported by this driver.

        @rtype: C{list} of C{str}
        """
        return list(self._ALGORITHM_TO_VALUE_MAP.keys())
