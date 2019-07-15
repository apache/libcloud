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
    'CloudFlareDNSDriver'
]

import itertools
import json

from libcloud.common.base import JsonResponse, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.dns.base import DNSDriver, Zone, Record
from libcloud.dns.types import Provider, RecordType
from libcloud.dns.types import RecordAlreadyExistsError, ZoneAlreadyExistsError
from libcloud.dns.types import RecordDoesNotExistError, ZoneDoesNotExistError
from libcloud.utils.misc import merge_valid_keys, reverse_dict

API_HOST = 'api.cloudflare.com'
API_BASE = '/client/v4'

CLOUDFLARE_TO_LIBCLOUD_ZONE_TYPE = {
    'full': 'master',
    'partial': 'slave',
}

LIBCLOUD_TO_CLOUDFLARE_ZONE_TYPE = reverse_dict(
    CLOUDFLARE_TO_LIBCLOUD_ZONE_TYPE)

ZONE_EXTRA_ATTRIBUTES = {
    'development_mode',
    'original_name_servers',
    'original_registrar',
    'original_dnshost',
    'created_on',
    'modified_on',
    'activated_on',
    'owner',
    'account',
    'permissions',
    'plan',
    'plan_pending',
    'status',
    'paused',
    'name_servers',
}

ZONE_UPDATE_ATTRIBUTES = {
    'paused',
    'vanity_name_servers',
    'plan',
}

ZONE_CREATE_ATTRIBUTES = {
    'jump_start',
}

RECORD_EXTRA_ATTRIBUTES = {
    'proxiable',
    'proxied',
    'locked',
    'created_on',
    'modified_on',
    'data',
}

RECORD_CREATE_ATTRIBUTES = {
    'ttl',
    'priority',
    'proxied',
}

RECORD_UPDATE_ATTRIBUTES = {
    'ttl',
    'proxied',
}


class CloudFlareDNSResponse(JsonResponse):
    exceptions = {
        9103: (InvalidCredsError, []),
        1001: (ZoneDoesNotExistError, ['zone_id']),
        1061: (ZoneAlreadyExistsError, ['zone_id']),
        1002: (RecordDoesNotExistError, ['record_id']),
        81053: (RecordAlreadyExistsError, ['record_id']),
    }

    def success(self):
        body = self.parse_body()

        is_success = body.get('success', False)

        return is_success

    def parse_error(self):
        body = self.parse_body()

        errors = body.get('errors', [])

        for error in errors:
            try:
                exception_class, context = self.exceptions[error['code']]
            except KeyError:
                exception_class, context = LibcloudError, []

            kwargs = {
                'value': '{}: {}'.format(error['code'], error['message']),
                'driver': self.connection.driver,
            }

            merge_valid_keys(kwargs, context, self.connection.context)

            raise exception_class(**kwargs)


class CloudFlareDNSConnection(ConnectionUserAndKey):
    host = API_HOST
    secure = True
    responseCls = CloudFlareDNSResponse

    def add_default_headers(self, headers):
        headers['Content-Type'] = 'application/json'
        headers['X-Auth-Email'] = self.user_id
        headers['X-Auth-Key'] = self.key

        return headers

    def encode_data(self, data):
        return json.dumps(data)


