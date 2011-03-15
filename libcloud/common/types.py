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

__all__ = [
    "LibcloudError",
    "MalformedResponseError",
    "InvalidCredsError",
    "InvalidCredsException"
    ]

class LibcloudError(Exception):
    """The base class for other libcloud exceptions"""

    def __init__(self, value, driver=None):
        self.value = value
        self.driver = driver

    def __str__(self):
        return ("<LibcloudError in "
                + repr(self.driver)
                +" "
                + repr(self.value) + ">")

class MalformedResponseError(LibcloudError):
    """Exception for the cases when a provider returns a malformed
    response, e.g. you request JSON and provider returns
    '<h3>something</h3>' due to some error on their side."""

    def __init__(self, value, body=None, driver=None):
        self.value = value
        self.driver = driver
        self.body = body

    def __str__(self):
        return ("<MalformedResponseException in "
                + repr(self.driver)
                + " "
                + repr(self.value)
                + ">: "
                + repr(self.body))

class InvalidCredsError(LibcloudError):
    """Exception used when invalid credentials are used on a provider."""

    def __init__(self, value='Invalid credentials with the provider',
                 driver=None):
        self.value = value
        self.driver = driver
    def __str__(self):
        return repr(self.value)

# Deprecated alias of L{InvalidCredsError}
InvalidCredsException = InvalidCredsError
