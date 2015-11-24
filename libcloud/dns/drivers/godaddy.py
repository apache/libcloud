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
    'GoDaddyDNSDriver'
]

try:
    import simplejson as json
except:
    import json

from libcloud.common.base import ConnectionKey, JsonResponse
from libcloud.common.types import LibcloudError
from libcloud.utils.py3 import httplib
from libcloud.dns.types import Provider, RecordType
from libcloud.dns.base import DNSDriver, Zone, Record

API_ROOT = 'https://api.godaddy.com/'
VALID_RECORD_EXTRA_PARAMS = ['prio', 'ttl']


class GoDaddyDNSException(LibcloudError):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.args = (code, message)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '<GoDaddyDNSException in %d: %s>' % (self.code, self.message)


class GoDaddyDNSResponse(JsonResponse):
    valid_response_codes = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                            httplib.NO_CONTENT]

    def parse_body(self):
        if not self.body:
            return None

        data = json.loads(self.body)
        return data

    def parse_error(self):
        data = self.parse_body()

        if self.status == httplib.UNAUTHORIZED:
            raise GoDaddyDNSException('%(code)s:%(message)s' % (data['error']))
        elif self.status == httplib.PRECONDITION_FAILED:
            raise GoDaddyDNSException(
                data['error']['code'], data['error']['message'])
        elif self.status == httplib.NOT_FOUND:
            raise GoDaddyDNSException(
                data['error']['code'], data['error']['message'])

        return self.body

    def success(self):
        return self.status in self.valid_response_codes


class GoDaddyDNSConnection(ConnectionKey):
    responseCls = GoDaddyDNSResponse
    host = API_ROOT

    allow_insecure = False

    def __init__(self, key, secret, shopper_id, secure=True, host=None,
                 port=None, url=None, timeout=None,
                 proxy_url=None, backoff=None, retry_delay=None):
        """
        Initialize `user_id` and `key`; set `secure` to an ``int`` based on
        passed value.
        """
        super(GoDaddyDNSConnection, self).__init__(
            secure=secure, host=host,
            port=port, url=url,
            timeout=timeout,
            proxy_url=proxy_url,
            backoff=backoff,
            retry_delay=retry_delay)
        self.key = key
        self.secret = secret
        self.shopper_id = shopper_id

    def add_default_headers(self, headers):
        headers['X-Shopper-Id'] = self.shopper_id
        headers['Authorization'] = "sso-key %s:%s" % \
            (self.key, self.secret)
        return headers

class GoDaddyDNSDriver(DNSDriver):
    type = Provider.GODADDY
    name = 'GoDaddy DNS'
    website = 'https://www.godaddy.com/'
    connectionCls = GoDaddyDNSConnection

    RECORD_TYPE_MAP = {
        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        RecordType.CNAME: 'CNAME',
        RecordType.MX: 'MX',
        RecordType.NS: 'SPF',
        RecordType.SRV: 'SRV',
        RecordType.TXT: 'TXT',
    }

    def __init__(self, shopper_id, key, secret,
                 secure=True, host=None, port=None):
        super(GoDaddyDNSDriver, self).__init__(key=key, secret=secret,
                                               secure=secure,
                                               host=host, port=port,
                                               shopper_id=shopper_id)

    def _to_zones(self, items):
        zones = []
        for item in items:
            zones.append(self._to_zone(item))
        return zones

    def _to_zone(self, item):
        extra = {}
        if 'records' in item:
            extra['records'] = item['records']
        if item['type'] == 'NATIVE':
            item['type'] = 'master'
        zone = Zone(id=item['id'], domain=item['name'],
                    type=item['type'], ttl=item['ttl'],
                    driver=self, extra=extra)
        return zone

    def _to_records(self, items, zone=None):
        records = []

        for item in items:
            records.append(self._to_record(item=item, zone=zone))
        return records

    def _to_record(self, item, zone=None):
        extra = {'ttl': item['ttl']}
        type = self._string_to_record_type(item['type'])
        name = item['name'][:-len(zone.domain) - 1]
        record = Record(id=item['id'], name=name,
                        type=type, data=item['content'],
                        zone=zone, driver=self, extra=extra)
        return record

    def list_zones(self):
        result = self.connection.request(
            '/v1/domains/').object
        zones = self._to_zones(result)
        return zones

    def list_records(self, zone):
        result = self.connection.request(
            '/v1/domains/%s/records' % zone.id).object
        records = self._to_records(items=result, zone=zone)
        return records

    def get_zone(self, zone_id):
        result = self.connection.request(
            '/v1/domains/%s/' % zone_id).object
        zone = self._to_zone(result)
        return zone

    def get_record(self, zone_id, record_type, record_name):
        result = self.connection.request(
            '/v1/domains/%s/record/%s/%s' % (zone_id, record_type, record_name)
            ).object
        record = self._to_record(item=result, zone=self.get_zone(zone_id))
        return record

    def delete_zone(self, zone):
        result = self.connection.request(
            '/v1/domains/%s' % zone.id,
            method='DELETE').object
        return bool(result)
