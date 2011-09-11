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
    'Record',
    'DNSDriver'
]


class Zone(object):
    """
    DNS zone.
    """

    def __init__(self, id, domain, type, ttl, extra, driver):
        """
        @type id: C{str}
        @param id: Zone id.

        @type domain: C{str}
        @param domain: The name of the domain.

        @type type: C{string}
        @param type: Zone type (master, slave).

        @type ttl: C{int}
        @param ttl: Default TTL for records in this zone (in seconds).

        @type extra: C{dict}
        @param extra: (optional) Extra attributes (driver specific).

        @type driver: C{DNSDriver}
        @param driver: DNSDriver instance.
        """
        self.id = str(id) if id else None
        self.domain = domain
        self.type = type
        self.ttl = ttl or None
        self.extra = extra or {}
        self.driver = driver

    def list_records(self):
        self.driver.list_records(zone=self)

    def create_record(self, name, type, data, extra=None):
        self.driver.create_record(name=name, type=type, data=data, extra=extra)

    def delete(self):
        return self.driver.delete_zone(zone=self)

    def __repr__(self):
        return ('<Zone: domain=%s, ttl=%s, provider=%s ...>' %
                (self.domain, self.ttl, self.driver.name))


class Record(object):
    """
    Zone record / resource.
    """

    def __init__(self, id, name, type, data, extra, zone, driver):
        """
        @type id: C{str}
        @param id: Record id

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
        self.zone = zone
        self.driver = driver

    def update(self, name, type, data, extra):
        return self.driver.update_record(record=self, name=name, type=type,
                                       data=data, extra=extra)

    def delete(self):
        return self.driver.delete_record(record=self)

    def __repr__(self):
        return ('<Record: zone=%s, name=%s, data=%s, provider=%s ...>' %
                (self.zone.id, self.name, self.data, self.driver.name))


class DNSDriver(object):
    """
    DNS driver.
    """

    def list_zones(self):
        """
        Return a list of zones.

        @return: A list of C{Zone} instances.
        """
        raise NotImplementedError(
            'list_zones not implemented for this driver')

    def list_records(self, zone):
        """
        Return a list of records for the provided zone.

        @type zone: C{Zone}
        @param zone: Zone to list records for.

        @return: A list of C{Record} instances.
        """
        raise NotImplementedError(
            'list_records not implemented for this driver')

    def get_zone(self, zone_id):
        """
        Return a Zone instance.

        @return: C{Zone} instance.
        """
        raise NotImplementedError(
            'get_zone not implemented for this driver')

    def get_record(self, zone_id, record_id):
        """
        Return a Record instance.

        @return: C{Record} instance.
        """
        raise NotImplementedError(
            'get_record not implemented for this driver')

    def create_zone(self, domain, type='master', ttl=None, extra=None):
        """
        Create a new zone.

        @type domain: C{string}
        @param domain: Zone domain name.

        @type type: C{string}
        @param type: Zone type (master / slave).

        @param ttl: C{int}
        @param ttl: (optional) TTL for new records.

        @type extra: C{dict}
        @param extra: (optional) Extra attributes (driver specific).
        """
        raise NotImplementedError(
            'create_zone not implemented for this driver')

    def create_record(self, name, zone, type, data, extra=None):
        """
        Create a new record.

        @param name: C{string}
        @type name: Hostname or FQDN.

        @type zone: C{Zone}
        @param zone: Zone where the requested record is created.

        @type type: C{RecordType}
        @param type: DNS record type (A, AAAA, ...).

        @type data: C{str}
        @param data: Data for the record (depends on the record type).

        @type extra: C{dict}
        @param extra: (optional) Extra attributes (driver specific).
        """
        raise NotImplementedError(
            'create_record not implemented for this driver')

    def update_record(self, record, name, type, data, extra):
        """
        Update an existing record.

        @param record: C{Record}
        @type record: Record to update.

        @param name: C{string}
        @type name: Hostname or FQDN.

        @type type: C{RecordType}
        @param type: DNS record type (A, AAAA, ...).

        @type data: C{str}
        @param data: Data for the record (depends on the record type).

        @type extra: C{dict}
        @param extra: (optional) Extra attributes (driver specific).
        """
        raise NotImplementedError(
            'update_record not implemented for this driver')

    def delete_zone(self, zone):
        """
        Delete a zone.

        Note: This will delete all the records belonging to this zone.

        @param zone: C{Zone}
        @type zone: Zone to delete.
        """
        raise NotImplementedError(
            'delete_zone not implemented for this driver')

    def delete_record(self, record):
        """
        Delete a record.

        @param record: C{Record}
        @type record: Record to delete.
        """
        raise NotImplementedError(
            'delete_record not implemented for this driver')
