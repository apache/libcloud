class Provider(object):
  """ Defines for each of the supported providers """
  DUMMY = 0 # Example provider
  EC2 = 1 # Amazon AWS

class NodeState(object):
  """ Standard states for a node """
  RUNNING = 0
  REBOOTING = 1
  TERMINATED = 2
  PENDING = 3
  UNKNOWN = 4

class ProviderCreds(object):
  """ An object for representing a standard provider """
  def __init__(self, provider, key, secret=None, name=None):
    self.provider = provider
    self.key = key
    self.secret = secret
    self.name = name

  def __repr__(self):
    return 'ProviderCreds(provider=%d, key="%s", secret="%s", name="%s"' % (self.provider, self.key, self.secret, self.name)

class Node(object):
  """ An object for representing a standard node """
  def __init__(self, uuid, name, state, ipaddress, creds, attrs={}):
    # every node should have a UUID, that is unique across the entire system
    # this is created on a per provider implementation basis
    self.uuid = uuid

    self.name = name
    self.state = state
    self.ipaddress = ipaddress
    
    # a reference to the ProviderCredentials object for this node
    self.creds = creds

    # an extra object for containing anything you want saved from the provider
    self.attrs = attrs

  def __repr__(self):
    return 'Node(uuid="%s", name="%s", state=%d, ipaddress="%s", creds="%s", attrs="%s")' % (self.uuid, self.name, self.state, self.ipaddress, self.creds, self.attrs)
