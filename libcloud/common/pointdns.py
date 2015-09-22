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
import base64
from libcloud.utils.py3 import b
from libcloud.utils.py3 import httplib

from libcloud.common.base import ConnectionUserAndKey
from libcloud.common.base import JsonResponse


class PointDNSDNSResponse(JsonResponse):

    def success(self):
        """
        Determine if our request was successful.

        The meaning of this can be arbitrary; did we receive OK status? Did
        the node get created? Were we authenticated?

        :rtype: ``bool``
        :return: ``True`` or ``False``
        """
        # response.success() only checks for 200 and 201 codes. Should we
        # add 202?
        return self.status in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]


class PointDNSConnection(ConnectionUserAndKey):
    host = 'pointhq.com'
    responseCls = PointDNSDNSResponse

    def add_default_headers(self, headers):
        """
        Add headers that are necessary for every request

        This method adds ``token`` to the request.
        """
        b64string = b('%s:%s' % (self.user_id, self.key))
        token = base64.b64encode(b64string)
        headers['Authorization'] = 'Basic %s' % token
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'
        return headers
