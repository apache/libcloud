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

__all__ = ["LinodeDNSDriver"]

from datetime import datetime

from libcloud.dns.base import Zone, Record, DNSDriver
from libcloud.dns.types import Provider, RecordType
from libcloud.utils.py3 import httplib
from libcloud.utils.misc import merge_valid_keys
from libcloud.common.linode import (
    DEFAULT_API_VERSION,
    LinodeResponseV4,
    LinodeExceptionV4,
    LinodeConnectionV4,
)

try:
    import simplejson as json
except ImportError:
    import json


VALID_ZONE_EXTRA_PARAMS_V4 = [
    "description",
    "expire_sec",
    "master_ips",
    "refresh_sec",
    "retry_sec",
    "soa_email",
    "status",
    "tags",
]

VALID_RECORD_EXTRA_PARAMS_V4 = [
    "port",
    "priority",
    "protocol",
    "service",
    "tag",
    "ttl_sec",
    "target",
    "weight",
]


class LinodeDNSDriver(DNSDriver):
    type = Provider.LINODE
    name = "Linode DNS"
    website = "http://www.linode.com/"

    def __new__(
        cls,
        key,
        secret=None,
        secure=True,
        host=None,
        port=None,
        api_version=DEFAULT_API_VERSION,
        **kwargs,
    ):
        if cls is LinodeDNSDriver:
            if api_version == "4.0":
                cls = LinodeDNSDriverV4
            else:
                raise NotImplementedError(
                    "No Linode driver found for API version: %s" % (api_version)
                )
        return super().__new__(cls)


class LinodeDNSResponseV4(LinodeResponseV4):
    pass


class LinodeDNSConnectionV4(LinodeConnectionV4):
    responseCls = LinodeDNSResponseV4


