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

import base64
import json
import hmac
import datetime

from hashlib import sha256

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b

from libcloud.common.base import ConnectionUserAndKey, JsonResponse

from libcloud.common.types import InvalidCredsError, ProviderError

from libcloud.dns.base import DNSDriver, Zone, Record
from libcloud.dns.types import RecordType, ZoneDoesNotExistError
from libcloud.dns.types import ZoneAlreadyExistsError, RecordDoesNotExistError


API_HOST = 'api.auroradns.eu'

# Default TTL required by libcloud, but doesn't do anything in AuroraDNS
DEFAULT_ZONE_TTL = 3600
DEFAULT_ZONE_TYPE = 'master'

VALID_RECORD_PARAMS_EXTRA = ['ttl' 'prio', 'health_check_id', 'disabled']


class AuroraDNSResponse(JsonResponse):
    def success(self):
        return self.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]

    def parse_error(self):
        status = int(self.status)

        if status == httplib.UNAUTHORIZED:
            raise InvalidCredsError(value='Authentication failed', driver=self)
        elif status == httplib.FORBIDDEN:
            raise ProviderError(value='Authorization failed', http_code=status,
                                driver=self)
        elif status == httplib.NOT_FOUND:
            context = self.connection.context
            if context['resource'] == 'zone':
                raise ZoneDoesNotExistError(value='', driver=self,
                                            zone_id=context['id'])
            elif context['resource'] == 'record':
                raise RecordDoesNotExistError(value='', driver=self,
                                              record_id=context['id'])
        elif status == httplib.CONFLICT:
            context = self.connection.context
            if context['resource'] == 'zone':
                raise ZoneAlreadyExistsError(value='', driver=self,
                                             zone_id=context['id'])


class AuroraDNSConnection(ConnectionUserAndKey):
    host = API_HOST
    responseCls = AuroraDNSResponse

    def calculate_auth_signature(self, secret_key, method, url, timestamp):
        b64_hmac = base64.b64encode(
            hmac.new(b(secret_key),
                     b(method) + b(url) + b(timestamp),
                     digestmod=sha256).digest()
        )

        return b64_hmac.decode('utf-8')

    def gen_auth_header(self, api_key, secret_key, method, url, timestamp):
        signature = self.calculate_auth_signature(secret_key, method, url,
                                                  timestamp)

        auth_b64 = base64.b64encode(b('%s:%s' % (api_key, signature)))
        return 'AuroraDNSv1 %s' % (auth_b64.decode('utf-8'))

    def request(self, action, params=None, data='', headers=None,
                method='GET'):
        if not headers:
            headers = {}
        if not params:
            params = {}

        if method in ("POST", "PUT"):
            headers = {'Content-Type': 'application/json; charset=UTF-8'}

        t = datetime.datetime.utcnow()
        timestamp = t.strftime('%Y%m%dT%H%M%SZ')

        headers['X-AuroraDNS-Date'] = timestamp
        headers['Authorization'] = self.gen_auth_header(self.user_id, self.key,
                                                        method, action,
                                                        timestamp)

        return super(AuroraDNSConnection, self).request(action=action,
                                                        params=params,
                                                        data=data,
                                                        method=method,
                                                        headers=headers)


class AuroraDNSDriver(DNSDriver):
    name = 'AuroraDNS'
    website = 'https://www.pcextreme.nl/en/aurora/dns'
    connectionCls = AuroraDNSConnection

    RECORD_TYPE_MAP = {
        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        RecordType.CNAME: 'CNAME',
        RecordType.MX: 'MX',
        RecordType.NS: 'NS',
        RecordType.SOA: 'SOA',
        RecordType.SPF: 'SPF',
        RecordType.SRV: 'SRV',
        RecordType.TXT: 'TXT',
    }

    def list_zones(self):
        zones = []

        res = self.connection.request('/zones')
        for zone in res.parse_body():
            zones.append(self.__res_to_zone(zone))

        return zones

    def list_records(self, zone):
        records = []
        res = self.connection.request('/zones/%s/records' % zone.id)

        for record in res.parse_body():
            records.append(self.__res_to_record(zone, record))

        return records

    def get_zone(self, zone_id):
        self.connection.set_context({'resource': 'zone', 'id': zone_id})
        res = self.connection.request('/zones/%s' % zone_id)
        zone = res.parse_body()
        return self.__res_to_zone(zone)

    def get_record(self, zone_id, record_id):
        self.connection.set_context({'resource': 'record', 'id': record_id})
        res = self.connection.request('/zones/%s/records/%s' % (zone_id,
                                                                record_id))
        record = res.parse_body()

        zone = self.get_zone(zone_id)

        return self.__res_to_record(zone, record)

    def create_zone(self, domain, type='master', ttl=None, extra=None):
        self.connection.set_context({'resource': 'zone', 'id': domain})
        res = self.connection.request('/zones', method='POST',
                                      data=json.dumps({'name': domain}))
        zone = res.parse_body()
        return self.__res_to_zone(zone)

    def create_record(self, name, zone, type, data, extra=None):
        if name is None:
            name = ""

        rdata = {
            'name': name,
            'type': type,
            'content': data
        }

        rdata = self.__merge_extra_data(rdata, extra)

        self.connection.set_context({'resource': 'zone', 'id': zone.id})
        res = self.connection.request('/zones/%s/records' % zone.id,
                                      method='POST',
                                      data=json.dumps(rdata))

        record = res.parse_body()
        return self.__res_to_record(zone, record)

    def delete_zone(self, zone):
        self.connection.request('/zones/%s' % zone.id, method='DELETE')

    def delete_record(self, record):
        self.connection.set_context({'resource': 'record', 'id': record.id})
        self.connection.request('/zones/%s/records/%s' % (record.zone.id,
                                                          record.id),
                                method='DELETE')

    def update_record(self, record, name, type, data, extra):
        rdata = {}

        if name is not None:
            rdata['name'] = name

        if type is not None:
            rdata['type'] = type

        if data is not None:
            rdata['content'] = data

        rdata = self.__merge_extra_data(rdata, extra)

        self.connection.set_context({'resource': 'record', 'id': record.id})
        self.connection.request('/zones/%s/records/%s' % (record.zone.id,
                                                          record.id),
                                method='PUT',
                                data=json.dumps(rdata))

        return self.get_record(record.zone.id, record.id)

    def __res_to_record(self, zone, record):
        if len(record['name']) == 0:
            name = None
        else:
            name = record['name']

        extra = {}
        extra['created'] = record['created']
        extra['modified'] = record['modified']
        extra['disabled'] = record['disabled']
        extra['ttl'] = record['ttl']
        extra['prio'] = record['prio']

        return Record(id=record['id'], name=name, type=record['type'],
                      data=record['content'], zone=zone, driver=self,
                      ttl=record['ttl'], extra=extra)

    def __res_to_zone(self, zone):
        return Zone(id=zone['id'], domain=zone['name'], type=DEFAULT_ZONE_TYPE,
                    ttl=DEFAULT_ZONE_TTL, driver=self,
                    extra={'created': zone['created'],
                           'servers': zone['servers'],
                           'account_id': zone['account_id'],
                           'cluster_id': zone['cluster_id']})

    def __merge_extra_data(self, rdata, extra):
        if extra is not None:
            for param in VALID_RECORD_PARAMS_EXTRA:
                if param in extra:
                    rdata[param] = extra[param]

        return rdata
