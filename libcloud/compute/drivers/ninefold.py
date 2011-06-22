import base64
import hashlib
import hmac
import time
import urllib

try:
    import json
except:
    import simplejson as json

from libcloud.common.base import ConnectionUserAndKey, Response
from libcloud.compute.base import Node, NodeDriver, NodeImage, NodeLocation, \
                                  NodeSize
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

    NODE_STATE_MAP = {
        'Running': NodeState.RUNNING,
        'Starting': NodeState.REBOOTING,
        'Stopped': NodeState.TERMINATED,
        'Stopping': NodeState.TERMINATED
    }
    JOB_STATUS_MAP = {
        0: None,
        1: True,
        2: False,
    }

    type = Provider.NINEFOLD
    name = 'Ninefold'
    connectionCls = NinefoldComputeConnection

    def _api_request(self, command, **kwargs):
        kwargs['command'] = command
        result = self.connection.request(self.API_PATH, params=kwargs).object
        command = command.lower() + 'response'
        if command not in result:
            raise MalformedResponseError(
                "Unknown response format",
                body=result.body,
                driver=NinefoldNodeDriver)
        return result[command]

    def _job_result(self, job_id):
        result = {}
        while result.get('jobstatus', 0) == 0:
            time.sleep(1)
            result = self._api_request('queryAsyncJobResult', jobid=job_id)
        return self.JOB_STATUS_MAP[result['jobstatus']]

    def list_images(self, location=None):
        args = {
            'templatefilter': 'executable'
        }
        if location is not None:
            args['zoneid'] = location.id
        imgs = self._api_request('listTemplates', **args)
        images = []
        for img in imgs['template']:
            images.append(NodeImage(img['id'], img['name'], self, {
                'hypervisor': img['hypervisor'],
                'format': img['format'],
                'os': img['ostypename'],
            }))
        return images

    def list_locations(self):
        locs = self._api_request('listZones')
        locations = []
        for loc in locs['zone']:
            locations.append(NodeLocation(loc['id'], loc['name'], 'AU', self))
        return locations

    def list_nodes(self):
        vms = self._api_request('listVirtualMachines')
        addrs = self._api_request('listPublicIpAddresses')

        public_ips = {}
        for addr in addrs['publicipaddress']:
            if 'virtualmachineid' not in addr:
                continue
            vm_id = addr['virtualmachineid']
            if vm_id not in public_ips:
                public_ips[vm_id] = []
            public_ips[vm_id].append(addr['ipaddress'])

        nodes = []

        for vm in vms['virtualmachine']:
            nodes.append(Node(id=vm['id'],
                              name=vm.get('displayname', None),
                              state=self.NODE_STATE_MAP[vm['state']],
                              public_ip=public_ips.get(vm['id'], []),
                              private_ip=[x['ipaddress'] for x in vm['nic']],
                              driver=self))

        return nodes

    def list_sizes(self, location=None):
        szs = self._api_request('listServiceOfferings')
        sizes = []
        for sz in szs['serviceoffering']:
            sizes.append(NodeSize(sz['id'], sz['name'], sz['memory'], 0, 0,
                                  0, self))
        return sizes

    def destroy_node(self, node):
        result = self._api_request('destroyVirtualMachine', id=node.id)
        return self._job_result(result['jobid'])

    def reboot_node(self, node):
        result = self._api_request('rebootVirtualMachine', id=node.id)
        return self._job_result(result['jobid'])
