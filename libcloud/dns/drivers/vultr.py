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
"""
Vultr DNS Driver
"""
import json
from typing import Any, Dict, List, Optional

from libcloud.dns.base import Zone, Record, DNSDriver
from libcloud.dns.types import (
    Provider,
    RecordType,
)
from libcloud.common.vultr import (
    DEFAULT_API_VERSION,
    VultrResponseV2,
    VultrConnectionV2,
)

__all__ = [
    "ZoneRequiredException",
    "VultrDNSResponseV2",
    "VultrDNSConnectionV2",
    "VultrDNSDriver",
]


class ZoneRequiredException(Exception):
    pass


class VultrDNSResponseV2(VultrResponseV2):
    pass


class VultrDNSConnectionV2(VultrConnectionV2):
    responseCls = VultrDNSResponseV2


class VultrDNSDriver(DNSDriver):
    type = Provider.VULTR
    name = "Vultr DNS"
    website = "https://www.vultr.com"

    def __new__(
        cls,
        key,
        secret=None,
        secure=True,
        host=None,
        port=None,
        api_version=DEFAULT_API_VERSION,
        region=None,
        **kwargs,
    ):
        if cls is VultrDNSDriver:
            if api_version == "2":
                cls = VultrDNSDriverV2
            else:
                raise NotImplementedError(
                    "No Vultr driver found for API version: %s" % (api_version)
                )

        return super().__new__(cls)


