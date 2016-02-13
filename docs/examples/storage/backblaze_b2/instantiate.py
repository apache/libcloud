from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

account_id = 'XXXXXX'
application_key = 'YYYYYY'

cls = get_driver(Provider.BACKBLAZE_B2)
driver = cls(account_id, application_key)
