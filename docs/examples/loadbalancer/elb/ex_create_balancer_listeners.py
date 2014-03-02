from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ACCESS_ID = 'your access id'
SECRET_KEY = 'your secret key'

cls = get_driver(Provider.ELB)
driver = cls(key=ACCESS_ID, secret=SECRET_KEY, region='')

print driver.list_balancers()

driver.ex_create_balancer_listeners(
    name='MyLB',
    listeners=[[1024, 65533, 'HTTPS',
               'arn:aws:iam::123456789012:server-certificate/servercert']])
