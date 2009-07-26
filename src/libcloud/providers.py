from libcloud.types import Provider, ProviderCreds

def get_provider(provider):
  if provider == Provider.DUMMY:
    from libcloud.drivers.dummy import DummyProvider
    return DummyProvider
  elif provider == Provider.EC2:
    from libcloud.drivers.ec2 import EC2Provider
    return EC2Provider
  if provider == Provider.EC2_EU:
    from libcloud.drivers.ec2 import EC2EUProvider
    return EC2EUProvider
  if provider == Provider.GOGRID:
    from libcloud.drivers.gogrid import GoGridProvider
    return GoGridProvider
  elif provider == Provider.RACKSPACE:
    from libcloud.drivers.rackspace import RackspaceProvider
    return RackspaceProvider
  elif provider == Provider.SLICEHOST:
    from libcloud.drivers.slicehost import SlicehostProvider
    return SlicehostProvider
  elif provider == Provider.VPSNET:
    from libcloud.drivers.vpsnet import VPSNetProvider
    return VPSNetProvider

def connect(provider, key, secret=None):
  creds = ProviderCreds(provider, key, secret)
  return get_provider(provider)(creds)
