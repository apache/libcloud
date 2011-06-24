from libcloud.loadbalancer.providers import Provider

from libcloud.loadbalancer.drivers.cloudstack import CloudStackLBDriver

class NinefoldLBDriver(CloudStackLBDriver):
    "Driver for load balancers on Ninefold's Compute platform."

    host = 'api.ninefold.com'
    path = '/compute/v1.0/'

    type = Provider.NINEFOLD
    name = 'Ninefold'
