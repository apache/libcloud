from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ACCESS_ID = 'your access id'
SECRET_KEY = 'your secret key'

cls = get_driver(Provider.ELB)
driver = cls(key=ACCESS_ID, secret=SECRET_KEY)

print(driver.list_balancers())

# create load balancer policy
driver.ex_create_balancer_policy(
    name='MyLB',
    policy_name='EnableProxyProtocol',
    policy_type='ProxyProtocolPolicyType',
    policy_attributes={'ProxyProtocol': 'true'})
