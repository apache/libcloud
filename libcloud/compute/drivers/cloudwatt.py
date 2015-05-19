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
Cloudwatt driver.
"""
import sys
try:
    import simplejson as json
except ImportError:
    import json
from libcloud.utils.py3 import httplib
from libcloud.compute.types import Provider
from libcloud.compute.drivers.openstack import OpenStack_1_1_Connection
from libcloud.compute.drivers.openstack import OpenStack_1_1_NodeDriver
from libcloud.common.openstack_identity import OpenStackIdentityConnection
from libcloud.utils.iso8601 import parse_date

from libcloud.compute.types import InvalidCredsError, MalformedResponseError


__all__ = [
    'CloudwattNodeDriver'
]

BASE_URL = 'https://identity.fr1.cloudwatt.com/v2.0'
AUTH_URL = BASE_URL + '/tokens'


class CloudwattAuthConnection(OpenStackIdentityConnection):
    """
    AuthConnection class for the Cloudwatt driver.
    """
    name = 'Cloudwatt Auth'

    def __init__(self, *args, **kwargs):
        self._ex_tenant_id = kwargs.pop('ex_tenant_id')
        super(CloudwattAuthConnection, self).__init__(*args, **kwargs)

    def authenticate(self, force=False):
        reqbody = json.dumps({'auth': {
            'passwordCredentials': {
                'username': self.user_id,
                'password': self.key
            },
            'tenantId': self._ex_tenant_id
        }})
        resp = self.request('/tokens', data=reqbody, headers={},
                            method='POST')

        if resp.status == httplib.UNAUTHORIZED:
            # HTTP UNAUTHORIZED (401): auth failed
            raise InvalidCredsError()
        elif resp.status != httplib.OK:
            body = 'code: %s body:%s' % (resp.status, resp.body)
            raise MalformedResponseError('Malformed response', body=body,
                                         driver=self.driver)
        else:
            try:
                body = json.loads(resp.body)
            except Exception:
                e = sys.exc_info()[1]
                raise MalformedResponseError('Failed to parse JSON', e)

            try:
                expires = body['access']['token']['expires']

                self.auth_token = body['access']['token']['id']
                self.auth_token_expires = parse_date(expires)
                self.urls = body['access']['serviceCatalog']
                self.auth_user_info = None
            except KeyError:
                e = sys.exc_info()[1]
                raise MalformedResponseError('Auth JSON response is \
                                             missing required elements', e)

        return self


class CloudwattConnection(OpenStack_1_1_Connection):
    """
    Connection class for the Cloudwatt driver.
    """
    auth_url = BASE_URL
    service_region = 'fr1'
    service_type = 'compute'

    def __init__(self, *args, **kwargs):
        self.ex_tenant_id = kwargs.pop('ex_tenant_id')
        super(CloudwattConnection, self).__init__(*args, **kwargs)
        osa = CloudwattAuthConnection(
            auth_url=AUTH_URL,
            user_id=self.user_id,
            key=self.key,
            tenant_name=self._ex_tenant_name,
            timeout=self.timeout,
            ex_tenant_id=self.ex_tenant_id,
            parent_conn=self
        )
        self._osa = osa
        self._auth_version = '2.0'


class CloudwattNodeDriver(OpenStack_1_1_NodeDriver):
    """
    Implements the :class:`NodeDriver`'s for Cloudwatt.
    """
    name = 'Cloudwatt'
    website = 'https://www.cloudwatt.com/'
    connectionCls = CloudwattConnection
    type = Provider.CLOUDWATT

    def __init__(self, key, secret, tenant_id, secure=True, tenant_name=None,
                 host=None, port=None, **kwargs):
        """
        @inherits:  :class:`NodeDriver.__init__`

        :param tenant_id: ID of tenant required for Cloudwatt auth
        :type tenant_id: ``str``
        """
        self.ex_tenant_id = tenant_id
        self.extra = {}
        super(CloudwattNodeDriver, self).__init__(
            key=key,
            secret=secret,
            secure=secure,
            host=host,
            port=port,
            **kwargs
        )

    def attach_volume(self, node, volume, device=None):
        return super(CloudwattNodeDriver, self)\
            .attach_volume(node, volume, device)

    def _ex_connection_class_kwargs(self):
        """
        Includes ``tenant_id`` in Connection.
        """
        return {
            'ex_tenant_id': self.ex_tenant_id
        }
