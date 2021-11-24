from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

apikey = "mykey"
secretkey = "mysecret"

Driver = get_driver(Provider.AURORACOMPUTE)
conn = Driver(key=apikey, secret=secretkey)
