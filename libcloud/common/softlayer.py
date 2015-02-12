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
"""
Softlayer connection
"""

from libcloud.common.base import ConnectionUserAndKey
from libcloud.common.xmlrpc import XMLRPCResponse, XMLRPCConnection
from libcloud.common.types import InvalidCredsError, LibcloudError


class SoftLayerException(LibcloudError):
    """
    Exception class for SoftLayer driver
    """
    pass


class SoftLayerObjectDoesntExist(LibcloudError):
    """
    Exception class for SoftLayer driver object doesnt exist
    """
    pass


class SoftLayerResponse(XMLRPCResponse):
    defaultExceptionCls = SoftLayerException
    exceptions = {
        'SoftLayer_Account': InvalidCredsError,
        'SoftLayer_Exception_ObjectNotFound': SoftLayerObjectDoesntExist
    }


class SoftLayerConnection(XMLRPCConnection, ConnectionUserAndKey):
    responseCls = SoftLayerResponse
    host = 'api.softlayer.com'
    endpoint = '/xmlrpc/v3'

    def request(self, service, method, *args, **kwargs):
        headers = {}
        headers.update(self._get_auth_headers())
        headers.update(self._get_init_params(service, kwargs.get('id')))
        headers.update(
            self._get_object_mask(service, kwargs.get('object_mask')))
        headers.update(
            self._get_object_mask(service, kwargs.get('object_mask')))

        args = ({'headers': headers}, ) + args
        endpoint = '%s/%s' % (self.endpoint, service)
        return super(SoftLayerConnection, self).request(method, *args,
                                                        **{'endpoint':
                                                            endpoint})

    def _get_auth_headers(self):
        return {
            'authenticate': {
                'username': self.user_id,
                'apiKey': self.key
            }
        }

    def _get_init_params(self, service, id):
        if id is not None:
            return {
                '%sInitParameters' % service: {'id': id}
            }
        else:
            return {}

    def _get_object_mask(self, service, mask):
        if mask is not None:
            return {
                '%sObjectMask' % service: {'mask': mask}
            }
        else:
            return {}
