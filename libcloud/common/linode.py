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

from libcloud.utils.py3 import httplib
from libcloud.common.base import JsonResponse, ConnectionKey
from libcloud.common.gandi import BaseObject
from libcloud.common.types import LibcloudError, InvalidCredsError

__all__ = [
    "API_HOST",
    "DEFAULT_API_VERSION",
    "LinodeResponseV4",
    "LinodeConnectionV4",
    "LinodeExceptionV4",
    "LinodeDisk",
    "LinodeIPAddress",
]

# Endpoint for the Linode API
API_HOST = "api.linode.com"

DEFAULT_API_VERSION = "4.0"

# Available filesystems for disk creation
LINODE_DISK_FILESYSTEMS_V4 = ["ext3", "ext4", "swap", "raw", "initrd"]


class LinodeExceptionV4(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "%s" % self.message

    def __repr__(self):
        return "<LinodeExceptionV4 '%s'>" % self.message


class LinodeResponseV4(JsonResponse):
    valid_response_codes = [
        httplib.OK,
        httplib.NO_CONTENT,
    ]

    def parse_body(self):
        """Parse the body of the response into JSON objects
        :return: ``dict`` of objects"""
        return super().parse_body()

    def parse_error(self):
        """
        Parse the error body and raise the appropriate exception
        """
        status = int(self.status)
        data = self.parse_body()
        # Use only the first error, as there'll be only one most of the time
        error = data["errors"][0]
        reason = error.get("reason")
        # The field in the request that caused this error
        field = error.get("field")

        if field is not None:
            error_msg = "{}-{}".format(reason, field)
        else:
            error_msg = reason

        if status in [httplib.UNAUTHORIZED, httplib.FORBIDDEN]:
            raise InvalidCredsError(value=error_msg)

        raise LibcloudError(
            "%s Status code: %d." % (error_msg, status), driver=self.connection.driver
        )

    def success(self):
        """Check the response for success
        :return: ``bool`` indicating a successful request"""
        return self.status in self.valid_response_codes


class LinodeConnectionV4(ConnectionKey):
    """
    A connection to the Linode API

    Wraps SSL connections to the Linode API
    """

    host = API_HOST
    responseCls = LinodeResponseV4

    def add_default_headers(self, headers):
        """
        Add headers that are necessary for every request

        This method adds ``token`` to the request.
        """
        headers["Authorization"] = "Bearer %s" % (self.key)
        headers["Content-Type"] = "application/json"
        return headers

    def add_default_params(self, params):
        """
        Add parameters that are necessary for every request

        This method adds ``page_size`` to the request to reduce the total
        number of paginated requests to the API.
        """
        # pylint: disable=maybe-no-member
        params["page_size"] = 25
        return params


class LinodeDisk(BaseObject):
    def __init__(self, id, state, name, filesystem, driver, size, extra=None):
        super().__init__(id, state, driver)
        self.name = name
        self.size = size
        self.filesystem = filesystem
        self.extra = extra or {}

    def __repr__(self):
        return (
            "<LinodeDisk: id=%s, name=%s, state=%s, size=%s," " filesystem=%s, driver=%s ...>"
        ) % (
            self.id,
            self.name,
            self.state,
            self.size,
            self.filesystem,
            self.driver.name,
        )


class LinodeIPAddress:
    def __init__(self, inet, public, version, driver, extra=None):
        self.inet = inet
        self.public = public
        self.version = version
        self.driver = driver
        self.extra = extra or {}

    def __repr__(self):
        return ("<IPAddress: address=%s, public=%r, version=%s, driver=%s ...>") % (
            self.inet,
            self.public,
            self.version,
            self.driver.name,
        )
