from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.PROFIT_BRICKS)
driver = cls("username", "password")
