from zope.interface import Interface, Attribute

class INodeDriver(Interface):
  """
  A driver which provides nodes, such as an Amazon EC2 instance, or Slicehost slice
  """

  def create_node(node):
    """
    Creates a new node based on the given skeleton node
    """

  def destroy_node(node):
    """
    Destroys (shuts down) the given node
    """

  def list_nodes():
    """
    Returns a list of nodes for this provider
    """
  
  def reboot_node(node):
    """
    Reboots the given node
    """
