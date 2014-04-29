from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.RACKSPACE_FIRST_GEN)

driver_us = cls('username', 'api key', region='us')
driver_uk = cls('username', 'api key', region='uk')
