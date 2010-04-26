# Licensed to the Apache Software Foundation (ASF) under one or more
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

"""
Enomaly ECP driver
"""
from libcloud.interface import INodeDriver
from libcloud.base import NodeDriver, NodeSize, NodeLocation
from libcloud.base import NodeImage, Node
from libcloud.base import Response, ConnectionUserAndKey
from libcloud.types import Provider, NodeState, InvalidCredsException
from zope.interface import implements

import uuid
import time
import base64

# JSON is included in the standard library starting with Python 2.6.  For 2.5
# and 2.4, there's a simplejson egg at: http://pypi.python.org/pypi/simplejson
try: import json
except: import simplejson as json

#Defaults
API_HOST = ''
API_PORT = (80,443)
API_SECURE = True

class ECPResponse(Response):

    #Interpret the json responses
    def parse_body(self):
        try:
            return json.loads(self.body)
        except ValueError, e:
            raise Exception("%s: %s" % (e, self.error))
            
    def getheaders(self):
        return self.headers
            
class ECPConnection(ConnectionUserAndKey):

    responseCls = ECPResponse
    host = API_HOST
    port = API_PORT
    secure = API_SECURE

    def request(self, *args, **kwargs):
        return super(ECPConnection, self).request(*args, **kwargs)
        
    def add_default_headers(self, headers):
        #Authentication
        username = self.user_id
        password = self.key
        base64string =  base64.encodestring(
                '%s:%s' % (username, password))[:-1]
        authheader =  "Basic %s" % base64string
        headers['Authorization']= authheader
        
        return headers
        
    def _encode_multipart_formdata(self, fields):
        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
        CRLF = '\r\n'
        L = []
        for i in fields.keys():
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % i)
            L.append('')
            L.append(fields[i])
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        header = {'Content-Type':content_type}
        return header, body


