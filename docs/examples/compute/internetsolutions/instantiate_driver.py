from pprint import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.INTERNETSOLUTIONS)
driver = cls("my username", "my password", region="is-af")

pprint(driver.list_nodes())
