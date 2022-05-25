from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

key_id = "XXXXXX"
application_key = "YYYYYY"

cls = get_driver(Provider.BACKBLAZE_B2)
driver = cls(key_id, application_key)
