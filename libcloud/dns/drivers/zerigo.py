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


import base64

from xml.etree import ElementTree as ET

from libcloud.utils import fixxpath, findtext, findattr, findall
from libcloud.common.base import Response, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.dns.types import Provider, RecordType
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.dns.base import DNSDriver, Zone, Record


API_HOST = 'ns.zerigo.com'
API_VERSION = '1.1'
API_ROOT = '/api/%s/' % (API_VERSION)


class ZerigoDNSResponse(Response):
    def parse_body(self):
        if not self.body:
            return None

        try:
            body = ET.XML(self.body)
        except:
            raise MalformedResponseError('Failed to parse XML', body=self.body)
        return body

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

        return self.body


class ZerigoDNSConnection(ConnectionUserAndKey):
    host = API_HOST
    secure = True
    responseCls = ZerigoDNSResponse

    def add_default_headers(self, headers):
        auth_b64 = base64.b64encode('%s:%s' % (self.user_id, self.key))
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

    def list_zones(self):
        # TODO: Use LazyList
        path = API_ROOT + 'zones.xml'
        data = self.connection.request(path).object
        zones = self._to_zones(elem=data)
        return zones

    def list_records(self, zone):
        # TODO: Use LazyList
        path = API_ROOT + 'zones/%s/hosts.xml' % (zone.id)
        self.connection.set_context({'resource': 'zone', 'id': zone.id})
        data = self.connection.request(path).object
        records = self._to_records(elem=data, zone=zone)
        return records

    def get_zone(self, zone_id):
        path = API_ROOT + 'zones/%s.xml' % (zone_id)
        self.connection.set_context({'resource': 'zone', 'id': zone_id})
        data = self.connection.request(path).object
        zone = self._to_zone(elem=data)
        return zone

    def get_record(self, zone_id, record_id):
        zone = self.get_zone(zone_id=zone_id)
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

        zone_elem = ET.Element('zone', {})
        domain_elem = ET.SubElement(zone_elem, 'domain')
        domain_elem.text = domain
        ns_type_elem = ET.SubElement(zone_elem, 'ns-type')

        if type == 'master':
            ns_type_elem.text = 'pri_sec'
        elif type == 'slave':
            if not extra or 'ns1' not in extra:
                raise LibcloudError('ns1 extra attribute is required when ' +
                                    'zone type is slave', driver=self)

            ns_type_elem.text = 'sec'
            ns1_elem = ET.SubElement(zone_elem, 'ns1')
            ns1_elem.text = extra['ns1']
        elif type == 'std_master':
            # TODO: Each driver should provide supported zone types
            # Slave name servers are elsewhere
            if not extra or 'slave-nameservers' not in extra:
                raise LibcloudError('slave-nameservers extra attribute is ' +
                                    'required whenzone type is std_master',
                                    driver=self)

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

        data = self.connection.request(action=path,
                                       data=ET.tostring(zone_elem),
                                       method='POST').object
        zone = self._to_zone(elem=data)
        return zone

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
