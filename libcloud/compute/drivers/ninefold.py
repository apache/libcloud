import base64
import hashlib
import hmac
import urllib

try:
    import json
except:
    import simplejson as json

from libcloud.common.base import ConnectionUserAndKey, Response
from libcloud.compute.base import Node, NodeDriver
from libcloud.compute.providers import Provider
from libcloud.compute.types import MalformedResponseError, NodeState

class NinefoldComputeResponse(Response):
    def parse_body(self):
        try:
            body = json.loads(self.body)
        except:
            raise MalformedResponseError(
                "Failed to parse JSON",
                body=self.body,
                driver=NinefoldNodeDriver)
        return body

class NinefoldComputeConnection(ConnectionUserAndKey):
    host = 'api.ninefold.com'
    responseCls = NinefoldComputeResponse

    def add_default_params(self, params):
        params['apiKey'] = self.user_id
        params['response'] = 'json'

        return params

    def pre_connect_hook(self, params, headers):
        signature = [(k.lower(), v) for k, v in params.items()]
        signature.sort(key=lambda x: x[0])
        signature = urllib.urlencode(signature)
        signature = signature.lower().replace('+', '%20')
        signature = hmac.new(self.key, msg=signature, digestmod=hashlib.sha1)
        params['signature'] = base64.b64encode(signature.digest())

        return params, headers

class NinefoldNodeDriver(NodeDriver):
    API_PATH = '/compute/v1.0/'

    NODE_STATE_MAP = { 'Running': NodeState.RUNNING,
                       'Starting': NodeState.REBOOTING,
                       'Stopped': NodeState.TERMINATED,
                       'Stopping': NodeState.TERMINATED }

    type = Provider.NINEFOLD
    connectionCls = NinefoldComputeConnection

    def _api_request(self, command, **kwargs):
        kwargs['command'] = command
        return self.connection.request(self.API_PATH, params=kwargs).object

    def list_nodes(self):
        vms = self._api_request('listVirtualMachines')
        vms = vms['listvirtualmachinesresponse']['virtualmachine']
        addrs = self._api_request('listPublicIpAddresses')
        addrs = addrs['listpublicipaddressesresponse']['publicipaddress']

        public_ips = {}
        for addr in addrs:
            if 'virtualmachineid' not in addr:
                continue
            vm_id = addr['virtualmachineid']
            if vm_id not in public_ips:
                public_ips[vm_id] = []
            public_ips[vm_id].append(addr['ipaddress'])

        nodes = []

        for vm in vms:
            nodes.append(Node(id=vm['id'],
                              name=vm.get('displayname', None),
                              state=self.NODE_STATE_MAP[vm['state']],
                              public_ip=public_ips.get(vm['id'], []),
                              private_ip=[x['ipaddress'] for x in vm['nic']],
                              driver=self.connection.driver))

        return nodes
