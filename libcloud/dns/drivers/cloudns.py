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

__all__ = [
    'ClouDNSDNSDriver'
]

from libcloud.common.base import JsonResponse, ConnectionUserAndKey
from libcloud.dns.types import Provider, RecordType
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.dns.types import ZoneAlreadyExistsError
from libcloud.dns.base import DNSDriver, Zone, Record

VALID_RECORD_EXTRA_PARAMS = ['priority', 'ttl']


class ClouDNSDNSResponse(JsonResponse):

    def success(self):
        if not super(ClouDNSDNSResponse, self).success():
            return False
        body = self.parse_body()
        if type(body) is dict and body.get('status') == 'Failed':
            return False
        return True

    def parse_error(self):
        context = self.connection.context
        status_description = self.parse_body()['statusDescription']
        if status_description == u'{} has been already added.'.format(
                context['id']):
            if context['resource'] == 'zone':
                raise ZoneAlreadyExistsError(value='', driver=self,
                                             zone_id=context['id'])
        super(ClouDNSDNSResponse, self).parse_error()
        return self.body


class ClouDNSDNSConnection(ConnectionUserAndKey):
    host = 'api.cloudns.net'
    secure = True
    responseCls = ClouDNSDNSResponse

    def add_default_params(self, params):
        params['auth-id'] = self.user_id
        params['auth-password'] = self.key

        return params

    def request(self, action, params=None, data='', headers=None,
                method='POST'):

        return super(ClouDNSDNSConnection, self).request(action=action,
                                                         params=params,
                                                         data=data,
                                                         method=method,
                                                         headers=headers)


class ClouDNSDNSDriver(DNSDriver):
    type = Provider.CLOUDNS
    name = 'ClouDNS DNS'
    website = 'https://www.cloudns.net'
    connectionCls = ClouDNSDNSConnection

    RECORD_TYPE_MAP = {
        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        RecordType.CNAME: 'CNAME',
        RecordType.MX: 'MX',
        RecordType.NS: 'SPF',
        RecordType.SRV: 'SRV',
        RecordType.TXT: 'TXT',
    }

    def _to_zone(self, item):
        ttl = item.get('ttl', 3600)
        zone = Zone(id=item['name'], domain=item['name'],
                    type=item['type'], ttl=ttl, driver=self)
        return zone

    def _to_record(self, item, zone=None):
        extra = {'ttl': item['ttl']}
        record = Record(id=item['id'], name=item['host'],
                        type=item['type'], data=item['record'],
                        zone=zone, driver=self, extra=extra)
        return record

    def get_zone(self, zone_id):
        self.connection.set_context({'resource': 'zone', 'id': zone_id})
        params = {'page': 1, 'rows-per-page': 10, 'search': zone_id}
        zone_result = self.connection.request(
            '/dns/list-zones.json', params=params).object
        if not zone_result:
            raise ZoneDoesNotExistError(value='', driver=self,
                                        zone_id=zone_id)
        return self._to_zone(zone_result[0])

    def iterate_zones(self):
        page = 1
        rows_per_page = 100
        params = {'page': page, 'rows-per-page': rows_per_page}
        zones_list = []
        while True:
            page_result = self.connection.request(
                '/dns/list-zones.json', params=params).object
            if not page_result:
                break
            zones_list.extend(page_result)
            params['page'] += 1
        for item in zones_list:
            yield self._to_zone(item)

    def create_zone(self, domain, ttl=None, extra=None):
        self.connection.set_context({'resource': 'zone', 'id': domain})
        params = {'domain-name': domain, 'zone-type': 'master'}
        self.connection.request(
            '/dns/register.json', params=params).object
        zone = Zone(id=domain, domain=domain,
                    type='master', ttl=3600, driver=self)
        return zone

    def delete_zone(self, zone):
        self.connection.set_context({'resource': 'zone', 'id': zone.id})
        params = {'domain-name': zone.id}
        self.connection.request(
            '/dns/delete.json', params=params).object
        return True

    def iterate_records(self, zone):
        self.connection.set_context({'resource': 'zone', 'id': zone.id})
        params = {'domain-name': zone.id}
        records_list = self.connection.request(
            '/dns/records.json', params=params).object
        if not len(records_list):
            return
        for item in records_list.values():
            yield self._to_record(item, zone=zone)

    def get_record(self, zone_id, record_id):
        zone = self.get_zone(zone_id=zone_id)
        for record in self.iterate_records(zone):
            if record.id == record_id:
                return record
        raise RecordDoesNotExistError(value='', driver=self,
                                      record_id=record_id)

    def delete_record(self, record):
        self.connection.set_context({'resource': 'record', 'id': record.id})
        params = {'domain-name': record.zone.id, 'record-id': record.id}
        self.connection.request(
            action='/dns/delete-record.json', params=params)
        return True

    def create_record(self, name, zone, type, data, extra=None):
        params = {
            'domain-name': zone.id,
            'host': name,
            'record-type': type,
            'record': data,
            'ttl': 3600
        }
        if extra:
            if extra.get('ttl'):
                params['ttl'] = extra['ttl']
            if extra.get('priority'):
                params['priority'] = extra['priority']

        record_result = self.connection.request(
            action='/dns/add-record.json', params=params).object

        return Record(id=record_result['data']['id'], name=name,
                      type=type, data=data,
                      zone=zone, driver=self, extra=extra)
