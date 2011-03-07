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

from libcloud.utils import get_driver as get_provider_driver
from libcloud.storage.types import Provider

DRIVERS = {
    Provider.DUMMY:
        ('libcloud.storage.drivers.dummy', 'DummyStorageDriver'),
    Provider.CLOUDFILES_US:
        ('libcloud.storage.drivers.cloudfiles', 'CloudFilesUSStorageDriver'),
    Provider.CLOUDFILES_UK:
        ('libcloud.storage.drivers.cloudfiles', 'CloudFilesUKStorageDriver'),
}

def get_driver(provider):
    return get_provider_driver(DRIVERS, provider)
