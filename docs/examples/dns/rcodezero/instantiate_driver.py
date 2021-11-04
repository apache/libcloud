from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

cls = get_driver(Provider.RCODEZERO)

APIKEY_RCODEZERO = "secrettoken"
API_HOST = "my.rcodezero.at"

cls = get_driver(Provider.RCODEZERO)
driver = cls(APIKEY_RCODEZERO, host=API_HOST)