class LinodeDNSDriverV4(LinodeDNSDriver):
    connectionCls = LinodeDNSConnectionV4

    RECORD_TYPE_MAP = {
        RecordType.SOA: "SOA",
        RecordType.NS: "NS",
        RecordType.MX: "MX",
        RecordType.A: "A",
        RecordType.AAAA: "AAAA",
        RecordType.CNAME: "CNAME",
        RecordType.TXT: "TXT",
        RecordType.SRV: "SRV",
        RecordType.CAA: "CAA",
    }

    def list_zones(self):
        """
        Return a list of zones.

        :return: ``list`` of :class:`Zone`
        """
        data = self._paginated_request("/v4/domains", "data")
        return [self._to_zone(zone) for zone in data]

    def list_records(self, zone):
        """
        Return a list of records for the provided zone.

        :param zone: Zone to list records for.
        :type zone: :class:`Zone`

        :return: ``list`` of :class:`Record`
        """
        if not isinstance(zone, Zone):
            raise LinodeExceptionV4("Invalid zone instance")

        data = self._paginated_request("/v4/domains/%s/records" % zone.id, "data")

        return [self._to_record(record, zone=zone) for record in data]

    def get_zone(self, zone_id):
        """
        Return a Zone instance.

        :param zone_id: ID of the zone to get
        :type  zone_id: ``str``

        :rtype: :class:`Zone`
        """
        data = self.connection.request("/v4/domains/%s" % zone_id).object

        return self._to_zone(data)

    def get_record(self, zone_id, record_id):
        """
        Return a record instance.

        :param zone_id: ID of the record's zone
        :type  zone_id: ``str``

        :param record_id: ID of the record to get
        :type  record_id: ``str``

        :rtype: :class:`Record`
        """
        data = self.connection.request(
            "/v4/domains/{}/records/{}".format(zone_id, record_id)
        ).object

        return self._to_record(data, self.get_zone(zone_id))

    def create_zone(self, domain, type="master", ttl=None, extra=None):
        """
        Create a new zone.

        :param domain: Zone domain name (e.g. example.com)
        :type domain: ``str``

        :keyword type: Zone type (master / slave).
        :type  type: ``str``

        :keyword ttl: TTL for new records. (optional)
        :type  ttl: ``int``

        :keyword extra: Extra attributes.('description', 'expire_sec', \
        'master_ips','refresh_sec', 'retry_sec', 'soa_email',\
        'status', 'tags'). 'soa_email' required for master zones
        :type extra: ``dict``

        :rtype: :class:`Zone`
        """

        attr = {
            "domain": domain,
            "type": type,
        }
        if ttl is not None:
            attr["ttl_sec"] = ttl

        merge_valid_keys(params=attr, valid_keys=VALID_ZONE_EXTRA_PARAMS_V4, extra=extra)
        data = self.connection.request("/v4/domains", data=json.dumps(attr), method="POST").object

        return self._to_zone(data)

    def create_record(self, name, zone, type, data, extra=None):
        """
        Create a record.

        :param name: The name of this Record.For A records\
        this is the subdomain being associated with an IP address.
        :type  name: ``str``

        :param zone: Zone which the records will be created for.
        :type zone: :class:`Zone`

        :param type: DNS record type.
        :type  type: :class:`RecordType`

        :param data: Data for the record (depends on the record type).\
         For A records, this is the address the domain should resolve to.
        :type  data: ``str``

        :param extra: Extra attributes.('port', 'priority', \
        'protocol', 'service', 'tag', 'ttl_sec', 'target', 'weight')
        :type  extra: ``dict``

        :rtype: :class:`Record`
        """
        if not isinstance(zone, Zone):
            raise LinodeExceptionV4("Invalid zone instance")

        attr = {
            "type": self.RECORD_TYPE_MAP[type],
            "name": name,
            "target": data,
        }

        merge_valid_keys(params=attr, valid_keys=VALID_RECORD_EXTRA_PARAMS_V4, extra=extra)
        data = self.connection.request(
            "/v4/domains/%s/records" % zone.id, data=json.dumps(attr), method="POST"
        ).object

        return self._to_record(data, zone=zone)

    def update_zone(self, zone, domain, type="master", ttl=None, extra=None):
        """
        Update an existing zone.

        :param zone: Zone to update.
        :type  zone: :class:`Zone`

        :param domain: Name of zone
        :type  domain: ``str``

        :param type: Zone type (master / slave).
        :type  type: ``str``

        :param ttl: TTL for new records. (optional)
        :type  ttl: ``int``

        :param extra: Extra attributes ('description', 'expire_sec', \
        'master_ips','refresh_sec', 'retry_sec', 'soa_email','status', 'tags')

        :type  extra: ``dict``

        :rtype: :class:`Zone`
        """
        if not isinstance(zone, Zone):
            raise LinodeExceptionV4("Invalid zone instance")

        attr = {
            "domain": domain,
            "type": type,
        }

        if ttl is not None:
            attr["ttl_sec"] = ttl

        merge_valid_keys(params=attr, valid_keys=VALID_ZONE_EXTRA_PARAMS_V4, extra=extra)

        data = self.connection.request(
            "/v4/domains/%s" % zone.id, data=json.dumps(attr), method="PUT"
        ).object

        return self._to_zone(data)

    def update_record(self, record, name=None, type=None, data=None, extra=None):
        """
        Update an existing record.

        :param record: Record to update.
        :type  record: :class:`Record`

        :param name: Record name.This field's actual usage\
         depends on the type of record this represents.
        :type  name: ``str``

        :param type: DNS record type
        :type  type: :class:`RecordType`

        :param data: Data for the record (depends on the record type).
        :type  data: ``str``

        :param extra: Extra attributes.('port', 'priority', \
        'protocol', 'service', 'tag', 'ttl_sec', 'target', 'weight')
        :type  extra: ``dict``

        :rtype: :class:`Record`
        """
        if not isinstance(record, Record):
            raise LinodeExceptionV4("Invalid zone instance")

        zone = record.zone
        attr = {}

        if name is not None:
            attr["name"] = name

        if type is not None:
            attr["type"] = self.RECORD_TYPE_MAP[type]

        if data is not None:
            attr["target"] = data

        merge_valid_keys(params=attr, valid_keys=VALID_RECORD_EXTRA_PARAMS_V4, extra=extra)

        data = self.connection.request(
            "/v4/domains/{}/records/{}".format(zone.id, record.id),
            data=json.dumps(attr),
            method="PUT",
        ).object

        return self._to_record(data, zone=zone)

    def delete_zone(self, zone):
        """
        Delete a zone.

        This will delete all the records belonging to this zone.

        :param zone: Zone to delete.
        :type  zone: :class:`Zone`

        :rtype: ``bool``
        """
        if not isinstance(zone, Zone):
            raise LinodeExceptionV4("Invalid zone instance")

        response = self.connection.request("/v4/domains/%s" % zone.id, method="DELETE")
        return response.status == httplib.OK

    def delete_record(self, record):
        """
        Delete a record.

        :param record: Record to delete.
        :type  record: :class:`Record`

        :rtype: ``bool``
        """
        if not isinstance(record, Record):
            raise LinodeExceptionV4("Invalid record instance")

        zone = record.zone

        response = self.connection.request(
            "/v4/domains/{}/records/{}".format(zone.id, record.id), method="DELETE"
        )
        return response.status == httplib.OK

    def _to_record(self, item, zone=None):
        extra = {
            "port": item["port"],
            "weight": item["weight"],
            "priority": item["priority"],
            "service": item["service"],
            "protocol": item["protocol"],
            "created": self._to_datetime(item["created"]),
            "updated": self._to_datetime(item["updated"]),
        }
        type = self._string_to_record_type(item["type"])
        record = Record(
            id=item["id"],
            name=item["name"],
            type=type,
            data=item["target"],
            zone=zone,
            driver=self,
            ttl=item["ttl_sec"],
            extra=extra,
        )
        return record

    def _to_zone(self, item):
        """
        Build an Zone object from the item dictionary.
        """
        extra = {
            "soa_email": item["soa_email"],
            "status": item["status"],
            "description": item["description"],
            "tags": item["tags"],
            "retry_sec": item["retry_sec"],
            "master_ips": item["master_ips"],
            "axfr_ips": item["axfr_ips"],
            "expire_sec": item["expire_sec"],
            "refresh_sec": item["refresh_sec"],
            "created": self._to_datetime(item["created"]),
            "updated": self._to_datetime(item["updated"]),
        }
        zone = Zone(
            id=item["id"],
            domain=item["domain"],
            type=item["type"],
            ttl=item["ttl_sec"],
            driver=self,
            extra=extra,
        )
        return zone

    def _to_datetime(self, strtime):
        return datetime.strptime(strtime, "%Y-%m-%dT%H:%M:%S")

    def _paginated_request(self, url, obj, params=None):
        """
        Perform multiple calls in order to have a full list of elements when
        the API responses are paginated.

        :param url: API endpoint
        :type url: ``str``

        :param obj: Result object key
        :type obj: ``str``

        :param params: Request parameters
        :type params: ``dict``

        :return: ``list`` of API response objects
        :rtype: ``list``
        """
        objects = []
        params = params if params is not None else {}

        ret = self.connection.request(url, params=params).object

        data = list(ret.get(obj, []))
        current_page = int(ret.get("page", 1))
        num_of_pages = int(ret.get("pages", 1))
        objects.extend(data)
        for page in range(current_page + 1, num_of_pages + 1):
            # add param to request next page
            params["page"] = page
            ret = self.connection.request(url, params=params).object
            data = list(ret.get(obj, []))
            objects.extend(data)
        return objects
