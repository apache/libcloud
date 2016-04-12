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

from libcloud.compute.providers import Provider
from libcloud.common.dimensiondata import (DimensionDataConnection,
                                           API_ENDPOINTS)
from libcloud.compute.drivers.dimensiondata import DimensionDataNodeDriver

DEFAULT_REGION = 'bsnl-in'


class BSNLNodeDriver(DimensionDataNodeDriver):
    """
    BSNL node driver, based on Dimension Data driver
    """

    selected_region = None
    connectionCls = DimensionDataConnection
    name = 'BSNL'
    website = 'http://www.bsnlcloud.com/'
    type = Provider.BSNL
    features = {'create_node': ['password']}
    api_version = 1.0

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=None, region=DEFAULT_REGION, **kwargs):

        if region not in API_ENDPOINTS:
            raise ValueError('Invalid region: %s' % (region))

        self.selected_region = API_ENDPOINTS[region]

        super(BSNLNodeDriver, self).__init__(
            key=key,
            secret=secret,
            secure=secure,
            host=host,
            port=port,
            api_version=api_version,
            region=region,
            **kwargs)
