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

from libcloud.common.base import ConnectionUserAndKey, BaseDriver

__all__ = [
    'BackupDriver'
]


class BackupDriver(BaseDriver):
    """
    A base BackupDriver class to derive from

    This class is always subclassed by a specific driver.
    """
    connectionCls = ConnectionUserAndKey
    name = None
    website = None

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 **kwargs):
        """
        :param    key: API key or username to used (required)
        :type     key: ``str``

        :param    secret: Secret password to be used (required)
        :type     secret: ``str``

        :param    secure: Whether to use HTTPS or HTTP. Note: Some providers
                only support HTTPS, and it is on by default.
        :type     secure: ``bool``

        :param    host: Override hostname used for connections.
        :type     host: ``str``

        :param    port: Override port used for connections.
        :type     port: ``int``

        :return: ``None``
        """
        super(BackupDriver, self).__init__(key=key, secret=secret,
                                           secure=secure, host=host, port=port,
                                           **kwargs)
