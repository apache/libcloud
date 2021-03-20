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
import string
import sys
import unittest

from integration.storage.base import Integration, random_string


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


if __name__ == '__main__':
    sys.exit(unittest.main())
