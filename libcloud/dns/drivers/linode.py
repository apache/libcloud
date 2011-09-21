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
    'LinodeDNSDriver'
]


from libcloud.common.linode import (API_ROOT, LinodeException,
                                    LinodeConnection,
                                    LINODE_PLAN_IDS)
from libcloud.common.linode import API_HOST, API_ROOT
from libcloud.dns.types import Provider
from libcloud.dns.base import DNSDriver, Zone, Record


class LinodeDNSDriver(DNSDriver):
    type = Provider.LINODE
    name = 'Linode DNS'
    connectionCls = LinodeConnection

    def list_zones(self):
        params = {'api_action': 'domain.list'}
        data = self.connection.request(API_ROOT, params=params).objects[0]
        zones = self._to_zones(data)
        return zones

    def list_records(self, zone):
        params = {'api_action': 'domain.resource.list', 'DOMAINID': zone.id}
        data = self.connection.request(API_ROOT, params=params).objects[0]
        records = self._to_records(items=data, zone=zone)
        return records

    def get_zone(self, zone_id):
        params = {'api_action': 'domain.list', 'DomainID': zone_id}

    def get_record(self, zone_id, record_id):
        params = {'api_action': 'domain.resource.list', 'DomainID': zone_id,
                   'ResourceID': record_id}

    def create_zone(self, domain, type='master', ttl=None, extra=None):
        params = {'api_action': 'domain.create'}

    def create_record(self, name, zone, type, data, extra=None):
        params = {'api_action': 'domain.resource.create'}

    def update_record(self, record, name, type, data, extra):
        params = {'api_action': 'domain.resource.update'}

    def delete_zone(self, zone):
        params = {'api_action': 'domain.delete', 'DomainID': zone.id}

    def delete_record(self, record):
        params = {'api_action': 'domain.resource.delete',
                   'DomainID': record.zone.id, 'ResourceID': record.id}

    def _to_zones(self, items):
        zones = []

        for item in items:
            zones.append(self._to_zone(item))

        return zones

    def _to_zone(self, item):
        extra = {'soa_email': item['SOA_EMAIL'], 'status': item['STATUS'],
                  'description': item['DESCRIPTION']}
        zone = Zone(id=item['DOMAINID'], domain=item['DOMAIN'],
                    type=item['TYPE'], ttl=item['TTL_SEC'], extra=extra,
                    driver=self)
        return zone

    def _to_records(self, items, zone=None):
        records = []

        for item in items:
            records.append(self._to_record(item=item, zone=zone))

        return records

    def _to_record(self, item, zone=None):
        extra = {'protocol': item['PROTOCOL'], 'ttl_sec': item['TTL_SEC'],
                  'port': item['PORT'], 'weight': item['WEIGHT']}
        type = self._string_to_record_type(item['TYPE'])
        record = Record(id=item['RESOURCEID'], name=item['NAME'], type=type,
                        data=item['TARGET'], extra=extra, zone=zone,
                        driver=self)
        return record
