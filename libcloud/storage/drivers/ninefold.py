from libcloud.storage.providers import Provider
from libcloud.storage.drivers.atmos import AtmosDriver

class NinefoldStorageDriver(AtmosDriver):
    host = 'api.ninefold.com'
    path = '/storage/v1.0'

    type = Provider.NINEFOLD
    name = 'Ninefold'
