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

from __future__ import with_statement

import json
from libcloud.dns.types import Provider, RecordType
from libcloud.dns.types import RecordError
from libcloud.dns.types import ZoneDoesNotExistError, \
    RecordDoesNotExistError, ZoneAlreadyExistsError, RecordAlreadyExistsError
from libcloud.dns.base import DNSDriver, Zone, Record
from libcloud.common.gandi_live import ResourceNotFoundError, \
    ResourceConflictError, GandiLiveResponse, GandiLiveConnection, \
    BaseGandiLiveDriver


__all__ = [
    'GandiLiveDNSDriver',
]


TTL_MIN = 300
TTL_MAX = 2592000  # 30 days
API_BASE = '/api/v5'


class GandiLiveDNSResponse(GandiLiveResponse):
    pass


class GandiLiveDNSConnection(GandiLiveConnection):
    responseCls = GandiLiveDNSResponse


class GandiLiveDNSDriver(BaseGandiLiveDriver, DNSDriver):
    """
    API reference can be found at:

    https://doc.livedns.gandi.net/

    Please note that the Libcloud paradigm of one zone per domain does not
    match exactly with Gandi LiveDNS.  For Gandi, a "zone" can apply to
    multiple domains.  This driver behaves as if the domain is a zone, but be
    warned that modifying a domain means modifying the zone.  Iif you have a
    zone associated with mutiple domains, all of those domains will be
    modified as well.
    """

    type = Provider.GANDI
    name = 'Gandi LiveDNS'
    website = 'http://www.gandi.net/domain'

    connectionCls = GandiLiveDNSConnection

    # also supports CAA, CDS
    RECORD_TYPE_MAP = {
        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        RecordType.ALIAS: 'ALIAS',
        RecordType.CNAME: 'CNAME',
        RecordType.DNAME: 'DNAME',
        RecordType.DS: 'DS',
        RecordType.KEY: 'KEY',
        RecordType.LOC: 'LOC',
        RecordType.MX: 'MX',
        RecordType.NS: 'NS',
        RecordType.PTR: 'PTR',
        RecordType.SPF: 'SPF',
        RecordType.SRV: 'SRV',
        RecordType.SSHFP: 'SSHFP',
        RecordType.TLSA: 'TLSA',
        RecordType.TXT: 'TXT',
        RecordType.WKS: 'WKS',
    }

    def _to_zone(self, zone):
        extra = {}
        if 'zone_uuid' in zone:
            extra = {
                'zone_uuid': zone['zone_uuid']
            }
        return Zone(
            id=str(zone['fqdn']),
            domain=zone['fqdn'],
            type='master',
            ttl=0,
            driver=self,
            extra=extra,
        )

    def _to_zones(self, zones):
        ret = []
        for z in zones:
            ret.append(self._to_zone(z))
        return ret

    def list_zones(self):
        zones = self.connection.request(action='%s/domains' % API_BASE,
                                        method='GET')
        return self._to_zones(zones.object)

    def get_zone(self, zone_id):
        action = '%s/domains/%s' % (API_BASE, zone_id)
        try:
            zone = self.connection.request(action=action, method='GET')
        except ResourceNotFoundError:
            raise ZoneDoesNotExistError(value='',
                                        driver=self.connection.driver,
                                        zone_id=zone_id)
        return self._to_zone(zone.object)

    """
    :param extra: (optional) Extra attributes ('name'); if not provided, name
                             is based on domain.
    """
    def create_zone(self, domain, type='master', ttl=None, extra=None):
        if extra and 'name' in extra:
            zone_name = extra['name']
        else:
            zone_name = '%s zone' % domain
        raw_zone_data = {
            'name': zone_name,
        }
        post_zone_data = json.dumps(raw_zone_data)

        try:
            new_zone = self.connection.request(action='%s/zones' % API_BASE,
                                               method='POST',
                                               data=post_zone_data)
        except ResourceConflictError:
            raise ZoneAlreadyExistsError(value='',
                                         driver=self.connection.driver,
                                         zone_id=zone_name)
        new_zone_uuid = new_zone.headers['location'].split('/')[-1]

        raw_domain_data = {
            'zone_uuid': new_zone_uuid,
        }
        patch_domain_data = json.dumps(raw_domain_data)

        self.connection.request(action='%s/domains/%s' % (API_BASE, domain),
                                method='PATCH',
                                data=patch_domain_data)
        return self._to_zone({'fqdn': domain})

    # There is nothing you can update about a domain; you can update zones'
    # names and which zone a domain is associated with, but the domain itself
    # is basically immutable.  This method is not implemented; the
    # implementation commented out will do a zone name update.

    # """
    # :param extra: (optional) Extra attributes ('name') to change the name of
    #                          a zone a domain is associated with.  Does
    #                          nothing otherwise.
    # """
    # def update_zone(self, zone, domain=None, type=None, ttl=None,
    #                 extra=None):
    #     if extra and 'name' in extra and 'zone_uuid' in zone.extra:
    #         action = '%s/zones/%s' % (API_BASE, zone.extra['zone_uuid'])
    #         raw_data = {
    #             'name': extra['name'],
    #         }
    #         patch_data = json.dumps(raw_data)
    #         self.connection.request(action=action, method='PATCH',
    #                                 data=patch_data)
    #         return zone
    #     return None

    # There is no concept of deleting domains in this API, not even to
    # disassociate a domain from a zone.  You can delete all the records in a
    # domain (not the same thing) and also delete a zone, but because that
    # level is being masked in this API, it isn't implemented here.  Otherwise
    # this Libcloud zone vs. Gandi zone mismatch gets even more confused.
    # This implementation deletes a zone.
    # def delete_zone(self, zone_uuid):
    #     self.connection.request(action='%s/zones/%s' % (API_BASE, zone_uuid),
    #                             method='DELETE')

    # Since zones are hidden, switching a domain from one zone to another
    # is as well.
    # def switch_zone(self, domain, new_zone_uuid):
    #     raw_domain_data = {
    #         'zone_uuid': new_zone_uuid,
    #     }
    #     post_domain_data = json.dumps(raw_domain_data)
    #     self.connection.request(action='%s/domains/%s' % (API_BASE, domain),
    #                             method='PATCH',
    #                             data=post_domain_data)

    def _to_record(self, record, zone):
        extra = {'ttl': int(record['rrset_ttl'])}
        # Since this returns all values per type, something like
        # extra['priority'] for MX doesn't make a whole lot of sense to set -
        # one priority, an array of values.  Currently do nothing other than
        # return array as received.
        value = record['rrset_values']
        return Record(
            id='%s:%s' % (record['rrset_type'], record['rrset_name']),
            name=record['rrset_name'],
            type=self._string_to_record_type(record['rrset_type']),
            data=value,
            zone=zone,
            driver=self,
            ttl=record['rrset_ttl'],
            extra=extra)

    def _to_records(self, records, zone):
        retval = []
        for r in records:
            retval.append(self._to_record(r, zone))
        return retval

    def list_records(self, zone):
        action = '%s/domains/%s/records' % (API_BASE, zone.id)
        records = self.connection.request(action=action, method='GET')
        return self._to_records(records.object, zone)

    def get_record(self, zone_id, record_id):
        record_type, name = record_id.split(':', 1)
        action = '%s/domains/%s/records/%s/%s' % (API_BASE,
                                                  zone_id,
                                                  name,
                                                  record_type)
        try:
            record = self.connection.request(action=action, method='GET')
        except ResourceNotFoundError:
            raise RecordDoesNotExistError(value='',
                                          driver=self.connection.driver,
                                          record_id=record_id)
        return self._to_record(record.object, self.get_zone(zone_id))

    def _validate_record(self, record_id, name, record_type, data, extra):
        if len(data) > 1024:
            raise RecordError('Record data must be <= 1024 characters',
                              driver=self, record_id=record_id)
        if extra and 'ttl' in extra:
            if extra['ttl'] < TTL_MIN:
                raise RecordError('TTL must be at least 300 seconds',
                                  driver=self, record_id=record_id)
            if extra['ttl'] > TTL_MAX:
                raise RecordError('TTL must not excdeed 30 days',
                                  driver=self, record_id=record_id)

    def create_record(self, name, zone, type, data, extra=None):
        self._validate_record(None, name, type, data, extra)

        action = '%s/domains/%s/records' % (API_BASE, zone.id)

        if isinstance(data, list):
            rvalue = data
        else:
            rvalue = [data]
        raw_data = {
            'rrset_name': name,
            'rrset_type': self.RECORD_TYPE_MAP[type],
            'rrset_values': rvalue,
        }

        if 'ttl' in extra:
            raw_data['rrset_ttl'] = extra['ttl']

        post_data = json.dumps(raw_data)
        try:
            self.connection.request(action=action, method='POST',
                                    data=post_data)
        except ResourceConflictError:
            raise RecordAlreadyExistsError(value='',
                                           driver=self.connection.driver,
                                           record_id='%s:%s' % (
                                               self.RECORD_TYPE_MAP[type],
                                               name))

        return self._to_record(raw_data, zone)

    def update_record(self, record, name, type, data, extra):
        self._validate_record(record.id, name, type, data, extra)

        action = '%s/domains/%s/records/%s/%s' % (
            API_BASE,
            record.zone.id,
            record.name,
            self.RECORD_TYPE_MAP[record.type]
        )

        if isinstance(data, list):
            rvalue = data
        else:
            rvalue = [data]
        raw_data = {
            'rrset_values': rvalue
        }

        if 'ttl' in extra:
            raw_data['rrset_ttl'] = extra['ttl']

        put_data = json.dumps(raw_data)
        raw_data['rrset_name'] = record.name
        raw_data['rrset_type'] = self.RECORD_TYPE_MAP[record.type]
        try:
            self.connection.request(action=action, method='PUT',
                                    data=put_data)
        except ResourceNotFoundError:
            raise RecordDoesNotExistError(value='',
                                          driver=self.connection.driver,
                                          record_id=record.id)

        return self._to_record(raw_data, record.zone)

    def delete_record(self, record):
        action = '%s/domains/%s/records/%s/%s' % (
            API_BASE,
            record.zone.id,
            record.name,
            self.RECORD_TYPE_MAP[record.type]
        )
        try:
            resp = self.connection.request(action=action, method='DELETE')
        except ResourceNotFoundError:
            raise RecordDoesNotExistError(value='',
                                          driver=self.connection.driver,
                                          record_id=record.id)

        if resp.success():
            return True

        return False

    def export_zone_to_bind_format(self, zone):
        action = '%s/domains/%s/records' % (API_BASE, zone.id)
        headers = {
            'Accept': 'text/plain'
        }
        resp = self.connection.request(action=action, method='GET',
                                       headers=headers, raw=True)
        return resp.body
