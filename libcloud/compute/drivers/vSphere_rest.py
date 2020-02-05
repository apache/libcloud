# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import json
import base64
import warnings
import time

import libcloud.security

from libcloud.utils.misc import lowercase_keys
from libcloud.utils.py3 import httplib
from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.common.types import ProviderError
from libcloud.common.exceptions import BaseHTTPError
from libcloud.common.base import JsonResponse, ConnectionKey
from libcloud.compute.base import NodeDriver
from libcloud.compute.base import Node, NodeSize
from libcloud.compute.base import NodeImage, NodeLocation
from libcloud.compute.types import NodeState, Provider


VALID_RESPONSE_CODES = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                        httplib.NO_CONTENT]

class VSphereNetwork(object):
    """
    Represents information about a VPC (Virtual Private Cloud) network

    Note: This class is VSphere specific.
    """

    def __init__(self, id, name, extra=None):
        self.id = id
        self.name = name
        self.extra = extra or {}

    def __repr__(self):
        return (('<VSphereNetwork: id=%s, name=%s')
                % (self.id, self.name))

class VSphereResponse(JsonResponse):

    def parse_error(self):
        if self.body:
            message = self.body
            message += "-- code: {}".format(self.status)
            return message
        return self.body      


class VSphereConnection(ConnectionKey):
    responseCls = VSphereResponse
    session_token=None

    def add_default_headers(self, headers):
        """
        VSphere needs an initial connection to a specific API endpoint to
        generate a session-token, which will be used for the purpose of
        authenticating for the rest of the session.
        """
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'
        if self.session_token is None:
            to_encode = '{}:{}'.format(self.key,self.secret)
            b64_user_pass = base64.b64encode(to_encode.encode())
            headers['Authorization'] = 'Basic {}'.format(b64_user_pass.decode())
        else:
            headers['vmware-api-seesion-id'] = self.session_token
        return headers


