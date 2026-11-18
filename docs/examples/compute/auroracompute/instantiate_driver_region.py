from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.drivers.auroracompute import AuroraComputeRegion

apikey = "mykey"
secretkey = "mysecret"

Driver = get_driver(Provider.AURORACOMPUTE)
conn = Driver(key=apikey, secret=secretkey, region=AuroraComputeRegion.MIA)
