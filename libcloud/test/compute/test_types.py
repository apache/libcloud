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

import sys
import unittest

from unittest import TestCase

from libcloud.compute.types import Provider, NodeState, StorageVolumeState, \
    VolumeSnapshotState, Type


class TestType(Type):
    INUSE = "inuse"
    NOTINUSE = "NOTINUSE"


class TestTestType(TestCase):
    model = TestType

    def test_provider_tostring(self):
        self.assertEqual(Provider.tostring(TestType.INUSE), "INUSE")
        self.assertEqual(Provider.tostring(TestType.NOTINUSE), "NOTINUSE")

    def test_provider_fromstring(self):
        self.assertEqual(TestType.fromstring("inuse"), TestType.INUSE)
        self.assertEqual(TestType.fromstring("NOTINUSE"), TestType.NOTINUSE)

    def test_provider_fromstring_caseinsensitive(self):
        self.assertEqual(TestType.fromstring("INUSE"), TestType.INUSE)
        self.assertEqual(TestType.fromstring("notinuse"), TestType.NOTINUSE)

    def test_compare_as_string(self):
        self.assertTrue(TestType.INUSE == 'inuse')
        self.assertFalse(TestType.INUSE == 'bar')


class TestProvider(TestCase):

    def test_provider_tostring(self):
        self.assertEqual(Provider.tostring(Provider.RACKSPACE), "RACKSPACE")

    def test_provider_fromstring(self):
        self.assertEqual(Provider.fromstring("rackspace"), Provider.RACKSPACE)


class TestNodeState(TestCase):

    def test_nodestate_tostring(self):
        self.assertEqual(NodeState.tostring(NodeState.RUNNING), "RUNNING")

    def test_nodestate_fromstring(self):
        self.assertEqual(NodeState.fromstring("running"), NodeState.RUNNING)


class TestStorageVolumeState(TestCase):

    def test_storagevolumestate_tostring(self):
        self.assertEqual(
            StorageVolumeState.tostring(StorageVolumeState.AVAILABLE),
            "AVAILABLE"
        )

    def test_storagevolumestate_fromstring(self):
        self.assertEqual(
            StorageVolumeState.fromstring("available"),
            StorageVolumeState.AVAILABLE
        )


class TestVolumeSnapshotState(TestCase):

    def test_volumesnapshotstate_tostring(self):
        self.assertEqual(
            VolumeSnapshotState.tostring(VolumeSnapshotState.AVAILABLE),
            "AVAILABLE"
        )

    def test_volumesnapshotstate_fromstring(self):
        self.assertEqual(
            VolumeSnapshotState.fromstring("available"),
            VolumeSnapshotState.AVAILABLE
        )


if __name__ == '__main__':
    sys.exit(unittest.main())
