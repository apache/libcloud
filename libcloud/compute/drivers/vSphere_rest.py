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

import libcloud.security

from libcloud.utils.misc import lowercase_keys
from libcloud.utils.py3 import httplib
from libcloud.common.base import JsonResponse, ConnectionKey
from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.compute.base import NodeDriver
from libcloud.compute.base import Node, NodeSize
from libcloud.compute.base import NodeImage, NodeLocation
from libcloud.compute.types import NodeState, Provider


VALID_RESPONSE_CODES = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                        httplib.NO_CONTENT]

class VSphereResponse(JsonResponse):

    def parse_error(self):
        if self.body:
            message = json.loads(self.body)['value']['messages'][0][
                'default_message']
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
        
        try:
            result = self.connection.request(req, params=params)
        except Exception as exc:
            raise

        vm_ids = [item['vm'] for item in result.object['value']]
        vms = []
        for vm_id in vm_ids:
            vms.append(self._to_node(vm_id))
        return vms
    
    def list_locations(self):
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

        try:
            result = self.connection.request(req,method=method)
            return result.status in VALID_RESPONSE_CODES
        except Exception as exc:
            raise
        

    def start_node(self, node):
        if node.state is NodeState.RUNNING:
            return True
        
        method = 'POST'
        req = "/rest/vcenter/vm/{}/power/start".format(node.id)
        try:
            result = self.connection.request(req,method=method)
            return result.status in VALID_RESPONSE_CODES
        except Exception as exc:
            raise
        
    def reboot_node(self, node):
        if node.state is not NodeState.RUNNING:
            return False

        method = 'POST'
        req = "/rest/vcenter/vm/{}/power/reset".format(node.id)
        try:
            result = self.connection.request(req,method=method)
            return result.status in VALID_RESPONSE_CODES
        except Exception as exc:
            raise
    
    def ex_suspend_node(self, node):
        if node.state is not NodeState.RUNNING:
            return False

        method = 'POST'
        req = "/rest/vcenter/vm/{}/power/suspend".format(node.id)
        try:
            result = self.connection.request(req,method=method)
            return result.status in VALID_RESPONSE_CODES
        except Exception as exc:
            raise

    def _to_node(self, vm_id):
        '''
         id, name, state, public_ips, private_ips,
                 driver, size=None, image=None, extra=None, created_at=None)
        '''
        try:
            req = '/rest/vcenter/vm/' + vm_id
            vm = self.connection.request(req).object['value']
        except Exception as exc:
            raise
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
        try:
            result = self.connection.request(req, params=params).object['value']
        except Exception as exc:
            raise

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
        try:
            result = self.connection.request(req, params=params).object['value']
        except Exception as exc:
            raise

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
        try:
            result = self.connection.request(req, params=params)
        except Exception as exc:
            raise

        to_return = [{'name': item['name'], 
                'id': item['datacenter']} for item in result.object['value']]
        return to_return
    
    def ex_list_content_libraries(self):
        req = '/rest/com/vmware/content/library'

        try:
            result = self.connection.request(req).object
        except Exception as exc:
            raise
        return result['value']
    
    def ex_list_content_library_items(self, library_id):
        
        req = "/rest/com/vmware/content/library/item"
        params = {'library_id': library_id}

        try:
            result = self.connection.request(req, params=params).object
        except Exception as exc:
            raise

        return result['value']

    def _get_library_item(self, item_id):
        req = "/rest/com/vmware/content/library/item/id:{}".format(item_id)

        try:
            result = self.connection.request(req).object
        except Exception as exc:
            raise
        return result['value']
    
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
                images.append(NodeImage(id=item['id'],
                              name=item['name'],
                              driver=driver))
        return images
    def create_node(self, name, image, location=None, ex_memory=None,
                    ex_cpu=None, ex_disk=None,
                    ex_network=None):
        """
        Image can be either a vm template , a ovf template or just
        the guest OS.

        ex_disk is datastore
        """
        if image.extra['type'] == 'ovf':
            #must later add the specs
            pass
        
        elif image.extra['type'] == 'template':
            spec = {}
            spec['name'] = name

            # storage
            if ex_disk:
                spec['disk_storage']={}
                spec['disk_storage']['datastore'] = ex_disk

            # location :: folder,resource group, datacenter, host
            spec['placement'] = {}

if __name__ == "__main__":
    host = "192.168.1.11"
    port = "443"
    username = "administrator@vsphere.local"
    password = "Mistrul2!"
    ca_cert = "/home/eis/Downloads/certs/lin/e65bea3e.0"
    driver = VSphereNodeDriver(key=username,secret=password,host=host,port=port, ca_cert=ca_cert)
    loc = driver.list_locations()
    print(loc)
    print(driver.ex_list_datacenters())
    nodes = driver.list_nodes()
    print(nodes)
    '''    
    
    clusters = driver.ex_list_clusters()
    print(clusters)
    
    import ipdb; ipdb.set_trace()
    driver.start_node(nodes[1])
    print(driver.ex_list_hosts())
    '''