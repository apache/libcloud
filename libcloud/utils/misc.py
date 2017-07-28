# -*- coding: utf-8 -*-
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
from __future__ import absolute_import, division

import binascii
import collections
import itertools
import logging
import os
import socket
import ssl
import sys
import time
from datetime import datetime
from datetime import timedelta
from functools import wraps

from libcloud.common.exceptions import RateLimitReachedError
from libcloud.common.providers import get_driver as _get_driver
from libcloud.common.providers import set_driver as _set_driver
from libcloud.utils.py3 import httplib

__all__ = [
    'find',
    'get_driver',
    'set_driver',
    'merge_valid_keys',
    'get_new_obj',
    'str2dicts',
    'dict2str',
    'reverse_dict',
    'lowercase_keys',
    'get_secure_random_string',
    'retry',

    'ReprMixin'
]

# Error message which indicates a transient SSL error upon which request
# can be retried
TRANSIENT_SSL_ERROR = 'The read operation timed out'

LOG = logging.getLogger(__name__)


class TransientSSLError(ssl.SSLError):
    """Represent transient SSL errors, e.g. timeouts"""
    pass


# Constants used by the ``retry`` decorator
DEFAULT_TIMEOUT = 30  # default retry timeout
DEFAULT_DELAY = 1  # default sleep delay used in each iterator
DEFAULT_BACKOFF = 1  # retry backup multiplier
RETRY_EXCEPTIONS = (RateLimitReachedError, socket.error, socket.gaierror,
                    httplib.NotConnected, httplib.ImproperConnectionState,
                    TransientSSLError)


def find(l, predicate):
    results = [x for x in l if predicate(x)]
    return results[0] if len(results) > 0 else None


# Note: Those are aliases for backward-compatibility for functions which have
# been moved to "libcloud.common.providers" module
get_driver = _get_driver
set_driver = _set_driver


def merge_valid_keys(params, valid_keys, extra):
    """
    Merge valid keys from extra into params dictionary and return
    dictionary with keys which have been merged.

    Note: params is modified in place.
    """
    merged = {}
    if not extra:
        return merged

    for key in valid_keys:
        if key in extra:
            params[key] = extra[key]
            merged[key] = extra[key]

    return merged


def get_new_obj(obj, klass, attributes):
    """
    Pass attributes from the existing object 'obj' and attributes
    dictionary to a 'klass' constructor.
    Attributes from 'attributes' dictionary are only passed to the
    constructor if they are not None.
    """
    kwargs = {}
    for key, value in list(obj.__dict__.items()):
        if isinstance(value, dict):
            kwargs[key] = value.copy()
        elif isinstance(value, (tuple, list)):
            kwargs[key] = value[:]
        else:
            kwargs[key] = value

    for key, value in list(attributes.items()):
        if value is None:
            continue

        if isinstance(value, dict):
            kwargs_value = kwargs.get(key, {})
            for key1, value2 in list(value.items()):
                if value2 is None:
                    continue

                kwargs_value[key1] = value2
            kwargs[key] = kwargs_value
        else:
            kwargs[key] = value

    return klass(**kwargs)


def str2dicts(data):
    """
    Create a list of dictionaries from a whitespace and newline delimited text.

    For example, this:
    cpu 1100
    ram 640

    cpu 2200
    ram 1024

    becomes:
    [{'cpu': '1100', 'ram': '640'}, {'cpu': '2200', 'ram': '1024'}]
    """
    list_data = []
    list_data.append({})
    d = list_data[-1]

    lines = data.split('\n')
    for line in lines:
        line = line.strip()

        if not line:
            d = {}
            list_data.append(d)
            d = list_data[-1]
            continue

        whitespace = line.find(' ')

        if not whitespace:
            continue

        key = line[0:whitespace]
        value = line[whitespace + 1:]
        d.update({key: value})

    list_data = [val for val in list_data if val != {}]
    return list_data


def str2list(data):
    """
    Create a list of values from a whitespace and newline delimited text
    (keys are ignored).

    For example, this:
    ip 1.2.3.4
    ip 1.2.3.5
    ip 1.2.3.6

    becomes:
    ['1.2.3.4', '1.2.3.5', '1.2.3.6']
    """
    list_data = []

    for line in data.split('\n'):
        line = line.strip()

        if not line:
            continue

        try:
            splitted = line.split(' ')
            # key = splitted[0]
            value = splitted[1]
        except Exception:
            continue

        list_data.append(value)

    return list_data


