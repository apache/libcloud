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

import base64
import os
import string
import sys
import unittest

try:
    from azure import identity
    from azure.mgmt import resource
    from azure.mgmt import storage
    from azure.mgmt.resource.resources import models as resource_models
    from azure.mgmt.storage import models as storage_models
except ImportError:
    identity = resource = storage = resource_models = storage_models = None

from integration.storage.base import Integration, random_string

DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_AZURE_LOCATION = 'EastUS2'
MAX_STORAGE_ACCOUNT_NAME_LENGTH = 24


class AzuriteStorageTest(Integration.ContainerTestBase):
    provider = 'azure_blobs'

    account = 'devstoreaccount1'
    secret = 'Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=='

    image = 'arafato/azurite'
    port = 10000
    environment = {'executable': 'blob'}
    ready_message = b'Azure Blob Storage Emulator listening'

    has_sas_support = False

    def test_cdn_url(self):
        if not self.has_sas_support:
            self.skipTest('Storage backend has no account SAS support')


class AzuriteV3StorageTest(AzuriteStorageTest):
    image = 'mcr.microsoft.com/azure-storage/azurite'
    ready_message = b'Azurite Blob service is successfully listening'

    has_sas_support = True

    def test_upload_via_stream_with_content_encoding(self):
        self.skipTest('Possible bug in AzuriteV3, see https://github.com/Azure/Azurite/issues/629')


class IotedgeStorageTest(Integration.ContainerTestBase):
    provider = 'azure_blobs'

    account = random_string(10, string.ascii_lowercase)
    secret = base64.b64encode(random_string(20).encode('ascii')).decode('ascii')

    image = 'mcr.microsoft.com/azure-blob-storage'
    port = 11002
    environment = {'LOCAL_STORAGE_ACCOUNT_NAME': account, 'LOCAL_STORAGE_ACCOUNT_KEY': secret}
    ready_message = b'BlobService - StartAsync completed'


class StorageTest(Integration.TestBase):
    provider = 'azure_blobs'

    kind = storage_models.Kind.STORAGE
    access_tier = None  # type: storage_models.AccessTier

    @classmethod
    def setUpClass(cls):
        if identity is None:
            raise unittest.SkipTest('missing azure-identity library')

        if resource is None or resource_models is None:
            raise unittest.SkipTest('missing azure-mgmt-resource library')

        if storage is None or storage_models is None:
            raise unittest.SkipTest('missing azure-mgmt-storage library')

        config = {
            key: os.getenv(key)
            for key in (
                'AZURE_TENANT_ID',
                'AZURE_SUBSCRIPTION_ID',
                'AZURE_CLIENT_ID',
                'AZURE_CLIENT_SECRET',
            )
        }

        for key, value in config.items():
            if not value:
                raise unittest.SkipTest('missing environment variable %s' % key)

        credentials = identity.ClientSecretCredential(
            tenant_id=config['AZURE_TENANT_ID'],
            client_id=config['AZURE_CLIENT_ID'],
            client_secret=config['AZURE_CLIENT_SECRET'],
        )

        resource_client = resource.ResourceManagementClient(
            credentials,
            config['AZURE_SUBSCRIPTION_ID'],
        )

        storage_client = storage.StorageManagementClient(
            credentials,
            config['AZURE_SUBSCRIPTION_ID'],
        )

        location = os.getenv('AZURE_LOCATION', DEFAULT_AZURE_LOCATION)
        name = 'libcloud'
        name += random_string(MAX_STORAGE_ACCOUNT_NAME_LENGTH - len(name))
        timeout = float(os.getenv('AZURE_TIMEOUT_SECONDS', DEFAULT_TIMEOUT_SECONDS))

        group = resource_client.resource_groups.create_or_update(
            resource_group_name=name,
            parameters=resource_models.ResourceGroup(
                location=location,
                tags={
                    'test': cls.__name__,
                    'run': os.getenv('GITHUB_RUN_ID', '-'),
                },
            ),
            timeout=timeout,
        )

        cls.addClassCleanup(lambda: resource_client.resource_groups
                            .begin_delete(group.name)
                            .result(timeout))

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


if __name__ == '__main__':
    sys.exit(unittest.main())
