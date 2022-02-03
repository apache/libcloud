from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls("username", "password", region="zrh", api_version="1.0")
