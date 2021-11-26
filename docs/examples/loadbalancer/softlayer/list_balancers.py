from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver

USER_NAME = "your user name"
SECRET_KEY = "your secret key"

cls = get_driver(Provider.SOFTLAYER)
driver = cls(key=USER_NAME, secret=SECRET_KEY)

balancers = driver.list_balancers()

for balancer in balancers:
    print("{} {}".format(balancer, balancer.extra))
