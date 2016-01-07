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

import sys
import unittest

from libcloud.dns.drivers.auroradns import AuroraDNSDriver
from libcloud.dns.types import RecordType
from libcloud.test import LibcloudTestCase, MockHttpTestCase
from libcloud.test.secrets import DNS_PARAMS_AURORADNS
from libcloud.test.file_fixtures import DNSFileFixtures


class AuroraDNSDriverTests(LibcloudTestCase):

    def setUp(self):
        AuroraDNSDriver.connectionCls.conn_classes = \
            (None, AuroraDNSDriverMockHttp)
        AuroraDNSDriverMockHttp.type = None
        self.driver = AuroraDNSDriver(*DNS_PARAMS_AURORADNS)

    def test_merge_extra_data(self):
        rdata = {
            'name': 'localhost',
            'type': RecordType.A,
            'content': '127.0.0.1'
        }

        params = {'ttl': 900,
                  'prio': 0,
                  'health_check_id': None,
                  'disabled': False}

        for param in params:
            extra = {
                param: params[param]
            }

            data = self.driver._AuroraDNSDriver__merge_extra_data(rdata,
                                                                  extra)
            self.assertEqual(data['content'], '127.0.0.1')
            self.assertEqual(data['type'], RecordType.A)
            self.assertEqual(data[param], params[param])
            self.assertEqual(data['name'], 'localhost')


class AuroraDNSDriverMockHttp(MockHttpTestCase):
    fixtures = DNSFileFixtures('auroradns')


if __name__ == '__main__':
    sys.exit(unittest.main())
