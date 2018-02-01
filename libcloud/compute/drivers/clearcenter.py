import json
import socket

from libcloud.compute.base import (Node, NodeDriver, NodeState,
                                   KeyPair, NodeLocation, NodeImage)
from libcloud.utils.networking import is_public_subnet
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

    def __init__(self, key=None,
                 uri='https://api.clearsdn.com',
                 verify=True):
        """
        :param key: apikey
        :param url: api endpoint
        """

        if not key:
            raise Exception("Api Key not specified")

        host = uri
        secure = False if host.startswith('http://') else True
        port = 80 if host.startswith('http://') else 443

        # strip the prefix
        prefixes = ['http://', 'https://']
        for prefix in prefixes:
            if host.startswith(prefix):
                host = host.replace(prefix, '')
        host = host.split('/')[0]

        self.connectionCls.host = host
        super(ClearCenterNodeDriver, self).__init__(
                                              key=key,
                                              uri=uri,
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
            raise Exception("Make sure clearcenter host <%s> is accessible and port "
                            "%s is open" % (host, port))
        # do not verify SSL certificate
        if not verify:
            self.connection.connection.ca_cert = False

    def _to_node(self, data):
        id = data[0]
        name = data[1]
        address = data[2]
        private_ips = []
        public_ips = []

        try:
            if is_public_subnet(address):
                public_ips.append(address)
            else:
                private_ips.append(address)
        except:
            # IPV6 not supported
            pass

        extra = self._get_extra_dict(data[3:])
        if extra.get('state') == 'Active':
            state = NodeState.RUNNING
        elif extra.get('state') == 'Pending':
            state = NodeState.PENDING
        elif extra.get('state') == 'Deleted':
            state = NodeState.TERMINATED
        else:
            state = NodeState.ERROR

        return Node(id, name,
                    state,
                    public_ips,
                    private_ips,
                    self,
                    extra=extra)

    @staticmethod
    def _get_extra_dict(data):
        extra = {}
        extra['user_id'] = data[0][0]
        extra['user_name'] = data[0][1]
        extra['software_id'] = data[1][0]
        extra['software_name'] = data[1][1]
        extra['state'] = data[2][1]
        extra['created_timestamp'] = data[4][0]
        extra['modified_timestamp'] = data[5][0]

        return extra

    def list_nodes(self):
        """
        List all clear center devices

        :rtype: ``list`` of :class:`ClearCenterNode`
        """
        response = self.connection.request("/api/v5/devices?limit=500")
        nodes = [self._to_node(device)
                 for device in response.object['data']]
        return nodes
