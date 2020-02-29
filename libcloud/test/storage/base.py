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
    'BaseRangeDownloadMockHttp'
]

from typing import Tuple

from libcloud.test import MockHttp  # pylint: disable-msg=E0611


class BaseRangeDownloadMockHttp(MockHttp):
    """
    Base MockHttp class which implements some utility methods for asserting
    range download requests.
    """

    def _get_start_and_end_bytes_from_range_str(self, range_str, body):
        # type: (str, str) -> Tuple[int, int]
        range_str = range_str.split('bytes=')[1]
        range_str = range_str.split('-')
        range_str = [value for value in range_str if value.strip()]
        start_bytes = int(range_str[0])

        if len(range_str) == 2:
            end_bytes = int(range_str[1])
        else:
            end_bytes = len(body)

        return start_bytes, end_bytes
