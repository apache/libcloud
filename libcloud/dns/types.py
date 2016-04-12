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

from libcloud.common.types import LibcloudError

__all__ = [
    'Provider',
    'RecordType',
    'ZoneError',
    'ZoneDoesNotExistError',
    'ZoneAlreadyExistsError',
    'RecordError',
    'RecordDoesNotExistError',
    'RecordAlreadyExistsError',

    'OLD_CONSTANT_TO_NEW_MAPPING'
]


class Provider(object):
    DUMMY = 'dummy'
    AURORADNS = 'auroradns'
    BUDDYNS = 'buddyns'
    CLOUDFLARE = 'cloudflare'
    DIGITAL_OCEAN = 'digitalocean'
    DNSIMPLE = 'dnsimple'
    DURABLEDNS = 'durabledns'
    GANDI = 'gandi'
    GODADDY = 'godaddy'
    GOOGLE = 'google'
    HOSTVIRTUAL = 'hostvirtual'
    LINODE = 'linode'
    LIQUIDWEB = 'liquidweb'
    LUADNS = 'luadns'
    NFSN = 'nfsn'
    NSONE = 'nsone'
    POINTDNS = 'pointdns'
    RACKSPACE = 'rackspace'
    ROUTE53 = 'route53'
    SOFTLAYER = 'softlayer'
    VULTR = 'vultr'
    WORLDWIDEDNS = 'worldwidedns'
    ZERIGO = 'zerigo'
    ZONOMI = 'zonomi'
    # Deprecated
    RACKSPACE_US = 'rackspace_us'
    RACKSPACE_UK = 'rackspace_uk'


OLD_CONSTANT_TO_NEW_MAPPING = {
    Provider.RACKSPACE_US: Provider.RACKSPACE,
    Provider.RACKSPACE_UK: Provider.RACKSPACE,
}


class RecordType(object):
    """
    DNS record type.
    """
    A = 'A'
    AAAA = 'AAAA'
    ALIAS = 'ALIAS'
    CNAME = 'CNAME'
    DNAME = 'DNAME'
    GEO = 'GEO'
    HINFO = 'HINFO'
    LOC = 'LOC'
    MX = 'MX'
    NAPTR = 'NAPTR'
    NS = 'NS'
    PTR = 'PTR'
    REDIRECT = 'REDIRECT'
    RP = 'RP'
    SOA = 'SOA'
    SPF = 'SPF'
    SRV = 'SRV'
    SSHFP = 'SSHFP'
    TXT = 'TXT'
    URL = 'URL'
    WKS = 'WKS'


class ZoneError(LibcloudError):
    error_type = 'ZoneError'
    kwargs = ('zone_id', )

    def __init__(self, value, driver, zone_id):
        self.zone_id = zone_id
        super(ZoneError, self).__init__(value=value, driver=driver)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return ('<%s in %s, zone_id=%s, value=%s>' %
                (self.error_type, repr(self.driver),
                 self.zone_id, self.value))


class ZoneDoesNotExistError(ZoneError):
    error_type = 'ZoneDoesNotExistError'


class ZoneAlreadyExistsError(ZoneError):
    error_type = 'ZoneAlreadyExistsError'


class RecordError(LibcloudError):
    error_type = 'RecordError'

    def __init__(self, value, driver, record_id):
        self.record_id = record_id
        super(RecordError, self).__init__(value=value, driver=driver)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return ('<%s in %s, record_id=%s, value=%s>' %
                (self.error_type, repr(self.driver),
                 self.record_id, self.value))


class RecordDoesNotExistError(RecordError):
    error_type = 'RecordDoesNotExistError'


class RecordAlreadyExistsError(RecordError):
    error_type = 'RecordAlreadyExistsError'
