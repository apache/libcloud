# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=unexpected-keyword-arg

__all__ = [
    'SoftLayerDNSDriver'
]


from libcloud.common.softlayer import SoftLayerConnection
from libcloud.common.softlayer import SoftLayerObjectDoesntExist
from libcloud.dns.types import Provider, RecordType
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.dns.base import DNSDriver, Zone, Record


VALID_RECORD_EXTRA_PARAMS = ['priority', 'ttl']


class SoftLayerDNSDriver(DNSDriver):
    type = Provider.SOFTLAYER
    name = 'Softlayer DNS'
    website = 'https://www.softlayer.com'
    connectionCls = SoftLayerConnection

    RECORD_TYPE_MAP = {
        RecordType.A: 'a',
        RecordType.AAAA: 'aaaa',
        RecordType.CNAME: 'cname',
        RecordType.MX: 'mx',
        RecordType.NS: 'ns',
        RecordType.PTR: 'ptr',
        RecordType.SOA: 'soa',
        RecordType.SPF: 'spf',
        RecordType.SRV: 'srv',
        RecordType.TXT: 'txt',
    }

    def create_zone(self, domain, ttl=None, extra=None):
        self.connection.set_context({'resource': 'zone', 'id': domain})
        data = {
            'name': domain,
            'resourceRecords': []
        }
        response = self.connection.request(
            'SoftLayer_Dns_Domain', 'createObject', data
        ).object
        zone = Zone(id=response['id'], domain=domain,
                    type='master', ttl=3600, driver=self)
        return zone

    def get_zone(self, zone_id):
        self.connection.set_context({'resource': 'zone', 'id': zone_id})
        try:
            response = self.connection.request(
                'SoftLayer_Dns_Domain', 'getObject', id=zone_id
            ).object
        except SoftLayerObjectDoesntExist:
            raise ZoneDoesNotExistError(value='', driver=self,
                                        zone_id=zone_id)
        return self._to_zone(response)

    def delete_zone(self, zone):
        self.connection.set_context({'resource': 'zone', 'id': zone.id})
        try:
            self.connection.request(
                'SoftLayer_Dns_Domain', 'deleteObject', id=zone.id
            ).object
        except SoftLayerObjectDoesntExist:
            raise ZoneDoesNotExistError(value='', driver=self,
                                        zone_id=zone.id)
        else:
            return True

    def iterate_zones(self):
        zones_list = self.connection.request(
            'SoftLayer_Dns_Domain', 'getByDomainName', '.'
        ).object
        for item in zones_list:
            yield self._to_zone(item)

    def iterate_records(self, zone):
        self.connection.set_context({'resource': 'zone', 'id': zone.id})
        records_list = self.connection.request(
            'SoftLayer_Dns_Domain', 'getResourceRecords', id=zone.id
        ).object
        for item in records_list:
            yield self._to_record(item, zone=zone)

    def get_record(self, zone_id, record_id):
        try:
            record = self.connection.request(
                'SoftLayer_Dns_Domain_ResourceRecord',
                'getObject',
                id=record_id
            ).object
            return self._to_record(record, zone=self.get_zone(zone_id))
        except SoftLayerObjectDoesntExist:
            raise RecordDoesNotExistError(value='', driver=self,
                                          record_id=record_id)

    def delete_record(self, record):
        try:
            self.connection.request(
                'SoftLayer_Dns_Domain_ResourceRecord',
                'deleteObject',
                id=record.id
            ).object
        except SoftLayerObjectDoesntExist:
            raise RecordDoesNotExistError(value='', driver=self,
                                          record_id=record.id)
        else:
            return True

    def create_record(self, name, zone, type, data, extra=None):
        params = {
            'domainId': zone.id,
            'type': self.RECORD_TYPE_MAP[type],
            'host': name,
            'data': data
        }
        if extra:
            if extra.get('ttl'):
                params['ttl'] = extra['ttl']
            if extra.get('refresh'):
                params['refresh'] = extra['refresh']
            if extra.get('retry'):
                params['retry'] = extra['retry']
            if extra.get('expire'):
                params['expire'] = extra['expire']
            if extra.get('priority'):
                params['mxPriority'] = extra['priority']
        response = self.connection.request(
            'SoftLayer_Dns_Domain_ResourceRecord',
            'createObject',
            params
        ).object

        return self._to_record(response, zone=zone)

    def update_record(
            self, record, name=None, type=None, data=None, extra=None):
        params = {}
        if type:
            params['type'] = self.RECORD_TYPE_MAP[type]
        if name:
            params['host'] = name
        if data:
            params['data'] = data

        if extra:
            if extra.get('ttl'):
                params['ttl'] = extra['ttl']
            if extra.get('refresh'):
                params['refresh'] = extra['refresh']
            if extra.get('retry'):
                params['retry'] = extra['retry']
            if extra.get('expire'):
                params['expire'] = extra['expire']
            if extra.get('priority'):
                params['mxPriority'] = extra['priority']

        response = self.connection.request(
            'SoftLayer_Dns_Domain_ResourceRecord',
            'editObject',
            params,
            id=record.id,
        ).object

        if response:
            changed_record = self.connection.request(
                'SoftLayer_Dns_Domain_ResourceRecord',
                'getObject',
                id=record.id,
            ).object
            return self._to_record(changed_record, zone=record.zone)
        else:
            return False

    def _to_zone(self, item):
        ttl = item.get('ttl', 3600)
        zone = Zone(id=item['id'], domain=item['name'],
                    type='master', ttl=ttl, driver=self)
        return zone

    def _to_record(self, item, zone=None):
        extra = {
            'ttl': item['ttl'],
            'expire': item['expire'],
            'mxPriority': item['mxPriority'],
            'refresh': item['refresh'],
            'retry': item['retry'],
        }
        record = Record(
            id=item['id'],
            name=item['host'],
            type=self._string_to_record_type(item['type']),
            data=item['data'],
            zone=zone,
            driver=self,
            ttl=item['ttl'],
            extra=extra
        )
        return record
