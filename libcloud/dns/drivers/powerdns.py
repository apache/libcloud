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
"""
PowerDNS Driver
"""
import json
import sys
import copy

from libcloud.common.base import ConnectionKey, JsonResponse
from libcloud.common.exceptions import BaseHTTPError
from libcloud.common.types import InvalidCredsError, MalformedResponseError
from libcloud.dns.base import DNSDriver, Zone, Record
from libcloud.dns.types import ZoneDoesNotExistError, ZoneAlreadyExistsError
from libcloud.dns.types import Provider, RecordType, RecordDoesNotExistError
from libcloud.utils.py3 import httplib

__all__ = [
    'PowerDNSDriver',
]


class PowerDNSResponse(JsonResponse):

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299

    def parse_error(self):
        if self.status == httplib.UNAUTHORIZED:
            raise InvalidCredsError('Invalid provider credentials')

        try:
            body = self.parse_body()
        except MalformedResponseError:
            e = sys.exc_info()[1]
            body = '%s: %s' % (e.value, e.body)

        try:
            errors = [body['error']]
        except TypeError:
            # parse_body() gave us a simple string, not a dict.
            return '%s (HTTP Code: %d)' % (body, self.status)
        try:
            errors.append(body['errors'])
        except KeyError:
            # The PowerDNS API does not return the "errors" list all the time.
            pass

        return '%s (HTTP Code: %d)' % (' '.join(errors), self.status)


class PowerDNSConnection(ConnectionKey):
    responseCls = PowerDNSResponse

    def add_default_headers(self, headers):
        headers['X-API-Key'] = self.key
        return headers


