from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver

USER_NAME = "your user name"
SECRET_KEY = "your secret key"

cls = get_driver(Provider.SOFTLAYER)
driver = cls(key=USER_NAME, secret=SECRET_KEY)

balancer = driver.list_balancers()[0]
balancer.destroy()
