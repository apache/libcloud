import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.ONEANDONE)
drv = cls(key=os.environ.get("ONEANDONE_TOKEN"))

try:
    public_ip = drv.ex_create_public_ip(type="IPV4")
    print(public_ip)
except Exception as e:
    print(e)
