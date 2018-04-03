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
        id = data['id']
        name = data['name']
        address = data['host'].get('ip_v4', '')
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

        extra = self._get_extra_dict(data)
        state = NodeState.RUNNING

        return Node(id, name,
                    state,
                    public_ips,
                    private_ips,
                    self,
                    extra=extra)

    @staticmethod
    def _get_extra_dict(data):
        extra = {}
        extra['hostname'] = data['host'].get('hostname', '')
        extra['software_id'] = data['software'].get('id', '')
        extra['software_name'] = data['software'].get('release', '') + " " + data['software'].get('versionn', '')
        extra['created_timestamp'] = data['created'][0]
        extra['monthly_cost_estimate'] = data['monthly_cost_estimate']['total']

        if data['subscription']:
            extra['subscription_label'] = data['subscription']['label']
            extra['subscription_value'] = data['subscription']['state']['value']
            extra['subscription_created'] = data['subscription']['created'][0]
            extra['subscription_expires'] = data['subscription']['expire'][0]


        return extra

    def list_nodes(self):
        """
        List all clear center devices

        :rtype: ``list`` of :class:`ClearCenterNode`
        """
        response = self.connection.request("/api/v5/glass?limit=500")
        nodes = [self._to_node(device)
                 for device in response.object['data']]
        return nodes
