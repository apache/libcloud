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

from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

cls = get_driver(Provider.KUBERNETES)

# You can retrieve cluster ip by running "minikube ip" command
conn = cls(key='my_token',
           host='126.32.21.4',
           ex_token_bearer_auth=True)

for cluster in conn.list_clusters():
    print(cluster.name)

for container in conn.list_containers():
    print(container.name)
