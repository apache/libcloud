from libcloud.compute.type import Provider
from libcloud.compute.providers import get_driver

driver = get_driver(Provider.GRIDSCALE)

driver = driver("USER-UUID", "API-TOKEN")
