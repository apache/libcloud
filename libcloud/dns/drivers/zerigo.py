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
    'ZerigoDNSDriver'
]


import copy
import base64

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b

from xml.etree import ElementTree as ET

from libcloud.utils.misc import merge_valid_keys, get_new_obj
from libcloud.utils.xml import findtext, findall
from libcloud.common.base import XmlResponse, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.common.types import MalformedResponseError, LazyList
from libcloud.dns.types import Provider, RecordType
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.dns.base import DNSDriver, Zone, Record

API_HOST = 'ns.zerigo.com'
API_VERSION = '1.1'
API_ROOT = '/api/%s/' % (API_VERSION)

VALID_ZONE_EXTRA_PARAMS = ['notes', 'tag-list', 'ns1', 'slave-nameservers']
VALID_RECORD_EXTRA_PARAMS = ['notes', 'ttl', 'priority']

# Number of items per page (maximum limit is 1000)
ITEMS_PER_PAGE = 100


class ZerigoError(LibcloudError):
    def __init__(self, code, errors):
        self.code = code
        self.errors = errors or []

    def __str__(self):
        return 'Errors: %s' % (', '.join(self.errors))

    def __repr__(self):
        return ('<ZerigoError response code=%s, errors count=%s>' %
                                                          (self.code,
                                                           len(self.errors)))


class ZerigoDNSResponse(XmlResponse):
    def success(self):
        return self.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]

    def parse_error(self):
        status = int(self.status)

        if status == 401:
            if not self.body:
                raise InvalidCredsError(str(self.status) + ': ' + self.error)
            else:
                raise InvalidCredsError(self.body)
        elif status == 404:
            context = self.connection.context
            if context['resource'] == 'zone':
                raise ZoneDoesNotExistError(value='', driver=self,
                                            zone_id=context['id'])
            elif context['resource'] == 'record':
                raise RecordDoesNotExistError(value='', driver=self,
                                              record_id=context['id'])
        elif status != 503:
            try:
                body = ET.XML(self.body)
            except:
                raise MalformedResponseError('Failed to parse XML',
                                             body=self.body)

            errors = []
            for error in findall(element=body, xpath='error'):
                errors.append(error.text)

            raise ZerigoError(code=status, errors=errors)

        return self.body


class ZerigoDNSConnection(ConnectionUserAndKey):
    host = API_HOST
    secure = True
    responseCls = ZerigoDNSResponse

    def add_default_headers(self, headers):
        auth_b64 = base64.b64encode(b('%s:%s' % (self.user_id, self.key)))
        headers['Authorization'] = 'Basic %s' % (auth_b64)
        return headers

    def request(self, action, params=None, data='', headers=None,
                method='GET'):
        if not headers:
            headers = {}
        if not params:
            params = {}

        if method in ("POST", "PUT"):
            headers = {'Content-Type': 'application/xml; charset=UTF-8'}
        return super(ZerigoDNSConnection, self).request(action=action,
                                                        params=params,
                                                        data=data,
                                                        method=method,
                                                        headers=headers)


