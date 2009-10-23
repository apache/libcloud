# Licensed to libcloud.org under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# libcloud.org licenses this file to You under the Apache License, Version 2.0
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
# Copyright 2009 RedRata Ltd

from libcloud.types import Provider, NodeState
from libcloud.base import ConnectionKey, Response, NodeDriver, NodeSize, Node
from libcloud.base import NodeImage
from copy import copy

# JSON is included in the standard library starting with Python 2.6.  For 2.5
# and 2.4, there's a simplejson egg at: http://pypi.python.org/pypi/simplejson
try: import json
except: import simplejson as json

# Defaults
API_CONTEXT = '/r'
API_HOST = 'api.rimuhosting.com'
API_PORT = (80,443)
API_SECURE = True

class RimuHostingException(BaseException):
    def __init__(self, error):
        self.error = error
        
    def __str__(self):
        return self.error

    def __repr__(self):
        return "<RimuHostingException '%s'>" % (self.error)

class RimuHostingResponse(Response):
    def __init__(self, response):
        self.body = response.read()
        self.status = response.status
        self.headers = dict(response.getheaders())
        self.error = response.reason

        self.object = self.parse_body()

    def parse_body(self):
        try:
            js = json.loads(self.body)
            if js[js.keys()[0]]['response_type'] == "ERROR":
                raise RimuHostingException(js[js.keys()[0]]['human_readable_message'])
            return js[js.keys()[0]]
        except ValueError:
            raise RimuHostingException('Could not parse body: %s' % (self.body))
        except KeyError:
            raise RimuHostingException('Could not parse body: %s' % (self.body))
    
class RimuHostingConnection(ConnectionKey):
    
    api_context = API_CONTEXT
    host = API_HOST
    port = API_PORT
    responseCls = RimuHostingResponse
    
    def __init__(self, key, secure=True):
        # override __init__ so that we can set secure of False for testing
        ConnectionKey.__init__(self,key,secure)

    def add_default_headers(self, headers):
        # We want JSON back from the server. Could be application/xml (but JSON
        # is better).
        headers['Accept'] = 'application/json'
        # Must encode all data as json, or override this header.
        headers['Content-Type'] = 'application/json'
      
        headers['Authorization'] = 'rimuhosting apikey=%s' % (self.key)
        return headers;

    def request(self, action, params={}, data='', headers={}, method='GET'):
        # Override this method to prepend the api_context
        return ConnectionKey.request(self, self.api_context + action, params, data, headers, method)

