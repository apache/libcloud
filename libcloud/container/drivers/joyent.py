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


from libcloud.container.providers import Provider

from libcloud.container.drivers.docker import (DockerContainerDriver,
                                               DockerConnection)


class JoyentContainerDriver(DockerContainerDriver):
    """
    Joyent Triton container driver class.

    >>> from libcloud.container.providers import get_driver
    >>> driver = get_driver('joyent')
    >>> conn = driver(host='https://us-east-1.docker.joyent.com',
        port=2376, key_file='key.pem', cert_file='cert.pem')
    """

    type = Provider.JOYENT
    name = 'Joyent Triton'
    website = 'http://joyent.com'
    connectionCls = DockerConnection
    supports_clusters = False

    def __init__(self, key=None, secret=None, secure=False, host='localhost',
                 port=2376, key_file=None, cert_file=None):

        super(JoyentContainerDriver, self).__init__(key=key, secret=secret,
                                                    secure=secure, host=host,
                                                    port=port,
                                                    key_file=key_file,
                                                    cert_file=cert_file)
        if host.startswith('https://'):
            secure = True

        # strip the prefix
        prefixes = ['http://', 'https://']
        for prefix in prefixes:
            if host.startswith(prefix):
                host = host.strip(prefix)

        if key_file or cert_file:
            # docker tls authentication-
            # https://docs.docker.com/articles/https/
            # We pass two files, a key_file with the
            # private key and cert_file with the certificate
            # libcloud will handle them through LibcloudHTTPSConnection
            if not (key_file and cert_file):
                raise Exception(
                    'Needs both private key file and '
                    'certificate file for tls authentication')
            self.connection.key_file = key_file
            self.connection.cert_file = cert_file
            self.connection.secure = True
        else:
            self.connection.secure = secure

        self.connection.host = host
        self.connection.port = port
