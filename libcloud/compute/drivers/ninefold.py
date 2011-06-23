from libcloud.compute.providers import Provider

from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver

class NinefoldNodeDriver(CloudStackNodeDriver):
    "Driver for Ninefold's Compute platform."

    host = 'api.ninefold.com'
    path = '/compute/v1.0/'

    type = Provider.NINEFOLD
    name = 'Ninefold'
