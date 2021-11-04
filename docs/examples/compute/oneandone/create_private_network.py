import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.ONEANDONE)
drv = cls(key=os.environ.get("ONEANDONE_TOKEN"))

try:
    public_network = drv.ex_create_private_network(name="TestPN")
    print(public_network)
except Exception as e:
    print(e)