class CloudFlareDNSDriver(DNSDriver):
    type = Provider.CLOUDFLARE
    name = 'CloudFlare DNS'
    website = 'https://www.cloudflare.com'
    connectionCls = CloudFlareDNSConnection

    RECORD_TYPE_MAP = {
        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        RecordType.CNAME: 'CNAME',
        RecordType.MX: 'MX',
        RecordType.TXT: 'TXT',
        RecordType.SPF: 'SPF',
        RecordType.NS: 'NS',
        RecordType.SRV: 'SRV',
        RecordType.URL: 'LOC'
    }

    ZONES_PAGE_SIZE = 50
    RECORDS_PAGE_SIZE = 100
    MEMBERSHIPS_PAGE_SIZE = 50

    def iterate_zones(self):
        def _iterate_zones(params):
            url = '{}/zones'.format(API_BASE)

            response = self.connection.request(url, params=params)

            items = response.object['result']
            zones = [self._to_zone(item) for item in items]

            return response, zones

        return self._paginate(_iterate_zones, self.ZONES_PAGE_SIZE)

    def iterate_records(self, zone):
        def _iterate_records(params):
            url = '{}/zones/{}/dns_records'.format(API_BASE, zone.id)

            self.connection.set_context({'zone_id': zone.id})
            response = self.connection.request(url, params=params)

            items = response.object['result']
            records = [self._to_record(zone, item) for item in items]

            return response, records

        return self._paginate(_iterate_records, self.RECORDS_PAGE_SIZE)

    def get_zone(self, zone_id):
        url = '{}/zones/{}'.format(API_BASE, zone_id)

        self.connection.set_context({'zone_id': zone_id})
        response = self.connection.request(url)

        item = response.object['result']
        zone = self._to_zone(item)

        return zone

    def create_zone(self, domain, type='master', ttl=None, extra=None):
        """
        @inherits: :class:`DNSDriver.create_zone`

        Note that for users who have more than one account membership,
        the id of the account in which to create the zone must be
        specified via the ``extra`` key ``account``.

        Note that for ``extra`` zone properties, only the ones specified in
        ``ZONE_CREATE_ATTRIBUTES`` can be set at creation time. Additionally,
        setting the ``ttl` property is not supported.
        """
        extra = extra or {}

        account = extra.get('account')
        if account is None:
            memberships = self.ex_get_user_account_memberships()
            memberships = list(itertools.islice(memberships, 2))

            if len(memberships) != 1:
                raise ValueError('must specify account for zone')

            account = memberships[0]['account']['id']

        url = '{}/zones'.format(API_BASE)

        body = {
            'name': domain,
            'account': {
                'id': account
            },
            'type': LIBCLOUD_TO_CLOUDFLARE_ZONE_TYPE[type]
        }

        merge_valid_keys(body, ZONE_CREATE_ATTRIBUTES, extra)

        response = self.connection.request(url, data=body, method='POST')

        item = response.object['result']
        zone = self._to_zone(item)

        return zone

    def update_zone(self, zone, domain, type='master', ttl=None, extra=None):
        """
        @inherits: :class:`DNSDriver.update_zone`

        Note that the ``zone``, ``type`` and ``ttl`` properties can't be
        updated. The only updatable properties are the ``extra`` zone
        properties specified in ``ZONE_UPDATE_ATTRIBUTES``. Only one property
        may be updated at a time. Any non-updatable properties are ignored.
        """
        body = merge_valid_keys({}, ZONE_UPDATE_ATTRIBUTES, extra)
        if len(body) != 1:
            return zone

        url = '{}/zones/{}'.format(API_BASE, zone.id)

        self.connection.set_context({'zone_id': zone.id})
        response = self.connection.request(url, data=body, method='PATCH')

        item = response.object['result']
        zone = self._to_zone(item)

        return zone

    def delete_zone(self, zone):
        url = '{}/zones/{}'.format(API_BASE, zone.id)

        self.connection.set_context({'zone_id': zone.id})
        response = self.connection.request(url, method='DELETE')

        item = response.object.get('result', {}).get('id')
        is_deleted = item == zone.id

        return is_deleted

    def get_record(self, zone_id, record_id):
        zone = self.get_zone(zone_id)

        url = '{}/zones/{}/dns_records/{}'.format(API_BASE, zone.id,
                                                  record_id)

        self.connection.set_context({'record_id': record_id})
        response = self.connection.request(url)

        item = response.object['result']
        record = self._to_record(zone, item)

        return record

    def create_record(self, name, zone, type, data, extra=None):
        """
        @inherits: :class:`DNSDriver.create_record`

        Note that for ``extra`` record properties, only the ones specified in
        ``RECORD_CREATE_ATTRIBUTES`` can be set at creation time. Any
        non-settable properties are ignored.
        """
        url = '{}/zones/{}/dns_records'.format(API_BASE, zone.id)

        body = {
            'type': type,
            'name': name,
            'content': data,
        }

        merge_valid_keys(body, RECORD_CREATE_ATTRIBUTES, extra)

        self.connection.set_context({'zone_id': zone.id})
        response = self.connection.request(url, data=body, method='POST')

        item = response.object['result']
        record = self._to_record(zone, item)

        return record

    def update_record(self, record, name=None, type=None, data=None,
                      extra=None):
        """
        @inherits: :class:`DNSDriver.update_record`

        Note that for ``extra`` record properties, only the ones specified in
        ``RECORD_UPDATE_ATTRIBUTES`` can be updated. Any non-updatable
        properties are ignored.
        """
        url = '{}/zones/{}/dns_records/{}'.format(API_BASE, record.zone.id,
                                                  record.id)

        body = {
            'type': record.type if type is None else type,
            'name': record.name if name is None else name,
            'content': record.data if data is None else data,
            'extra': record.extra or {},
        }

        merge_valid_keys(body['extra'], RECORD_UPDATE_ATTRIBUTES, extra)

        self.connection.set_context({'record_id': record.id})
        response = self.connection.request(url, data=body, method='PUT')

        item = response.object['result']
        record = self._to_record(record.zone, item)

        return record

    def delete_record(self, record):
        url = '{}/zones/{}/dns_records/{}'.format(API_BASE, record.zone.id,
                                                  record.id)

        self.connection.set_context({'record_id': record.id})
        response = self.connection.request(url, method='DELETE')

        item = response.object.get('result', {}).get('id')
        is_deleted = item == record.id

        return is_deleted

    def ex_get_user_account_memberships(self):
        def _ex_get_user_account_memberships(params):
            url = '{}/memberships'.format(API_BASE)

            response = self.connection.request(url, params=params)
            return response, response.object['result']

        return self._paginate(_ex_get_user_account_memberships,
                              self.MEMBERSHIPS_PAGE_SIZE)

    def ex_get_zone_stats(self, zone, interval=30):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_zone_check(self, zones):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_get_ip_threat_score(self, ip):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_get_zone_settings(self, zone):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_set_zone_security_level(self, zone, level):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_set_zone_cache_level(self, zone, level):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_enable_development_mode(self, zone):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_disable_development_mode(self, zone):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_purge_cached_files(self, zone):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_purge_cached_file(self, zone, url):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_whitelist_ip(self, zone, ip):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_blacklist_ip(self, zone, ip):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_unlist_ip(self, zone, ip):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_enable_ipv6_support(self, zone):
        raise NotImplementedError('not yet implemented in v4 driver')

    def ex_disable_ipv6_support(self, zone):
        raise NotImplementedError('not yet implemented in v4 driver')

    def _to_zone(self, item):
        return Zone(
            id=item['id'],
            domain=item['name'],
            type=CLOUDFLARE_TO_LIBCLOUD_ZONE_TYPE[item['type']],
            ttl=None,
            driver=self,
            extra={key: item.get(key) for key in ZONE_EXTRA_ATTRIBUTES},
        )

    def _to_record(self, zone, item):
        name = item['name']
        name = name.replace('.' + item['zone_name'], '')
        name = name.replace(item['zone_name'], '')
        name = name or None

        ttl = item.get('ttl')
        if ttl is not None:
            ttl = int(ttl)

        return Record(
            id=item['id'],
            name=name,
            type=item['type'],
            data=item['content'],
            zone=zone,
            driver=self,
            ttl=ttl,
            extra={key: item.get(key) for key in RECORD_EXTRA_ATTRIBUTES},
        )

    def _paginate(self, get_page, page_size):
        for page in itertools.count(start=1):
            params = {'page': page, 'per_page': page_size}

            response, items = get_page(params)

            for item in items:
                yield item

            if self._is_last_page(response):
                break

            if len(items) < page_size:
                break

    def _is_last_page(self, response):
        try:
            result_info = response.object['result_info']
            last_page = result_info['total_pages']
            current_page = result_info['page']
        except KeyError:
            return False

        return current_page == last_page
