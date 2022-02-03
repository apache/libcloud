from libcloud.compute.providers import get_driver
from libcloud.compute.type import Provider

driver = get_driver(Provider.GRIDSCALE)

driver = driver("USER-UUID", "API-TOKEN")
