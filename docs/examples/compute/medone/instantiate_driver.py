from pprint import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.MEDONE)
driver = cls("my username", "my password", region="med1-il")

pprint(driver.list_nodes())
