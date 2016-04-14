from unittest import TestCase

from libcloud.compute.types import Provider, NodeState, StorageVolumeState, \
    VolumeSnapshotState, Type


class TestType(Type):
    INUSE = "inuse"


class TestTestType(TestCase):
    model = TestType
    attribute = TestType.INUSE

    def test_provider_tostring(self):
        self.assertEqual(Provider.tostring(TestType.INUSE), "INUSE")

    def test_provider_fromstring(self):
        self.assertEqual(TestType.fromstring("inuse"), TestType.INUSE)

    def test_provider_fromstring_caseinsensitive(self):
        self.assertEqual(TestType.fromstring("INUSE"), TestType.INUSE)


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