class PowerDNSDriver(DNSDriver):
    type = Provider.POWERDNS
    name = 'PowerDNS'
    website = 'https://www.powerdns.com/'
    connectionCls = PowerDNSConnection

    RECORD_TYPE_MAP = {
        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        # RecordType.AFSDB: 'AFSDB',
        RecordType.CERT: 'CERT',
        RecordType.CNAME: 'CNAME',
        RecordType.DNSKEY: 'DNSKEY',
        RecordType.DS: 'DS',
        RecordType.HINFO: 'HINFO',
        RecordType.KEY: 'KEY',
        RecordType.LOC: 'LOC',
        RecordType.MX: 'MX',
        RecordType.NAPTR: 'NAPTR',
        RecordType.NS: 'NS',
        RecordType.NSEC: 'NSEC',
        RecordType.OPENPGPKEY: 'OPENPGPKEY',
        RecordType.PTR: 'PTR',
        RecordType.RP: 'RP',
        RecordType.RRSIG: 'RRSIG',
        RecordType.SOA: 'SOA',
        RecordType.SPF: 'SPF',
        RecordType.SSHFP: 'SSHFP',
        RecordType.SRV: 'SRV',
        RecordType.TLSA: 'TLSA',
        RecordType.TXT: 'TXT',
    }

    def __init__(self, key, secret=None, secure=False, host=None, port=None,
                 api_version='experimental', **kwargs):
        """
        PowerDNS Driver defaulting to using PowerDNS 3.x API (ie
        "experimental").

        :param    key: API key or username to used (required)
        :type     key: ``str``

        :param    secure: Whether to use HTTPS or HTTP. Note: Off by default
                          for PowerDNS.
        :type     secure: ``bool``

        :param    host: Hostname used for connections.
        :type     host: ``str``

        :param    port: Port used for connections.
        :type     port: ``int``

        :param    api_version: Specifies the API version to use.
                               ``experimental`` and ``v1`` are the only valid
                               options. Defaults to using ``experimental``
                               (optional)
        :type     api_version: ``str``

        :return: ``None``
        """
        # libcloud doesn't really have a concept of "servers". We'll just use
        # localhost for now.
        self.ex_server = 'localhost'

        if api_version == 'experimental':
            # PowerDNS 3.x has no API root prefix.
            self.api_root = ''
            self.canonical_name = False
            self.version = 0

        elif api_version == 'v1':
            # PowerDNS 4.x has an '/api/v1' root prefix.
            self.api_root = '/api/v1'
            self.canonical_name = True
            self.version = 1
        else:
            raise NotImplementedError('Unsupported API version: %s' %
                                      api_version)

        super(PowerDNSDriver, self).__init__(key=key, secure=secure,
                                             host=host, port=port,
                                             **kwargs)

    def create_record(self, name, zone, type, data, extra=None):
        """
        Create a new record.

        There are two PowerDNS-specific quirks here. Firstly, this method will
        silently clobber any pre-existing records that might already exist. For
        example, if PowerDNS already contains a "test.example.com" A record,
        and you create that record using this function, then the old A record
        will be replaced with your new one.

        Secondly, PowerDNS requires that you provide a ttl for all new records.
        In other words, the "extra" parameter must be ``{'ttl':
        <some-integer>}`` at a minimum.

        :param name: FQDN of the new record, for example "www.example.com".
        :type  name: ``str``

        :param zone: Zone where the requested record is created.
        :type  zone: :class:`Zone`

        :param type: DNS record type (A, AAAA, ...).
        :type  type: :class:`RecordType`

        :param data: Data for the record (depends on the record type).
        :type  data: ``str``

        :param extra: Extra attributes (driver specific, e.g. 'ttl').
                      Note that PowerDNS *requires* a ttl value for every
                      record.
        :type extra: ``dict``

        :rtype: :class:`Record`
        """
        action = '%s/servers/%s/zones/%s' % (self.api_root, self.ex_server,
                                             zone.id)
        if extra is None or extra.get('ttl', None) is None:
            raise ValueError('PowerDNS requires a ttl value for every record')

        record_name = self._fmt_name(name)
        id = ':'.join((self.RECORD_TYPE_MAP[type], record_name))
        zone_records = self.list_records(zone)
        zone_records = self.ex_filter_records(zone_records, id=id)

        records = self._add_records([{
            'content': data,
            'disabled': False,
            'name': record_name,
            'ttl': extra['ttl'],
            'type': type,
            'extra': extra,
        }])

        if len(zone_records) > 0:
            _records = []
            for r in zone_records:
                _records.append({
                    'content': r.data,
                    'name': r.name,
                    'ttl': r.ttl,
                    'type': r.type,
                    'extra': r.extra,
                    })
            records += self._add_records(_records, data)

        payload = self._create_rrsets('REPLACE', name, type, extra['ttl'],
                                        records)
        try:
            self.connection.request(action=action, data=json.dumps(payload),
                                        method='PATCH')
        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.UNPROCESSABLE_ENTITY and \
               e.message.startswith('Could not find domain'):
                raise ZoneDoesNotExistError(zone_id=zone.id, driver=self,
                                            value=e.message)
            raise e
        return Record(id=id, name=record_name, data=data, type=type,
                      zone=zone, driver=self, ttl=extra['ttl'], extra=extra)

    def create_zone(self, domain, type=None, ttl=None, extra={}):
        """
        Create a new zone.

        There are two PowerDNS-specific quirks here. Firstly, the "type" and
        "ttl" parameters are ignored (no-ops). The "type" parameter is simply
        not implemented, and PowerDNS does not have an ability to set a
        zone-wide default TTL. (TTLs must be set per-record.)

        Secondly, PowerDNS requires that you provide a list of nameservers for
        the zone upon creation.  In other words, the "extra" parameter must be
        ``{'nameservers': ['ns1.example.org']}`` at a minimum.

        :param name: Zone domain name (e.g. example.com)
        :type  name: ``str``

        :param domain: Zone type (master / slave). (optional).  Note that the
                       PowerDNS driver does nothing with this parameter.
        :type  domain: :class:`Zone`

        :param ttl: TTL for new records. (optional). Note that the PowerDNS
                    driver does nothing with this parameter.
        :type  ttl: ``int``

        :param extra: Extra attributes (driver specific).
                      For example, specify
                      ``extra={'nameservers': ['ns1.example.org']}`` to set
                      a list of nameservers for this new zone.
        :type extra: ``dict``

        :rtype: :class:`Zone`
        """
        action = '%s/servers/%s/zones' % (self.api_root, self.ex_server)
        if extra is None or extra.get('nameservers', None) is None:
            msg = 'PowerDNS requires a list of nameservers for every new zone'
            raise ValueError(msg)

        domain_name = self._fmt_name(domain)
        payload = {'name': domain_name, 'kind': 'Native'}
        for idx, ns in enumerate(extra['nameservers']):
            extra['nameservers'][idx] = self._fmt_name(ns)
        payload.update(extra)
        zone_id = domain + '.'

        try:
            response = self.connection.request(action=action,
                                                data=json.dumps(payload),
                                                method='POST')
            zone_id = response.object['id']
        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.UNPROCESSABLE_ENTITY and \
                    e.message.startswith(
                        "Domain '%s' already exists" % domain_name):
                raise ZoneAlreadyExistsError(zone_id=zone_id, driver=self,
                                             value=e.message)
            raise e

        return Zone(id=zone_id, domain=domain_name, type=None, ttl=None,
                    driver=self, extra=extra)

    def delete_record(self, record):
        """
        Use this method to delete a record.

        :param record: record to delete
        :type record: `Record`

        :rtype: ``bool``
        """
        action = '%s/servers/%s/zones/%s' % (self.api_root, self.ex_server,
                                             record.zone.id)

        payload = self._create_rrsets('DELETE', record.name, record.type)

        if '_multi_value' in record.extra:
            records = self._add_records(record.extra['_other_records'])
            if len(records) > 0:
                other_payload = self._create_rrsets('REPLACE', record.name,
                                            record.type, record.ttl, records)
                payload['rrsets'] += other_payload['rrsets']

        try:
            self.connection.request(action=action, data=json.dumps(payload),
                                    method='PATCH')
        except BaseHTTPError:
            # I'm not sure if we should raise a ZoneDoesNotExistError here. The
            # base DNS API only specifies that we should return a bool. So,
            # let's ignore this code for now.
            # e = sys.exc_info()[1]
            # if e.code == httplib.UNPROCESSABLE_ENTITY and \
            #     e.message.startswith('Could not find domain'):
            #     raise ZoneDoesNotExistError(zone_id=zone.id, driver=self,
            #                                 value=e.message)
            # raise e
            return False
        return True

    def delete_zone(self, zone):
        """
        Use this method to delete a zone.

        :param zone: zone to delete
        :type zone: `Zone`

        :rtype: ``bool``
        """
        action = '%s/servers/%s/zones/%s' % (self.api_root, self.ex_server,
                                             zone.id)
        try:
            self.connection.request(action=action, method='DELETE')
        except BaseHTTPError:
            # I'm not sure if we should raise a ZoneDoesNotExistError here. The
            # base DNS API only specifies that we should return a bool. So,
            # let's ignore this code for now.
            # e = sys.exc_info()[1]
            # if e.code == httplib.UNPROCESSABLE_ENTITY and \
            #     e.message.startswith('Could not find domain'):
            #     raise ZoneDoesNotExistError(zone_id=zone.id, driver=self,
            #                                 value=e.message)
            # raise e
            return False
        return True

    def get_zone(self, zone_id):
        """
        Return a Zone instance.

        (Note that PowerDNS does not support per-zone TTL defaults, so all Zone
        objects will have ``ttl=None``.)

        :param zone_id: name of the required zone with the trailing period, for
                        example "example.com.".
        :type  zone_id: ``str``

        :rtype: :class:`Zone`
        :raises: ZoneDoesNotExistError: If no zone could be found.
        """
        action = '%s/servers/%s/zones/%s' % (self.api_root, self.ex_server,
                                             zone_id)
        try:
            response = self.connection.request(action=action, method='GET')
        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.UNPROCESSABLE_ENTITY:
                raise ZoneDoesNotExistError(zone_id=zone_id, driver=self,
                                            value=e.message)
            raise e
        return self._to_zone(response.object)

    def list_records(self, zone):
        """
        Return a list of all records for the provided zone.

        :param zone: Zone to list records for.
        :type zone: :class:`Zone`

        :return: ``list`` of :class:`Record`
        """
        action = '%s/servers/%s/zones/%s' % (self.api_root, self.ex_server,
                                             zone.id)
        try:
            response = self.connection.request(action=action, method='GET')
        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.UNPROCESSABLE_ENTITY and \
               e.message.startswith('Could not find domain'):
                raise ZoneDoesNotExistError(zone_id=zone.id, driver=self,
                                            value=e.message)
            raise e
        return self._to_records(response, zone)

    def list_zones(self):
        """
        Return a list of zones.

        :return: ``list`` of :class:`Zone`
        """
        action = '%s/servers/%s/zones' % (self.api_root, self.ex_server)
        response = self.connection.request(action=action, method='GET')
        return self._to_zones(response)

    def update_record(self, record, name, type, data, extra=None):
        """
        Update an existing record.

        :param record: Record to update.
        :type  record: :class:`Record`

        :param name: FQDN of the new record, for example "www.example.com".
        :type  name: ``str``

        :param type: DNS record type (A, AAAA, ...).
        :type  type: :class:`RecordType`

        :param data: Data for the record (depends on the record type).
        :type  data: ``str``

        :param extra: (optional) Extra attributes (driver specific).
        :type  extra: ``dict``

        :rtype: :class:`Record`
        """
        action = '%s/servers/%s/zones/%s' % (self.api_root, self.ex_server,
                                             record.zone.id)

        record_name = self._fmt_name(name)
        if extra and 'ttl' in extra:
            ttl = extra['ttl']
        else:
            ttl = record.ttl

        if ttl is None:
            raise ValueError('PowerDNS requires a ttl value for every record')

        records = self._add_records([{
            'content': data,
            'disabled': False,
            'name': record_name,
            'ttl': ttl,
            'type': type,
            'extra': extra,
        }])
        records = []
        records += self._add_records({
            'content': data,
            'disabled': False,
            'name': record_name,
            'ttl': ttl,
            'type': type,
            'extra': extra,
        })

        if '_multi_value' in record.extra:
            records += self._add_records(record.extra['_other_records'], data)

        payload = self._create_rrsets('REPLACE', record_name, type, ttl, records)

        try:
            self.connection.request(action=action, data=json.dumps(payload),
                                    method='PATCH')
        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.UNPROCESSABLE_ENTITY and \
               e.message.startswith('Could not find domain'):
                raise ZoneDoesNotExistError(zone_id=record.zone.id,
                                            driver=self, value=e.message)
            raise e

        id = ':'.join((self.RECORD_TYPE_MAP[type], record_name))
        return Record(id=id, name=record_name, data=data, type=type,
                      zone=record.zone, driver=self, ttl=ttl, extra=extra)

    def ex_get_record(self, zone_id, record_id):
        zone = self.get_zone(zone_id)
        try:
            record = self.ex_filter_records(zone.list_records(), id=record_id)[0]
        except:
            raise RecordDoesNotExistError(value='', driver=self,
                                            record_id=record_id)
        return record

    def ex_filter_records(self, records, **kwargs):
        """
        Given a list of records, it filter by record attribute passed as kwargs

        :return: ``list`` of :class:`Record`
        """
        exclude_record = kwargs.pop('exclude_record', None)
        filtered = []
        for record in records:
            insert = True
            for key, value in kwargs.iteritems():
                if '__' not in key:
                    if getattr(record, key) != value:
                        insert = False
                        break
                else:
                    k1, k2 = key.split('__')
                    if hasattr(record, k1) and record.extra.get(k2) != value:
                            insert = False
                            break

            if exclude_record and exclude_record.id == record.id:
                insert = False
            if insert:
                filtered.append(record)
        return filtered

    def _add_records(self, records, data=None):
        rrset = []
        for r in records:
            if data is not None and r['content'] == data:
                continue

            content = r['content']
            if r['type'] == 'MX':
                r['content'] = self._fmt_name(r['content'])
                content = "{extra[priority]} {content}".format(**r)

            if self.version == 0:
                rrset.append({
                    'content': content,
                    'disabled': False,
                    'name': r['name'],
                    'type': r['type'],
                    'ttl': r['extra']['ttl'] if 'extra' in r and r['extra'].get('ttl', None) else r['ttl'],
                })

            else:
                rrset.append({
                    'content': content,
                    'disabled': False,
                })
        return rrset

    def _create_rrsets(self, command, name, type, ttl=None, records=[]):
        rrsets = {'rrsets': [{
                        'name': self._fmt_name(name),
                        'type': type,
                        'changetype': command,
                        'records': records
                        }
                    ]}
        if ttl is not None:
            rrsets['rrsets'][0]['ttl'] = ttl
        return rrsets

    def _to_zone(self, item):
        extra = {}
        for e in ['kind', 'dnssec', 'account', 'masters', 'serial',
                  'notified_serial', 'last_check']:
            extra[e] = item[e]
        # XXX: we have to hard-code "ttl" to "None" here because PowerDNS does
        # not support per-zone ttl defaults. However, I don't know what "type"
        # should be; probably not None.
        return Zone(id=item['id'], domain=item['name'], type=None,
                    ttl=None, driver=self, extra=extra)

    def _to_zones(self, items):
        zones = []
        for item in items.object:
            zones.append(self._to_zone(item))
        return zones

    def _fmt_record_data(self, item):
        extra = {'ttl': item['ttl']}

        if item['type'] == 'MX':
            split = item['content'].split()
            priority, data = split
            extra['priority'] = int(priority)
            item['content'] = data

        item['extra'] = extra
        return item

    def _to_record(self, item, zone):
        item = self._fmt_record_data(item)
        id = ':'.join((self.RECORD_TYPE_MAP[item['type']], item['name']))
        record = Record(id=id, name=item['name'], type=item['type'],
                        data=item['content'], zone=zone, driver=self,
                        ttl=item['extra'].get('ttl', None), extra=item['extra'])
        return record

    def _to_records(self, items, zone):
        if self.version == 0:
            return self._to_records_3x(items, zone)
        return self._to_records_4x(items, zone)

    def _to_records_3x(self, items, zone):
        records = []
        rrset = items.object['records']
        for item in rrset:
            record = self._to_record(item, zone)

            record_set_records = filter(lambda r: (
                r['type'] == item['type'] and r['name'] == item['name'] and
                r['content'] != item['content']), rrset)

            if len(record_set_records) > 0:
                record.extra['_multi_value'] = True
                record.extra['_other_records'] = record_set_records
            records.append(record)
        return records

    def _to_records_4x(self, items, zone):
        records = []
        rrsets = items.object['rrsets']

        for raw_record in rrsets:
            # preapre a template base on the current record
            _record = {'name': raw_record['name'], 'type': raw_record['type'],
                        'ttl': raw_record['ttl']}

            # verify if it as sibillings
            has_record_set_records = len(raw_record['records']) > 0
            for record_rset in raw_record['records']:
                # create the Record object
                tmp = copy.deepcopy(_record)
                tmp['content'] = record_rset['content']
                record = self._to_record(tmp, zone)

                if has_record_set_records:
                    # if it has sibillings fill the field _other_records with
                    # raw_record['records'] less record itself
                    record.extra['_multi_value'] = True
                    record.extra['_other_records'] = []

                    _filtered_rrset = filter(lambda r: r['content'] != record.data, raw_record['records'])

                    for el in _filtered_rrset:
                        tmp2 = copy.deepcopy(_record)
                        tmp2['content'] = el['content']
                        record.extra['_other_records'].append(self._fmt_record_data(tmp2))
                records.append(record)
        return records

    def _fmt_name(self, value):
        if self.canonical_name and len(value) and value[-1] != '.':
            return value + '.'
        elif not self.canonical_name and len(value) and value[-1] == '.':
            return value[:-1]
        return value
