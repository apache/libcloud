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
from libcloud.common.types import InvalidCredsError
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
        if int(self.status) == 401:
            if not self.body:
                raise InvalidCredsError(str(self.status) + ': ' + self.error)
            else:
                raise InvalidCredsError(self.body)


class ZerigoDNSConnection(ConnectionUserAndKey):
    host = API_HOST
    secure = True
    responseCls = ZerigoDNSResponse

    def add_default_headers(self, headers):
        auth_b64 = base64.b64encode('%s:%s' % (self.user_id, self.key))
        headers['Authorization'] = 'Basic %s' % (auth_b64)
        return headers


class ZerigoDNSDriver(DNSDriver):
    type = Provider.ZERIGO
    name = 'Zerigo DNS'
    connectionCls = ZerigoDNSConnection

    def list_zones(self):
        # TODO: Use LazyList
        path = API_ROOT + 'zones.xml'
        data = self.connection.request(path).object
        zones = self._to_zones(elem=data)

        if len(zones) == 0:
            return []

        return zones[0]

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

        extra = {'hostmaster': hostmaster, 'custom-ns': custom_ns,
                'custom-nameservers': custom_nameservers, 'notes': notes,
                'nx-ttl': nx_ttl, 'slave-nameservers': slave_nameservers}
        zone = Zone(id=str(id), domain=domain, type=type, ttl=int(ttl),
                    extra=extra, driver=self)
        return zone
