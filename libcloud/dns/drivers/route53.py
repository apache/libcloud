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

from hashlib import sha1
from xml.etree import ElementTree as ET

from libcloud.utils.py3 import b

from libcloud.utils.xml import findtext, findall, fixxpath
from libcloud.dns.types import Provider, RecordType
from libcloud.dns.types import ZoneDoesNotExistError, RecordDoesNotExistError
from libcloud.dns.base import DNSDriver, Zone, Record
from libcloud.common.types import LibcloudError
from libcloud.common.aws import AWSBaseResponse
from libcloud.common.base import ConnectionUserAndKey


API_VERSION = '2012-02-29'
API_HOST = 'route53.amazonaws.com'
API_ROOT = '/%s/' % (API_VERSION)

NAMESPACE = 'https://%s/doc%s' % (API_HOST, API_ROOT)


class Route53Error(LibcloudError):
    def __init__(self, code, errors):
        self.code = code
        self.errors = errors or []

    def __str__(self):
        return 'Errors: %s' % (', '.join(self.errors))

    def __repr__(self):
        return('<Route53 response code=%s>' %
               (self.code, len(self.errors)))


class Route53DNSResponse(AWSBaseResponse):
    """
    Amazon Route53 response class.
    """
    def success(self):
        return self.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]

    def error(self):
        status = int(self.status)

        if status == 403:
            if not self.body:
                raise InvalidCredsError(str(self.status) + ': ' + self.error)
            else:
                raise InvalidCredsError(self.body)

        elif status == 400:
            context = self.connection.context
            messages = []
            if context['InvalidChangeBatch']['Messages']:
                for message in context['InvalidChangeBatch']['Messages']:
                    messages.append(message['Message'])

                raise Route53Error('InvalidChangeBatch message(s): %s ',
                                   messages)


class Route53Connection(ConnectionUserAndKey):
    host = API_HOST

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
        RecordType.SRV: 'SRV'
    }

    def list_zones(self):
        data = ET.XML(self.connection.request(API_ROOT + 'hostedzone').object)
        zones = self._to_zones(data=data)
        return zones

    def list_records(self, zone):
        data = ET.XML(self.connection.request(API_ROOT + 'hostedzone/'
                      + zone.id + '/rrset').object)
        records = self._to_records(data=data, zone=zone)
        return records

    def get_zone(self, zone_id):
        data = ET.XML(self.connection.request(API_ROOT + 'hostedzone/'
                      + zone_id).object)
        zone = self._to_zone(elem=findall(element=data, xpath='HostedZone',
                                          namespace=NAMESPACE)[0])
        return zone

    def get_record(self, zone_id, record_id):
        zone = self.get_zone(zone_id=zone_id)
        data = ET.XML(self.connection.request(API_ROOT + 'hostedzone/'
                      + zone_id + '/rrset?maxitems=1&name=' + record_id)
                      .object)

        record = self._to_records(data=data, zone=zone)
        return record

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
        for elem in data.findall(
            fixxpath(xpath='ResourceRecordSets/ResourceRecordSet',
                     namespace=NAMESPACE)):
            records.append(self._to_record(elem, zone))

        return records

    def _to_record(self, elem, zone):
        name = findtext(element=elem, xpath='Name',
                        namespace=NAMESPACE)
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
        record = Record(id=name, name=name, type=type, data=data, zone=zone,
                        driver=self, extra=extra)
        return record
