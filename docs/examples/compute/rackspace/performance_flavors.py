from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.RACKSPACE)
driver = cls('username', 'api key', region='iad')

sizes = driver.list_sizes()

performance_sizes = [size for size in sizes if 'performance' in size.id]

for size in performance_sizes:
    print(size)
