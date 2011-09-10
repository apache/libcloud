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

__all__ = [
    'Zone',
    'Host',
    'DNSDriver'
]

class Zone(object):
    """
    DNS zone.
    """

    def __init__(self, id, domain, ttl, extra, driver):
        """
        @type id: C{str}
        @param id: Zone id.

        @type domain: C{str}
        @param domain: The name of the domain.

        @type ttl: C{int}
        @param ttl: Default TTL for host records in this zone (in seconds).

        @type extra: C{dict}
        @param extra: (optional) Extra attributes (driver specific).

        @type driver: C{DNSDriver}
        @param driver: DNSDriver instance.
        """

        self.id = str(id) if id else None
        self.domain = domain
        self.ttl = ttl or None
        self.extra = extra or {}
        self.driver = driver

    def list(self):
        return self.driver.list_zones()

    def create(self, type='master', ttl=None):
        """
        master, slave
        ttl - Default TTL for records
        """
        return self.driver.create_zone(type=type, ttl=ttl)

    def delete(self):
        return self.driver.delete_zone(zone=self)

    def __repr__(self):
        return ('<Zone: domain=%s, ttl=%s, provider=%s ...>' %
                (self.domain, self.ttl, self.driver.name))


class Host(object):
    """
    Zone host / resource.
    """

    def __init__(self, id, name, type, data, extra, zone, driver):
        """
        @type id: C{str}
        @param id: Host id

        @type name: C{str}
        @param name: Hostname or FQDN.


        @type type: C{RecordType}
        @param type: DNS record type (A, AAAA, ...).

        @type data: C{str}
        @param data: Data for the record (depends on the record type).

        @type extra: C{dict}
        @param extra: (optional) Extra attributes (driver specific).

        @type zone: C{Zone}
        @param zone: Zone instance.

        @type driver: C{DNSDriver}
        @param driver: DNSDriver instance.
        """

        self.id = str(id) if id else None
        self.name = name
        self.type = type
        self.data = data
        self.extra = extra or {}
        self.driver = driver

    def list(self):
        return self.driver.list_hosts()

    def create(self, name, type, data, extra):
        return self.driver.create_host(name=name, type=type, data=data, extra=extra)

    def update(self, name, type, data, extra):
       return self.driver.update_host(host=self, name=name, type=type,
                                      data=data, extra=extra)

    def delete(self):
        return self.driver.delete_host(host=self)

    def __repr__(self):
        return ('<Host: zone=%s, name=%s, data=%s provider=%s ...>' %
                (self.zone, self.name, self.data, self.driver.name))


class DNSDriver(object):
    """
    DNS driver.
    """

    def list_zones(self):
        raise NotImplementedError(
            'list_zones not implemented for this driver')

    def list_hosts(self):
        raise NotImplementedError(
            'list_hosts not implemented for this driver')

    def create_zone(self, type='master', ttl=None):
        raise NotImplementedError(
            'create_zone not implemented for this driver')

    def create_host(self, name, type, data, extra):
        raise NotImplementedError(
            'create_host not implemented for this driver')

    def update_host(self, host, name, type, data, extra):
        raise NotImplementedError(
            'update_host not implemented for this driver')

    def delete_zone(self, zone):
        raise NotImplementedError(
            'delete_zone not implemented for this driver')

    def delete_host(self, host):
        raise NotImplementedError(
            'delete_host not implemented for this driver')
