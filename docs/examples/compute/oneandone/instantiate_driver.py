from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# First we need to instantiate desired libcoud driver.
cls = get_driver(Provider.ONEANDONE)

token = "your_token"
# Then pass in your security token
drv = cls(key=token)
