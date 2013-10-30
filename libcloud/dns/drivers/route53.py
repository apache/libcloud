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
    'Route53DNSDriver'
]

import base64
import hmac
import datetime
import uuid
from libcloud.utils.py3 import httplib

from hashlib import sha1
from xml.etree import ElementTree as ET

from libcloud.utils.py3 import b, urlencode

from libcloud.utils.xml import findtext, findall, fixxpath
from libcloud.dns.types import Provider, RecordType
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.dns.base import DNSDriver, Zone, Record
from libcloud.common.types import LibcloudError
from libcloud.common.aws import AWSGenericResponse
from libcloud.common.base import ConnectionUserAndKey


API_VERSION = '2012-02-29'
API_HOST = 'route53.amazonaws.com'
API_ROOT = '/%s/' % (API_VERSION)

NAMESPACE = 'https://%s/doc%s' % (API_HOST, API_ROOT)


class InvalidChangeBatch(LibcloudError):
    pass


class Route53DNSResponse(AWSGenericResponse):
    """
    Amazon Route53 response class.
    """

    namespace = NAMESPACE
    xpath = 'Error'

    exceptions = {
        'NoSuchHostedZone': ZoneDoesNotExistError,
        'InvalidChangeBatch': InvalidChangeBatch,
    }


class Route53Connection(ConnectionUserAndKey):
    host = API_HOST
    responseCls = Route53DNSResponse

    def pre_connect_hook(self, params, headers):
        time_string = datetime.datetime.utcnow() \
                              .strftime('%a, %d %b %Y %H:%M:%S GMT')
        headers['Date'] = time_string
        tmp = []

        signature = self._get_aws_auth_b64(self.key, time_string)
        auth = {'AWSAccessKeyId': self.user_id, 'Signature': signature,
                'Algorithm': 'HmacSHA1'}

        for k, v in auth.items():
            tmp.append('%s=%s' % (k, v))

        headers['X-Amzn-Authorization'] = 'AWS3-HTTPS ' + ','.join(tmp)

        return params, headers

    def _get_aws_auth_b64(self, secret_key, time_string):
        b64_hmac = base64.b64encode(
            hmac.new(b(secret_key), b(time_string), digestmod=sha1).digest()
        )

        return b64_hmac.decode('utf-8')


