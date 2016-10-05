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

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

import sys
from libcloud.utils.py3 import httplib

from libcloud.common.dimensiondata import DimensionDataAPIException
from libcloud.common.types import InvalidCredsError
from libcloud.backup.base import BackupTargetJob
from libcloud.backup.drivers.dimensiondata import DimensionDataBackupDriver as DimensionData
from libcloud.backup.drivers.dimensiondata import DEFAULT_BACKUP_PLAN

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

    def test_create_target_DEFAULT(self):
        DimensionDataMockHttp.type = 'DEFAULT'
        target = self.driver.create_target(
            'name',
            'e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(target.id, 'ee7c4b64-f7af-4a4f-8384-be362273530f')
        self.assertEqual(target.address, 'e75ead52-692f-4314-8725-c8a4f4d13a87')

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
        extra = {'servicePlan': 'Essentials'}
        new_target = self.driver.update_target(target, extra=extra)
        self.assertEqual(new_target.extra['servicePlan'], 'Essentials')

    def test_update_target_DEFAULT(self):
        DimensionDataMockHttp.type = 'DEFAULT'
        target = 'e75ead52-692f-4314-8725-c8a4f4d13a87'
        self.driver.update_target(target)

    def test_update_target_STR(self):
        target = 'e75ead52-692f-4314-8725-c8a4f4d13a87'
        extra = {'servicePlan': 'Essentials'}
        new_target = self.driver.update_target(target, extra=extra)
        self.assertEqual(new_target.extra['servicePlan'], 'Essentials')

    def test_delete_target(self):
        target = self.driver.list_targets()[0]
        self.assertTrue(self.driver.delete_target(target))

    def test_ex_add_client_to_target(self):
        target = self.driver.list_targets()[0]
        client = self.driver.ex_list_available_client_types(target)[0]
        storage_policy = self.driver.ex_list_available_storage_policies(target)[0]
        schedule_policy = self.driver.ex_list_available_schedule_policies(target)[0]
        self.assertTrue(
            self.driver.ex_add_client_to_target(target, client, storage_policy,
                                                schedule_policy, 'ON_FAILURE', 'nobody@example.com')
        )

    def test_ex_add_client_to_target_STR(self):
        self.assertTrue(
            self.driver.ex_add_client_to_target('e75ead52-692f-4314-8725-c8a4f4d13a87', 'FA.Linux', '14 Day Storage Policy',
                                                '12AM - 6AM', 'ON_FAILURE', 'nobody@example.com')
        )

    def test_ex_get_backup_details_for_target(self):
        target = self.driver.list_targets()[0]
        response = self.driver.ex_get_backup_details_for_target(target)
        self.assertEqual(response.service_plan, 'Enterprise')
        client = response.clients[0]
        self.assertEqual(client.id, '30b1ff76-c76d-4d7c-b39d-3b72be0384c8')
        self.assertEqual(client.type.type, 'FA.Linux')
        self.assertEqual(client.running_job.progress, 5)
        self.assertTrue(isinstance(client.running_job, BackupTargetJob))
        self.assertEqual(len(client.alert.notify_list), 2)
        self.assertTrue(isinstance(client.alert.notify_list, list))

    def test_ex_get_backup_details_for_target_NOBACKUP(self):
        target = self.driver.list_targets()[0].address
        DimensionDataMockHttp.type = 'NOBACKUP'
        response = self.driver.ex_get_backup_details_for_target(target)
        self.assertTrue(response is None)

    def test_ex_cancel_target_job(self):
        target = self.driver.list_targets()[0]
        response = self.driver.ex_get_backup_details_for_target(target)
        client = response.clients[0]
        self.assertTrue(isinstance(client.running_job, BackupTargetJob))
        success = client.running_job.cancel()
        self.assertTrue(success)

    def test_ex_cancel_target_job_with_extras(self):
        success = self.driver.cancel_target_job(
            None,
            ex_client='30b1ff76_c76d_4d7c_b39d_3b72be0384c8',
            ex_target='e75ead52_692f_4314_8725_c8a4f4d13a87'
        )
        self.assertTrue(success)

    def test_ex_cancel_target_job_FAIL(self):
        DimensionDataMockHttp.type = 'FAIL'
        with self.assertRaises(DimensionDataAPIException) as context:
            self.driver.cancel_target_job(
                None,
                ex_client='30b1ff76_c76d_4d7c_b39d_3b72be0384c8',
                ex_target='e75ead52_692f_4314_8725_c8a4f4d13a87'
            )
        self.assertEqual(context.exception.code, 'ERROR')

    """Test a backup info for a target that does not have a client"""
    def test_ex_get_backup_details_for_target_NO_CLIENT(self):
        DimensionDataMockHttp.type = 'NOCLIENT'
        response = self.driver.ex_get_backup_details_for_target('e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(response.service_plan, 'Essentials')
        self.assertEqual(len(response.clients), 0)

    """Test a backup details that has a client, but no alerting or running jobs"""
    def test_ex_get_backup_details_for_target_NO_JOB_OR_ALERT(self):
        DimensionDataMockHttp.type = 'NOJOB'
        response = self.driver.ex_get_backup_details_for_target('e75ead52-692f-4314_8725-c8a4f4d13a87')
        self.assertEqual(response.service_plan, 'Enterprise')
        self.assertTrue(isinstance(response.clients, list))
        self.assertEqual(len(response.clients), 1)
        client = response.clients[0]
        self.assertEqual(client.id, '30b1ff76-c76d-4d7c-b39d-3b72be0384c8')
        self.assertEqual(client.type.type, 'FA.Linux')
        self.assertIsNone(client.running_job)
        self.assertIsNone(client.alert)

    """Test getting backup info for a server that doesn't exist"""
    def test_ex_get_backup_details_for_target_DISABLED(self):
        DimensionDataMockHttp.type = 'DISABLED'
        with self.assertRaises(DimensionDataAPIException) as context:
            self.driver.ex_get_backup_details_for_target('e75ead52-692f-4314-8725-c8a4f4d13a87')
        self.assertEqual(context.exception.code, 'ERROR')
        self.assertEqual(context.exception.msg, 'Server e75ead52-692f-4314-8725-c8a4f4d13a87 has not been provisioned for backup')

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

    def test_ex_remove_client_from_target(self):
        target = self.driver.list_targets()[0]
        client = self.driver.ex_get_backup_details_for_target('e75ead52-692f-4314-8725-c8a4f4d13a87').clients[0]
        self.assertTrue(self.driver.ex_remove_client_from_target(target, client))

    def test_ex_remove_client_from_target_STR(self):
        self.assertTrue(
            self.driver.ex_remove_client_from_target(
                'e75ead52-692f-4314-8725-c8a4f4d13a87',
                '30b1ff76-c76d-4d7c-b39d-3b72be0384c8'
            )
        )

    def test_ex_remove_client_from_target_FAIL(self):
        DimensionDataMockHttp.type = 'FAIL'
        with self.assertRaises(DimensionDataAPIException) as context:
            self.driver.ex_remove_client_from_target(
                'e75ead52-692f-4314-8725-c8a4f4d13a87',
                '30b1ff76-c76d-4d7c-b39d-3b72be0384c8'
            )
        self.assertEqual(context.exception.code, 'ERROR')
        self.assertTrue('Backup Client is currently performing another operation' in context.exception.msg)

    def test_priv_target_to_target_address(self):
        target = self.driver.list_targets()[0]
        self.assertEqual(
            self.driver._target_to_target_address(target),
            'e75ead52-692f-4314-8725-c8a4f4d13a87'
        )

    def test_priv_target_to_target_address_STR(self):
        self.assertEqual(
            self.driver._target_to_target_address('e75ead52-692f-4314-8725-c8a4f4d13a87'),
            'e75ead52-692f-4314-8725-c8a4f4d13a87'
        )

    def test_priv_target_to_target_address_TYPEERROR(self):
        with self.assertRaises(TypeError):
            self.driver._target_to_target_address([1, 2, 3])

    def test_priv_client_to_client_id(self):
        client = self.driver.ex_get_backup_details_for_target('e75ead52-692f-4314-8725-c8a4f4d13a87').clients[0]
        self.assertEqual(
            self.driver._client_to_client_id(client),
            '30b1ff76-c76d-4d7c-b39d-3b72be0384c8'
        )

    def test_priv_client_to_client_id_STR(self):
        self.assertEqual(
            self.driver._client_to_client_id('30b1ff76-c76d-4d7c-b39d-3b72be0384c8'),
            '30b1ff76-c76d-4d7c-b39d-3b72be0384c8'
        )

    def test_priv_client_to_client_id_TYPEERROR(self):
        with self.assertRaises(TypeError):
            self.driver._client_to_client_id([1, 2, 3])


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

    def _oec_0_9_myaccount_DEFAULT(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_INPROGRESS(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_FAIL(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_NOCLIENT(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_DISABLED(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_NOJOB(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_e75ead52_692f_4314_8725_c8a4f4d13a87(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_server_e75ead52_692f_4314_8725_c8a4f4d13a87.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_e75ead52_692f_4314_8725_c8a4f4d13a87_DEFAULT(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_server_e75ead52_692f_4314_8725_c8a4f4d13a87_DEFAULT.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_e75ead52_692f_4314_8725_c8a4f4d13a87_NOCLIENT(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_server_e75ead52_692f_4314_8725_c8a4f4d13a87_DEFAULT.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_e75ead52_692f_4314_8725_c8a4f4d13a87_NOJOB(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_server_e75ead52_692f_4314_8725_c8a4f4d13a87_DEFAULT.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_e75ead52_692f_4314_8725_c8a4f4d13a87_DISABLED(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_server_e75ead52_692f_4314_8725_c8a4f4d13a87_DEFAULT.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server(self, method, url, body, headers):
        body = self.fixtures.load(
            'server_server.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_type(self, method, url, body, headers):
        body = self.fixtures.load(
            '_backup_client_type.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_storagePolicy(
            self, method, url, body, headers):
        body = self.fixtures.load(
            '_backup_client_storagePolicy.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_schedulePolicy(
            self, method, url, body, headers):
        body = self.fixtures.load(
            '_backup_client_schedulePolicy.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client(
            self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                '_backup_client_SUCCESS_PUT.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        else:
            raise ValueError("Unknown Method {0}".format(method))

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_NOCLIENT(
            self, method, url, body, headers):
        # only gets here are implemented
        # If we get any other method something has gone wrong
        assert(method == 'GET')
        body = self.fixtures.load(
            '_backup_INFO_NOCLIENT.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_DISABLED(
            self, method, url, body, headers):
        # only gets here are implemented
        # If we get any other method something has gone wrong
        assert(method == 'GET')
        body = self.fixtures.load(
            '_backup_INFO_DISABLED.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_NOJOB(
            self, method, url, body, headers):
        # only gets here are implemented
        # If we get any other method something has gone wrong
        assert(method == 'GET')
        body = self.fixtures.load(
            '_backup_INFO_NOJOB.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_DEFAULT(
            self, method, url, body, headers):
        if method != 'POST':
            raise InvalidRequestError('Only POST is accepted for this test')
        request = ET.fromstring(body)
        service_plan = request.get('servicePlan')
        if service_plan != DEFAULT_BACKUP_PLAN:
            raise InvalidRequestError('The default plan %s should have been passed in.  Not %s' % (DEFAULT_BACKUP_PLAN, service_plan))
        body = self.fixtures.load(
            '_backup_ENABLE.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup(
            self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                '_backup_ENABLE.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])
        elif method == 'GET':
            if url.endswith('disable'):
                body = self.fixtures.load(
                    '_backup_DISABLE.xml')
                return (httplib.OK, body, {}, httplib.responses[httplib.OK])
            body = self.fixtures.load(
                '_backup_INFO.xml')
            return (httplib.OK, body, {}, httplib.responses[httplib.OK])

        else:
            raise ValueError("Unknown Method {0}".format(method))

    def _caas_2_3_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_server_e75ead52_692f_4314_8725_c8a4f4d13a87_NOBACKUP(
            self, method, url, body, headers):
        assert(method == 'GET')
        body = self.fixtures.load('server_server_NOBACKUP.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_EXISTS(
            self, method, url, body, headers):
        # only POSTs are implemented
        # If we get any other method something has gone wrong
        assert(method == 'POST')
        body = self.fixtures.load(
            '_backup_EXISTS.xml')
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_modify(
            self, method, url, body, headers):
        request = ET.fromstring(body)
        service_plan = request.get('servicePlan')
        if service_plan != 'Essentials':
            raise InvalidRequestError("Expected Essentials backup plan in request")
        body = self.fixtures.load('_backup_modify.xml')

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_modify_DEFAULT(
            self, method, url, body, headers):
        request = ET.fromstring(body)
        service_plan = request.get('servicePlan')
        if service_plan != DEFAULT_BACKUP_PLAN:
            raise InvalidRequestError("Expected % backup plan in test" % DEFAULT_BACKUP_PLAN)
        body = self.fixtures.load('_backup_modify.xml')

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_30b1ff76_c76d_4d7c_b39d_3b72be0384c8(
            self, method, url, body, headers):
        if url.endswith('disable'):
            body = self.fixtures.load(
                ('_remove_backup_client.xml')
            )
        elif url.endswith('cancelJob'):
            body = self.fixtures.load(
                (''
                 '_backup_client_30b1ff76_c76d_4d7c_b39d_3b72be0384c8_cancelJob.xml')
            )
        else:
            raise ValueError("Unknown URL: %s" % url)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_server_e75ead52_692f_4314_8725_c8a4f4d13a87_backup_client_30b1ff76_c76d_4d7c_b39d_3b72be0384c8_FAIL(
            self, method, url, body, headers):
        if url.endswith('disable'):
            body = self.fixtures.load(
                ('_remove_backup_client_FAIL.xml')
            )
        elif url.endswith('cancelJob'):
            body = self.fixtures.load(
                (''
                 '_backup_client_30b1ff76_c76d_4d7c_b39d_3b72be0384c8_cancelJob_FAIL.xml')
            )
        else:
            raise ValueError("Unknown URL: %s" % url)
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
