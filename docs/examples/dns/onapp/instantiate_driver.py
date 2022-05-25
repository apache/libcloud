from libcloud.dns.types import Provider
from libcloud.dns.providers import get_driver

username = "your account username"
password = "your account password"
host = "onapp.test"

cls = get_driver(Provider.ONAPP)
driver = cls(key=username, secret=password, host=host)
