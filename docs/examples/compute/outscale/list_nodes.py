from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

key = "my_key"
secret = "my_secret"
region = "eu-west-2"
service = "api"

Driver = get_driver(Provider.OUTSCALE)
driver = Driver(key=key, secret=secret, region=region, service=service)

nodes = driver.list_nodes()

print(nodes)
