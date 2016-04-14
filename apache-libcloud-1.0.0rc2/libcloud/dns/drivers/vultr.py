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
Vultr DNS Driver
"""

from libcloud.utils.py3 import urlencode
from libcloud.common.vultr import VultrConnection, VultrResponse
from libcloud.dns.base import DNSDriver, Zone, Record
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.dns.types import ZoneAlreadyExistsError, RecordAlreadyExistsError
from libcloud.dns.types import Provider, RecordType


__all__ = [
    'ZoneRequiredException',
    'VultrDNSResponse',
    'VultrDNSConnection',
    'VultrDNSDriver',
]


class ZoneRequiredException(Exception):
    pass


class VultrDNSResponse(VultrResponse):
    pass


class VultrDNSConnection(VultrConnection):
    responseCls = VultrDNSResponse


class VultrDNSDriver(DNSDriver):

    type = Provider.VULTR
    name = 'Vultr DNS'
    website = 'http://www.vultr.com/'
    connectionCls = VultrDNSConnection

    RECORD_TYPE_MAP = {

        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        RecordType.TXT: 'TXT',
        RecordType.CNAME: 'CNAME',
        RecordType.MX: 'MX',
        RecordType.NS: 'NS',
        RecordType.SRV: 'SRV',
    }

    def list_zones(self):
        """
        Return a list of records for the provided zone.

        :param zone: Zone to list records for.
        :type zone: :class:`Zone`

        :return: ``list`` of :class:`Record`
        """
        action = '/v1/dns/list'
        params = {'api_key': self.key}
        response = self.connection.request(action=action,
                                           params=params)
        zones = self._to_zones(response.objects[0])

        return zones

    def list_records(self, zone):
        """
        Returns a list of records for the provided zone.

        :param zone: zone to list records for
        :type zone: `Zone`

        :rtype: list of :class: `Record`
        """
        if not isinstance(zone, Zone):
            raise ZoneRequiredException('zone should be of type Zone')

        zones = self.list_zones()

        if not self.ex_zone_exists(zone.domain, zones):
            raise ZoneDoesNotExistError(value='', driver=self,
                                        zone_id=zone.domain)

        action = '/v1/dns/records'
        params = {'domain': zone.domain}
        response = self.connection.request(action=action,
                                           params=params)
        records = self._to_records(response.objects[0], zone=zone)

        return records

    def get_zone(self, zone_id):
        """
        Returns a `Zone` instance.

        :param zone_id: name of the zone user wants to get.
        :type zone_id: ``str``

        :rtype: :class:`Zone`
        """
        ret_zone = None

        action = '/v1/dns/list'
        params = {'api_key': self.key}
        response = self.connection.request(action=action,
                                           params=params)
        zones = self._to_zones(response.objects[0])

        if not self.ex_zone_exists(zone_id, zones):
            raise ZoneDoesNotExistError(value=None, zone_id=zone_id,
                                        driver=self)

        for zone in zones:
            if zone_id == zone.domain:
                ret_zone = zone

        return ret_zone

    def get_record(self, zone_id, record_id):
        """
        Returns a Record instance.

        :param zone_id: name of the required zone
        :type zone_id: ``str``

        :param record_id: ID of the required record
        :type record_id: ``str``

        :rtype: :class: `Record`
        """
        ret_record = None
        zone = self.get_zone(zone_id=zone_id)
        records = self.list_records(zone=zone)

        if not self.ex_record_exists(record_id, records):
            raise RecordDoesNotExistError(value='', driver=self,
                                          record_id=record_id)

        for record in records:
            if record_id == record.id:
                ret_record = record

        return ret_record

    def create_zone(self, domain, type='master', ttl=None, extra=None):
        """
        Returns a `Zone` object.

        :param domain: Zone domain name, (e.g. example.com).
        :type domain: ``str``

        :param type: Zone type (master / slave).
        :type  type: ``str``

        :param ttl: TTL for new records. (optional)
        :type  ttl: ``int``

        :param extra: (optional) Extra attributes (driver specific).
                      (e.g. {'serverip':'127.0.0.1'})
        """
        extra = extra or {}
        if extra and extra.get('serverip'):
            serverip = extra['serverip']

        params = {'api_key': self.key}
        data = urlencode({'domain': domain, 'serverip': serverip})
        action = '/v1/dns/create_domain'
        zones = self.list_zones()
        if self.ex_zone_exists(domain, zones):
            raise ZoneAlreadyExistsError(value='', driver=self,
                                         zone_id=domain)

        self.connection.request(params=params, action=action, data=data,
                                method='POST')
        zone = Zone(id=domain, domain=domain, type=type, ttl=ttl,
                    driver=self, extra=extra)

        return zone

    def create_record(self, name, zone, type, data, extra=None):
        """
        Create a new record.

        :param name: Record name without the domain name (e.g. www).
                     Note: If you want to create a record for a base domain
                     name, you should specify empty string ('') for this
                     argument.
        :type  name: ``str``

        :param zone: Zone where the requested record is created.
        :type  zone: :class:`Zone`

        :param type: DNS record type (A, AAAA, ...).
        :type  type: :class:`RecordType`

        :param data: Data for the record (depends on the record type).
        :type  data: ``str``

        :param extra: Extra attributes (driver specific). (optional)
        :type extra: ``dict``

        :rtype: :class:`Record`
        """
        extra = extra or {}

        ret_record = None
        old_records_list = self.list_records(zone=zone)
        # check if record already exists
        # if exists raise RecordAlreadyExistsError
        for record in old_records_list:
            if record.name == name and record.data == data:
                raise RecordAlreadyExistsError(value='', driver=self,
                                               record_id=record.id)

        MX = self.RECORD_TYPE_MAP.get('MX')
        SRV = self.RECORD_TYPE_MAP.get('SRV')

        if extra and extra.get('priority'):
            priority = int(extra['priority'])

        post_data = {'domain': zone.domain, 'name': name,
                     'type': self.RECORD_TYPE_MAP.get(type), 'data': data}

        if type == MX or type == SRV:
            post_data['priority'] = priority

        encoded_data = urlencode(post_data)
        params = {'api_key': self.key}
        action = '/v1/dns/create_record'

        self.connection.request(action=action, params=params,
                                data=encoded_data, method='POST')
        updated_zone_records = zone.list_records()

        for record in updated_zone_records:
            if record.name == name and record.data == data:
                ret_record = record

        return ret_record

    def delete_zone(self, zone):
        """
        Delete a zone.

        Note: This will delete all the records belonging to this zone.

        :param zone: Zone to delete.
        :type  zone: :class:`Zone`

        :rtype: ``bool``
        """
        action = '/v1/dns/delete_domain'
        params = {'api_key': self.key}
        data = urlencode({'domain': zone.domain})
        zones = self.list_zones()
        if not self.ex_zone_exists(zone.domain, zones):
            raise ZoneDoesNotExistError(value='', driver=self,
                                        zone_id=zone.domain)

        response = self.connection.request(params=params, action=action,
                                           data=data, method='POST')

        return response.status == 200

    def delete_record(self, record):
        """
        Delete a record.

        :param record: Record to delete.
        :type  record: :class:`Record`

        :rtype: ``bool``
        """
        action = '/v1/dns/delete_record'
        params = {'api_key': self.key}
        data = urlencode({'RECORDID': record.id,
                         'domain': record.zone.domain})

        zone_records = self.list_records(record.zone)
        if not self.ex_record_exists(record.id, zone_records):
            raise RecordDoesNotExistError(value='', driver=self,
                                          record_id=record.id)

        response = self.connection.request(action=action, params=params,
                                           data=data, method='POST')

        return response.status == 200

    def ex_zone_exists(self, zone_id, zones_list):
        """
        Function to check if a `Zone` object exists.

        :param zone_id: Name of the `Zone` object.
        :type zone_id: ``str``

        :param zones_list: A list containing `Zone` objects
        :type zones_list: ``list``

        :rtype: Returns `True` or `False`
        """

        zone_ids = []
        for zone in zones_list:
            zone_ids.append(zone.domain)

        return zone_id in zone_ids

    def ex_record_exists(self, record_id, records_list):
        """
        :param record_id: Name of the `Record` object.
        :type record_id: ``str``

        :param records_list: A list containing `Record` objects
        :type records_list: ``list``

        :rtype: ``bool``
        """
        record_ids = []
        for record in records_list:
            record_ids.append(record.id)

        return record_id in record_ids

    def _to_zone(self, item):
        """
        Build an object `Zone` from the item dictionary

        :param item: item to build the zone from
        :type item: `dictionary`

        :rtype: :instance: `Zone`
        """
        type = 'master'
        extra = {'date_created': item['date_created']}

        zone = Zone(id=item['domain'], domain=item['domain'], driver=self,
                    type=type, ttl=None, extra=extra)

        return zone

    def _to_zones(self, items):
        """
        Returns a list of `Zone` objects.

        :param: items: a list that contains dictionary objects to be passed
        to the _to_zone function.
        :type items: ``list``
        """
        zones = []
        for item in items:
            zones.append(self._to_zone(item))

        return zones

    def _to_record(self, item, zone):
        extra = {}

        if item.get('priority'):
            extra['priority'] = item['priority']

        type = self._string_to_record_type(item['type'])
        record = Record(id=item['RECORDID'], name=item['name'], type=type,
                        data=item['data'], zone=zone, driver=self, extra=extra)

        return record

    def _to_records(self, items, zone):
        records = []
        for item in items:
            records.append(self._to_record(item, zone=zone))

        return records
