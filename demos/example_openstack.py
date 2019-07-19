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

from pprint import pprint

from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

Openstack = get_driver(Provider.OPENSTACK)

con = Openstack(
    'admin', 'password',
    ex_force_auth_url='http://23.12.198.36/identity/v3/auth/tokens',
    ex_force_base_url='http://23.12.198.36:8774/v2.1',
    api_version='2.0',
    ex_tenant_name='demo')

pprint(con.list_locations())
pprint(con.list_images())
pprint(con.list_nodes())
