from libcloud.types import Node, NodeState
from libcloud.interface import INodeDriver
from zope.interface import implements

import uuid

class DummyNodeDriver(object):

  implements(INodeDriver)

  def __init__(self, creds):
    self.creds = creds

  def get_uuid(self, unique_field=None):
    return str(uuid.uuid4())
    
  def list_nodes(self):
    return [
      Node(uuid=self.get_uuid(), name='dummy-1', state=NodeState.RUNNING, ipaddress='127.0.0.1', creds=self.creds, attrs={'foo': 'bar'}),
      Node(uuid=self.get_uuid(), name='dummy-2', state=NodeState.REBOOTING, ipaddress='127.0.0.2', creds=self.creds, attrs={'foo': 'bar'})
    ]

  def reboot_node(self, node):
    node.state = NodeState.REBOOTING
    return node

  def destroy_node(self, node):
    pass

  def create_node(self, node):
    pass
