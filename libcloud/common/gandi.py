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
import hashlib

from libcloud.utils.py3 import xmlrpclib
from libcloud.utils.py3 import b

from libcloud.common.base import ConnectionKey

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


class GandiConnection(ConnectionKey):
    """
    Connection class for the Gandi driver
    """

    proxyCls = GandiProxy

    def __init__(self, key, password=None):
        super(GandiConnection, self).__init__(key)
        self.driver = BaseGandiDriver

        try:
            self._proxy = self.proxyCls(self._user_agent())
        except xmlrpclib.Fault:
            e = sys.exc_info()[1]
            raise GandiException(1000, e)

    def request(self, method, *args):
        """ Request xmlrpc method with given args"""
        try:
            return getattr(self._proxy, method)(self.key, *args)
        except xmlrpclib.Fault:
            e = sys.exc_info()[1]
            raise GandiException(1001, e)


class BaseGandiDriver(object):
    """
    Gandi base driver

    """
    connectionCls = GandiConnection
    name = 'Gandi'

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
            except Exception:
                e = sys.exc_info()[1]
                raise GandiException(1002, e)

            time.sleep(check_interval)
        return False


class BaseObject(object):
    """Base class for objects not conventional"""

    uuid_prefix = ''

    def __init__(self, id, state, driver):
        self.id = str(id) if id else None
        self.state = state
        self.driver = driver
        self.uuid = self.get_uuid()

    def get_uuid(self):
        """Unique hash for this object

        @return: C{string}

        The hash is a function of an SHA1 hash of prefix, the object's ID and
        its driver which means that it should be unique between all
        interfaces.
        TODO : to review
        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> vif = driver.create_interface()
        >>> vif.get_uuid()
        'd3748461511d8b9b0e0bfa0d4d3383a619a2bb9f'

        Note, for example, that this example will always produce the
        same UUID!
        """
        return hashlib.sha1(b("%s:%s:%d" % \
            (self.uuid_prefix, self.id, self.driver.type))).hexdigest()


class IPAddress(BaseObject):
    """
    Provide a common interface for ip addresses
    """

    uuid_prefix = 'inet:'

    def __init__(self, id, state, inet, driver, version=4, extra=None):
        super(IPAddress, self).__init__(id, state, driver)
        self.inet = inet
        self.version = version
        self.extra = extra or {}

    def __repr__(self):
        return (('<IPAddress: id=%s, address=%s, state=%s, driver=%s ...>')
                % (self.id, self.inet, self.state, self.driver.name))


class NetworkInterface(BaseObject):
    """
    Provide a common interface for network interfaces
    """

    uuid_prefix = 'if:'

    def __init__(self, id, state, mac_address, driver,
            ips=None, node_id=None, extra=None):
        super(NetworkInterface, self).__init__(id, state, driver)
        self.mac = mac_address
        self.ips = ips or {}
        self.node_id = node_id
        self.extra = extra or {}

    def __repr__(self):
        return (('<Interface: id=%s, mac=%s, state=%s, driver=%s ...>')
                % (self.id, self.mac, self.state, self.driver.name))


class Disk(BaseObject):
    """
    Gandi disk component
    """
    def __init__(self, id, state, name, driver, size, extra=None):
        super(Disk, self).__init__(id, state, driver)
        self.name = name
        self.size = size
        self.extra = extra or {}

    def __repr__(self):
        return (('<Disk: id=%s, name=%s, state=%s, size=%s, driver=%s ...>')
            % (self.id, self.name, self.state, self.size, self.driver.name))
