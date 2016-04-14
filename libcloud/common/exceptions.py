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
    'BaseHTTPError',
    'RateLimitReachedError',

    'exception_from_message'
]


class BaseHTTPError(Exception):

    """
    The base exception class for all HTTP related exceptions.
    """

    def __init__(self, code, message, headers=None):
        self.code = code
        self.message = message
        self.headers = headers
        # preserve old exception behavior for tests that
        # look for e.args[0]
        super(BaseHTTPError, self).__init__(message)

    def __str__(self):
        return self.message


class RateLimitReachedError(BaseHTTPError):
    """
    HTTP 429 - Rate limit: you've sent too many requests for this time period.
    """
    code = 429
    message = '%s Rate limit exceeded' % (code)

    def __init__(self, *args, **kwargs):
        self.retry_after = int(kwargs.pop('retry_after', 0))


_error_classes = [RateLimitReachedError]
_code_map = dict((c.code, c) for c in _error_classes)


def exception_from_message(code, message, headers=None):
    """
    Return an instance of BaseHTTPException or subclass based on response code.

    Usage::
        raise exception_from_message(code=self.status,
                                     message=self.parse_error())
    """
    kwargs = {
        'code': code,
        'message': message,
        'headers': headers
    }

    if headers and 'retry_after' in headers:
        kwargs['retry_after'] = headers['retry_after']

    cls = _code_map.get(code, BaseHTTPError)
    return cls(**kwargs)