class ECPNodeDriver(NodeDriver):

    name = "Enomaly Elastic Computing Platform"
    type = Provider.ECP

    implements(INodeDriver)

    def __init__(self, user_name, password):
        """
        Sets the username and password on creation. Also creates the connection 
        object
        """
        self.user_name = user_name
        self.password = password
        self.connection = ECPConnection(self.user_name, self.password)
        self.connection.driver = self

    def list_nodes(self):
        """
        Returns a list of all running Nodes
        """
        
        #Make the call
        res = self.connection.request('/rest/hosting/vm/list').parse_body()
        
        #Check for application level error
        if not res['errno'] == 0:
            raise Exception('Cannot retrieve nodes list.')
        
        #Put together a list of node objects
        nodes=[]
        for vm in res['vms']:
            node = self._to_node(vm)
            if not node == None:
                nodes.append(node)
                
        #And return it
        return nodes
        

    def _to_node(self, vm):
        """
        Turns a (json) dictionary into a Node object.
        This returns only running VMs.
        """
        
        #Check state
        if not vm['state'] == "running":
            return None
        
        #IPs
        iplist = [interface['ip'] for interface in vm['interfaces']  if interface['ip'] != '127.0.0.1']
        
        #Create the node object
        n = Node(
          id=vm['uuid'],
          name=vm['name'],
          state=NodeState.RUNNING,
          public_ip=iplist,
          private_ip=iplist,
          driver=self,
        )
        
        return n

    def reboot_node(self, node):
        """
        This works by black magic.
        """
        
        #Turn the VM off
        #Black magic to make the POST requests work
        d = self.connection._encode_multipart_formdata({'action':'stop'})
        response = self.connection.request(
                   '/rest/hosting/vm/%s' % node.id, 
                   method='POST', 
                   headers=d[0], 
                   data=d[1]
        ).parse_body()
        
        #Check for application level error
        if response['errno'] == 0:
            node.state = NodeState.REBOOTING
            #Wait for it to turn off and then continue (to turn it on again)
            while node.state == NodeState.REBOOTING:
              #Check if it's off.
              response = self.connection.request(
                         '/rest/hosting/vm/%s' % node.id
                         ).parse_body()
              if response['vm']['state'] == 'off':
                node.state = NodeState.TERMINATED
              else:
                time.sleep(5)
        else:
            raise Exception('Node reboot failed due to ECP error: %s' % \
                            response['message'])
        
        
        #Turn the VM back on.
        #Black magic to make the POST requests work
        d = self.connection._encode_multipart_formdata({'action':'start'})
        response = self.connection.request(
            '/rest/hosting/vm/%s' % node.id,
            method='POST', 
            headers=d[0], 
            data=d[1]
        ).parse_body()
        
        #Check for application level error
        if response['errno'] == 0:
            node.state = NodeState.RUNNING
            return True
        else:
            raise Exception('Node reboot failed due to ECP error: %s' % \
                            response['message'])

    def destroy_node(self, node):
        """
        Shuts down and deletes a VM. Also black magic.
        """
        
        #Shut down first
        #Black magic to make the POST requests work
        d = self.connection._encode_multipart_formdata({'action':'stop'})
        response = self.connection.request(
            '/rest/hosting/vm/%s' % node.id,
            method = 'POST', 
            headers=d[0], 
            data=d[1]
        ).parse_body()
        
        #Ensure there was no applicationl level error
        if response['errno'] == 0:
            node.state = NodeState.PENDING
            #Wait for the VM to turn off before continuing
            while node.state == NodeState.PENDING:
              #Check if it's off.
              response = self.connection.request(
                         '/rest/hosting/vm/%s' % node.id
                         ).parse_body()
              if response['vm']['state'] == 'off':
                node.state = NodeState.TERMINATED
              else:
                time.sleep(5)
        else:
            raise Exception('Node destroy failed due to ECP error: %s' % \
                            response['message'])
        
        #Delete the VM
        #Black magic to make the POST requests work
        d = self.connection._encode_multipart_formdata({'action':'delete'})
        response = self.connection.request(
            '/rest/hosting/vm/%s' % (node.id), 
            method='POST', 
            headers=d[0], 
            data=d[1]
        ).parse_body()
        
        #Ensure there was no applicaiton level error
        if response['errno'] == 0:
            return True
        else:
            raise Exception('Node destroy failed due to ECP error: %s' % \
                            response['message'])

    def list_images(self, location=None):
        """
        Returns a list of all package templates aka appiances aka images
        """
        
        #Make the call
        response = self.connection.request(
            '/rest/hosting/ptemplate/list').parse_body()
        
        #Ensure there was no applicaiton level error
        if not response['errno'] == 0:
            raise Exception('Cannot get images list. Error: %s' % \
                  response['message'])
        
        #Turn the response into an array of NodeImage objects
        images = []
        for ptemplate in response['packages']:
            images.append(NodeImage(
                id=ptemplate['uuid'],
                name='%s: %s' % (ptemplate['name'], ptemplate['description']),
                driver=self,
                ))
                
        return images
    

    def list_sizes(self, location=None):
        """
        Returns a list of all hardware templates
        """
        
        #Make the call
        response = self.connection.request(
            '/rest/hosting/htemplate/list').parse_body()
        
        #Ensure there was no application level error
        if not response['errno'] == 0:
            raise Exception('Cannot get sizes list. Error: %s' % \
                            response['message'])
        
        #Turn the response into an array of NodeSize objects
        sizes = []
        for htemplate in response['templates']:
            sizes.append(NodeSize(
                id = htemplate['uuid'],
                name = htemplate['name'],
                ram = htemplate['memory'],
                disk = 0, #Disk is independent of hardware template
                bandwidth = 0, #There is no way to keep track of bandwidth
                price = 0, #The billing system is external
                driver = self,
                ))
                
        return sizes

    def list_locations(self):
        """
        This feature does not exist in ECP. Returns hard coded dummy location.
        """
        return [
          NodeLocation(id=1,
                       name="Cloud",
                       country='',
                       driver=self),
        ]

    def create_node(self, **kwargs):
        """
        Creates a virtual machine.
        
        Parameters: name (string), image (NodeImage), size (NodeSize)
        """
        
        #Find out what network to put the VM on.
        res = self.connection.request('/rest/hosting/network/list').parse_body()
        if not res['errno'] == 0:
            raise Exception('Cannot get network list. Error: %s' % \
                            res['message'])
                            
        #Use the first / default network because there is no way to specific 
        #which one
        network = res['networks'][0]['uuid']
        
        #Prepare to make the VM
        data = {
            'name' : str(kwargs['name']),
            'package' : str(kwargs['image'].id),
            'hardware' : str(kwargs['size'].id),
            'network_uuid' : str(network),
            'disk' : ''
        }
        
        #Black magic to make the POST requests work
        d = self.connection._encode_multipart_formdata(data)
        response = self.connection.request(
            '/rest/hosting/vm/', 
            method='PUT', 
            headers = d[0], 
            data=d[1]
        ).parse_body()
        
        #Check of application level error
        if not response['errno'] == 0:
            raise Exception('Cannot create Node. Error: %s' % \
                            response['message'])
        
        #Create a node object and return it.
        n = Node(
            id=response['machine_id'],
            name=data['name'],
            state=NodeState.RUNNING,
            public_ip=[],
            private_ip=[],
            driver=self,
        )
        
        return n