class VSphereException(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.args = (code, message)

    def __str__(self):
        return "{} {}".format(self.code, self.message)

    def __repr__(self):
        return "VSphereException {} {}".format(self.code, self.message)

class VSphereNodeDriver(NodeDriver):
    name = 'VMware vSphere'
    website = 'http://www.vmware.com/products/vsphere/'
    type = Provider.VSPHERE
    connectionCls = VSphereConnection

    NODE_STATE_MAP = {
        'powered_on': NodeState.RUNNING,
        'powered_off': NodeState.STOPPED,
        'suspended': NodeState.SUSPENDED
    }

    def __init__(self, key, secret=None, secure=True, host=None, port=443,
                 ca_cert=None):

        if not key or not secret:
            raise InvalidCredsError("Please provide both username "
                                    "(key) and password (secret).")
        super(VSphereNodeDriver, self).__init__(key=key,
                                                secure=secure, host=host,
                                                port=port)

        if ca_cert:
            self.connection.connection.ca_cert = ca_cert
        else:
            self.connection.connection.ca_cert = False

        self.connection.secret = secret

        # getting session token
        self._get_session_token()

    def _get_session_token(self):
        uri = "/rest/com/vmware/cis/session"
        try:
            result = self.connection.request(uri, method="POST")
        except Exception as exc:
            raise
        self.connection.session_token = result.object['value']

    def list_nodes(self, ex_filter_power_states=None, ex_filter_folders=None,
                   ex_filter_names=None, ex_filter_hosts=None,
                   ex_filter_clusters=None, ex_filter_vms=None,
                   ex_filter_datacenters=None, ex_filter_resource_pools=None):
        """
        The ex parameters are search options and must be an array of strings,
        even ex_filter_power_states which can have at most two items but makes
        sense to keep only one ("POWERED_ON" or "POWERED_OFF")
        Keep in mind that this method will return up to 1000 nodes so if your
        network has more, do use the provided filters and call it multiple
        times.
        """
        req = "/rest/vcenter/vm"
        kwargs = {'filter.power_states': ex_filter_power_states,
                  'filter.folders': ex_filter_folders,
                   'filter.names': ex_filter_names,
                   'filter.hosts': ex_filter_hosts,
                   'filter.clusters': ex_filter_clusters,
                   'filter.vms': ex_filter_vms,
                   'filter.datacenters': ex_filter_datacenters,
                   'filter.resource_pools': ex_filter_resource_pools}
        params={}
        for param,value in kwargs.items():
            if value:
                params[param]=value
        
        result = self._request(req, params=params)

        vm_ids = [item['vm'] for item in result.object['value']]
        vms = []
        for vm_id in vm_ids:
            vms.append(self._to_node(vm_id))
        return vms
    
    def list_locations(self):
        #TODO add resource-pools as locations
        """
        Location in the general sense means any resource that allows for node
        creation. In vSphere's case that usually is a host but if a cluster
        has rds enabled, a cluster can be assigned to create the VM, thus the
        clusters with rds enabled will be added to locations. Extra will hold
        a 'type' key to distinguish each location.
        """
        hosts = self.ex_list_hosts()
        clusters = self.ex_list_clusters()
        driver = self.connection.driver
        locations = []
        for host in hosts:
            extra = {'type': 'host', 'status': host['connection_state'],
                     'state': host['power_state']}
            locations.append(NodeLocation(id=host['host'], name=host['name'],
                                          country="", driver=driver,
                                          extra=extra))
        for cluster in clusters:
            if cluster['drs_enabled']:
                extra = {'type': 'cluster', 'drs': True,
                         'ha': cluster['ha_enabled']}
                locations.append(NodeLocation(id=cluster['cluster'],
                                              name=cluster['name'],
                                              country='', driver=driver,
                                              extra=extra))
        return locations     
    
    def stop_node(self, node):
        if node.state == NodeState.STOPPED:
            return True
        
        method = 'POST'
        req = "/rest/vcenter/vm/{}/power/stop".format(node.id)

        result = self._request(req,method=method)
        return result.status in VALID_RESPONSE_CODES

    def start_node(self, node):
        if node.state is NodeState.RUNNING:
            return True
        
        method = 'POST'
        req = "/rest/vcenter/vm/{}/power/start".format(node.id)
        result = self._request(req,method=method)
        return result.status in VALID_RESPONSE_CODES
        
    def reboot_node(self, node):
        if node.state is not NodeState.RUNNING:
            return False

        method = 'POST'
        req = "/rest/vcenter/vm/{}/power/reset".format(node.id)
        result = self._request(req, method=method)
        return result.status in VALID_RESPONSE_CODES
    
    def destroy_node(self, node):
        # make sure the machine is stopped
        if node.state is not NodeState.STOPPED:
            self.stop_node(node)
        # wait to make sure it stopped
        # at one point this can be made asynchronously
        for i in range(3):
            if node.state is NodeState.STOPPED:
                break
            time.sleep(3)
        if node.state is not NodeState.STOPPED:
            raise ProviderError("Something went wrong, I could not stop the VM"
                                " and it cannot be deleted while running.",
                                503)
        req = "/rest/vcenter/vm/{}".format(node.id)
        resp = self._request(req, method="DELETE")
        return resp.status in VALID_RESPONSE_CODES

    def ex_suspend_node(self, node):
        if node.state is not NodeState.RUNNING:
            return False

        method = 'POST'
        req = "/rest/vcenter/vm/{}/power/suspend".format(node.id)
        result = self._request(req,method=method)
        return result.status in VALID_RESPONSE_CODES

    def _to_node(self, vm_id):
        '''
         id, name, state, public_ips, private_ips,
                 driver, size=None, image=None, extra=None, created_at=None)
        '''
        req = '/rest/vcenter/vm/' + vm_id
        vm = self._request(req).object['value']
        name = vm['name']
        state = self.NODE_STATE_MAP[vm['power_state'].lower()]
        public_ips = []  # api 6.7
        private_ips = [] # api 6.7
        driver = self.connection.driver

        ##  size
        total_size = 0
        gb_converter = 1024*3
        for disk in vm['disks']:
            total_size += int(int(disk['value']['capacity']/gb_converter))
        ram = int(vm['memory']['size_MiB'])
        cpus = int(vm['cpu']['count'])
        size_id = vm_id + "-size"
        size_name = name + "-size"
        size_extra = {'cpus': cpus}
        size = NodeSize(id=size_id, name=size_name, ram=ram, disk= total_size,
                        bandwidth=0, price=0, driver=driver, extra=size_extra)

        ## image
        image_name = vm['guest_OS']
        image_id = image_name + "_id"
        image = NodeImage(id=image_id, name=image_name, driver=driver)

        return Node(id=vm_id, name=name, state=state, public_ips=public_ips,
                    private_ips=private_ips, driver=driver,
                    size=size, image=image)

    def ex_list_hosts(self, ex_filter_folders=None, ex_filter_standalone=None,
                      ex_filter_hosts=None, ex_filter_clusters=None,
                      ex_filter_names=None, ex_filter_datacenters=None,
                      ex_filter_connection_states=None):

        kwargs = {'filter.folders': ex_filter_folders,
                  'filter.names': ex_filter_names,
                  'filter.hosts': ex_filter_hosts,
                  'filter.clusters': ex_filter_clusters,
                  'filter.standalone': ex_filter_standalone,
                  'filter.datacenters': ex_filter_datacenters,
                  'filter.connection_states': ex_filter_connection_states}
        
        params={}
        for param,value in kwargs.items():
            if value:
                params[param]=value
        req = "/rest/vcenter/host"     
        result = self._request(req, params=params).object['value']
        return result
    
    def ex_list_clusters(self, ex_filter_folders=None, ex_filter_names=None,
                         ex_filter_datacenters=None, ex_filter_clusters=None):
        kwargs = {'filter.folders': ex_filter_folders,
                  'filter.names': ex_filter_names,
                  'filter.datacenters': ex_filter_datacenters,
                  'filter.clusters': ex_filter_clusters}
        params={}
        for param,value in kwargs.items():
            if value:
                params[param]=value
        req = "/rest/vcenter/cluster"
        result = self._request(req, params=params).object['value']
        return result

    def ex_list_datacenters(self, ex_filter_folders=None, ex_filter_names=None,
                            ex_filter_datacenters=None):
        req = "/rest/vcenter/datacenter"
        kwargs = {'filter.folders': ex_filter_folders,
                  'filter.names': ex_filter_names,
                  'filter.datacenters': ex_filter_datacenters,}
        params={}
        for param,value in kwargs.items():
            if value:
                params[param]=value       
        result = self._request(req, params=params)
        to_return = [{'name': item['name'], 
                'id': item['datacenter']} for item in result.object['value']]
        return to_return
    
    def ex_list_content_libraries(self):
        req = '/rest/com/vmware/content/library'
        result = self._request(req).object
        return result['value']
    
    def ex_list_content_library_items(self, library_id):
        req = "/rest/com/vmware/content/library/item"
        params = {'library_id': library_id}
        result = self._request(req, params=params).object
        return result['value']

    def ex_list_folders(self):
        req = "/rest/vcenter/folder"
        response = self._request(req).object
        return response['value']

    def ex_update_memory(self, node, ram):
        pass

    def ex_update_cpu(self, node, cores):
        pass

    def ex_update_capacity(self, node, capacity):
        pass

    def ex_add_nic(self, node, network):
        """
        Creates a network adapater that will connect to the specified network
        for the given node. Returns a boolean indicating success or not.
        """
        spec = {}
        spec['mac_type'] = "GENERATED"
        spec['backing'] = {}
        spec['backing']['type'] = "STANDARD_PORTGROUP"
        spec['backing']['network'] = network.id
        spec['start_connected'] = True

        data = json.dumps({'spec': spec})
        req = "/rest/vcenter/vm/{}/hardware/ethernet".format(node.id)
        method = "POST"
        resp = self._request(req, method=method, data=data)
        return resp.status

    def _get_library_item(self, item_id):
        req = "/rest/com/vmware/content/library/item/id:{}".format(item_id)
        result = self._request(req).object
        return result['value']

    def _get_resource_pool(self, host_id=None, cluster_id=None, name=None):
        if host_id:
            pms = {"filter.hosts": host_id}
        if cluster_id:
            pms = {"filter.clusters": cluster_id}
        if name:
            pms = {"filter.names": name}
        rp_request = "/rest/vcenter/resource-pool"
        resource_pool = self._request(rp_request,
                                      params=pms).object
        return resource_pool['value'][0]['resource_pool']

    def _request(self, req, method="GET", params=None, data=None):
        try:
            result = self.connection.request(req, method=method,
                                             params=params, data=data)
        except BaseHTTPError as exc:
            if exc.code == "401":
                self.connection.session_token = None
                self._get_session_token()
                result = self.connection.request(req, method=method,
                                                params=params, data=data)
            else:
                raise
        except Exception as exc:
            raise
        return result

    def list_images(self):
        libraries = self.ex_list_content_libraries()
        item_ids=[]
        if libraries:
            for library in libraries:
                item_ids.extend(self.ex_list_content_library_items(library))
        items = []
        if item_ids:
            for item_id in item_ids:
                items.append(self._get_library_item(item_id))
        images=[]
        if items:
            driver = self.connection.driver
            for item in items:
                extra = {"type": item['type']}
                images.append(NodeImage(id=item['id'],
                              name=item['name'],
                              driver=driver, extra=extra))
        return images

    def ex_list_networks(self):
        #TODO VSphereNetwork
        pass
    def create_node(self, name, image, size=None, location=None,
                    ex_datastore=None, ex_disks=None,
                    ex_folder=None, ex_network=None, ex_turned_on=True):
        """
        Image can be either a vm template , a ovf template or just
        the guest OS.

        ex_folder is necessary if the image is a vm-template, this method
        will attempt to put the VM in a random folder and a warning about it
        will be issued.
        """
        # post creation checks
        create_nic = False
        update_memory = False
        update_cpu = False
        create_disk = False
        update_capacity = False

        if image.extra['type'] == 'ovf':
            ovf_request=('/rest/com/vmware/vcenter/ovf/library-item'
                         '/id:{}?~action=filter'.format(image.id))
            spec = {}
            spec['target'] = {}
            if location.extra.get('type') == "resource-pool":
                spec['target']['resource_pool_id'] = location.id
            elif location.extra.get('type') == "host":
                resource_pool = self._get_resource_pool(host_id=location.id)
                if not resource_pool:
                    msg = ("Could not find resource-pool for given location "
                           "(host). Please make sure the location is valid.")
                    raise VSphereException(code="504", msg=msg)
                spec['target']['resource_pool_id'] = resource_pool
                spec['target']['host_id'] = location.id
            elif location.extra.get('type') == 'cluster':
                resource.pool = self._get_resource_pool(cluster=location.id)
                if not resource_pool:
                    msg = ("Could not find resource-pool for given location "
                           "(cluster). Please make sure the location "
                           "is valid.")
                    raise VSphereException(code="504", msg=msg)
                spec['target']['resource_pool_id'] = resource_pool
            ovf = self._request(ovf_request,method="POST",
                                              data=json.dumps(spec)).object[
                                                  'value']
            spec['deployment_spec'] = {}
            spec['deployment_spec']['name'] = name
            # assuming that since you want to make a vm you don't need reminder
            spec['deployment_spec']['accept_all_EULA'] = True
            # network
            if ex_network and ovf['networks']:
                spec['deployment_spec'][
                    'network_mappings'] = [{ovf['networks'][0]: ex_network.id}]
            elif not ovf['networks']:
                create_nic=True
            # storage
            if ex_datastore:
                spec['deployment_spec']['storage_mappings'] = []
                store_map={"type": "DATASTORE","datastore_id": ex_datastore}
                spec['deployment_spec']['storage_mappings'].append(store_map)
            if size and size.ram:
                update_memory = True
            if size and size.extra and size.extra.get('cpu'):
                update_cpu = True
            if size and size.disk:
                update_capacity = True
            if ex_disks:
                create_disk = True

            create_request = ('/rest/com/vmware/vcenter/ovf/library-item'
                         '/id:{}?~action=deploy'.format(image.id))
            data = json.dumps({"target": spec['target'],
                               'deployment_spec': spec['deployment_spec']})

        elif image.extra['type'] == 'vm-template':
            tp_request = "/rest/vcenter/vm-template/library-items/" + image.id
            template = self._request(tp_request).object['value']
            spec = {}
            spec['name'] = name

            # storage
            if ex_datastore:
                spec['disk_storage']={}
                spec['disk_storage']['datastore'] = ex_datastore

            # location :: folder,resource group, datacenter, host
            spec['placement'] = {}
            if not ex_folder:
                warn = ("The API(6.7) requires the folder to be given, I will"
                        " place it into a random folder, after creation you "
                        "might find it convenient to move it into a better "
                        "folder.")
                warnings.warn(warn)
                folders = self.ex_list_folders()
                vm_folder = None
                for folder in folders:
                    if folder['type'] == "VIRTUAL_MACHINE":
                        vm_folder = folder['folder']
                if vm_folder is None:
                    msg = "No suitable folder vor VMs found, please create one"
                    raise ProviderError(msg, 404)
            spec['placement']['folder'] = vm_folder
            if location.extra['type'] == 'host':
                spec['placement']['host']= location.id
            elif location.extra['type'] == 'cluster':
                spec['placement']['cluster'] == location.id
            # network changes the network to existing nics if there are no adapters
            # in the template then we will make on in the vm after the creation finishes
            # only one network atm??
            spec['hardware_customization'] = {}
            if ex_network:
                nics = template['nics']
                if len(nics) > 0:
                    nic = nics[0].keys()[0]
                    spec['hardware_customization']['nics'] = [{nic: ex_network.id}]
                else:
                    create_nic = True
            # hardware
            if size:
                if size.ram:
                    spec['hardware_customization']['memory_update'] = {
                        'memory': int(size.ram) * 1024}
                if size.extra.get('cpu'):
                    spec['hardware_customization']['cpu_update'] = {
                        'num_cpus': size.extra['cpu']}
                if size.disk:
                    if not len(template['disks']) > 0:
                        create_disk = True
                    else:
                        capacity = size.disk * 1024 * 1024 * 1024
                        dsk = template['disks'][0]['key']
                        if template['disks'][0]['value']['capacity'] < capacity:
                            update = {'capacity': capacity}
                            spec['hardware_customization'][
                                'disks_to_update'] = [{'key': dsk, 'value': update}]

            create_request = ("/rest/vcenter/vm-template/library-items/"
            "{}/?action=deploy".format(image.id))
            data = json.dumps({'spec': spec})
        # deploy the node
        result = self._request(create_request,
                               method="POST", data=data)
        # wait until the node is up and then add extra config
        node_id = result.object['value']
        for i in range(3):
            node_l = self.list_nodes(ex_filter_vms=node_id['resource_id']['id'])
            if len(node_l) > 0:
                break
            time.sleep(3)
        node = node_l[0]
        if create_nic:
            self.ex_add_nic(node, ex_network)
        if update_memory:
            self.ex_update_memory(node, size.ram)
        if update_cpu:
            self.ex_update_cpu(node, size.extra['cpu'])
        if create_disk:
            pass  # until volumes are added
        if update_capacity:
            self.ex_update_capacity(node, size.disk)
        if ex_turned_on:
            self.start_node(node)

        return node


if __name__ == "__main__":
    host = "192.168.1.11"
    port = "443"
    username = "administrator@vsphere.local"
    password = "Mistrul2!"
    ca_cert = "/home/eis/work/certs/lin/e65bea3e.0"
    driver = VSphereNodeDriver(key=username,secret=password,host=host,port=port, ca_cert=ca_cert)
    loc = driver.list_locations()
    print(loc)
    print(driver.ex_list_datacenters())
    nodes = driver.list_nodes()
    images = driver.list_images()
    sss = NodeSize(id="111", name="minimal",ram="256", extra={'cpu':"1"},disk=7,bandwidth=0,driver=driver,price=0)
    res = driver.create_node("apiOvf", images[1], size=sss, location=loc[0],
                         ex_datastore=None, ex_disks=None,
                         ex_network=None, ex_turned_on=True)

    print(res)