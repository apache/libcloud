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
    :param extra: (optional) Extra attribute ('name'); if not provided, name
                             is based on domain.

    :return: :class:`Zone` with attribute zone_uuid set in extra ``dict``
    """
    def create_zone(self, domain, type='master', ttl=None, extra=None):
        if extra and 'name' in extra:
            zone_name = extra['name']
        else:
            zone_name = '%s zone' % domain
        zone_data = {
            'name': zone_name,
        }

        try:
            new_zone = self.connection.request(action='%s/zones' % API_BASE,
                                               method='POST',
                                               data=zone_data)
        except ResourceConflictError:
            raise ZoneAlreadyExistsError(value='',
                                         driver=self.connection.driver,
                                         zone_id=zone_name)
        new_zone_uuid = new_zone.headers['location'].split('/')[-1]

        self.ex_switch_domain_gandi_zone(domain, new_zone_uuid)

        return self._to_zone({'fqdn': domain, 'zone_uuid': new_zone_uuid})

    def list_records(self, zone):
        action = '%s/domains/%s/records' % (API_BASE, zone.id)
        records = self.connection.request(action=action, method='GET')
        return self._to_records(records.object, zone)

    """
    :return: :class:`Record` with the extra ``dict`` containing attribute
             other_values ``list`` of ``str`` for other values; the first
             value is returned through Record.data.
    """
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

    def create_record(self, name, zone, type, data, extra=None):
        self._validate_record(None, name, type, data, extra)

        action = '%s/domains/%s/records' % (API_BASE, zone.id)

        record_data = {
            'rrset_name': name,
            'rrset_type': self.RECORD_TYPE_MAP[type],
            'rrset_values': [data],
        }

        if 'ttl' in extra:
            record_data['rrset_ttl'] = extra['ttl']

        try:
            self.connection.request(action=action, method='POST',
                                    data=record_data)
        except ResourceConflictError:
            raise RecordAlreadyExistsError(value='',
                                           driver=self.connection.driver,
                                           record_id='%s:%s' % (
                                               self.RECORD_TYPE_MAP[type],
                                               name))

        return self._to_record(record_data, zone)

    """
    The Gandi service requires all values for a record when doing an update.
    This implementation makes an attempt to coerce the Libcloud notion
    of a record update into the service's record update, but to do so
    requires some extra interpretation of this method.

    It depends on record.extra['other_records'] and extra['other_records'].
    The value will be set to the list of data and extra['other_records'] so
    long as it exists; if it's an empty list, the value will just be data.
    If extra['other_records'] is not set at all, the value will be set to the
    list of data and record.extra['other_records'].

    It's incumbent on the user to figure out what to pass to this method
    in order to get the desired end result.
    """
    def update_record(self, record, name, type, data, extra):
        self._validate_record(record.id, name, type, data, extra)

        action = '%s/domains/%s/records/%s/%s' % (
            API_BASE,
            record.zone.id,
            record.name,
            self.RECORD_TYPE_MAP[record.type]
        )

        if extra is not None and 'other_records' in extra:
            if len(extra['other_records']) > 0:
                rvalue = [data] + extra['other_records']
            else:
                rvalue = [data]
        elif record.extra is not None and 'other_records' in record.extra:
            rvalue = [data] + record.extra['other_records']
        else:
            rvalue = [data]
        record_data = {
            'rrset_values': rvalue
        }

        if 'ttl' in extra:
            record_data['rrset_ttl'] = extra['ttl']

        try:
            self.connection.request(action=action, method='PUT',
                                    data=record_data)
        except ResourceNotFoundError:
            raise RecordDoesNotExistError(value='',
                                          driver=self.connection.driver,
                                          record_id=record.id)

        record_data['rrset_name'] = record.name
        record_data['rrset_type'] = self.RECORD_TYPE_MAP[record.type]
        return self._to_record(record_data, record.zone)

    def delete_record(self, record):
        action = '%s/domains/%s/records/%s/%s' % (
            API_BASE,
            record.zone.id,
            record.name,
            self.RECORD_TYPE_MAP[record.type]
        )
        try:
            self.connection.request(action=action, method='DELETE')
        except ResourceNotFoundError:
            raise RecordDoesNotExistError(value='',
                                          driver=self.connection.driver,
                                          record_id=record.id)
        # Originally checked for success here, but it should never reach
        # this point with anything other than HTTP 200
        return True

    def export_zone_to_bind_format(self, zone):
        action = '%s/domains/%s/records' % (API_BASE, zone.id)
        headers = {
            'Accept': 'text/plain'
        }
        resp = self.connection.request(action=action, method='GET',
                                       headers=headers, raw=True)
        return resp.body

    # There is nothing you can update about a domain; you can update zones'
    # names and which zone a domain is associated with, but the domain itself
    # is basically immutable.  Instead, some ex_ methods for dealing with
    # Gandi zones.

    """
    Update the name of a Gandi zone.

    Note that a Gandi zone is not the same as a Libcloud zone.  A Gandi zone
    is a separate object type from a Gandi domain; a Gandi zone can be reused
    by multiple Gandi domains, and the actual records are associated with the
    zone directly.  This is mostly masked in this driver to make it look like
    records are associated with domains.  If you need to step out of that
    masking, use these extension methods.

    :param zone_uuid: Identifier for the Gandi zone.
    :type  zone_uuid: ``str``

    :param name: New name for the Gandi zone.
    :type  name: ``str``

    :return: ``bool``
    """
    # @@@ test
    def ex_update_gandi_zone_name(self, zone_uuid, name):
        action = '%s/zones/%s' % (API_BASE, zone_uuid)
        data = {
            'name': name,
        }
        self.connection.request(action=action, method='PATCH',
                                data=data)
        return True

    # There is no concept of deleting domains in this API, not even to
    # disassociate a domain from a zone.  You can delete a zone, though.
    """
    Delete a Gandi zone.  This may raise a ResourceConflictError if you
    try to delete a zone that has domains still using it.

    :param zone_uuid: Identifier for the Gandi zone
    :type  zone_uuid: ``str``

    :return: ``bool``
    """
    # @@@ test
    def ex_delete_gandi_zone(self, zone_uuid):
        self.connection.request(action='%s/zones/%s' % (API_BASE, zone_uuid),
                                method='DELETE')
        return True

    """
    Change the Gandi zone a domain is asociated with.

    :param domain: Domain name to switch zones.
    :type  domain: ``str``

    :param zone_uuid: Identifier for the new Gandi zone to switch to.
    :type  zone_uuid: ``str``

    :return: ``bool``
    """
    def ex_switch_domain_gandi_zone(self, domain, zone_uuid):
        domain_data = {
            'zone_uuid': zone_uuid,
        }
        self.connection.request(action='%s/domains/%s' % (API_BASE, domain),
                                method='PATCH',
                                data=domain_data)
        return True

    """
    Create a new record with multiple values.

    :param data: Record values (depends on the record type)
    :type  data: ``list`` (of ``str``)
    """
    # @@@ test
    def ex_create_multi_value_record(self, name, zone, type, data, extra=None):
        self._validate_record(None, name, type, data, extra)

        action = '%s/domains/%s/records' % (API_BASE, zone.id)

        record_data = {
            'rrset_name': name,
            'rrset_type': self.RECORD_TYPE_MAP[type],
            'rrset_values': data,
        }

        if 'ttl' in extra:
            record_data['rrset_ttl'] = extra['ttl']

        try:
            self.connection.request(action=action, method='POST',
                                    data=record_data)
        except ResourceConflictError:
            raise RecordAlreadyExistsError(value='',
                                           driver=self.connection.driver,
                                           record_id='%s:%s' % (
                                               self.RECORD_TYPE_MAP[type],
                                               name))
        return self._to_record(record_data, zone)

    # The Gandi service returns a set of values for a record,
    # so setting something like extra['priority'] for MX records
    # doesn't make a lot of sense.  Instead, the value is the
    # first from the set, with extra['other_values'] for the
    # remainder of values (not set if no other values).
    def _to_record(self, record, zone):
        extra = {
            'ttl': int(record['rrset_ttl']),
        }
        rrset_values = record['rrset_values']
        value = rrset_values[0]
        if len(rrset_values) > 1:
            extra['other_values'] = rrset_values[1:]
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

    def _validate_record(self, record_id, name, record_type, data, extra):
        if len(data) > 1024:
            raise RecordError('Record data must be <= 1024 characters',
                              driver=self, record_id=record_id)
        if extra is not None and 'other_values' in extra:
            for other_value in other_values:
                if len(other_value) > 1024:
                    raise RecordError('Record data must be <= 1024 characters',
                                      driver=self, record_id=record_id)
        if extra is not None and 'ttl' in extra:
            if extra['ttl'] < TTL_MIN:
                raise RecordError('TTL must be at least 300 seconds',
                                  driver=self, record_id=record_id)
            if extra['ttl'] > TTL_MAX:
                raise RecordError('TTL must not exceed 30 days',
                                  driver=self, record_id=record_id)
