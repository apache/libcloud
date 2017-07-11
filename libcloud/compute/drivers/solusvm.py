import json
import socket

from libcloud.compute.base import (Node, NodeDriver, NodeState,
                                   KeyPair, NodeLocation, NodeImage)
from libcloud.common.solusvm import SolusVMConnection
from libcloud.utils.networking import is_public_subnet
from libcloud.utils.publickey import get_pubkey_ssh2_fingerprint
from libcloud.compute.providers import Provider

__all__ = [
    "SolusVMNodeDriver"
]


class SolusVMNodeDriver(NodeDriver):
    """
    Base SolusVM node driver.
    """

    connectionCls = SolusVMConnection
    type = Provider.SOLUSVM
    name = 'SolusVM'
    website = 'http://solusvm.com/'

    def __init__(self, key=None, secret=None,
                 host='solusvm.com', port=None,
                 verify=True
                 ):
        """
        :param key: username
        :param secret: password
        :param host: solusvm host
        :param port: solusvm host port
        """
        if not key or not secret:
            raise Exception("Key and secret not specified")

        secure = True if host.startswith('https://') else False

        if not port:
            port = 443 if host.startswith('https://') else 80

        # strip the prefix
        prefixes = ['http://', 'https://']
        for prefix in prefixes:
            if host.startswith(prefix):
                host = host.replace(prefix, '')
        host = host.split('/')[0]

        super(SolusVMNodeDriver, self).__init__(key=key,
                                                secret=secret,
                                                host=host,
                                                port=port,
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
            raise Exception("Make sure solusvm host is accessible and port "
                            "%s is open" % port)
        # do not verify SSL certificate
        if not verify:
            self.connection.connection.ca_cert = False

    def create_node(self):
        """
        Add a VS

        """
        pass

    def ex_start_node(self, node):
        """
        Start a node
        """
        action = "/api/virtual_machines/{identifier}/boot".format(
            identifier=node.id)

        result = self.connection.request(action, method="POST")
        return True if result.status == 201 else False

    def ex_stop_node(self, node):
        """
        Stop a node
        """
        action = "/api/virtual_machines/{identifier}/shutdown".format(
            identifier=node.id)

        result = self.connection.request(action, method="POST")
        return True if result.status == 201 else False

    def reboot_node(self, node):
        """
        Reboot a node
        """
        action = "/api/virtual_machines/{identifier}/reboot".format(
            identifier=node.id)

        result = self.connection.request(action, method="POST")
        return True if result.status == 201 else False

    def destroy_node(self, node):
        """
        Delete a VS
        """
        action = "/api/virtual_machines/{identifier}".format(
            identifier=node.id)

        self.connection.request(action, method="DELETE")
        return True

    def list_nodes(self):
        """
        List all VS

        :rtype: ``list`` of :class:`SolusVMNode`
        """
        response = self.connection.request("/api/virtual_machines")
        nodes = [self._to_node(vm["virtual_machine"])
                 for vm in response.object]
        return nodes

    def list_locations(self):
        """
        List locations
        """
        pass

    def list_sizes(self):
        """
        List sizes
        """
        pass

    def list_images(self):
        """
        List images
        """
        pass

    def _to_node(self, data):
        identifier = data['id']
        name = data['hostname']
        private_ips = []
        public_ips = []
        mainipaddress = data.get('mainipaddress')
        ipaddresses = data.get('ipaddresses')
        all_ips = [mainipaddress]
        if ipaddresses and isinstance(ipaddresses, basestring):
            all_ips.append(ipaddresses)
        if ipaddresses and isinstance(ipaddresses, list):
            all_ips.extend(ipaddresses)
        for ip in all_ips:
            try:
                if is_public_subnet(ip):
                    if ip not in public_ips:
                        public_ips.append(ip)
                else:
                    if ip not in private_ips:
                        private_ips.append(ip)
            except:
                # IPV6 not supported
                pass
        extra = {}
        extra['creationdate'] = data.get('creationdate')
        extra['clientid'] = data.get('clientid')
        extra['consoleusername'] = data.get('consoleusername')
        extra['hostname'] = data.get('hostname')
        extra['os'] = data.get('templatename')
        extra['type'] = data.get('type')
        extra['disk'] = data.get('disk')
        extra['memory'] = data.get('ram')
        extra['bandwidth'] = data.get('freebandwidth')

        status = data.get('status')
        if status == 'online':
            state = NodeState.RUNNING
        elif status == 'offline':
            state = NodeState.STOPPED
        else:
            state = NodeState.UNKNOWN

        return Node(identifier,
                    name,
                    state,
                    public_ips,
                    private_ips,
                    self,
                    extra=extra)