class VultrDNSDriverV2(VultrDNSDriver):
    connectionCls = VultrDNSConnectionV2

    RECORD_TYPE_MAP = {
        RecordType.A: "A",
        RecordType.AAAA: "AAAA",
        RecordType.CNAME: "CNAME",
        RecordType.NS: "NS",
        RecordType.MX: "MX",
        RecordType.SRV: "SRV",
        RecordType.TXT: "TXT",
        RecordType.CAA: "CAA",
        RecordType.SSHFP: "SSHFP",
    }

    def list_zones(self) -> List[Zone]:
        """Return a list of zones.

        :return: ``list`` of :class:`Zone`
        """
        data = self._paginated_request("/v2/domains", "domains")

        return [self._to_zone(item) for item in data]

    def get_zone(self, zone_id: str) -> Zone:
        """Return a Zone instance.

        :param zone_id: ID of the required zone
        :type  zone_id: ``str``

        :rtype: :class:`Zone`
        """
        resp = self.connection.request("/v2/domains/%s" % zone_id)

        return self._to_zone(resp.object["domain"])

    def create_zone(
        self,
        domain: str,
        type: str = "master",
        ttl: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Zone:
        """Create a new zone.

        :param domain: Zone domain name (e.g. example.com)
        :type domain: ``str``

        :param type: Zone type. Only 'master' value is supported.
        :type  type: ``str``

        :param ttl: TTL for new records. (unused)
        :type  ttl: ``int``

        :param extra: Extra attributes 'ip': ``str`` IP for a default A record
                                       'dns_sec': ``bool`` Enable DSNSEC.
        :type extra: ``dict``

        :rtype: :class:`Zone`
        """

        data = {
            "domain": domain,
        }

        extra = extra or {}

        if "ip" in extra:
            data["ip"] = extra["ip"]

        if "dns_sec" in extra:
            data["dns_sec"] = "enabled" if extra["dns_sec"] is True else "disabled"

        resp = self.connection.request("/v2/domains", data=json.dumps(data), method="POST")

        return self._to_zone(resp.object["domain"])

    def delete_zone(self, zone: Zone) -> bool:
        """Delete a zone.

        Note: This will delete all the records belonging to this zone.

        :param zone: Zone to delete.
        :type  zone: :class:`Zone`

        :rtype: ``bool``
        """
        resp = self.connection.request("/v2/domains/%s" % zone.domain, method="DELETE")

        return resp.success()

    def list_records(self, zone: Zone) -> List[Record]:
        """Return a list of records for the provided zone.

        :param zone: Zone to list records for.
        :type zone: :class:`Zone`

        :return: ``list`` of :class:`Record`
        """
        data = self._paginated_request("/v2/domains/%s/records" % zone.domain, "records")

        return [self._to_record(item, zone) for item in data]

    def get_record(self, zone_id: str, record_id: str) -> Record:
        """Return a Record instance.

        :param zone_id: ID of the required zone
        :type  zone_id: ``str``

        :param record_id: ID of the required record
        :type  record_id: ``str``

        :rtype: :class:`Record`
        """
        resp = self.connection.request("/v2/domains/{}/records/{}".format(zone_id, record_id))

        # Avoid making an extra API call, as zone_id is enough for
        # standard fields
        zone = Zone(id=zone_id, domain=zone_id, type="master", ttl=None, driver=self)

        return self._to_record(resp.object["record"], zone)

    def create_record(
        self,
        name: str,
        zone: Zone,
        type: RecordType,
        data: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Record:
        """Create a new record.

        :param name: Record name without the domain name (e.g. www).
                     Note: If you want to create a record for a base domain
                     name, you should specify empty string ('') for this
                     argument.
        :type  name: ``str``

        :param zone: Zone where the requested record is created.
        :type  zone: :class:`Zone`

        :param type: DNS record type (A, AAAA, ...).
        :type  type: :class:`RecordType`

        :param data: Data for the record (depends on the record type).
        :type  data: ``str``

        :keyword extra: Extra attributes 'ttl': Time to live in seconds
                                         'priority': DNS priority. Only
                                                     required for MX and SRV
        :type extra: ``dict``

        :rtype: :class:`Record`
        """
        data = {
            "name": name,
            "type": self.RECORD_TYPE_MAP[type],
            "data": data,
        }
        extra = extra or {}

        if "ttl" in extra:
            data["ttl"] = int(extra["ttl"])

        if "priority" in extra:
            data["priority"] = int(extra["priority"])

        resp = self.connection.request(
            "/v2/domains/%s/records" % zone.domain, data=json.dumps(data), method="POST"
        )

        return self._to_record(resp.object["record"], zone)

    def update_record(
        self,
        record: Record,
        name: Optional[str] = None,
        type: Optional[RecordType] = None,
        data: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update an existing record.

        :param record: Record to update.
        :type  record: :class:`Record`

        :keyword name: Record name without the domain name (e.g. www).
                     Note: If you want to create a record for a base domain
                     name, you should specify empty string ('') for this
                     argument.
        :type  name: ``str``

        :keyword type: DNS record type. (Unused)
        :type  type: :class:`RecordType`

        :keyword data: Data for the record (depends on the record type).
        :type  data: ``str``

        :keyword extra: Extra attributes 'ttl': Time to live in seconds
                                         'priority': DNS priority. Only
                                                     required for MX and SRV
        :type  extra: ``dict``

        :rtype: ``bool``
        """
        body = {}

        if name:
            body["name"] = name

        if data:
            body["data"] = data

        extra = extra or {}

        if "ttl" in extra:
            body["ttl"] = int(extra["ttl"])

        if "priority" in extra:
            body["priority"] = int(extra["priority"])

        resp = self.connection.request(
            "/v2/domains/{}/records/{}".format(record.zone.domain, record.id),
            data=json.dumps(body),
            method="PATCH",
        )

        return resp.success()

    def delete_record(self, record: Record) -> bool:
        """Delete a record.

        :param record: Record to delete.
        :type  record: :class:`Record`

        :rtype: ``bool``
        """
        resp = self.connection.request(
            "/v2/domains/{}/records/{}".format(record.zone.domain, record.id),
            method="DELETE",
        )

        return resp.success()

    def _to_zone(self, data: Dict[str, Any]) -> Zone:
        type_ = "master"
        domain = data["domain"]
        extra = {
            "date_created": data["date_created"],
        }

        return Zone(id=domain, domain=domain, driver=self, type=type_, ttl=None, extra=extra)

    def _to_record(self, data: Dict[str, Any], zone: Zone) -> Record:
        id_ = data["id"]
        name = data["name"]
        type_ = self._string_to_record_type(data["type"])
        data_ = data["data"]
        ttl = data["ttl"]
        extra = {
            "priority": data["priority"],
        }

        return Record(
            id=id_,
            name=name,
            type=type_,
            data=data_,
            ttl=ttl,
            driver=self,
            zone=zone,
            extra=extra,
        )

    def _paginated_request(
        self,
        url: str,
        key: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """Perform multiple calls to get the full list of items when
        the API responses are paginated.

        :param url: API endpoint
        :type url: ``str``

        :param key: Result object key
        :type key: ``str``

        :param params: Request parameters
        :type params: ``dict``

        :return: ``list`` of API response objects
        :rtype: ``list``
        """
        params = params if params is not None else {}
        resp = self.connection.request(url, params=params).object
        data = list(resp.get(key, []))
        objects = data

        while True:
            next_page = resp["meta"]["links"]["next"]

            if next_page:
                params["cursor"] = next_page
                resp = self.connection.request(url, params=params).object
                data = list(resp.get(key, []))
                objects.extend(data)
            else:
                return objects
