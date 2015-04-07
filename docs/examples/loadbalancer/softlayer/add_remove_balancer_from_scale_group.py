import time

from libcloud.compute.base import NodeLocation
from libcloud.compute.types import AutoScaleTerminationPolicy

from libcloud.loadbalancer.base import Algorithm

from libcloud.loadbalancer.types import Provider as lb_provider
from libcloud.loadbalancer.providers import get_driver as lb_get_driver
lb_cls = lb_get_driver(lb_provider.SOFTLAYER)

from libcloud.compute.types import Provider as provider
from libcloud.compute.providers import get_driver
cls = get_driver(provider.SOFTLAYER)

USER_NAME = 'your user name'
SECRET_KEY = 'your secret key'

DATACENTER = 'dal05'
REGION = 'na-usa-central-1'

CAPACITY = 50

FRONTEND_PORT = 80
BACKEND_PORT1 = 8080
BACKEND_PORT2 = 100

lb_driver = lb_cls(USER_NAME, SECRET_KEY)
driver = cls(USER_NAME, SECRET_KEY)

# select package to create balancer from
packages = lb_driver.ex_list_balancer_packages()
lb_package = [p for p in packages if p.capacity == CAPACITY][0]

print 'Creating balancer from package %s' % lb_package

lb_driver.ex_place_balancer_order(lb_package, NodeLocation(DATACENTER,
                                  None, None, None))
time.sleep(60)

# find our balancer (assuming single balancer in our datacenter with
# given capacity)
balancers = lb_driver.list_balancers()
balancer = [b for b in balancers if
            b.extra.get('datacenter') == DATACENTER and
            b.extra.get('connection_limit') == CAPACITY][0]

print 'Created balancer: %s' % balancer

# add balancer with front-end port, protocol and algorithm
lb_driver.ex_add_service_group(balancer,
                               port=FRONTEND_PORT,
                               protocol='http',
                               algorithm=Algorithm.SHORTEST_RESPONSE)
balancer = lb_driver.get_balancer(balancer.id)
print 'Added front-end port: %s to balancer: %s' % (FRONTEND_PORT,
                                                    balancer)
# create scale group with balancer and backend port is 8080
# Note: scale group members must be in same datacenter balancer is
group = driver.create_auto_scale_group(
    name='libcloud-group', min_size=1, max_size=5, cooldown=300,
    location=NodeLocation(DATACENTER, None, None, None),
    termination_policies=AutoScaleTerminationPolicy.CLOSEST_TO_NEXT_CHARGE,
    balancer=balancer, ex_service_port=BACKEND_PORT1, ex_region=REGION)

print 'Created scale group: %s' % group
time.sleep(60)

driver.ex_detach_balancer_from_auto_scale_group(group, balancer)
print 'Detached balancer: %s from scale group: %s' % (balancer, group)
time.sleep(30)


driver.ex_attach_balancer_to_auto_scale_group(group=group,
                                              balancer=balancer,
                                              ex_service_port=BACKEND_PORT2)

print 'Attached balancer: %s to scale group: %s with backend port %s' %\
    (balancer, group, BACKEND_PORT2)
time.sleep(30)


driver.delete_auto_scale_group(group=group)
print 'Deleted scale group: %s' % group


# remove front-end port
lb_driver.ex_delete_service_group(balancer=balancer, port=80)
balancer = lb_driver.get_balancer(balancer.id)
print 'Removed front-end port: %s from balancer: %s' % (FRONTEND_PORT,
                                                        balancer)


balancer.destroy()
print 'Deleted balancer: %s' % balancer
