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

import datetime
import mock
import sys
import unittest

from libcloud.utils.py3 import httplib
from libcloud.compute.drivers.gce import (
    GCENodeDriver, API_VERSION, timestamp_to_datetime, GCEAddress, GCEBackend,
    GCEBackendService, GCEFirewall, GCEForwardingRule, GCEHealthCheck,
    GCENetwork, GCENodeImage, GCERoute, GCERegion, GCETargetHttpProxy,
    GCEUrlMap, GCEZone, GCESubnetwork)
from libcloud.common.google import (GoogleBaseAuthConnection,
                                    ResourceNotFoundError, ResourceExistsError,
                                    GoogleBaseError)
from libcloud.test.common.test_google import GoogleAuthMockHttp, GoogleTestCase
from libcloud.compute.base import Node, StorageVolume

from libcloud.test import MockHttp
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures

from libcloud.test.secrets import GCE_PARAMS, GCE_KEYWORD_PARAMS


class GKEContainerDriverTestCase(GoogleTestCase, TestCaseMixin):
    """
    Google Compute Engine Test Class.
    """
    # Mock out a few specific calls that interact with the user, system or
    # environment.
    GCEZone._now = lambda x: datetime.datetime(2013, 6, 26, 19, 0, 0)
    datacenter = 'us-central1-a'

    def setUp(self):
        GCEMockHttp.test = self
        GCENodeDriver.connectionCls.conn_class = GCEMockHttp
        GoogleBaseAuthConnection.conn_class = GoogleAuthMockHttp
        GCEMockHttp.type = None
        kwargs = GCE_KEYWORD_PARAMS.copy()
        kwargs['auth_type'] = 'IA'
        kwargs['datacenter'] = self.datacenter
        self.driver = GCENodeDriver(*GCE_PARAMS, **kwargs)

    def test_default_scopes(self):
        self.assertEqual(self.driver.scopes, None)
