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

from libcloud.common.base import ConnectionKey, JsonResponse
from libcloud.common.types import LibcloudError
from libcloud.dns.types import Provider, RecordType
from libcloud.dns.types import ZoneAlreadyExistsError
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.dns.base import DNSDriver, Zone, Record

from libcloud.utils.py3 import urllib
from libcloud.utils.py3 import urllib2

__all__ = [
    'LeaseWebException',
    'LeaseWebResponse',
    'LeaseWebConnection',
    'LeaseWebDNSDriver',
]


class LeaseWebException(Exception):
    """Error originating from the LeaseWeb API

    This class wraps a LeaseWeb API error, a list of which is available in the
    API documentation.  All LeaseWeb API errors are a numeric code and a
    human-readable description.
    """
    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.args = (code, message)

    def __str__(self):
        return "(%u) %s" % (self.code, self.message)

    def __repr__(self):
        return "<LeaseWebException code %u '%s'>" % (self.code, self.message)


class LeaseWebResponse(JsonResponse):
    """
    LeaseWeb API response

    Wraps the HTTP response returned by the LeaseWeb API.
    """
    def parse_error(self):
        if self.status == 404:
            if self.connection.context['resource'] == 'zone':
                raise ZoneDoesNotExistError(
                    value='',
                    driver=self.connection.driver,
                    zone_id=self.connection.context['id']
                )
            elif self.connection.context['resource'] == 'record':
                raise RecordDoesNotExistError(
                    value='',
                    driver=self.connection.driver,
                    zone_id=self.connection.context['id']
                )
        raise LeaseWebException(self.status, self.error)


class LeaseWebConnection(ConnectionKey):
    """
    A connection to the LeaseWeb API

    Wraps SSL connections to the LeaseWeb API, automagically injecting the
    parameters that the API needs for each request.
    """
    host = 'api.leaseweb.com'
    responseCls = LeaseWebResponse

    def add_default_headers(self, headers):
        """
        Add header that is necessary for authenticating every request

        This method adds ``X-Lsw-Auth`` to
        the request.
        """
        headers['X-Lsw-Auth'] = self.key
        return headers


class LeaseWebDNSDriver(DNSDriver):
    type = Provider.LEASEWEB
    name = 'LeaseWeb'
    website = 'http://www.leaseweb.com/'
    connectionCls = LeaseWebConnection
    RECORD_TYPE_MAP = {
        RecordType.MX: 'MX',
        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        RecordType.CNAME: 'CNAME',
        RecordType.TXT: 'TXT',
        RecordType.SRV: 'SRV',
    }

    def list_zones(self):
        data = self.connection.request('/v1/domains').object['domains']
        zones = self._to_zones(data)
        return zones

    def list_records(self, zone):
        self.connection.set_context(context={'resource': 'zone',
                                             'id': zone.id})
        data = self.connection.request(
            '/v1/domains/{}/dnsRecords'.format(zone.id)).object['dnsRecords']
        records = self._to_records(items=data, zone=zone)
        return records

    def get_zone(self, zone_domain):
        self.connection.set_context(context={'resource': 'zone',
                                             'id': zone_domain})
        data = self.connection.request(
            '/v1/domains/{}'.format(zone_domain)).object
        return self._to_zone(data['domain'])

    def get_record(self, zone_id, record_id):
        zone = self.get_zone(zone_id=zone_id)
        self.connection.set_context(context={'resource': 'record',
                                             'id': record_id})
        data = self.connection.request(
            '/v1/domains/{}/dnsRecords/{}'.format(zone_id, record_id)
        ).object['dnsRecord']
        records = self._to_record(data, zone=zone)
        return records

    def create_zone(self, domain, type='master', ttl=None, extra=None):
        """Using older API that supports creating zones"""

        data = urllib.urlencode({'aid': self.connection.key, 'domain': domain})
        req = urllib2.Request(
            'https://secure.leaseweb.com/api/domain/register/dnsOnly', data)
        res = urllib2.urlopen(req).read()

        if (('The following domain is already'
                ' registered in our system: {}').format(domain) in res):
            raise ZoneAlreadyExistsError(value=domain, driver=self,
                                         zone_id=domain)
        zone = self.get_zone(domain)

        # Delete all default records that point to leaseweb.com
        for record in self.list_records(zone=zone):
            self.delete_record(record)

    def update_zone(self, zone, domain=None, type=None, ttl=None, extra=None):
        if domain:
            raise LibcloudError('Domain cannot be changed', driver=self)
        if type:
            raise LibcloudError('Type cannot be changed', driver=self)
        params = {'ttl': ttl}
        data = self.connection.request(
            '/v1/domains/{}'.format(zone.domain), params=params, method='PUT'
        ).object
        return self._to_zone(data['domain'])

    def create_record(self, name, zone, type, data, extra=None):

        self.connection.set_context(context={'resource': 'zone',
                                             'id': zone.id})
        if not name or name == '':
            host = zone.domain
        else:
            host = '{}.{}'.format(name, zone.domain)
        params = {
            'host': host,
            'type': type,
            'content': data,
        }
        if extra and extra.get('priority'):
            params['priority'] = extra['priority']
        data = self.connection.request(
            '/v1/domains/{}/dnsRecords/'.format(zone.id),
            params=params,
            method='POST'
        ).object

        return self._to_record(data['dnsRecord'], zone=zone)

    def update_record(self, record, name=None, type=None, data=None,
                      extra=None):
        self.connection.set_context(context={'resource': 'zone',
                                             'id': record.id})
        params = {
            'host': '{}.{}'.format(name, record.zone.domain),
            'type': type,
            'content': data,
        }
        if extra and extra.get('priority'):
            params['priority'] = extra['priority']
        data = self.connection.request(
            '/v1/domains/{}/dnsRecords/{}'.format(record.zone.id, record.id),
            params=params,
            method='PUT'
        ).object

        return self._to_record(data['dnsRecord'], zone=record.zone)

    def delete_zone(self, zone):
        """Whole zone cannot be deleted, so we just remove all records."""
        for record in self.list_records(zone):
            self.delete_record(record)
        return True

    def delete_record(self, record):
        self.connection.set_context(context={'resource': 'record',
                                             'id': record.id})
        self.connection.request(
            '/v1/domains/{}/dnsRecords/{}'.format(
                record.zone.id, record.id), method='DELETE'
        )
        return True

    def _to_zones(self, items):
        """
        Convert a list of items to the Zone objects.
        """
        zones = []

        for item in items:
            zones.append(self._to_zone(item['domain']))

        return zones

    def _to_zone(self, item):
        """
        Build an Zone object from the item dictionary.
        """
        zone = Zone(id=item['domain'], domain=item['domain'],
                    type='master', ttl=item['ttl'], driver=self)
        return zone

    def _to_records(self, items, zone=None):
        """
        Convert a list of items to the Record objects.
        """
        records = []

        for item in items:
            records.append(self._to_record(item=item['dnsRecord'], zone=zone))

        return records

    def _to_record(self, item, zone=None):
        """
        Build a Record object from the item dictionary.
        """
        if item['host'] == zone.domain:
            name = ''
        else:
            name = item['host'].split('.')[0]
        record = Record(id=item['id'], name=name, type=item['type'],
                        data=item['content'], zone=zone, driver=self)
        return record
