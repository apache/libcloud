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

import sys
from libcloud.utils.py3 import httplib

from libcloud.common.dimensiondata import DimensionDataAPIException
from libcloud.common.types import InvalidCredsError
from libcloud.backup.drivers.dimensiondata import DimensionDataBackupDriver as DimensionData

from libcloud.test import MockHttp, unittest
from libcloud.test.backup import TestCaseMixin
from libcloud.test.file_fixtures import BackupFileFixtures

from libcloud.test.secrets import DIMENSIONDATA_PARAMS


class DimensionDataTests(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        DimensionData.connectionCls.conn_classes = (None, DimensionDataMockHttp)
        DimensionDataMockHttp.type = None
        self.driver = DimensionData(*DIMENSIONDATA_PARAMS)

    def test_invalid_region(self):
        with self.assertRaises(ValueError):
            self.driver = DimensionData(*DIMENSIONDATA_PARAMS, region='blah')

    def test_invalid_creds(self):
        DimensionDataMockHttp.type = 'UNAUTHORIZED'
        with self.assertRaises(InvalidCredsError):
            self.driver.list_targets()

    def test_list_targets(self):
        targets = self.driver.list_targets()
        self.assertEqual(len(targets), 2)
        self.assertEqual(targets[0].id, '5579f3a7-4c32-4cf5-8a7e-b45c36a35c10')
        self.assertEqual(targets[0].address, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(targets[0].extra['servicePlan'], 'Enterprise')

    def test_create_target(self):
        target = self.driver.create_target(
            'name',
            'e75ead52-692f-4314-8725-c8a4f4d13a87',
            extra={'servicePlan': 'Enterprise'})
        self.assertEqual(target.id, 'ee7c4b64-f7af-4a4f-8384-be362273530f')
        self.assertEqual(target.address, 'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(target.extra['servicePlan'], 'Enterprise')

    def test_create_target_EXISTS(self):
        DimensionDataMockHttp.type = 'EXISTS'
        with self.assertRaises(DimensionDataAPIException) as context:
            self.driver.create_target(
                'name',
                'e75ead52-692f-4314-8725-c8a4f4d13a87',
                extra={'servicePlan': 'Enterprise'})
        self.assertEqual(context.exception.code, 'ERROR')
        self.assertEqual(context.exception.msg, 'Cloud backup for this server is already enabled or being enabled (state: NORMAL).')

    def test_update_target(self):
        target = self.driver.list_targets()[0]
        extra = {'servicePlan': 'Enterprise'}
        new_target = self.driver.update_target(target, extra=extra)
        self.assertEqual(new_target.extra['servicePlan'], 'Enterprise')

    def test_delete_target(self):
        target = self.driver.list_targets()[0]
        self.assertTrue(self.driver.delete_target(target))

    def test_ex_add_client_to_target(self):
        target = self.driver.list_targets()[0]
        self.assertTrue(
            self.driver.ex_add_client_to_target(target, 'FA.Linux', '14 Day Storage Policy',
                                                '12AM - 6AM', 'ON_FAILURE', 'nobody@example.com')
        )

    def test_ex_get_backup_details_for_target(self):
        target = self.driver.list_targets()[0]
        response = self.driver.ex_get_backup_details_for_target(target)
        self.assertEqual(response.service_plan, 'Enterprise')
        client = response.clients[0]
        self.assertEqual(client.type, 'FA.Linux')
        self.assertEqual(client.running_job.percentage, 5)

    def test_ex_list_available_client_types(self):
        target = self.driver.list_targets()[0]
        answer = self.driver.ex_list_available_client_types(target)
        self.assertEqual(len(answer), 1)
        self.assertEqual(answer[0].type, 'FA.Linux')
        self.assertEqual(answer[0].is_file_system, True)
        self.assertEqual(answer[0].description, 'Linux File system')

    def test_ex_list_available_storage_policies(self):
        target = self.driver.list_targets()[0]
        answer = self.driver.ex_list_available_storage_policies(target)
        self.assertEqual(len(answer), 1)
        self.assertEqual(answer[0].name,
                         '30 Day Storage Policy + Secondary Copy')
        self.assertEqual(answer[0].retention_period, 30)
        self.assertEqual(answer[0].secondary_location, 'Primary')

    def test_ex_list_available_schedule_policies(self):
        target = self.driver.list_targets()[0]
        answer = self.driver.ex_list_available_schedule_policies(target)
        self.assertEqual(len(answer), 1)
        self.assertEqual(answer[0].name, '12AM - 6AM')
        self.assertEqual(answer[0].description, 'Daily backup will start between 12AM - 6AM')


class InvalidRequestError(Exception):
    def __init__(self, tag):
        super(InvalidRequestError, self).__init__("Invalid Request - %s" % tag)


class DimensionDataMockHttp(MockHttp):

    fixtures = BackupFileFixtures('dimensiondata')

    def _oec_0_9_myaccount_UNAUTHORIZED(self, method, url, body, headers):
        return (httplib.UNAUTHORIZED, "", {}, httplib.responses[httplib.UNAUTHORIZED])

    def _oec_0_9_myaccount(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_EXISTS(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_INPROGRESS(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server(self, method, url, body, headers):
        body = self.fixtures.load(
            'caas_2_1_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_type(self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_type.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_storagePolicy(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_storagePolicy.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_schedulePolicy(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_schedulePolicy.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client(
            self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_SUCCESS_PUT.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            raise ValueError("Unknown Method {0}".format(method))

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup(
            self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_ENABLE.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == 'GET':
            if url.endswith('disable'):
                body = self.fixtures.load(
                    'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_DISABLE.xml')
                return (httplib.OK, body, {}, httplib.responses[httplib.OK])
            body = self.fixtures.load(
                'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_INFO.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        else:
            raise ValueError("Unknown Method {0}".format(method))

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_EXISTS(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_EXISTS.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_modify(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_modify.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
