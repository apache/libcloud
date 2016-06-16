# from libcloud.compute.types import Provider
# from libcloud.compute.providers import get_driver
# from libcloud import compute
# from libcloud import loadbalancer
#
# from libcloud.loadbalancer.base import Algorithm
# from libcloud.loadbalancer.drivers.dimensiondata \
#     import DimensionDataLBDriver as DimensionData
#
# cls = compute.providers.get_driver(compute.types.Provider.DIMENSIONDATA)
# driver = cls('maglanam', 'W0cr3pu5!')
# image = driver.list_images(location='NA12')[0]
# node = driver.create_node(
#         name='mmaglana',
#         image='de4b3002-3a7d-4b85-9dfd-6934391e4e8a',
#         auth='321y0k4M',
#         ex_description='mmaglana deleteme',
#         ex_network_domain='8c787b6e-a012-4059-a315-230893441a7c',
#         ex_vlan='71ea07e3-8c24-41b6-97b6-ed6e4ea21b4a',
#         # ex_primary_ipv4='10.0.3.99',
#         ex_primary_dns='10.0.3.9',
#         ex_secondary_dns='8.8.8.8',
#         ex_is_started=True)

from libcloud.loadbalancer.base import Algorithm
from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver

cls = get_driver(Provider.DIMENSIONDATA)
driver = cls('maglanam', 'W0cr3pu5!')
driver.ex_set_current_network_domain('8c787b6e-a012-4059-a315-230893441a7c')
balancer = driver.create_balancer(
    name='xxxxtestxxxx',
    protocol='http',
    algorithm=Algorithm.ROUND_ROBIN,
    members=[])
