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
    'RecordAlreadyExistsError'
]


class Provider(object):
    DUMMY = 0
    LINODE = 1
    ZERIGO = 2
    RACKSPACE_US = 3
    RACKSPACE_UK = 4
    ROUTE_53 = 5


class RecordType(object):
    """
    DNS record type.
    """
    A = 0
    AAAA = 1
    MX = 2
    NS = 3
    CNAME = 4
    DNAME = 5
    TXT = 6
    PTR = 7
    SOA = 8
    SPF = 9
    SRV = 10
    PTR = 11
    NAPTR = 12
    REDIRECT = 13

    @classmethod
    def __repr__(self, value):
        reverse = dict((v, k) for k, v in list(RecordType.__dict__.items()))
        return reverse[value]


class ZoneError(LibcloudError):
    error_type = 'ZoneError'

    def __init__(self, value, driver, zone_id):
        self.zone_id = zone_id
        super(ZoneError, self).__init__(value=value, driver=driver)

    def __str__(self):
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
        return ('<%s in %s, record_id=%s, value=%s>' %
                (self.error_type, repr(self.driver),
                 self.record_id, self.value))


class RecordDoesNotExistError(RecordError):
    error_type = 'RecordDoesNotExistError'


class RecordAlreadyExistsError(RecordError):
    error_type = 'RecordAlreadyExistsError'
