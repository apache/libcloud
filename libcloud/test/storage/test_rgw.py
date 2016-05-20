import sys
import unittest

from libcloud.storage.drivers.rgw import S3RGWStorageDriver
from libcloud.storage.drivers.rgw import S3RGWOutscaleStorageDriver
from libcloud.storage.drivers.rgw import S3RGWConnectionAWS4
from libcloud.storage.drivers.rgw import S3RGWConnectionAWS2

from libcloud.test.secrets import STORAGE_S3_PARAMS


class S3RGWTests(unittest.TestCase):
    driver_type = S3RGWStorageDriver
    driver_args = STORAGE_S3_PARAMS
    default_host = 'localhost'

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args,
                                signature_version='2',
                                host=self.default_host)

    def setUp(self):
        self.driver = self.create_driver()

    def test_connection_class_type(self):
        res = self.driver.connectionCls is S3RGWConnectionAWS2
        self.assertTrue(res, 'driver.connectionCls does not match!')

    def test_connection_class_host(self):
        host = self.driver.connectionCls.host
        self.assertEqual(host, self.default_host)


class S3RGWOutscaleTests(S3RGWTests):
    driver_type = S3RGWOutscaleStorageDriver
    default_host = 'osu.eu-west-2.outscale.com'

    @classmethod
    def create_driver(self):
        return self.driver_type(*self.driver_args,
                                signature_version='4')

    def test_connection_class_type(self):
        res = self.driver.connectionCls is S3RGWConnectionAWS4
        self.assertTrue(res, 'driver.connectionCls does not match!')

    def test_connection_class_host(self):
        host = self.driver.connectionCls.host
        self.assertEqual(host, self.default_host)


class S3RGWOutscaleDoubleInstanceTests(S3RGWTests):
    driver_type = S3RGWOutscaleStorageDriver
    default_host = 'osu.eu-west-2.outscale.com'

    @classmethod
    def create_driver(self):
        d = self.driver_type(*self.driver_args, signature_version='4')
        self.driver_type(*self.driver_args, signature_version='2')
        return d

    def test_connection_class_type(self):
        res = self.driver.connectionCls is S3RGWConnectionAWS4
        self.assertTrue(res, 'driver.connectionCls does not match!')

    def test_connection_class_host(self):
        host = self.driver.connectionCls.host
        self.assertEqual(host, self.default_host)


if __name__ == '__main__':
    sys.exit(unittest.main())