class RimuHostingNodeDriver(NodeDriver):
    type = Provider.RIMUHOSTING
    name = 'RimuHosting'
    connectionCls = RimuHostingConnection
    
    def __init__(self, key, host=API_HOST, port=API_PORT, api_context=API_CONTEXT, secure=API_SECURE):
        # Pass in some extra vars so that
        self.key = key
        self.secure = secure
        self.connection = self.connectionCls(key ,secure)
        self.connection.host = host
        self.connection.api_context = api_context
        self.connection.port = port
        self.connection.driver = self
        self.connection.connect()

    def _order_uri(self, node,resource):
        # Returns the order uri with its resourse appended.
        return "/orders/%s/%s" % (node.slug,resource)
   
    # TODO: Get the node state.
    def _to_node(self, order):
        n = Node(id=order['order_oid'],
                name=order['domain_name'],
                state=NodeState.RUNNING,
                public_ip=[order['allocated_ips']['primary_ip']]+order['allocated_ips']['secondary_ips'],
                private_ip=None,
                driver=self.connection.driver)
        n.slug = order['slug']
        return n

    def _to_size(self,plan):
        return NodeSize(id=plan['pricing_plan_code'],
            name=plan['pricing_plan_description'],
            ram=plan['minimum_memory_mb'],
            disk=plan['minimum_disk_gb'],
            bandwidth=plan['minimum_data_transfer_allowance_gb'],
            price=plan['monthly_recurring_fee_usd'],
            driver=self.connection.driver)
                
    def _to_image(self,image):
        return NodeImage(id=image['distro_code'],
            name=image['distro_description'],
            driver=self.connection.driver)
        
    def list_sizes(self):
        # Returns a list of sizes (aka plans)
        # Get plans. Note this is really just for libcloud. We are happy with any size.
        res = self.connection.request('/pricing-plans;server-type=VPS').object
        return map(lambda x : self._to_size(x), res['pricing_plan_infos'])

    def list_nodes(self):
        # Returns a list of Nodes
        # Will only include active ones.
        res = self.connection.request('/orders;include_inactive=N').object
        return map(lambda x : self._to_node(x), res['about_orders'])
    
    def list_images(self):
        # Get all base images.
        # TODO: add other image sources. (Such as a backup of a VPS)
        res = self.connection.request('/distributions').object
        return map(lambda x : self._to_image(x), res['distro_infos'])

    def reboot_node(self, node):
        # Reboot
        # PUT the state of RESTARTING to restart a VPS.
        # All data is encoded as JSON
        data = {'reboot_request':{'running_state':'RESTARTING'}}
        uri = self._order_uri(node,'vps/running-state')
        self.connection.request(uri,data=json.dumps(data),method='PUT')
        # XXX check that the response was actually successful
        return True
    
    def destroy_node(self, node):
        # Shutdown a VPS.
        uri = self._order_uri(node,'vps')
        self.connection.request(uri,method='DELETE')
        # XXX check that the response was actually successful
        return True

    def create_node(self, name, image, size, **kwargs):
        # Creates a RimuHosting instance
        #
        #   name    Must be a FQDN. e.g example.com.
        #   image   NodeImage from list_images
        #   size    NodeSize from list_sizes
        #
        # Keyword arguements supported:
        #
        #   billing_oid             If not set, a billing method is automatically picked.
        #   host_server_oid         The host server to set the VPS up on.
        #   vps_order_oid_to_clone  Clone another VPS to use as the image for the new VPS.
        #  
        #   num_ips = 1         Number of IPs to allocate. Defaults to 1.
        #   extra_ip_reason     Reason for needing the extra IPS.
        #   
        #   memory_mb           Memory to allocate to the VPS.
        #   disk_space_mb=4096  Diskspace to allocate to the VPS. Default is 4GB.
        #   disk_space_2_mb     Secondary disk size allocation. Disabled by default.
        #   
        #   pricing_plan_code       Plan from list_sizes
        #   
        #   control_panel       Control panel to install on the VPS.
        #   password            Password to set on the VPS.
        #
        #
        # Note we don't do much error checking in this because we the API to error out if there is a problem.  
        data = {
            'instantiation_options':{'domain_name': name, 'distro': image.id},
            'pricing_plan_code': size.id,
        }
        
        if kwargs.has_key('control_panel'):
            data['instantiation_options']['control_panel'] = kwargs['control_panel']
        

        if kwargs.has_key('password'):
            data['instantiation_options']['password'] = kwargs['password']
        
        if kwargs.has_key('billing_oid'):
            #TODO check for valid oid.
            data['billing_oid'] = kwargs['billing_oid']
        
        if kwargs.has_key('host_server_oid'):
            data['host_server_oid'] = kwargs['host_server_oid']
            
        if kwargs.has_key('vps_order_oid_to_clone'):
            data['vps_order_oid_to_clone'] = kwargs['vps_order_oid_to_clone']
        
        if kwargs.has_key('num_ips') and int(kwargs['num_ips']) > 1:
            if not kwargs.has_key('extra_ip_reason'):
                raise RimuHostingException('Need an reason for having an extra IP')
            else:
                if not data.has_key('ip_request'):
                    data['ip_request'] = {}
                data['ip_request']['num_ips'] = int(kwargs['num_ips'])
                data['ip_request']['extra_ip_reason'] = kwargs['extra_ip_reason']
        
        if kwargs.has_key('memory_mb'):
            if not data.has_key('vps_parameters'):
                data['vps_parameters'] = {}
            data['vps_parameters']['memory_mb'] = kwargs['memory_mb']
        
        if kwargs.has_key('disk_space_mb'):
            if not data.has_key('vps_parameters'):
                data['vps_parameters'] = {}
            data['vps_parameters']['disk_space_mb'] = kwargs['disk_space_mb']
        
        if kwargs.has_key('disk_space_2_mb'):
            if not data.has_key('vps_parameters'):
                data['vps_parameters'] = {}
            data['vps_parameters']['disk_space_2_mb'] = kwargs['disk_space_2_mb']
        
        
        res = self.connection.request('/orders/new-vps', method='POST', data=json.dumps({"new-vps":data})).object
        return self._to_node(res['about_order'])
    
        
