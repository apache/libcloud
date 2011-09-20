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
Gandi driver base classes
"""

import time
import xmlrpclib

import libcloud
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, Node, \
    NodeLocation, NodeSize, NodeImage

# Global constants
API_VERSION = '2.0'
API_PREFIX = "https://rpc.gandi.net/xmlrpc/%s/" % API_VERSION

DEFAULT_TIMEOUT = 600   # operation pooling max seconds
DEFAULT_INTERVAL = 20   # seconds between 2 operation.info


class GandiException(Exception):
    """
    Exception class for Gandi driver
    """
    def __str__(self):
        return "(%u) %s" % (self.args[0], self.args[1])

    def __repr__(self):
        return "<GandiException code %u '%s'>" % (self.args[0], self.args[1])


class GandiSafeTransport(xmlrpclib.SafeTransport):
    pass


class GandiTransport(xmlrpclib.Transport):
    pass


class GandiProxy(xmlrpclib.ServerProxy):
    transportCls = (GandiTransport, GandiSafeTransport)

    def __init__(self, user_agent, verbose=0):
        cls = self.transportCls[0]
        if API_PREFIX.startswith("https://"):
            cls = self.transportCls[1]
        t = cls(use_datetime=0)
        t.user_agent = user_agent
        xmlrpclib.ServerProxy.__init__(
            self,
            uri="%s" % (API_PREFIX),
            transport=t,
            verbose=verbose,
            allow_none=True
        )


class GandiConnection(object):
    """
    Connection class for the Gandi driver
    """

    proxyCls = GandiProxy
    driver = 'gandi'

    def __init__(self, user, password=None):
        self.ua = []

        # Connect only with an api_key generated on website
        self.api_key = user

        try:
            self._proxy = self.proxyCls(self._user_agent())
        except xmlrpclib.Fault, e:
            raise GandiException(1000, e)

    def _user_agent(self):
        return 'libcloud/%s (%s)%s' % (
                libcloud.__version__,
                self.driver,
                "".join([" (%s)" % x for x in self.ua]))

    def user_agent_append(self, s):
        self.ua.append(s)

    def request(self, method, *args):
        """ Request xmlrpc method with given args"""
        try:
            return getattr(self._proxy, method)(self.api_key, *args)
        except xmlrpclib.Fault, e:
            raise GandiException(1001, e)


class BaseGandiDriver(object):
    """
    Gandi base driver

    """
    connectionCls = GandiConnection
    name = 'Gandi'
    api_name = 'gandi'
    friendly_name = 'Gandi.net'
    country = 'FR'
    type = Provider.GANDI
    # TODO : which features to enable ?
    features = {}

    def __init__(self, key, secret=None, secure=False):
        self.key = key
        self.secret = secret
        self.connection = self.connectionCls(key, secret)
        self.connection.driver = self

    # Specific methods for gandi
    def _wait_operation(self, id, \
        timeout=DEFAULT_TIMEOUT, check_interval=DEFAULT_INTERVAL):
        """ Wait for an operation to succeed"""

        for i in range(0, timeout, check_interval):
            try:
                op = self.connection.request('operation.info', int(id))

                if op['step'] == 'DONE':
                    return True
                if op['step'] in  ['ERROR', 'CANCEL']:
                    return False
            except (KeyError, IndexError):
                pass
            except Exception, e:
                raise GandiException(1002, e)

            time.sleep(check_interval)
        return False
