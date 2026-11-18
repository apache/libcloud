from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

access_key = "XXXXXX"
secret_key = "YYYYYY"

cls = get_driver(Provider.AURORAOBJECTS)
driver = cls(access_key, secret_key)
