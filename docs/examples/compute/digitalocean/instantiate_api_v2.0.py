from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.DIGITAL_OCEAN)

driver = cls('access token', api_version='v2')
# Note: Driver defaults to v2.0 so api_version argument can be omitted and the
# following is the same
driver = cls('access token')
