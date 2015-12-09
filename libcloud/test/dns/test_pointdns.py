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

from libcloud.utils.py3 import httplib

from libcloud.dns.types import RecordType
from libcloud.dns.types import ZoneDoesNotExistError
from libcloud.dns.types import RecordDoesNotExistError
from libcloud.dns.drivers.pointdns import PointDNSDriver
from libcloud.dns.drivers.pointdns import PointDNSException

from libcloud.test import MockHttp
from libcloud.test.file_fixtures import DNSFileFixtures
from libcloud.test.secrets import DNS_PARAMS_POINTDNS


class PointDNSTests(unittest.TestCase):
    def setUp(self):
        PointDNSDriver.connectionCls.conn_classes = (
            None, PointDNSMockHttp)
        PointDNSMockHttp.type = None
        self.driver = PointDNSDriver(*DNS_PARAMS_POINTDNS)

    def assertHasKeys(self, dictionary, keys):
        for key in keys:
            self.assertTrue(key in dictionary, 'key "%s" not in dictionary' %
                            (key))

    def test_list_record_types(self):
        record_types = self.driver.list_record_types()
        self.assertEqual(len(record_types), 10)
        self.assertTrue(RecordType.A in record_types)
        self.assertTrue(RecordType.AAAA in record_types)
        self.assertTrue(RecordType.ALIAS in record_types)
        self.assertTrue(RecordType.CNAME in record_types)
        self.assertTrue(RecordType.MX in record_types)
        self.assertTrue(RecordType.NS in record_types)
        self.assertTrue(RecordType.PTR in record_types)
        self.assertTrue(RecordType.SRV in record_types)
        self.assertTrue(RecordType.SSHFP in record_types)
        self.assertTrue(RecordType.TXT in record_types)

    def test_list_zones_success(self):
        PointDNSMockHttp.type = 'GET'
        zones = self.driver.list_zones()
        self.assertEqual(len(zones), 2)

        zone1 = zones[0]
        self.assertEqual(zone1.id, '1')
        self.assertEqual(zone1.type, 'master')
        self.assertEqual(zone1.domain, 'example.com')
        self.assertEqual(zone1.ttl, 3600)
        self.assertHasKeys(zone1.extra, ['group', 'user-id'])

        zone2 = zones[1]
        self.assertEqual(zone2.id, '2')
        self.assertEqual(zone2.type, 'master')
        self.assertEqual(zone2.domain, 'example2.com')
        self.assertEqual(zone2.ttl, 3600)
        self.assertHasKeys(zone2.extra, ['group', 'user-id'])

    def test_list_records_success(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 2)

        record1 = records[0]
        self.assertEqual(record1.id, '141')
        self.assertEqual(record1.name, 'site.example.com')
        self.assertEqual(record1.type, RecordType.A)
        self.assertEqual(record1.data, '1.2.3.4')
        self.assertHasKeys(record1.extra, ['ttl', 'zone_id', 'aux'])

        record2 = records[1]
        self.assertEqual(record2.id, '150')
        self.assertEqual(record2.name, 'site.example1.com')
        self.assertEqual(record2.type, RecordType.A)
        self.assertEqual(record2.data, '1.2.3.6')
        self.assertHasKeys(record2.extra, ['ttl', 'zone_id', 'aux'])

    def test_get_zone_success(self):
        PointDNSMockHttp.type = 'GET'
        zone1 = self.driver.get_zone(zone_id='1')
        self.assertEqual(zone1.id, '1')
        self.assertEqual(zone1.type, 'master')
        self.assertEqual(zone1.domain, 'example.com')
        self.assertEqual(zone1.ttl, 3600)
        self.assertHasKeys(zone1.extra, ['group', 'user-id'])

    def test_get_zone_zone_not_exists(self):
        PointDNSMockHttp.type = 'GET_ZONE_NOT_EXIST'
        try:
            self.driver.get_zone(zone_id='1')
        except ZoneDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_get_record_success(self):
        PointDNSMockHttp.type = 'GET'
        record = self.driver.get_record(zone_id='1',
                                        record_id='141')
        self.assertEqual(record.id, '141')
        self.assertEqual(record.name, 'site.example.com')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '1.2.3.4')
        self.assertHasKeys(record.extra, ['ttl', 'zone_id', 'aux'])

    def test_get_record_record_not_exists(self):
        PointDNSMockHttp.type = 'GET_RECORD_NOT_EXIST'
        try:
            self.driver.get_record(zone_id='1',
                                   record_id='141')
        except RecordDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_create_zone_success(self):
        PointDNSMockHttp.type = 'CREATE'
        zone = self.driver.create_zone(domain='example.com')
        self.assertEqual(zone.id, '2')
        self.assertEqual(zone.domain, 'example.com')
        self.assertEqual(zone.ttl, 3600)
        self.assertEqual(zone.type, 'master')
        self.assertHasKeys(zone.extra, ['group', 'user-id'])

    def test_create_zone_with_error(self):
        PointDNSMockHttp.type = 'CREATE_ZONE_WITH_ERROR'
        try:
            self.driver.create_zone(domain='example.com')
        except PointDNSException:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_create_record_success(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'CREATE'
        record = self.driver.create_record(name='site.example.com', zone=zone,
                                           type=RecordType.A,
                                           data='1.2.3.4')
        self.assertEqual(record.id, '143')
        self.assertEqual(record.name, 'site.example.com')
        self.assertEqual(record.type, RecordType.A)
        self.assertEqual(record.data, '1.2.3.4')
        self.assertHasKeys(record.extra, ['ttl', 'zone_id', 'aux'])

    def test_create_record_with_error(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'CREATE_WITH_ERROR'
        try:
            self.driver.create_record(name='site.example.com',
                                      zone=zone, type=RecordType.A,
                                      data='1.2.3.4')
        except PointDNSException:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_update_zone_success(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'ZONE_UPDATE'
        extra = {'user-id': 6}
        _zone = self.driver.update_zone(zone, zone.domain, zone.ttl,
                                        extra=extra)
        self.assertEqual(_zone.extra.get('user-id'), 6)

    def test_update_zone_with_error(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'UPDATE_ZONE_WITH_ERROR'
        extra = {'user-id': 6}
        try:
            self.driver.update_zone(zone, zone.domain, zone.ttl, extra=extra)
        except PointDNSException:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_update_record_success(self):
        PointDNSMockHttp.type = 'GET'
        record = self.driver.get_record(zone_id='1',
                                        record_id='141')
        PointDNSMockHttp.type = 'UPDATE'
        extra = {'ttl': 4500}
        record1 = self.driver.update_record(record=record, name='updated.com',
                                            type=RecordType.A, data='1.2.3.5',
                                            extra=extra)
        self.assertEqual(record.data, '1.2.3.4')
        self.assertEqual(record.extra.get('ttl'), 3600)
        self.assertEqual(record1.data, '1.2.3.5')
        self.assertEqual(record1.extra.get('ttl'), 4500)

    def test_update_record_with_error(self):
        PointDNSMockHttp.type = 'GET'
        record = self.driver.get_record(zone_id='1',
                                        record_id='141')
        PointDNSMockHttp.type = 'UPDATE_RECORD_WITH_ERROR'
        extra = {'ttl': 4500}
        try:
            self.driver.update_record(record=record, name='updated.com',
                                      type=RecordType.A, data='1.2.3.5',
                                      extra=extra)
        except PointDNSException:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_zone_success(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'DELETE'
        status = self.driver.delete_zone(zone=zone)
        self.assertTrue(status)

    def test_delete_zone_zone_not_exists(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'DELETE_ZONE_NOT_EXIST'
        try:
            self.driver.delete_zone(zone=zone)
        except ZoneDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_delete_record_success(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 2)
        record = records[1]
        PointDNSMockHttp.type = 'DELETE'
        status = self.driver.delete_record(record=record)
        self.assertTrue(status)

    def test_delete_record_record_not_exists(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        records = self.driver.list_records(zone=zone)
        self.assertEqual(len(records), 2)
        record = records[1]
        PointDNSMockHttp.type = 'DELETE_RECORD_NOT_EXIST'
        try:
            self.driver.delete_record(record=record)
        except RecordDoesNotExistError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_ex_list_redirects_success(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'LIST'
        redirects = self.driver.ex_list_redirects(zone)
        self.assertEqual(len(redirects), 2)

        redirect1 = redirects[0]
        self.assertEqual(redirect1.id, '36843229')
        self.assertEqual(redirect1.name, 'redirect2.domain1.com.')
        self.assertEqual(redirect1.type, '302')
        self.assertEqual(redirect1.data, 'http://other.com')
        self.assertEqual(redirect1.iframe, None)
        self.assertEqual(redirect1.query, False)
        self.assertEqual(zone, redirect1.zone)

        redirect2 = redirects[1]
        self.assertEqual(redirect2.id, '36843497')
        self.assertEqual(redirect2.name, 'redirect1.domain1.com.')
        self.assertEqual(redirect2.type, '302')
        self.assertEqual(redirect2.data, 'http://someother.com')
        self.assertEqual(redirect2.iframe, None)
        self.assertEqual(redirect2.query, False)
        self.assertEqual(zone, redirect1.zone)

    def test_ex_list_mail_redirects(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'LIST'
        mail_redirects = self.driver.ex_list_mail_redirects(zone)
        self.assertEqual(len(mail_redirects), 2)

        mail_redirect1 = mail_redirects[0]
        self.assertEqual(mail_redirect1.id, '5')
        self.assertEqual(mail_redirect1.source, 'admin')
        self.assertEqual(mail_redirect1.destination, 'user@example-site.com')
        self.assertEqual(zone, mail_redirect1.zone)

        mail_redirect2 = mail_redirects[1]
        self.assertEqual(mail_redirect2.id, '7')
        self.assertEqual(mail_redirect2.source, 'new_admin')
        self.assertEqual(mail_redirect2.destination,
                         'second.user@example-site.com')
        self.assertEqual(zone, mail_redirect2.zone)

    def test_ex_create_redirect(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'CREATE'
        redirect = self.driver.ex_create_redirect('http://other.com',
                                                  'redirect2', '302', zone,
                                                  iframe='An Iframe',
                                                  query=True)
        self.assertEqual(redirect.id, '36843229')
        self.assertEqual(redirect.name, 'redirect2.domain1.com.')
        self.assertEqual(redirect.type, '302')
        self.assertEqual(redirect.data, 'http://other.com')
        self.assertEqual(redirect.iframe, 'An Iframe')
        self.assertEqual(redirect.query, True)
        self.assertEqual(zone.id, redirect.zone.id)

    def test_ex_create_redirect_with_error(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'CREATE_WITH_ERROR'
        try:
            self.driver.ex_create_redirect('http://other.com', 'redirect2',
                                           '302', zone, iframe='An Iframe',
                                           query=True)
        except PointDNSException:
            e = sys.exc_info()[1]
            # The API actually responds with httplib.UNPROCESSABLE_ENTITY code,
            # but httplib.responses doesn't have it.
            self.assertEqual(e.http_code, httplib.METHOD_NOT_ALLOWED)
        else:
            self.fail('Exception was not thrown')

    def test_ex_create_mail_redirect(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'CREATE'
        mail_redirect = self.driver.ex_create_mail_redirect(
            'user@example-site.com', 'admin', zone)
        self.assertEqual(mail_redirect.id, '5')
        self.assertEqual(mail_redirect.source, 'admin')
        self.assertEqual(mail_redirect.destination, 'user@example-site.com')
        self.assertEqual(zone.id, mail_redirect.zone.id)

    def test_ex_create_mail_redirect_with_error(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'CREATE_WITH_ERROR'
        try:
            self.driver.ex_create_mail_redirect('user@example-site.com',
                                                'admin', zone)
        except PointDNSException:
            e = sys.exc_info()[1]
            # The API actually responds with httplib.UNPROCESSABLE_ENTITY code,
            # but httplib.responses doesn't have it.
            self.assertEqual(e.http_code, httplib.METHOD_NOT_ALLOWED)
        else:
            self.fail('Exception was not thrown')

    def test_ex_get_redirect(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        redirect = self.driver.ex_get_redirect(zone.id, '36843229')
        self.assertEqual(redirect.id, '36843229')
        self.assertEqual(redirect.name, 'redirect2.domain1.com.')
        self.assertEqual(redirect.type, '302')
        self.assertEqual(redirect.data, 'http://other.com')
        self.assertEqual(redirect.iframe, None)
        self.assertEqual(redirect.query, False)
        self.assertEqual(zone.id, redirect.zone.id)

    def test_ex_get_redirect_with_error(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'GET_WITH_ERROR'
        try:
            self.driver.ex_get_redirect(zone.id, '36843229')
        except PointDNSException:
            e = sys.exc_info()[1]
            # The API actually responds with httplib.UNPROCESSABLE_ENTITY code,
            # but httplib.responses doesn't have it.
            self.assertEqual(e.http_code, httplib.METHOD_NOT_ALLOWED)
        else:
            self.fail('Exception was not thrown')

    def test_ex_get_redirect_not_found(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'GET_NOT_FOUND'
        try:
            self.driver.ex_get_redirect(zone.id, '36843229')
        except PointDNSException:
            e = sys.exc_info()[1]
            self.assertEqual(e.http_code, httplib.NOT_FOUND)
            self.assertEqual(e.value, "Couldn't found redirect")
        else:
            self.fail('Exception was not thrown')

    def test_ex_get_mail_redirects(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        mail_redirect = self.driver.ex_get_mail_redirects(zone.id, '5')
        self.assertEqual(mail_redirect.id, '5')
        self.assertEqual(mail_redirect.source, 'admin')
        self.assertEqual(mail_redirect.destination, 'user@example-site.com')
        self.assertEqual(zone.id, mail_redirect.zone.id)

    def test_ex_get_mail_redirects_with_error(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        PointDNSMockHttp.type = 'GET_WITH_ERROR'
        try:
            self.driver.ex_get_mail_redirects(zone.id, '5')
        except PointDNSException:
            e = sys.exc_info()[1]
            # The API actually responds with httplib.UNPROCESSABLE_ENTITY code,
            # but httplib.responses doesn't have it.
            self.assertEqual(e.http_code, httplib.METHOD_NOT_ALLOWED)
        else:
            self.fail('Exception was not thrown')

    def test_ex_update_redirect(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        redirect = self.driver.ex_get_redirect(zone.id, '36843229')
        PointDNSMockHttp.type = 'UPDATE'
        _redirect = self.driver.ex_update_redirect(
            redirect, 'http://updatedother.com', 'redirect3', '302')
        self.assertEqual(_redirect.id, '36843229')
        self.assertEqual(_redirect.name, 'redirect3.domain1.com.')
        self.assertEqual(_redirect.type, '302')
        self.assertEqual(_redirect.data, 'http://updatedother.com')
        self.assertEqual(_redirect.iframe, None)
        self.assertEqual(_redirect.query, False)
        self.assertEqual(zone.id, _redirect.zone.id)

    def test_ex_update_redirect_with_error(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        redirect = self.driver.ex_get_redirect(zone.id, '36843229')
        PointDNSMockHttp.type = 'UPDATE_WITH_ERROR'
        try:
            self.driver.ex_update_redirect(
                redirect, 'http://updatedother.com', 'redirect3', '302')
        except PointDNSException:
            e = sys.exc_info()[1]
            # The API actually responds with httplib.UNPROCESSABLE_ENTITY code,
            # but httplib.responses doesn't have it.
            self.assertEqual(e.http_code, httplib.METHOD_NOT_ALLOWED)
        else:
            self.fail('Exception was not thrown')

    def test_ex_update_mail_redirect(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        mailredirect = self.driver.ex_get_mail_redirects(zone.id, '5')
        PointDNSMockHttp.type = 'UPDATE'
        _mailredirect = self.driver.ex_update_mail_redirect(
            mailredirect, 'new_user@example-site.com', 'new_admin')
        self.assertEqual(_mailredirect.id, '5')
        self.assertEqual(_mailredirect.source, 'new_admin')
        self.assertEqual(_mailredirect.destination,
                         'new_user@example-site.com')
        self.assertEqual(zone.id, _mailredirect.zone.id)

    def test_ex_update_mail_redirect_with_error(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        mailredirect = self.driver.ex_get_mail_redirects(zone.id, '5')
        PointDNSMockHttp.type = 'UPDATE_WITH_ERROR'
        try:
            self.driver.ex_update_mail_redirect(
                mailredirect, 'new_user@example-site.com', 'new_admin')
        except PointDNSException:
            e = sys.exc_info()[1]
            # The API actually responds with httplib.UNPROCESSABLE_ENTITY code,
            # but httplib.responses doesn't have it.
            self.assertEqual(e.http_code, httplib.METHOD_NOT_ALLOWED)
        else:
            self.fail('Exception was not thrown')

    def test_ex_delete_redirect(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        redirect = self.driver.ex_get_redirect(zone.id, '36843229')
        PointDNSMockHttp.type = 'DELETE'
        status = self.driver.ex_delete_redirect(redirect)
        self.assertTrue(status)

    def test_ex_delete_redirect_with_error(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        redirect = self.driver.ex_get_redirect(zone.id, '36843229')
        PointDNSMockHttp.type = 'DELETE_WITH_ERROR'
        try:
            self.driver.ex_delete_redirect(redirect)
        except PointDNSException:
            e = sys.exc_info()[1]
            # The API actually responds with httplib.UNPROCESSABLE_ENTITY code,
            # but httplib.responses doesn't have it.
            self.assertEqual(e.http_code, httplib.METHOD_NOT_ALLOWED)
        else:
            self.fail('Exception was not thrown')

    def test_ex_delete_redirect_not_found(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        redirect = self.driver.ex_get_redirect(zone.id, '36843229')
        PointDNSMockHttp.type = 'DELETE_NOT_FOUND'
        try:
            self.driver.ex_delete_redirect(redirect)
        except PointDNSException:
            e = sys.exc_info()[1]
            self.assertEqual(e.http_code, httplib.NOT_FOUND)
            self.assertEqual(e.value, "Couldn't found redirect")
        else:
            self.fail('Exception was not thrown')

    def test_ex_delete_mail_redirect(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        mailredirect = self.driver.ex_get_mail_redirects(zone.id, '5')
        PointDNSMockHttp.type = 'DELETE'
        status = self.driver.ex_delete_mail_redirect(mailredirect)
        self.assertTrue(status)

    def test_ex_delete_mail_redirect_with_error(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        mailredirect = self.driver.ex_get_mail_redirects(zone.id, '5')
        PointDNSMockHttp.type = 'DELETE_WITH_ERROR'
        try:
            self.driver.ex_delete_mail_redirect(mailredirect)
        except PointDNSException:
            e = sys.exc_info()[1]
            # The API actually responds with httplib.UNPROCESSABLE_ENTITY code,
            # but httplib.responses doesn't have it.
            self.assertEqual(e.http_code, httplib.METHOD_NOT_ALLOWED)
        else:
            self.fail('Exception was not thrown')

    def test_ex_delete_mail_redirect_not_found(self):
        PointDNSMockHttp.type = 'GET'
        zone = self.driver.list_zones()[0]
        mailredirect = self.driver.ex_get_mail_redirects(zone.id, '5')
        PointDNSMockHttp.type = 'DELETE_NOT_FOUND'
        try:
            self.driver.ex_delete_mail_redirect(mailredirect)
        except PointDNSException:
            e = sys.exc_info()[1]
            self.assertEqual(e.http_code, httplib.NOT_FOUND)
            self.assertEqual(e.value, "Couldn't found mail redirect")
        else:
            self.fail('Exception was not thrown')


class PointDNSMockHttp(MockHttp):
    fixtures = DNSFileFixtures('pointdns')

    def _zones_GET(self, method, url, body, headers):
        body = self.fixtures.load('_zones_GET.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_CREATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_CREATE_ZONE_WITH_ERROR(self, method, url, body, headers):
        body = self.fixtures.load('error.json')
        return (httplib.PAYMENT_REQUIRED, body, {},
                httplib.responses[httplib.PAYMENT_REQUIRED])

    def _zones_1_GET(self, method, url, body, headers):
        body = self.fixtures.load('_zones_GET_1.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_ZONE_UPDATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_ZONE_UPDATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_UPDATE_ZONE_WITH_ERROR(self, method, url, body, headers):
        body = self.fixtures.load('error.json')
        return (httplib.PAYMENT_REQUIRED, body, {},
                httplib.responses[httplib.PAYMENT_REQUIRED])

    def _zones_1_GET_ZONE_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load('not_found.json')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _zones_example_com_UPDATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_example_com_UPDATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_DELETE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_DELETE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_DELETE_ZONE_NOT_EXIST(self, method, url, body, headers):
        body = self.fixtures.load('not_found.json')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _zones_1_records_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_example_com_records_CREATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_records_CREATE_WITH_ERROR(self, method, url, body, headers):
        body = self.fixtures.load('error.json')
        return (httplib.PAYMENT_REQUIRED, body, {},
                httplib.responses[httplib.PAYMENT_REQUIRED])

    def _zones_1_records_GET(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_records_GET.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_records_141_GET_RECORD_NOT_EXIST(self, method, url, body,
                                                  headers):
        body = self.fixtures.load('not_found.json')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _zones_1_records_141_GET(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_records_141_GET.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_records_141_UPDATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_records_141_UPDATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_records_141_UPDATE_RECORD_WITH_ERROR(self, method, url, body,
                                                      headers):
        body = self.fixtures.load('error.json')
        return (httplib.PAYMENT_REQUIRED, body, {},
                httplib.responses[httplib.PAYMENT_REQUIRED])

    def _zones_1_records_150_DELETE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_records_150_DELETE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_records_150_DELETE_RECORD_NOT_EXIST(self, method, url, body,
                                                     headers):
        body = self.fixtures.load('not_found.json')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _zones_1_redirects_LIST(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_redirects_LIST.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_mail_redirects_LIST(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_mail_redirects_LIST.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_redirects_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_redirects_CREATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_redirects_CREATE_WITH_ERROR(self, method, url, body, headers):
        body = self.fixtures.load('redirect_error.json')
        return (httplib.METHOD_NOT_ALLOWED, body, {},
                httplib.responses[httplib.METHOD_NOT_ALLOWED])

    def _zones_1_mail_redirects_CREATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_mail_redirects_CREATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_mail_redirects_CREATE_WITH_ERROR(self, method, url, body,
                                                  headers):
        body = self.fixtures.load('redirect_error.json')
        return (httplib.METHOD_NOT_ALLOWED, body, {},
                httplib.responses[httplib.METHOD_NOT_ALLOWED])

    def _zones_1_redirects_36843229_GET_WITH_ERROR(self, method, url, body,
                                                   headers):
        body = self.fixtures.load('redirect_error.json')
        return (httplib.METHOD_NOT_ALLOWED, body, {},
                httplib.responses[httplib.METHOD_NOT_ALLOWED])

    def _zones_1_redirects_36843229_GET(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_redirects_GET.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_redirects_36843229_GET_NOT_FOUND(self, method, url, body,
                                                  headers):
        body = self.fixtures.load('not_found.json')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _zones_1_mail_redirects_5_GET(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_mail_redirects_GET.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_mail_redirects_5_GET_WITH_ERROR(self, method, url, body,
                                                 headers):
        body = self.fixtures.load('redirect_error.json')
        return (httplib.METHOD_NOT_ALLOWED, body, {},
                httplib.responses[httplib.METHOD_NOT_ALLOWED])

    def _zones_1_redirects_36843229_UPDATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_redirects_UPDATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_redirects_36843229_UPDATE_WITH_ERROR(self, method, url, body,
                                                      headers):
        body = self.fixtures.load('redirect_error.json')
        return (httplib.METHOD_NOT_ALLOWED, body, {},
                httplib.responses[httplib.METHOD_NOT_ALLOWED])

    def _zones_1_mail_redirects_5_UPDATE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_mail_redirects_UPDATE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_mail_redirects_5_UPDATE_WITH_ERROR(self, method, url, body,
                                                    headers):
        body = self.fixtures.load('redirect_error.json')
        return (httplib.METHOD_NOT_ALLOWED, body, {},
                httplib.responses[httplib.METHOD_NOT_ALLOWED])

    def _zones_1_redirects_36843229_DELETE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_redirects_DELETE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_mail_redirects_5_DELETE(self, method, url, body, headers):
        body = self.fixtures.load('_zones_1_mail_redirects_DELETE.json')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _zones_1_redirects_36843229_DELETE_WITH_ERROR(self, method, url, body,
                                                      headers):
        body = self.fixtures.load('redirect_error.json')
        return (httplib.METHOD_NOT_ALLOWED, body, {},
                httplib.responses[httplib.METHOD_NOT_ALLOWED])

    def _zones_1_mail_redirects_5_DELETE_WITH_ERROR(self, method, url, body,
                                                    headers):
        body = self.fixtures.load('redirect_error.json')
        return (httplib.METHOD_NOT_ALLOWED, body, {},
                httplib.responses[httplib.METHOD_NOT_ALLOWED])

    def _zones_1_redirects_36843229_DELETE_NOT_FOUND(self, method, url, body,
                                                     headers):
        body = self.fixtures.load('not_found.json')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])

    def _zones_1_mail_redirects_5_DELETE_NOT_FOUND(self, method, url, body,
                                                   headers):
        body = self.fixtures.load('not_found.json')
        return (httplib.NOT_FOUND, body, {},
                httplib.responses[httplib.NOT_FOUND])


if __name__ == '__main__':
    sys.exit(unittest.main())
