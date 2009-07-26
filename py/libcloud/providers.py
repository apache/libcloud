from libcloud.types import Provider, ProviderCreds

PROVIDERS = {
  Provider.DUMMY:
    ('libcloud.drivers.dummy', 'DummyProvider'),
  Provider.EC2:
    ('libcloud.drivers.ec2', 'EC2Provider'),
  Provider.EC2_EU:
    ('libcloud.drivers.ec2', 'EC2EUProvider'),
  Provider.GOGRID:
    ('libcloud.drivers.gogrid', 'GoGridProvider'),
  Provider.RACKSPACE:
    ('libcloud.drivers.rackspace', 'RackspaceProvider'),
  Provider.SLICEHOST:
    ('libcloud.drivers.slicehost', 'SlicehostProvider'),
  Provider.VPSNET:
    ('libcloud.drivers.vpsnet', 'VPSNetProvider'),
}

def get_provider(provider):
  if provider in PROVIDERS:
    mod_name, provider_name = PROVIDERS[provider]
    _mod = __import__(mod_name, globals(), locals(), [provider_name])
    return getattr(_mod, provider_name)

def connect(provider, key, secret=None):
  creds = ProviderCreds(provider, key, secret)
  return get_provider(provider)(creds)
