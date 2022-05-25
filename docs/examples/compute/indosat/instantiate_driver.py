from pprint import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.INDOSAT)
driver = cls("my username", "my password", region="indosat-id")

pprint(driver.list_nodes())