class ZerigoDNSDriver(DNSDriver):
    type = Provider.ZERIGO
    name = 'Zerigo DNS'
    connectionCls = ZerigoDNSConnection

    RECORD_TYPE_MAP = {
        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        RecordType.CNAME: 'CNAME',
        RecordType.MX: 'MX',
        RecordType.REDIRECT: 'REDIRECT',
        RecordType.TXT: 'TXT',
        RecordType.SRV: 'SRV',
        RecordType.NAPTR: 'NAPTR',
        RecordType.NS: 'NS',
        RecordType.PTR: 'PTR',
        RecordType.SPF: 'SPF',
    }

    def list_zones(self):
        value_dict = {'type': 'zones'}
        return LazyList(get_more=self._get_more, value_dict=value_dict)

    def list_records(self, zone):
        value_dict = {'type': 'records', 'zone': zone}
        return LazyList(get_more=self._get_more, value_dict=value_dict)

    def get_zone(self, zone_id):
        path = API_ROOT + 'zones/%s.xml' % (zone_id)
        self.connection.set_context({'resource': 'zone', 'id': zone_id})
        data = self.connection.request(path).object
        zone = self._to_zone(elem=data)
        return zone

    def get_record(self, zone_id, record_id):
        zone = self.get_zone(zone_id=zone_id)
        self.connection.set_context({'resource': 'record', 'id': record_id})
        path = API_ROOT + 'hosts/%s.xml' % (record_id)
        data = self.connection.request(path).object
        record = self._to_record(elem=data, zone=zone)
        return record

    def create_zone(self, domain, type='master', ttl=None, extra=None):
        """
        Create a new zone.

        Provider API docs:
        https://www.zerigo.com/docs/apis/dns/1.1/zones/create
        """
        path = API_ROOT + 'zones.xml'
        zone_elem = self._to_zone_elem(domain=domain, type=type, ttl=ttl,
                                       extra=extra)
        data = self.connection.request(action=path,
                                       data=ET.tostring(zone_elem),
                                       method='POST').object
        zone = self._to_zone(elem=data)
        return zone

    def update_zone(self, zone, domain=None, type=None, ttl=None, extra=None):
        """
        Update an existing zone.

        Provider API docs:
        https://www.zerigo.com/docs/apis/dns/1.1/zones/update
        """
        if domain:
            raise LibcloudError('Domain cannot be changed', driver=self)

        path = API_ROOT + 'zones/%s.xml' % (zone.id)
        zone_elem = self._to_zone_elem(domain=domain, type=type, ttl=ttl,
                                       extra=extra)
        response = self.connection.request(action=path,
                                       data=ET.tostring(zone_elem),
                                       method='PUT')
        assert response.status == httplib.OK

        merged = merge_valid_keys(params=copy.deepcopy(zone.extra),
                                  valid_keys=VALID_ZONE_EXTRA_PARAMS,
                                  extra=extra)
        updated_zone = get_new_obj(obj=zone, klass=Zone,
                                   attributes={'type': type,
                                               'ttl': ttl,
                                               'extra': merged})
        return updated_zone

    def create_record(self, name, zone, type, data, extra=None):
        """
        Create a new record.

        Provider API docs:
        https://www.zerigo.com/docs/apis/dns/1.1/hosts/create
        """
        path = API_ROOT + 'zones/%s/hosts.xml' % (zone.id)
        record_elem = self._to_record_elem(name=name, type=type, data=data,
                                           extra=extra)
        response = self.connection.request(action=path,
                                           data=ET.tostring(record_elem),
                                           method='POST')
        assert response.status == httplib.CREATED
        record = self._to_record(elem=response.object, zone=zone)
        return record

    def update_record(self, record, name=None, type=None, data=None,
                      extra=None):
        path = API_ROOT + 'hosts/%s.xml' % (record.id)
        record_elem = self._to_record_elem(name=name, type=type, data=data,
                                           extra=extra)
        response = self.connection.request(action=path,
                                           data=ET.tostring(record_elem),
                                           method='PUT')
        assert response.status == httplib.OK

        merged = merge_valid_keys(params=copy.deepcopy(record.extra),
                                  valid_keys=VALID_RECORD_EXTRA_PARAMS,
                                  extra=extra)
        updated_record = get_new_obj(obj=record, klass=Record,
                                     attributes={'type': type,
                                                 'data': data,
                                                 'extra': merged})
        return updated_record

    def delete_zone(self, zone):
        path = API_ROOT + 'zones/%s.xml' % (zone.id)
        self.connection.set_context({'resource': 'zone', 'id': zone.id})
        response = self.connection.request(action=path, method='DELETE')
        return response.status == httplib.OK

    def delete_record(self, record):
        path = API_ROOT + 'hosts/%s.xml' % (record.id)
        self.connection.set_context({'resource': 'record', 'id': record.id})
        response = self.connection.request(action=path, method='DELETE')
        return response.status == httplib.OK

    def ex_get_zone_by_domain(self, domain):
        """
        Retrieve a zone object by the domain name.
        """
        path = API_ROOT + 'zones/%s.xml' % (domain)
        self.connection.set_context({'resource': 'zone', 'id': domain})
        data = self.connection.request(path).object
        zone = self._to_zone(elem=data)
        return zone

    def ex_force_slave_axfr(self, zone):
        """
        Force a zone transfer.
        """
        path = API_ROOT + 'zones/%s/force_slave_axfr.xml' % (zone.id)
        self.connection.set_context({'resource': 'zone', 'id': zone.id})
        response = self.connection.request(path, method='POST')
        assert response.status == httplib.ACCEPTED
        return zone

    def _to_zone_elem(self, domain=None, type=None, ttl=None, extra=None):
        zone_elem = ET.Element('zone', {})

        if domain:
            domain_elem = ET.SubElement(zone_elem, 'domain')
            domain_elem.text = domain

        if type:
            ns_type_elem = ET.SubElement(zone_elem, 'ns-type')

            if type == 'master':
                ns_type_elem.text = 'pri_sec'
            elif type == 'slave':
                if not extra or 'ns1' not in extra:
                    raise LibcloudError('ns1 extra attribute is required ' +
                                        'when zone type is slave', driver=self)

                ns_type_elem.text = 'sec'
                ns1_elem = ET.SubElement(zone_elem, 'ns1')
                ns1_elem.text = extra['ns1']
            elif type == 'std_master':
                # TODO: Each driver should provide supported zone types
                # Slave name servers are elsewhere
                if not extra or 'slave-nameservers' not in extra:
                    raise LibcloudError('slave-nameservers extra ' +
                                        'attribute is required whenzone ' +
                                        'type is std_master', driver=self)

                ns_type_elem.text = 'pri'
                slave_nameservers_elem = ET.SubElement(zone_elem,
                                                      'slave-nameservers')
                slave_nameservers_elem.text = extra['slave-nameservers']

        if ttl:
            default_ttl_elem = ET.SubElement(zone_elem, 'default-ttl')
            default_ttl_elem.text = str(ttl)

        if extra and 'tag-list' in extra:
            tags = extra['tag-list']

            tags_elem = ET.SubElement(zone_elem, 'tag-list')
            tags_elem.text = ' '.join(tags)

        return zone_elem

    def _to_record_elem(self, name=None, type=None, data=None, extra=None):
        record_elem = ET.Element('host', {})

        if name:
            name_elem = ET.SubElement(record_elem, 'hostname')
            name_elem.text = name

        if type:
            type_elem = ET.SubElement(record_elem, 'host-type')
            type_elem.text = self.RECORD_TYPE_MAP[type]

        if data:
            data_elem = ET.SubElement(record_elem, 'data')
            data_elem.text = data

        if extra:
            if 'ttl' in extra:
                ttl_elem = ET.SubElement(record_elem, 'ttl',
                                         {'type': 'integer'})
                ttl_elem.text = str(extra['ttl'])

            if 'priority' in extra:
                # Only MX and SRV records support priority
                priority_elem = ET.SubElement(record_elem, 'priority',
                                              {'type': 'integer'})

                priority_elem.text = str(extra['priority'])

            if 'notes' in extra:
                notes_elem = ET.SubElement(record_elem, 'notes')
                notes_elem.text = extra['notes']

        return record_elem

    def _to_zones(self, elem):
        zones = []

        for item in findall(element=elem, xpath='zone'):
            zone = self._to_zone(elem=item)
            zones.append(zone)

        return zones

    def _to_zone(self, elem):
        id = findtext(element=elem, xpath='id')
        domain = findtext(element=elem, xpath='domain')
        type = findtext(element=elem, xpath='ns-type')
        type = 'master' if type.find('pri') == 0 else 'slave'
        ttl = findtext(element=elem, xpath='default-ttl')

        hostmaster = findtext(element=elem, xpath='hostmaster')
        custom_ns = findtext(element=elem, xpath='custom-ns')
        custom_nameservers = findtext(element=elem, xpath='custom-nameservers')
        notes = findtext(element=elem, xpath='notes')
        nx_ttl = findtext(element=elem, xpath='nx-ttl')
        slave_nameservers = findtext(element=elem, xpath='slave-nameservers')
        tags = findtext(element=elem, xpath='tag-list')
        tags = tags.split(' ') if tags else []

        extra = {'hostmaster': hostmaster, 'custom-ns': custom_ns,
                'custom-nameservers': custom_nameservers, 'notes': notes,
                'nx-ttl': nx_ttl, 'slave-nameservers': slave_nameservers,
                'tags': tags}
        zone = Zone(id=str(id), domain=domain, type=type, ttl=int(ttl),
                    driver=self, extra=extra)
        return zone

    def _to_records(self, elem, zone):
        records = []

        for item in findall(element=elem, xpath='host'):
            record = self._to_record(elem=item, zone=zone)
            records.append(record)

        return records

    def _to_record(self, elem, zone):
        id = findtext(element=elem, xpath='id')
        name = findtext(element=elem, xpath='hostname')
        type = findtext(element=elem, xpath='host-type')
        type = self._string_to_record_type(type)
        data = findtext(element=elem, xpath='data')

        notes = findtext(element=elem, xpath='notes')
        state = findtext(element=elem, xpath='state')
        fqdn = findtext(element=elem, xpath='fqdn')
        priority = findtext(element=elem, xpath='priority')

        extra = {'notes': notes, 'state': state, 'fqdn': fqdn,
                 'priority': priority}

        record = Record(id=id, name=name, type=type, data=data,
                        zone=zone, driver=self, extra=extra)
        return record

    def _get_more(self, last_key, value_dict):
        # Note: last_key in this case really is a "last_page".
        # TODO: Update base driver and change last_key to something more
        # generic - e.g. marker
        params = {}
        params['per_page'] = ITEMS_PER_PAGE
        params['page'] = last_key + 1 if last_key else 1
        transform_func_kwargs = {}

        if value_dict['type'] == 'zones':
            path = API_ROOT + 'zones.xml'
            response = self.connection.request(path)
            transform_func = self._to_zones
        elif value_dict['type'] == 'records':
            zone = value_dict['zone']
            path = API_ROOT + 'zones/%s/hosts.xml' % (zone.id)
            self.connection.set_context({'resource': 'zone', 'id': zone.id})
            response = self.connection.request(path, params=params)
            transform_func = self._to_records
            transform_func_kwargs['zone'] = value_dict['zone']

        exhausted = False
        result_count = int(response.headers.get('x-query-count', 0))
        transform_func_kwargs['elem'] = response.object

        if (params['page'] * ITEMS_PER_PAGE) >= result_count:
            exhausted = True

        if response.status == httplib.OK:
            items = transform_func(**transform_func_kwargs)
            return items, params['page'], exhausted
        else:
            return [], None, True
