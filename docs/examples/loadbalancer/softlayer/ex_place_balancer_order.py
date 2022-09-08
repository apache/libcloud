from libcloud.compute.base import NodeLocation
from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver

USER_NAME = "your user name"
SECRET_KEY = "your secret key"

cls = get_driver(Provider.SOFTLAYER)
driver = cls(key=USER_NAME, secret=SECRET_KEY)

# order loadbalancer with a capacity of 50 connections
CAPACITY = 50
# create the balancer in Dallas 5 datacenter
DATACENTER = "dal05"

# select package to create balancer from
packages = driver.ex_list_balancer_packages()
lb_package = [p for p in packages if p.capacity == CAPACITY][0]

driver.ex_place_balancer_order(lb_package, NodeLocation(DATACENTER, None, None, None))

print("Successfully submitted oder request, from package %s" % (lb_package))
