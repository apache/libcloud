from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

apikey = 'your api key'
secretkey = 'your secret key'
url = 'http://example.com/path/to/api'

Driver = get_driver(Provider.CLOUDSTACK)
conn = Driver(key=apikey, secret=secretkey, url=url)
