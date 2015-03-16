from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.DIGITAL_OCEAN)
driver = cls('client id', 'api key', api_version='v1')
