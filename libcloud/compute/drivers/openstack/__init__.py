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
OpenStack Nova driver base class and factory.
"""

from libcloud.compute.types import Provider
from libcloud.compute.base import NodeState, NodeDriver


class OpenStackNodeDriverBase(NodeDriver):

    name = 'OpenStack'
    api_name = 'openstack'
    type = Provider.OPENSTACK
    _auth_url = None
    features = {
        'create_node': ['generates_password'],
    }

    NODE_STATE_MAP = {
        'BUILD': NodeState.PENDING,
        'REBUILD': NodeState.PENDING,
        'ACTIVE': NodeState.RUNNING,
        'SUSPENDED': NodeState.TERMINATED,
        'QUEUE_RESIZE': NodeState.PENDING,
        'PREP_RESIZE': NodeState.PENDING,
        'VERIFY_RESIZE': NodeState.RUNNING,
        'PASSWORD': NodeState.PENDING,
        'RESCUE': NodeState.PENDING,
        'REBUILD': NodeState.PENDING,
        'REBOOT': NodeState.REBOOTING,
        'HARD_REBOOT': NodeState.REBOOTING,
        'SHARE_IP': NodeState.PENDING,
        'SHARE_IP_NO_CONFIG': NodeState.PENDING,
        'DELETE_IP': NodeState.PENDING,
        'UNKNOWN': NodeState.UNKNOWN,
    }

    def __init__(self, username, api_key, ex_force_base_url=None):
        self._ex_force_base_url = ex_force_base_url
        NodeDriver.__init__(self, username, secret=api_key)

    def _ex_connection_class_kwargs(self):
        kwargs = {}
        if self._ex_force_base_url:
            kwargs['ex_force_base_url'] = self._ex_force_base_url
        return kwargs
