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

import asyncio
import aiohttp

from libcloud.connection import LibcloudConnection


class LibcloudAsyncConnection(LibcloudConnection):
    """
    An asynchronous connection object
    """
    def __init__(self, loop=None, *args, **kwargs):
        super(LibcloudAsyncConnection, self).__init__(*args, **kwargs)
        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()

    async def request_async(self, method, url, body=None,
                            headers=None, raw=False,
                            stream=False):
        url = urlparse.urljoin(self.host, url)
        async with aiohttp.ClientSession(loop=self.loop) as client:
            async with client.get(url) as resp:
                return await resp
