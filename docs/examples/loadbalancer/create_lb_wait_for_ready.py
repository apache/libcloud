import time
from pprint import pprint

from libcloud.loadbalancer.base import Member, Algorithm
from libcloud.loadbalancer.types import State, Provider
from libcloud.loadbalancer.providers import get_driver

driver = get_driver(Provider.RACKSPACE_US)("username", "api key")

name = "test-lb"
members = (Member(None, "192.168.86.1", 8080), Member(None, "192.168.86.2", 8080))

print("Creating load balancer")
new_balancer = driver.create_balancer(
    name=name,
    algorithm=Algorithm.ROUND_ROBIN,
    port=80,
    protocol="http",
    members=members,
)

print("Waiting for load balancer to become ready...")
while True:
    balancer = driver.get_balancer(balancer_id=new_balancer.id)

    if balancer.state == State.RUNNING:
        break

    print("Load balancer not ready yet, sleeping 20 seconds...")
    time.sleep(20)

print("Load balancer is ready")
pprint(balancer)

# fetch list of members
members = balancer.list_members()
pprint(members)