def dict2str(data):
    """
    Create a string with a whitespace and newline delimited text from a
    dictionary.

    For example, this:
    {'cpu': '1100', 'ram': '640', 'smp': 'auto'}

    becomes:
    cpu 1100
    ram 640
    smp auto

    cpu 2200
    ram 1024
    """
    result = ''
    for k in data:
        if data[k] is not None:
            result += '%s %s\n' % (str(k), str(data[k]))
        else:
            result += '%s\n' % str(k)

    return result


def reverse_dict(dictionary):
    return dict([(value, key) for key, value in list(dictionary.items())])


def lowercase_keys(dictionary):
    return dict(((k.lower(), v) for k, v in dictionary.items()))


def repeat_last(iterable):
    """
    Iterates over the sequence and repeats the last element in forever loop.

    :param iterable: The sequence to iterate on.
    :type iterable: :class:`collections.Sequence`

    :rtype: :class:`types.GeneratorType`
    """
    item = DEFAULT_DELAY
    for item in iterable:
        yield item
    while True:
        yield item


def total_seconds(td):
    """
    Total seconds in the duration.

    :type td: :class:`timedelta`
    """
    # Keep backward compatibility with Python 2.6 which
    # doesn't have this method
    if hasattr(td, 'total_seconds'):
        return td.total_seconds()
    else:
        return ((td.days * 86400 + td.seconds) * 10**6 +
                td.microseconds) / 10**6


def get_secure_random_string(size):
    """
    Return a string of ``size`` random bytes. Returned string is suitable for
    cryptographic use.

    :param size: Size of the generated string.
    :type size: ``int``

    :return: Random string.
    :rtype: ``str``
    """
    value = os.urandom(size)
    value = binascii.hexlify(value)
    value = value.decode('utf-8')[:size]
    return value


class ReprMixin(object):
    """
    Mixin class which adds __repr__ and __str__ methods for the attributes
    specified on the class.
    """

    _repr_attributes = []

    def __repr__(self):
        attributes = []
        for attribute in self._repr_attributes:
            value = getattr(self, attribute, None)
            attributes.append('%s=%s' % (attribute, value))

        values = (self.__class__.__name__, ', '.join(attributes))
        result = '<%s %s>' % values
        return result

    def __str__(self):
        return str(self.__repr__())


def retry(retry_exceptions=None, retry_delay=None, timeout=None,
          backoff=None):
    """
    Retry decorator that helps to handle common transient exceptions.

    :param retry_delay: retry delay between the attempts.
    :type retry_delay: int or :class:`collections.Sequence[int]`

    :param backoff: the denominator of a geometric progression
        (:math:`retry\_delay_n = retry\_delay × backoff^{n-1}`).
    :type backoff: int

    :param timeout: maximum time to wait.
    :type timeout: int

    :param retry_exceptions: types of exceptions to retry on.
    :type retry_exceptions: tuple of :class:`Exception`

    :Example:

    >>> retry_request = retry(
    >>>     timeout=1,
    >>>     retry_delay=1,
    >>>     backoff=1)
    >>> retry_request(connection.request)()
    """
    if retry_exceptions is None:
        retry_exceptions = RETRY_EXCEPTIONS
    if retry_delay is None or (
            isinstance(retry_delay, collections.Sequence) and
            len(retry_delay) == 0):
        retry_delay = DEFAULT_DELAY
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    if backoff is None:
        backoff = DEFAULT_BACKOFF

    timeout = max(timeout, 0)

    def transform_ssl_error(func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ssl.SSLError:
            exc = sys.exc_info()[1]

            if TRANSIENT_SSL_ERROR in str(exc):
                raise TransientSSLError(*exc.args)

            raise exc

    def decorator(func):
        @wraps(func)
        def retry_loop(*args, **kwargs):
            retry_msg = "Server returned %r, retrying request " \
                        "in %s seconds ..."
            end_time = datetime.now() + timedelta(seconds=timeout)

            if isinstance(retry_delay, collections.Sequence):
                retry_time_progression = repeat_last(retry_delay)
            else:
                retry_time_progression = (
                    retry_delay * (backoff ** i) for i in itertools.count()
                )

            for delay in retry_time_progression:
                try:
                    return transform_ssl_error(func, *args, **kwargs)
                except retry_exceptions as exc:
                    to_timeout = total_seconds(end_time - datetime.now())
                    if to_timeout <= 0:
                        raise
                    if isinstance(exc, RateLimitReachedError) \
                            and exc.retry_after:
                        LOG.debug(retry_msg, exc, exc.retry_after)
                        time.sleep(exc.retry_after)
                        return retry_loop(*args, **kwargs)
                    delay = min(delay, to_timeout)
                    LOG.debug(retry_msg, exc, delay)
                    time.sleep(delay)
        return retry_loop
    return decorator
