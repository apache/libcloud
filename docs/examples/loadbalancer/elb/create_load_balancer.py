from libcloud.loadbalancer.base import Member, Algorithm
from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver

ACCESS_ID = "your access id"
SECRET_KEY = "your secret key"

cls = get_driver(Provider.ELB)
driver = cls(key=ACCESS_ID, secret=SECRET_KEY)

print(driver.list_balancers())

# members associated with the load balancer
members = (Member(None, "192.168.88.1", 8000), Member(None, "192.168.88.2", 8080))
new_balancer = driver.create_balancer(
    name="MyLB",
    algorithm=Algorithm.ROUND_ROBIN,
    port=80,
    protocol="http",
    members=members,
)

print(new_balancer)
