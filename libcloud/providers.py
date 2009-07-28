from libcloud.types import Provider, ProviderCreds

DRIVERS = {
    Provider.DUMMY:
        ('libcloud.drivers.dummy', 'DummyNodeDriver'),
    Provider.EC2:
        ('libcloud.drivers.ec2', 'EC2NodeDriver'),
    Provider.EC2_EU:
        ('libcloud.drivers.ec2', 'EC2EUNodeDriver'),
    Provider.GOGRID:
        ('libcloud.drivers.gogrid', 'GoGridNodeDriver'),
    Provider.RACKSPACE:
        ('libcloud.drivers.rackspace', 'RackspaceNodeDriver'),
    Provider.SLICEHOST:
        ('libcloud.drivers.slicehost', 'SlicehostNodeDriver'),
    Provider.VPSNET:
        ('libcloud.drivers.vpsnet', 'VPSNetNodeDriver'),
}

def get_driver(provider):
    if provider in DRIVERS:
        mod_name, driver_name = DRIVERS[provider]
        _mod = __import__(mod_name, globals(), locals(), [driver_name])
        return getattr(_mod, driver_name)

def connect(provider, key, secret=None):
    creds = ProviderCreds(provider, key, secret)
    return get_driver(provider)(creds)
