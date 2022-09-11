# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the 'License'); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import time
import base64
import string
import datetime
import unittest

from integration.storage.base import Integration, random_string

try:
    from azure import identity
    from azure.mgmt import storage, resource
    from azure.mgmt.storage import models as storage_models
    from azure.mgmt.resource.resources import models as resource_models
except ImportError as e:
    print("Failed to import from azure module: %s" % (str(e)))
    identity = resource = storage = resource_models = storage_models = None


# Prefix which is added to all the groups created by tests
RESOURCE_GROUP_NAME_PREFIX = "libclouditests"
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_AZURE_LOCATION = "EastUS2"
MAX_STORAGE_ACCOUNT_NAME_LENGTH = 24


class AzuriteStorageTest(Integration.ContainerTestBase):
    provider = "azure_blobs"

    account = "devstoreaccount1"
    secret = (
        "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
    )

    image = "arafato/azurite"
    port = 10000
    environment = {"executable": "blob"}
    ready_message = b"Azure Blob Storage Emulator listening"

    has_sas_support = False

    def test_cdn_url(self):
        if not self.has_sas_support:
            self.skipTest("Storage backend has no account SAS support")


class AzuriteV3StorageTest(AzuriteStorageTest):
    image = "mcr.microsoft.com/azure-storage/azurite"
    ready_message = b"Azurite Blob service is successfully listening"

    has_sas_support = True

    def test_upload_via_stream_with_content_encoding(self):
        self.skipTest("Possible bug in AzuriteV3, see https://github.com/Azure/Azurite/issues/629")


class IotedgeStorageTest(Integration.ContainerTestBase):
    provider = "azure_blobs"

    account = random_string(10, string.ascii_lowercase)
    secret = base64.b64encode(random_string(20).encode("ascii")).decode("ascii")

    image = "mcr.microsoft.com/azure-blob-storage"
    port = 11002
    environment = {"LOCAL_STORAGE_ACCOUNT_NAME": account, "LOCAL_STORAGE_ACCOUNT_KEY": secret}
    ready_message = b"BlobService - StartAsync completed"


class StorageTest(Integration.TestBase):
    provider = "azure_blobs"

    kind = storage_models.Kind.STORAGE
    access_tier = None  # type: storage_models.AccessTier

    @classmethod
    def setUpClass(cls):
        if identity is None:
            raise unittest.SkipTest("missing azure-identity library")

        if resource is None or resource_models is None:
            raise unittest.SkipTest("missing azure-mgmt-resource library")

        if storage is None or storage_models is None:
            raise unittest.SkipTest("missing azure-mgmt-storage library")

        config = {
            key: os.getenv(key)
            for key in (
                "AZURE_TENANT_ID",
                "AZURE_SUBSCRIPTION_ID",
                "AZURE_CLIENT_ID",
                "AZURE_CLIENT_SECRET",
            )
        }

        for key, value in config.items():
            if not value:
                raise unittest.SkipTest("missing environment variable %s" % key)

        credentials = identity.ClientSecretCredential(
            tenant_id=config["AZURE_TENANT_ID"],
            client_id=config["AZURE_CLIENT_ID"],
            client_secret=config["AZURE_CLIENT_SECRET"],
        )

        resource_client = resource.ResourceManagementClient(
            credentials,
            config["AZURE_SUBSCRIPTION_ID"],
        )

        storage_client = storage.StorageManagementClient(
            credentials,
            config["AZURE_SUBSCRIPTION_ID"],
        )

        location = os.getenv("AZURE_LOCATION", DEFAULT_AZURE_LOCATION)
        name = RESOURCE_GROUP_NAME_PREFIX
        name += random_string(MAX_STORAGE_ACCOUNT_NAME_LENGTH - len(name))
        timeout = float(os.getenv("AZURE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))

        # We clean up any left over resource groups from previous runs on setUpClass. If tests on
        # CI get terminated non-gracefully, old resources will be left laying around and we want
        # to clean those up to ensure we dont hit any limits.
        # To avoid deleting groups from concurrent runs, we only delete resources older than a
        # couple (6) of hours
        print("Checking and cleaning up any old stray resource groups...")

        resource_groups = resource_client.resource_groups.list()
        now_ts = int(time.time())
        delete_threshold_ts = now_ts - int(datetime.timedelta(hours=6).total_seconds())

        for resource_group in resource_groups:
            resource_create_ts = int(resource_group.tags.get("create_ts", now_ts))

            if (
                resource_group.name.startswith(RESOURCE_GROUP_NAME_PREFIX)
                and resource_group.location.lower() == location.lower()
                and "test" in resource_group.tags
                and resource_create_ts <= delete_threshold_ts
            ):
                assert resource_group.name.startswith(RESOURCE_GROUP_NAME_PREFIX)
                print("Deleting old stray resource group: %s..." % (resource_group.name))

                try:
                    resource_client.resource_groups.begin_delete(resource_group.name)
                except Exception as e:
                    print("Failed to delete resource group: %s" % (str(e)), file=sys.stderr)

        group = resource_client.resource_groups.create_or_update(
            resource_group_name=name,
            parameters=resource_models.ResourceGroup(
                location=location,
                tags={
                    "test": cls.__name__,
                    "create_ts": str(now_ts),
                    "gh_run_id": os.getenv("GITHUB_RUN_ID", "unknown"),
                    "gh_job_id": os.getenv("GITHUB_JOB_ID", "unknown"),
                    "gh_sha": os.getenv("GITHUB_SHA", "unknown"),
                    "gh_ref": os.getenv("GITHUB_REF", "unknown"),
                },
            ),
            timeout=timeout,
        )

        cls.addClassCleanup(
            lambda: resource_client.resource_groups.begin_delete(group.name).result(timeout)
        )

        account = storage_client.storage_accounts.begin_create(
            resource_group_name=group.name,
            account_name=name,
            parameters=storage_models.StorageAccountCreateParameters(
                sku=storage_models.Sku(name=storage_models.SkuName.STANDARD_LRS),
                access_tier=cls.access_tier,
                kind=cls.kind,
                location=location,
            ),
        ).result(timeout)

        keys = storage_client.storage_accounts.list_keys(
            resource_group_name=group.name,
            account_name=account.name,
            timeout=timeout,
        )

        cls.account = account.name
        cls.secret = keys.keys[0].value


class StorageV2Test(StorageTest):
    kind = storage_models.Kind.STORAGE_V2


class BlobStorageTest(StorageTest):
    kind = storage_models.Kind.BLOB_STORAGE
    access_tier = storage_models.AccessTier.HOT


if __name__ == "__main__":
    sys.exit(unittest.main())
