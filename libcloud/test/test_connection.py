# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more§
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

import sys

from mock import Mock, call

from libcloud.test import unittest
from libcloud.common.base import Connection


class ConnectionClassTestCase(unittest.TestCase):
    def setUp(self):
        self.originalConnect = Connection.connect
        self.originalResponseCls = Connection.responseCls

        Connection.connect = Mock()
        Connection.responseCls = Mock()

    def tearDown(self):
        Connection.connect = self.originalConnect
        Connection.responseCls = Connection.responseCls

    def test_content_length(self):
        con = Connection()
        con.connection = Mock()

        ## GET method
        # No data, no content length should be present
        con.request('/test', method='GET', data=None)
        call_kwargs = con.connection.request.call_args[1]
        self.assertTrue('Content-Length' not in call_kwargs['headers'])

        # '' as data, no content length should be present
        con.request('/test', method='GET', data='')
        call_kwargs = con.connection.request.call_args[1]
        self.assertTrue('Content-Length' not in call_kwargs['headers'])

        # 'a' as data, content length should be present (data in GET is not
        # corect, but anyways)
        con.request('/test', method='GET', data='a')
        call_kwargs = con.connection.request.call_args[1]
        self.assertEqual(call_kwargs['headers']['Content-Length'], '1')

        ## POST, PUT method
        # No data, content length should be present
        for method in ['POST', 'PUT', 'post', 'put']:
            con.request('/test', method=method, data=None)
            call_kwargs = con.connection.request.call_args[1]
            self.assertEqual(call_kwargs['headers']['Content-Length'], '0')

        # '' as data, content length should be present
        for method in ['POST', 'PUT', 'post', 'put']:
            con.request('/test', method=method, data='')
            call_kwargs = con.connection.request.call_args[1]
            self.assertEqual(call_kwargs['headers']['Content-Length'], '0')

        # No data, raw request, do not touch Content-Length if present
        for method in ['POST', 'PUT', 'post', 'put']:
            con.request('/test', method=method, data=None,
                        headers={'Content-Length': '42'}, raw=True)
            putheader_call_list = con.connection.putheader.call_args_list
            self.assertIn(call('Content-Length', '42'), putheader_call_list)

        # '' as data, raw request, do not touch Content-Length if present
        for method in ['POST', 'PUT', 'post', 'put']:
            con.request('/test', method=method, data=None,
                        headers={'Content-Length': '42'}, raw=True)
            putheader_call_list = con.connection.putheader.call_args_list
            self.assertIn(call('Content-Length', '42'), putheader_call_list)

        # 'a' as data, content length should be present
        for method in ['POST', 'PUT', 'post', 'put']:
            con.request('/test', method=method, data='a')
            call_kwargs = con.connection.request.call_args[1]
            self.assertEqual(call_kwargs['headers']['Content-Length'], '1')


if __name__ == '__main__':
    sys.exit(unittest.main())