class Route53DNSDriver(DNSDriver):
    type = Provider.ROUTE53
    name = 'Route53 DNS'
    website = 'http://aws.amazon.com/route53/'
    connectionCls = Route53Connection

    RECORD_TYPE_MAP = {
        RecordType.NS: 'NS',
        RecordType.MX: 'MX',
        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        RecordType.CNAME: 'CNAME',
        RecordType.TXT: 'TXT',
        RecordType.SRV: 'SRV',
        RecordType.PTR: 'PTR',
        RecordType.SOA: 'SOA',
        RecordType.SPF: 'SPF',
        RecordType.TXT: 'TXT'
    }

    def list_zones(self):
        data = self.connection.request(API_ROOT + 'hostedzone').object
        zones = self._to_zones(data=data)
        return zones

    def list_records(self, zone):
        self.connection.set_context({'zone_id': zone.id})
        uri = API_ROOT + 'hostedzone/' + zone.id + '/rrset'
        data = self.connection.request(uri).object
        records = self._to_records(data=data, zone=zone)
        return records

    def get_zone(self, zone_id):
        self.connection.set_context({'zone_id': zone_id})
        uri = API_ROOT + 'hostedzone/' + zone_id
        data = self.connection.request(uri).object
        elem = findall(element=data, xpath='HostedZone',
                       namespace=NAMESPACE)[0]
        return self._to_zone(elem)

    def get_record(self, zone_id, record_id):
        zone = self.get_zone(zone_id=zone_id)
        record_type, name = record_id.split(':', 1)
        if name:
            full_name = ".".join((name, zone.domain))
        else:
            full_name = zone.domain
        self.connection.set_context({'zone_id': zone_id})
        params = urlencode({
            'name': full_name,
            'type': record_type,
            'maxitems': '1'
        })
        uri = API_ROOT + 'hostedzone/' + zone_id + '/rrset?' + params
        data = self.connection.request(uri).object

        record = self._to_records(data=data, zone=zone)[0]

        # A cute aspect of the /rrset filters is that they are more pagination
        # hints than filters!!
        # So will return a result even if its not what you asked for.
        record_type_num = self._string_to_record_type(record_type)
        if record.name != name or record.type != record_type_num:
            raise RecordDoesNotExistError(value='', driver=self,
                                          record_id=record_id)

        return record

    def create_zone(self, domain, type='master', ttl=None, extra=None):
        zone = ET.Element('CreateHostedZoneRequest', {'xmlns': NAMESPACE})
        ET.SubElement(zone, 'Name').text = domain
        ET.SubElement(zone, 'CallerReference').text = str(uuid.uuid4())

        if extra and 'Comment' in extra:
            hzg = ET.SubElement(zone, 'HostedZoneConfig')
            ET.SubElement(hzg, 'Comment').text = extra['Comment']

        uri = API_ROOT + 'hostedzone'
        data = ET.tostring(zone)
        rsp = self.connection.request(uri, method='POST', data=data).object

        elem = findall(element=rsp, xpath='HostedZone', namespace=NAMESPACE)[0]
        return self._to_zone(elem=elem)

    def delete_zone(self, zone, ex_delete_records=False):
        self.connection.set_context({'zone_id': zone.id})

        if ex_delete_records:
            self.ex_delete_all_records(zone=zone)

        uri = API_ROOT + 'hostedzone/%s' % (zone.id)
        response = self.connection.request(uri, method='DELETE')
        return response.status in [httplib.OK]

    def create_record(self, name, zone, type, data, extra=None):
        batch = [('CREATE', name, type, data, extra)]
        self._post_changeset(zone, batch)
        id = ':'.join((self.RECORD_TYPE_MAP[type], name))
        return Record(id=id, name=name, type=type, data=data, zone=zone,
                      driver=self, extra=extra)

    def update_record(self, record, name, type, data, extra):
        batch = [
            ('DELETE', record.name, record.type, record.data, record.extra),
            ('CREATE', name, type, data, extra)]
        self._post_changeset(record.zone, batch)
        id = ':'.join((self.RECORD_TYPE_MAP[type], name))
        return Record(id=id, name=name, type=type, data=data, zone=record.zone,
                      driver=self, extra=extra)

    def delete_record(self, record):
        try:
            r = record
            batch = [('DELETE', r.name, r.type, r.data, r.extra)]
            self._post_changeset(record.zone, batch)
        except InvalidChangeBatch:
            raise RecordDoesNotExistError(value='', driver=self,
                                          record_id=r.id)
        return True

    def ex_delete_all_records(self, zone):
        """
        Remove all the records for the provided zone.

        :param zone: Zone to delete records for.
        :type  zone: :class:`Zone`
        """
        deletions = []
        for r in zone.list_records():
            if r.type in (RecordType.NS, RecordType.SOA):
                continue
            deletions.append(('DELETE', r.name, r.type, r.data, r.extra))

        if deletions:
            self._post_changeset(zone, deletions)

    def _post_changeset(self, zone, changes_list):
        attrs = {'xmlns': NAMESPACE}
        changeset = ET.Element('ChangeResourceRecordSetsRequest', attrs)
        batch = ET.SubElement(changeset, 'ChangeBatch')
        changes = ET.SubElement(batch, 'Changes')

        for action, name, type_, data, extra in changes_list:
            change = ET.SubElement(changes, 'Change')
            ET.SubElement(change, 'Action').text = action

            rrs = ET.SubElement(change, 'ResourceRecordSet')
            ET.SubElement(rrs, 'Name').text = name + "." + zone.domain
            ET.SubElement(rrs, 'Type').text = self.RECORD_TYPE_MAP[type_]
            ET.SubElement(rrs, 'TTL').text = str(extra.get('ttl', '0'))

            rrecs = ET.SubElement(rrs, 'ResourceRecords')
            rrec = ET.SubElement(rrecs, 'ResourceRecord')
            ET.SubElement(rrec, 'Value').text = data

        uri = API_ROOT + 'hostedzone/' + zone.id + '/rrset'
        data = ET.tostring(changeset)
        self.connection.set_context({'zone_id': zone.id})
        self.connection.request(uri, method='POST', data=data)

    def _to_zones(self, data):
        zones = []
        for element in data.findall(fixxpath(xpath='HostedZones/HostedZone',
                                             namespace=NAMESPACE)):
            zones.append(self._to_zone(element))

        return zones

    def _to_zone(self, elem):
        name = findtext(element=elem, xpath='Name', namespace=NAMESPACE)
        id = findtext(element=elem, xpath='Id',
                      namespace=NAMESPACE).replace('/hostedzone/', '')
        comment = findtext(element=elem, xpath='Config/Comment',
                           namespace=NAMESPACE)
        resource_record_count = int(findtext(element=elem,
                                             xpath='ResourceRecordSetCount',
                                             namespace=NAMESPACE))

        extra = {'Comment': comment, 'ResourceRecordSetCount':
                 resource_record_count}

        zone = Zone(id=id, domain=name, type='master', ttl=0, driver=self,
                    extra=extra)
        return zone

    def _to_records(self, data, zone):
        records = []
        elems = data.findall(
            fixxpath(xpath='ResourceRecordSets/ResourceRecordSet',
                     namespace=NAMESPACE))
        for elem in elems:
            records.append(self._to_record(elem, zone))

        return records

    def _to_record(self, elem, zone):
        name = findtext(element=elem, xpath='Name',
                        namespace=NAMESPACE)
        name = name[:-len(zone.domain) - 1]

        type = self._string_to_record_type(findtext(element=elem, xpath='Type',
                                                    namespace=NAMESPACE))
        ttl = findtext(element=elem, xpath='TTL', namespace=NAMESPACE)

        # TODO: Support records with multiple values
        value_elem = elem.findall(
            fixxpath(xpath='ResourceRecords/ResourceRecord',
                     namespace=NAMESPACE))[0]
        data = findtext(element=(value_elem), xpath='Value',
                        namespace=NAMESPACE)

        extra = {'ttl': ttl}

        id = ':'.join((self.RECORD_TYPE_MAP[type], name))
        record = Record(id=id, name=name, type=type, data=data, zone=zone,
                        driver=self, extra=extra)
        return record
