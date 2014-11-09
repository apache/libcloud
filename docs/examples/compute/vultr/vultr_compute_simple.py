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

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
import libcloud.security
libcloud.security.VERIFY_SSL_CERT = False

VULTR = get_driver(Provider.VULTR)

driver = VULTR("your api key")

nodes = driver.list_nodes()
locations = driver.list_locations()
sizes = driver.list_sizes()
images = driver.list_images()

print nodes
print locations
print sizes
print images
