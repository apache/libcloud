from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.KAMATERA)
driver = cls("KAMATERA API CLIENT ID", "KAMATERA API SECRET")
