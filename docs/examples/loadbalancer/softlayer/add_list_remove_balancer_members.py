from libcloud.loadbalancer.base import DEFAULT_ALGORITHM, Member
from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver

USER_NAME = "your user name"
SECRET_KEY = "your secret key"

cls = get_driver(Provider.SOFTLAYER)
driver = cls(key=USER_NAME, secret=SECRET_KEY)

balancer = driver.list_balancers()[0]

if balancer.port < 0:
    # no front-end port defined, configure it with such one
    driver.ex_configure_load_balancer(
        balancer, port=80, protocol="http", algorithm=DEFAULT_ALGORITHM
    )

member1 = balancer.attach_member(Member(None, "192.168.88.1", 8000))
member2 = balancer.attach_member(Member(None, "192.168.88.2", 8080))

print(balancer.list_members())

balancer.detach_member(member1)
print(balancer.list_members())

balancer.detach_member(member2)
print(balancer.list_members())
