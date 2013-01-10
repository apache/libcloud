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
    'GandiDNSDriver'
]

from libcloud.common.gandi import BaseGandiDriver, GandiException
from libcloud.dns.types import Provider, RecordType
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.dns.base import DNSDriver, Zone, Record
from libcloud.common.types import LibcloudError


class GandiDNSDriver(BaseGandiDriver, DNSDriver):
    type = Provider.GANDI
    name = 'Gandi DNS'
    website = 'http://doc.rpc.gandi.net/domain/reference.html'

    RECORD_TYPE_MAP = {
        RecordType.NS: 'NS',
        RecordType.MX: 'MX',
        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        RecordType.CNAME: 'CNAME',
        RecordType.TXT: 'TXT',
        RecordType.SRV: 'SRV',
        RecordType.SPF: 'SPF',
        RecordType.WKS: 'WKS',
        RecordType.LOC: 'LOC',
    }

    def _to_zone(self, zone):
        return Zone(
            id=zone["id"],
            domain=zone["name"],
            type="master",
            ttl=0,
            driver=self,
            extra={},
            )

    def _to_zones(self, zones):
        ret = []
        for z in zones:
            ret.append(self._to_zone(z))
        return ret

    def list_zones(self):
        zones = self.connection.request("domain.zone.list")
        return self._to_zones(zones)

    def get_zone(self, zone_id):
        zone = self.connection.request("domain.zone.info", zone_id)
        return self._to_zone(zone)

    def create_zone(self, domain, type='master', ttl=None, extra=None):
        zone_id = domain.replace(".", "-")
        info = self.connection.request("domain.zone.create", zone_id)
        return self._to_zone(info)

    def update_zone(self, zone, domain=None, type=None, ttl=None, extra=None):
        #params = {
        #    "name": domain,
        #}
        #zone = self.connect.request("domain.zone.update", zone.id, params)
        #return self._to_zone(zone)
        pass

    def delete_zone(self, zone):
        res = self.connection.request("domain.zone.delete", zone.id)
        return res

    def _to_record(self, record, zone):
        return Record(
            id=record["id"],
            name=record["name"],
            type=self._string_to_record_type(record["type"]),
            data=record["value"],
            zone=zone,
            driver=self,
            extra={"ttl": record["ttl"]},
            )

    def _to_records(self, records, zone):
        retval = []
        for r in records:
            retval.append(self._to_record(r, zone))
        return retval

    def create_record(self, name, zone, type, data, extra=None):
        create = {
            "name": name,
            "type": type,  # FIXME: This needs turning to a string
            "value": data,
        }

        if "ttl" in extra:
            #FIXME: Assert between 5 minutes and 30 days
            create["ttl"] = extra["ttl"]

        rec = self.connection.request("domain.zone.record.add",
                                      zone.id,
                                      0,
                                      create)

        return self._to_record(rec, zone)

    def list_records(self, zone):
        records = self.connection.request("domain.zone.record.list", zone.id,
                                            0, {})
        return self._to_records(records, zone)

    def get_record(self, zone_id, record_id):
        filter_opts = {"id": record_id}
        records = self.connection.request("domain.zone.record.list",
                                          zone_id, 0, filter_opts)
        if len(records) == 0:
            raise RecordDoesNotExistError()

        return self._to_record(records[0], self.get_zone(zone_id))

    def update_record(self, record, name, type, data, extra):
        #FIXME: Assert that data is < 1024 characters
        # "Currently limited to 1024 ASCII characters. In case of TXT, each
        # part between quotes is limited to 255 characters"
        update = {
            "name": name,
            "type": type,  # FIXME: This needs turning to a string
            "value": data,
        }

        if "ttl" in extra:
            #FIXME: Assert between 5 minutes and 30 days
            update["ttl"] = extra["ttl"]

        rec = self.connection.request("domain.zone.record.update",
                                      record.zone.id,
                                      0,
                                      {"id": record.id},
                                      update)

        return self._to_record(rec, record.zone)

    def delete_record(self, record):
        count = self.connection.request("domain.zone.record.delete",
                                        record.zone.id,
                                        0,
                                        {"id": record.id})

        if count == 1:
            return True

        return False
