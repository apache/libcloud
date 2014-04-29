from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ACCESS_ID = 'your access id'
SECRET_KEY = 'your secret key'

cls = get_driver(Provider.ELB)
driver = cls(key=ACCESS_ID, secret=SECRET_KEY)

driver.ex_set_balancer_policies_backend_server(
    name='MyLB',
    port=80,
    policies=['MyDurationStickyPolicy'])
