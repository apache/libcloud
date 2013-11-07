from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)

# "api_version" argument can be left out since it defaults to 2.0
driver = cls('username', 'password', region='zrh', api_version='2.0')
