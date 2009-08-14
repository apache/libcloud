#
# libcloud Linode Support
# Copyright (C) 2009 Linode, LLC.  Licensed to libcloud.org; see LICENSE.MIT.
# Maintainer: Jed Smith <jsmith@linode.com>
#
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
#
# BETA TESTING THE LINODE API AND DRIVERS
#
# A beta account that incurs no financial charge may be arranged for.  Please
# contact Jed Smith <jsmith@linode.com> for your request.
#

from libcloud.types import Provider, NodeState
from libcloud.base import ConnectionKey, Response, NodeDriver, Node
from copy import copy

# JSON is included in the standard library starting with Python 2.6.  For 2.5
# and 2.4, there's a simplejson egg at: http://pypi.python.org/pypi/simplejson
try: import json
except: import simplejson as json


# Base exception for problems arising from this driver
class LinodeException(BaseException):
    def __init__(self, code, message):
        self.code = code
        self.message = message
    def __repr__(self):
        return "<LinodeException code %u '%s'>" % (self.code, self.message)

# For beta accounts, change this to "beta.linode.com".
LINODE_API = "beta.linode.com"

# For beta accounts, change this to "/api/".
LINODE_ROOT = "/api/"


class LinodeResponse(Response):
    # Wraps a Linode API HTTP response.
    
    def __init__(self, response):
        # Given a response object, slurp the information from it.
        self.body = response.read()
        self.status = response.status
        self.headers = dict(response.getheaders())
        self.error = response.reason
        invalid = LinodeException(0xFF, "Invalid JSON received from server")
        
        # Move parse_body() to here;  we can't be sure of failure until we've
        # parsed the body into JSON.
        self.action, self.object, self.errors = self.parse_body()
        
        if not self.success():
            # Raise the first error, as there will usually only be one
            raise self.errors[0]
    
    def parse_body(self):
        # Parse the body of the response into JSON.  Will return None if the
        # JSON response chokes the parser.  Returns a triple:
        #    (action, data, errorarray)
        try:
            js = json.loads(self.body)
            if "DATA" not in js or "ERRORARRAY" not in js or "ACTION" not in js:
                return (None, None, [self.invalid])
            errs = [self._make_excp(e) for e in js["ERRORARRAY"]]
            return (js["ACTION"], js["DATA"], errs)
        except:
            # Assume invalid JSON, and use an error code unused by Linode API.
            return (None, None, [self.invalid])
    
    def parse_error(self):
        # Obtain the errors from the response.  Will always return a list.
        try:
            js = json.loads(self.body)
            if "ERRORARRAY" not in js:
                return [self.invalid]
            return [self._make_excp(e) for e in js["ERRORARRAY"]]
        except:
            return [self.invalid]
    
    def success(self):
        # Does the response indicate success?  If ERRORARRAY has more than one
        # entry, we'll say no.
        return len(self.errors) == 0
    
    def _make_excp(self, error):
        # Make an exception from an entry in ERRORARRAY.
        if "ERRORCODE" not in error or "ERRORMESSAGE" not in error:
            return None
        return LinodeException(error["ERRORCODE"], error["ERRORMESSAGE"])
        

class LinodeConnection(ConnectionKey):
    # Wraps a Linode HTTPS connection, and passes along the connection key.
    host = LINODE_API
    responseCls = LinodeResponse
    def add_default_params(self, params):
        params["api_key"] = self.key
        # Be explicit about this in case the default changes.
        params["api_responseFormat"] = "json"
        return params


class LinodeNodeDriver(NodeDriver):
    # The meat of Linode operations; the Node Driver.
    type = Provider.LINODE
    name = 'Linode'
    connectionCls = LinodeConnection

    # Converts Linode's state from DB to a NodeState constant.
    # Some of these are lightly questionable.
    LINODE_STATES = {
        -2: NodeState.UNKNOWN,              # Boot Failed
        -1: NodeState.PENDING,              # Being Created
         0: NodeState.PENDING,              # Brand New
         1: NodeState.RUNNING,              # Running
         2: NodeState.REBOOTING,            # Powered Off (TODO: Extra state?)
         3: NodeState.REBOOTING,            # Shutting Down (?)
         4: NodeState.UNKNOWN               # Reserved
    }

    def list_nodes(self):
        # List
        # Provide a list of all nodes that this API key has access to.
        params = {'api_action': 'linode.list'}
        data = self.connection.request(LINODE_ROOT, params=params).object
        return [self._to_node(n) for n in data]

    def _to_node(self, obj):
        # Convert a returned Linode instance into a Node instance.
        lid = obj["LINODEID"]
        
        # Get the IP addresses for a Linode
        params = { "api_action": "linode.ip.list", "LinodeID": lid }        
        req = self.connection.request(LINODE_ROOT, params=params)
        if not req.success() or len(req.object) == 0:
            return None
        
        # TODO: Multiple IP support.  How do we handle that case?
        public_ip = private_ip = None
        for ip in req.object:
            if ip["ISPUBLIC"]: public_ip = ip["IPADDRESS"]
            else: private_ip = ip["IPADDRESS"]

        n = Node(id=lid, name=obj["LABEL"],
            state=self.LINODE_STATES[obj["STATUS"]], public_ip=public_ip,
            private_ip=private_ip, driver=self.connection.driver)
        n.extra = copy(obj)
        return n
