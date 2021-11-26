from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

cls = get_driver(Provider.DIGITALOCEAN_SPACES)

driver = cls(key="DO_ACCESS_KEY", secret="DO_SECRET_KEY")
