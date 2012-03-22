from libcloud.loadbalancer.types import State, Provider
from libcloud.loadbalancer.providers import get_driver
from libcloud.loadbalancer.base import Member
driver = get_driver(Provider.ELB_US_WEST_OREGON)('072JVYDPZQN2W324G6R2', 'sQYX61dZoMosFcojRQXN/T6jkNitpgwduFA2bof4')
#print str(driver.list_balancers()[0].port)
membera = Member('i-00453f30', None, 80) # QA1
memberb = Member('i-70453f40', '172.16.0.2', 80) # QA2
response = driver.create_balancer('test-lb', 80, 'http'.upper(), None, (membera, memberb))
balancer = driver.get_balancer('test-lb')
print balancer.ip
print '^^got balancer^^'
print str(response)
print str(dir(balancer))
print str(driver.balancer_list_members(balancer))
driver.balancer_detach_member(balancer, membera)
balancer.detach_member(memberb)
print str(balancer.destroy())
