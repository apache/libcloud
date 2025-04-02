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

from typing import Any, Dict, Optional

from libcloud.utils.py3 import httplib
from libcloud.common.base import JsonResponse, ConnectionKey
from libcloud.compute.base import VolumeSnapshot

__all__ = [
    "API_HOST",
    "VultrException",
    "DEFAULT_API_VERSION",
    "VultrResponseV2",
    "VultrConnectionV2",
    "VultrNetwork",
    "VultrNodeSnapshot",
]

# Endpoint for the Vultr API
API_HOST = "api.vultr.com"

DEFAULT_API_VERSION = "2"


class VultrResponseV2(JsonResponse):
    valid_response_codes = [
        httplib.OK,
        httplib.CREATED,
        httplib.ACCEPTED,
        httplib.NO_CONTENT,
    ]

    def parse_error(self):
        """
        Parse the error body and raise the appropriate exception
        """
        status = self.status
        data = self.parse_body()
        error_msg = data.get("error", "")

        raise VultrException(code=status, message=error_msg)

    def success(self):
        """Check the response for success

        :return: ``bool`` indicating a successful request
        """
        return self.status in self.valid_response_codes


class VultrConnectionV2(ConnectionKey):
    """
    A connection to the Vultr API v2
    """

    host = API_HOST
    responseCls = VultrResponseV2

    def add_default_headers(self, headers):
        headers["Authorization"] = "Bearer %s" % (self.key)
        headers["Content-Type"] = "application/json"
        return headers

    def add_default_params(self, params):
        params["per_page"] = 500
        return params


class VultrException(Exception):
    """
    Error originating from the Vultr API
    """

    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.args = (code, message)

    def __str__(self):
        return "(%u) %s" % (self.code, self.message)

    def __repr__(self):
        return "VultrException code %u '%s'" % (self.code, self.message)


class VultrNetwork:
    """
    Represents information about a Vultr private network.
    """

    def __init__(
        self,
        id: str,
        cidr_block: str,
        location: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.id = id
        self.cidr_block = cidr_block
        self.location = location
        self.extra = extra or {}

    def __repr__(self):
        return "<Vultrnetwork: id={} cidr_block={} location={}>".format(
            self.id,
            self.cidr_block,
            self.location,
        )


class VultrNodeSnapshot(VolumeSnapshot):
    def __repr__(self):
        return "<VultrNodeSnapshot id={} size={} driver={} state={}>".format(
            self.id,
            self.size,
            self.driver.name,
            self.state,
        )
