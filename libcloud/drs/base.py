class DRSConsistencyGroup(object):
    """
    Provide a common interface for handling Load Balancers.
    """

    def __init__(self, id, name, description, journalSizeGB,  serverPairSourceServerId, serverPairtargetServerId,
                 driver, extra=None):
        """
        :param id: Load balancer ID.
        :type id: ``str``

        :param name: Load balancer name.
        :type name: ``str``

        :param state: State this loadbalancer is in.
        :type state: :class:`libcloud.loadbalancer.types.State`

        :param ip: IP address of this loadbalancer.
        :type ip: ``str``

        :param port: Port of this loadbalancer.
        :type port: ``int``

        :param driver: Driver this loadbalancer belongs to.
        :type driver: :class:`.Driver`

        :param extra: Provider specific attributes. (optional)
        :type extra: ``dict``
        """
        self.id = str(id) if id else None
        self.name = name
        self.description = description
        self.journalSizeGB = journalSizeGB

        self.serverPairSourceServerId = serverPairSourceServerId
        self.serverPairtargetServerId = serverPairtargetServerId
        self.driver = driver
        self.extra = extra or {}