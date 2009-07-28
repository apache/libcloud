import unittest

from libcloud.providers import DRIVERS, get_driver, connect
from libcloud.types import ProviderCreds, InvalidCredsException, Provider
from libcloud.interface import INodeDriver
from zope.interface.verify import verifyObject
from zope.interface.exceptions import BrokenImplementation

class BaseTests(unittest.TestCase):
    
    def test_drivers_interface(self):
        failures = []
        for driver in DRIVERS:
            creds = ProviderCreds(driver, 'foo', 'bar')
            try:
                verifyObject(INodeDriver, get_driver(driver)(creds))
            except BrokenImplementation:
                failures.append(DRIVERS[driver][1])

        if failures:
            self.fail('the following drivers do not support the \
                       INodeDriver interface: %s' % (', '.join(failures)))

    def test_invalid_creds(self):
        failures = []
        for driver in DRIVERS:
            if driver == Provider.DUMMY:
                continue
            conn = connect(driver, 'bad', 'keys')
            try:
                conn.list_nodes()
            except InvalidCredsException:
                pass
            else:
                failures.append(DRIVERS[driver][1])

        if failures:
            self.fail('the following drivers did not throw an \
                       InvalidCredsException: %s' % (', '.join(failures)))
