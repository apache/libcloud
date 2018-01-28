import json
import socket

from libcloud.compute.base import (Node, NodeDriver, NodeState,
                                   KeyPair, NodeLocation, NodeImage)
from libcloud.common.clearcenter import ClearCenterConnection
from libcloud.compute.providers import Provider

__all__ = [
    "ClearCenterNodeDriver"
]

class ClearCenterNodeDriver(NodeDriver):
    """
    Base ClearCenter node driver.
    """

    connectionCls = ClearCenterConnection
    type = Provider.CLEARCENTER
    name = 'ClearCenter'
    website = 'https://www.clearcenter.com/'

    def __init__(self, key=None, host='', verify=True):
        """
        :param key: apikey
        :param url: api endpoint
        """

        if not key or not host:
            raise Exception("Key and url not specified")

        secure = False if host.startswith('http://') else True
        port = 80 if host.startswith('http://') else 443

        # strip the prefix
        prefixes = ['http://', 'https://']
        for prefix in prefixes:
            if host.startswith(prefix):
                host = host.replace(prefix, '')
        import ipdb; ipdb.set_trace()
        host = host.split('/')[0]

        super(ClearCenterNodeDriver, self).__init__(
                                              key=key,
                                              url=host,
                                              secure=secure)

        self.connection.secure = secure

        self.connection.host = host
        self.connection.port = port

        try:
            socket.setdefaulttimeout(15)
            so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            so.connect((host, int(port)))
            so.close()
        except:
            raise Exception("Make sure clearcenter host is accessible and port "
                            "%s is open" % port)
        # do not verify SSL certificate
        if not verify:
            self.connection.connection.ca_cert = False

    def list_nodes(self):
        """
        List all clear center devices

        :rtype: ``list`` of :class:`ClearCenterNode`
        """
        response = self.connection.request("/virtual_machines.json")
        nodes = [self._to_node(vm["virtual_machine"])
                 for vm in response.object]
        return nodes
