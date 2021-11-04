from pprint import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.NTTA)
driver = cls("my username", "my password", region="ntta-na")

pprint(driver.list_nodes())
