from zope.interface import Interface, Attribute


class IDriver(Interface):
    """
    TODO
    
    A Driver represents an interface to a provider Web Service. This is the
    Interface which all base drivers (`EC2Driver`, `SliceDriver`, etc.) should
    implement!
    """
    connectionCls = Attribute("""A suitable provider-specific Connection class""")
    nodesCls = Attribute("""A suitable provider-specific NodeDriver class""")
    connection = Attribute("""A suitable provider-specific Connection instance""")
    nodes = Attribute("""A suitable provider-specific NodeDriver instance""")


class IDriverFactory(Interface):
    """
    TODO

    Creates IDrivers
    """
    def __call__():
        """
        Initialize `connection` and `nodes` 
        """


class INodeDriver(Interface):
  """
  A driver which provides nodes, such as an Amazon EC2 instance, or Slicehost slice
  """

  def create(node):
    """
    Creates a new node based on the given skeleton node
    """

  def destroy(node):
    """
    Destroys (shuts down) the given node
    """

  def list():
    """
    Returns a list of nodes for this provider
    """

  def reboot(node):
    """
    Reboots the given node
    """
