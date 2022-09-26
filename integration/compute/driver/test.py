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
from libcloud.common.base import JsonResponse, ConnectionUserAndKey
from libcloud.compute.base import Node, NodeDriver


class TestResponseType(JsonResponse):
    pass


class TestConnection(ConnectionUserAndKey):
    host = "localhost"
    secure = True
    responseCls = TestResponseType

    allow_insecure = True

    def __init__(
        self,
        user_id,
        key,
        secure=True,
        host=None,
        port=None,
        url=None,
        timeout=None,
        proxy_url=None,
        api_version=None,
        **conn_kwargs,
    ):
        super().__init__(
            user_id=user_id,
            key=key,
            secure=secure,
            host=host,
            port=port,
            url=url,
            timeout=timeout,
            proxy_url=proxy_url,
        )

    def add_default_headers(self, headers):
        user_b64 = base64.b64encode(b("{}:{}".format(self.user_id, self.key)))
        headers["Authorization"] = "Basic %s" % (user_b64)
        return headers


class TestNodeDriver(NodeDriver):
    connectionCls = TestConnection
    type = "testing"
    api_name = "testing"
    name = "Test Compute Driver"
    website = "http://libcloud.apache.org"
    features = {"create_node": ["ssh_key", "password"]}

    def __init__(self, key, secret=None, secure=True, host=None, port=None, **kwargs):
        super().__init__(key=key, secret=secret, secure=secure, host=host, port=port, **kwargs)

    def list_nodes(self):
        r = self.connection.request("/compute/nodes")
        nodes = []
        for node in r.object:
            nodes.append(Node(driver=self, **node))
        return nodes

    def ex_report_data(self):
        r = self.connection.request("/compute/report_data", raw=True)
        return r.response.read()
