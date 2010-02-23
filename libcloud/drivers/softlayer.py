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
Softlayer driver
"""

import xmlrpclib

import libcloud
from libcloud.types import NodeState, InvalidCredsException, Provider
from libcloud.base import ConnectionUserAndKey, Response, NodeDriver, Node
from libcloud.base import NodeSize, NodeImage, NodeLocation

API_PREFIX = "http://api.service.softlayer.com/xmlrpc/v3"

class SoftLayerTransport(xmlrpclib.Transport):
    user_agent = "libcloud/%s (SoftLayer)" % libcloud.__version__
#   def request(self, host, handler, request_body, verbose=0):
#        print request_body
#        xmlrpclib.Transport.request(self, host, handler, request_body, verbose)

 #   def _parse_response(self, file, sock):
 #       print file.read()
 #       xmlrpclib.Transport.request(self, file, sock)

class SoftLayerProxy(xmlrpclib.ServerProxy):
    def __init__(self, service, verbose=1):
        xmlrpclib.ServerProxy.__init__(
            self,
            uri="%s/%s" % (API_PREFIX, service),
            transport=SoftLayerTransport(use_datetime=0),
            verbose=verbose
        )

class SoftLayerConnection(object):
    driver = None

    def __init__(self, user, key):
        self.user = user
        self.key = key 

    def request(self, service, method, *args):
        sl = SoftLayerProxy(service, 1)
        params = [self._get_auth_param(service)] + list(args)
        return getattr(sl, method)(*params)

    def _get_auth_param(self, service, init_params=None):
        if not init_params:
            init_params = {}

        return {
            'headers': {
                'authenticate': {
                    'username': self.user,
                    'apiKey': self.key
                },
                '%sInitParameters' % service: init_params
            }
        }

class SoftLayerNodeDriver(NodeDriver):
    connectionCls = SoftLayerConnection

    def __init__(self, user, key=None, secure=False):
        self.key = key
        self.secret = secret
        self.connection = connectionCls(user, key)
        self.connection.driver = self
