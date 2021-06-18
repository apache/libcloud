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

from typing import List
from collections import OrderedDict

import os
import binascii

from libcloud.common.providers import get_driver as _get_driver
from libcloud.common.providers import set_driver as _set_driver

# Imported for backward compatibility
# noinspection PyProtectedMember
from libcloud.utils.retry import Retry  # flake8: noqa
from libcloud.utils.retry import DEFAULT_DELAY  # noqa: F401
from libcloud.utils.retry import DEFAULT_TIMEOUT  # noqa: F401
from libcloud.utils.retry import DEFAULT_BACKOFF  # noqa: F401
from libcloud.utils.retry import TRANSIENT_SSL_ERROR  # noqa: F401
from libcloud.utils.retry import TransientSSLError  # noqa: F401

__all__ = [
    "find",
    "get_driver",
    "set_driver",
    "merge_valid_keys",
    "get_new_obj",
    "str2dicts",
    "dict2str",
    "reverse_dict",
    "lowercase_keys",
    "get_secure_random_string",
    "retry",
    "ReprMixin",
]

K8S_UNIT_MAP = OrderedDict(
    {
        "K": 1000,
        "Ki": 1024,
        "M": 1000 * 1000,
        "Mi": 1024 * 1024,
        "G": 1000 * 1000 * 1000,
        "Gi": 1024 * 1024 * 1024,
    }
)


def to_n_bytes_from_k8s_memory_size_str(k8s_memory_size_str):
    """Convert k8s memory string to number of bytes
    (e.g. '1234Mi'-> 1293942784)
    """
    if k8s_memory_size_str.startswith("0"):
        return 0
    for unit, multiplier in K8S_UNIT_MAP.items():
        if k8s_memory_size_str.endswith(unit):
            return int(k8s_memory_size_str.strip(unit)) * multiplier


def to_k8s_memory_size_str_from_n_bytes(n_bytes, unit=None):
    """Convert number of bytes to k8s memory string
    (e.g. 1293942784 -> '1234Mi')
    """
    if n_bytes == 0:
        return "0K"
    n_bytes = int(n_bytes)
    k8s_memory_size_str = None
    if unit is None:
        for unit, multiplier in reversed(K8S_UNIT_MAP.items()):
            converted_n_bytes_float = n_bytes / multiplier
            converted_n_bytes = n_bytes // multiplier
            k8s_memory_size_str = f"{converted_n_bytes}{unit}"
            if converted_n_bytes_float % 1 == 0:
                break
    elif K8S_UNIT_MAP.get(unit):
        k8s_memory_size_str = f"{n_bytes // K8S_UNIT_MAP[unit]}{unit}"
    return k8s_memory_size_str


# Error message which indicates a transient SSL error upon which request
# can be retried
TRANSIENT_SSL_ERROR = "The read operation timed out"


def find(value, predicate):
    results = [x for x in value if predicate(x)]
    return results[0] if len(results) > 0 else None


# Note: Those are aliases for backward-compatibility for functions which have
# been moved to "libcloud.common.providers" module
get_driver = _get_driver
set_driver = _set_driver
# Note: This is an alias for backward-compatibility for a function which has
# been moved to "libcloud.util.retry" module
retry = Retry


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

    lines = data.split("\n")
    for line in lines:
        line = line.strip()

        if not line:
            d = {}
            list_data.append(d)
            d = list_data[-1]
            continue

        whitespace = line.find(" ")

        if not whitespace:
            continue

        key = line[0:whitespace]
        value = line[whitespace + 1 :]
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

    for line in data.split("\n"):
        line = line.strip()

        if not line:
            continue

        try:
            splitted = line.split(" ")
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
    result = ""
    for k in data:
        if data[k] is not None:
            result += "%s %s\n" % (str(k), str(data[k]))
        else:
            result += "%s\n" % str(k)

    return result


def reverse_dict(dictionary):
    return dict([(value, key) for key, value in list(dictionary.items())])


def lowercase_keys(dictionary):
    return dict(((k.lower(), v) for k, v in dictionary.items()))


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
    value = value.decode("utf-8")[:size]
    return value


class ReprMixin(object):
    """
    Mixin class which adds __repr__ and __str__ methods for the attributes
    specified on the class.
    """

    _repr_attributes = []  # type: List[str]

    def __repr__(self):
        attributes = []
        for attribute in self._repr_attributes:
            value = getattr(self, attribute, None)
            attributes.append("%s=%s" % (attribute, value))

        values = (self.__class__.__name__, ", ".join(attributes))
        result = "<%s %s>" % values
        return result

    def __str__(self):
        return str(self.__repr__())
