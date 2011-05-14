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

from libcloud.common.base import ConnectionKey

__all__ = [
        "LBNode",
        "LB",
        "LBDriver",
        ]

class LBNode(object):

    def __init__(self, id, ip, port):
        self.id = str(id) if id else None
        self.ip = ip
        self.port = port

    def __repr__(self):
        return ('<LBNode: id=%s, address=%s:%s>' % (self.id,
            self.ip, self.port))


class LB(object):
    """
    Provide a common interface for handling Load Balancers.
    """

    def __init__(self, id, name, state, ip, port, driver):
        self.id = str(id) if id else None
        self.name = name
        self.state = state
        self.ip = ip
        self.port = port
        self.driver = driver

    def attach_node(self, **kwargs):
        return self.driver.balancer_attach_node(self, **kwargs)

    def detach_node(self, node):
        return self.driver.balancer_detach_node(self, node)

    def list_nodes(self):
        return self.driver.balancer_list_nodes(self)

    def __repr__(self):
        return ('<LB: id=%s, name=%s, state=%s>' % (self.id,
                self.name, self.state))


class LBDriver(object):
    """
    A base LBDriver class to derive from

    This class is always subclassed by a specific driver.

    """

    connectionCls = ConnectionKey

    def __init__(self, key, secret=None, secure=True):
        self.key = key
        self.secret = secret
        args = [self.key]

        if self.secret is not None:
            args.append(self.secret)

        args.append(secure)

        self.connection = self.connectionCls(*args)
        self.connection.driver = self
        self.connection.connect()

    def list_balancers(self):
        """
        List all loadbalancers

        @return: C{list} of L{LB} objects

        """

        raise NotImplementedError, \
                'list_balancers not implemented for this driver'

    def create_balancer(self, **kwargs):
        """
        Create a new load balancer instance

        @keyword name: Name of the new load balancer (required)
        @type name: C{str}
        @keyword port: Port the load balancer should listen on (required)
        @type port: C{str}
        @keyword nodes: C{list} of L{LBNode}s to attach to balancer
        @type: C{list} of L{LBNode}s

        """

        raise NotImplementedError, \
                'create_balancer not implemented for this driver'

    def destroy_balancer(self, balancer):
        """Destroy a load balancer

        @return: C{bool} True if the destroy was successful, otherwise False

        """

        raise NotImplementedError, \
                'destroy_balancer not implemented for this driver'

    def balancer_detail(self, **kwargs):
        """
        Returns a detailed info about load balancer given by
        existing L{LB} object or its id

        @keyword balancer: L{LB} object you already fetched using list method for example
        @type balancer: L{LB}
        @keyword balancer_id: id of a load balancer you want to fetch
        @type balancer_id: C{str}

        @return: L{LB}

        """

        raise NotImplementedError, \
                'balancer_detail not implemented for this driver'

    def balancer_attach_node(self, balancer, **kwargs):
        """
        Attach a node to balancer

        @keyword ip: IP address of a node
        @type ip: C{str}
        @keyword port: port that services we're balancing listens on on the node
        @keyword port: C{str}

        """

        raise NotImplementedError, \
                'balancer_attach_node not implemented for this driver'

    def balancer_detach_node(self, balancer, node):
        """
        Detach node from balancer

        @return: C{bool} True if node detach was successful, otherwise False

        """

        raise NotImplementedError, \
                'balancer_detach_node not implemented for this driver'

    def balancer_list_nodes(self, balancer):
        """
        Return list of nodes attached to balancer

        @return: C{list} of L{LBNode}s

        """

        raise NotImplementedError, \
                'balancer_list_nodes not implemented for this driver'
